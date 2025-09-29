# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base, get_db # get_db 现在从这里导入
from app import models, schemas, auth
from datetime import timedelta
from typing import List
import uuid
from app import models, schemas, auth, llm_service # 导入 llm_service
from fastapi import UploadFile, File, Response
from fastapi.responses import StreamingResponse
import io
from fastapi.middleware.cors import CORSMiddleware # 导入 CORSMiddleware

# 定义 OpenAPI tags metadata，用于组织 Swagger UI
tags_metadata = [
    {
        "name": "Authentication",
        "description": "Operations related to user authentication and authorization.",
    },
    {
        "name": "Users",
        "description": "Manage users in the system.",
    },
    {
        "name": "Roles",
        "description": "Manage AI role configurations.",
    },
    {
        "name": "Chats",
        "description": "Manage user chat sessions and messages.",
    },
    {
        "name": "Audio", # 新增 Audio Tag
        "description": "Operations related to Audio (ASR and TTS).",
    },
]

# 定义 Bearer Token 安全方案，用于 Swagger UI 中的授权按钮
security_definitions = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
    }
}

app = FastAPI(
    title="AI Role Playing Website API",
    description="API for an AI-powered role-playing website featuring characters like Spider-Man and a Girlfriend Trainer.",
    version="0.1.0",
    openapi_tags=tags_metadata,
    # components={"securitySchemes": security_definitions}, # 移除全局安全定义，因为它应该在 Fast API 实例中
    # security=[{"BearerAuth": []}] # 移除全局安全设置
    # swagger_ui_oauth2_redirect_url="/oauth2-redirect" # 移除此行
)

