# app/schemas.py
import datetime
import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field

# --- User Schemas ---
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):#UserCreate用于用户注册
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):#用于在 API 响应中返回用户数据，但不包含敏感的 password。
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True # 兼容 SQLAlchemy ORM 对象

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[uuid.UUID] = None # 添加 user_id

# --- Role Schemas ---
class RoleBase(BaseModel):#AI角色创建
    name: str = Field(..., min_length=1, max_length=50)
    description: str
    system_prompt: str
    few_shot_examples: Optional[List[dict]] = None # 存储 JSON 列表
    is_active: bool = True

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):#AI角色响应
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

# --- Message Schemas ---
class MessageBase(BaseModel):
    sender_type: Literal["user", "ai"]
    content: str

class MessageCreate(MessageBase):
    pass # 可以在这里添加一些额外的验证

class MessageResponse(MessageBase):
    id: uuid.UUID
    chat_id: uuid.UUID
    timestamp: datetime.datetime
    order_in_chat: int

    class Config:
        from_attributes = True

# --- Chat Schemas ---
class ChatBase(BaseModel):
    title: Optional[str] = None

class ChatCreate(ChatBase):
    role_id: uuid.UUID

class ChatResponse(ChatBase):
    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime
    # messages: List[MessageResponse] = [] # 可以选择在获取聊天详情时包含消息列表

    class Config:
        from_attributes = True

class TTSRequest(BaseModel):
    input_text: str = Field(..., min_length=1, max_length=2000) # 文本转语音的输入文本

class ChatDeleteBulkRequest(BaseModel):
    chat_ids: List[uuid.UUID] = Field(..., min_length=1)