origins = [
    "http://localhost:3000",  # 允许前端应用访问的域名
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建所有数据库表
Base.metadata.create_all(bind=engine)

# 在应用启动时创建默认角色
db = SessionLocal()
try:
    models.create_default_roles(db)
finally:
    db.close()

@app.get("/", tags=["General"], include_in_schema=False)
async def read_root():
    return {"message": "Hello, FastAPI Backend!"}

@app.get("/items/{item_id}", tags=["General"], include_in_schema=False)
async def read_item(item_id: int, q: str = None, db: Session = Depends(get_db)):
    return {"item_id": item_id, "q": q}

# --- 用户认证相关的 API 路由 ---

@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user_by_username = auth.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
    db_user_by_email = auth.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/token", response_model=schemas.Token, tags=["Authentication"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"username": user.username, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=schemas.UserResponse, tags=["Users"], dependencies=[Depends(auth.get_current_active_user)]) # 通过 dependencies 参数声明认证
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

# --- 角色相关的 API 路由 ---

@app.post("/roles/", response_model=schemas.RoleResponse, status_code=status.HTTP_201_CREATED, tags=["Roles"], dependencies=[Depends(auth.get_current_active_user)]) # 声明认证
def create_role(role: schemas.RoleCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_role = models.Role(
        name=role.name,
        description=role.description,
        system_prompt=role.system_prompt,
        few_shot_examples=role.few_shot_examples,
        is_active=role.is_active
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

@app.get("/roles/", response_model=List[schemas.RoleResponse], tags=["Roles"], dependencies=[Depends(auth.get_current_active_user)]) # 声明认证
def get_roles(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    roles = db.query(models.Role).filter(models.Role.is_active == True).all()
    return roles

@app.get("/roles/{role_id}", response_model=schemas.RoleResponse, tags=["Roles"], dependencies=[Depends(auth.get_current_active_user)]) # 声明认证
def get_role(role_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    role = db.query(models.Role).filter(models.Role.id == role_id, models.Role.is_active == True).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or inactive")
    return role

# --- 聊天相关的 API 路由 ---

@app.post("/chats/", response_model=schemas.ChatResponse, status_code=status.HTTP_201_CREATED, tags=["Chats"], dependencies=[Depends(auth.get_current_active_user)]) # 声明认证
def create_chat(chat_create: schemas.ChatCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    role = db.query(models.Role).filter(models.Role.id == chat_create.role_id, models.Role.is_active == True).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found or inactive")

    db_chat = models.Chat(
        user_id=current_user.id,
        role_id=chat_create.role_id,
        title=chat_create.title if chat_create.title else f"Chat with {role.name}"
    )
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)

    initial_ai_message_content = f"Hello, I am {role.name}. How can I help you today?"
    initial_ai_message = models.Message(
        chat_id=db_chat.id,
        sender_type="ai",
        content=initial_ai_message_content,
        order_in_chat=0
    )
    db.add(initial_ai_message)
    db.commit()
    db.refresh(initial_ai_message)

    return db_chat

@app.get("/chats/", response_model=List[schemas.ChatResponse], tags=["Chats"], dependencies=[Depends(auth.get_current_active_user)]) # 声明认证
def get_user_chats(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    chats = db.query(models.Chat).filter(models.Chat.user_id == current_user.id).order_by(models.Chat.created_at.desc()).all()
    return chats

@app.get("/chats/{chat_id}/messages", response_model=List[schemas.MessageResponse], tags=["Chats"], dependencies=[Depends(auth.get_current_active_user)]) # 声明认证
def get_chat_messages(chat_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found or unauthorized")

    messages = db.query(models.Message).filter(models.Message.chat_id == chat_id).order_by(models.Message.order_in_chat).all()
    return messages

@app.post("/chats/{chat_id}/message", response_model=schemas.MessageResponse, tags=["Chats"], dependencies=[Depends(auth.get_current_active_user)]) # 声明认证
async def send_message(chat_id: uuid.UUID, message: schemas.MessageCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    chat = db.query(models.Chat).filter(models.Chat.id == chat_id, models.Chat.user_id == current_user.id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found or unauthorized")

    current_message_count = db.query(models.Message).filter(models.Message.chat_id == chat_id).count()

    # 保存用户消息
    db_user_message = models.Message(
        chat_id=chat_id,
        sender_type="user",
        content=message.content,
        order_in_chat=current_message_count
    )
    db.add(db_user_message)
    db.commit()
    db.refresh(db_user_message)

    # --- 调用 LLM 服务获取真实回复 ---
    role = db.query(models.Role).filter(models.Role.id == chat.role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Associated role not found")

    # 获取聊天历史 (需要调整，以符合 LLM 接口的 messages 格式)
    # 我们需要从数据库中获取所有历史消息，并按顺序组织成 LLM 需要的格式
    chat_history_db = db.query(models.Message).filter(models.Message.chat_id == chat_id).order_by(models.Message.order_in_chat).all()
    
    # 转换为 LLM 期望的格式 (只包含 sender_type 和 content)
    llm_chat_history = []
    for msg in chat_history_db:
        llm_chat_history.append({"sender_type": msg.sender_type, "content": msg.content})

    ai_response_content = await llm_service.get_qwen_response(
        system_prompt=role.system_prompt,
        chat_history=llm_chat_history, # 传递所有历史消息
        user_message=message.content,
        few_shot_examples=role.few_shot_examples,
        model="deepseek-v3" # 确保使用正确的模型ID
    )
    # --- LLM 调用结束 ---

    # 保存 AI 回复
    db_ai_message = models.Message(
        chat_id=chat_id,
        sender_type="ai",
        content=ai_response_content,
        order_in_chat=current_message_count + 1
    )
    db.add(db_ai_message)
    db.commit()
    db.refresh(db_ai_message)

    return db_ai_message

@app.delete("/chats/bulk", status_code=status.HTTP_204_NO_CONTENT, tags=["Chats"], dependencies=[Depends(auth.get_current_active_user)])
def delete_chats_bulk(chat_delete_request: schemas.ChatDeleteBulkRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    try:
        # 过滤掉不属于当前用户的聊天ID，防止越权删除
        chats_to_delete = db.query(models.Chat).filter(
            models.Chat.id.in_(chat_delete_request.chat_ids),
            models.Chat.user_id == current_user.id
        ).all()

        if not chats_to_delete:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No chats found for deletion or unauthorized")

        for chat in chats_to_delete:
            db.delete(chat)
        db.commit()

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        print(f"Error during bulk chat deletion: {e}") # 打印详细错误信息
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error during bulk deletion: {e}")

# --- 语音相关的 API 路由 ---

@app.post("/audio/transcribe", tags=["Audio"], dependencies=[Depends(auth.get_current_active_user)])
async def transcribe_audio(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    if not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only audio files are allowed")

    # 将上传的文件保存到临时位置，或者直接传递文件内容（如果 API 支持）
    # 这里为了简化，我们假设llm_service可以处理文件路径或字节流
    # 实际上，你可能需要将文件保存到临时文件，然后将路径传递给llm_service
    # 或者llm_service可以直接接收BytesIO对象

    # 为了演示，我们将文件内容读取到内存中，然后假装它是一个文件路径
    # 在生产环境中，建议使用 tempfile 模块创建临时文件
    audio_content = await file.read()
    # For `client.audio.transcriptions.create` to work with `file`, 
    # we need to pass a file-like object directly.
    # We'll create a BytesIO object to simulate an in-memory file.
    audio_file_like = io.BytesIO(audio_content)
    audio_file_like.name = file.filename # Add a name attribute for the API
    
    transcript_text = await llm_service.get_asr_transcript(audio_file_like) # 传递文件对象
    
    return {"transcript": transcript_text}

@app.post("/audio/speak", tags=["Audio"], dependencies=[Depends(auth.get_current_active_user)])
async def speak_text(text: schemas.TTSRequest, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    audio_content = await llm_service.get_tts_audio(text.input_text)
    
    if not audio_content:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate audio")
    
    return StreamingResponse(io.BytesIO(audio_content), media_type="audio/mpeg") # 返回 mp3 格式的音频流