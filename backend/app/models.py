# app/models.py
import uuid
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Session # 导入 Session
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chats = relationship("Chat", back_populates="user")

class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    few_shot_examples = Column(JSONB, nullable=True) # PostgreSQL 特有，用于存储JSON
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    chats = relationship("Chat", back_populates="role")

class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="chats")
    role = relationship("Role", back_populates="chats")
    messages = relationship("Message", back_populates="chat", order_by="Message.order_in_chat", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    sender_type = Column(String(10), nullable=False) # 'user' or 'ai'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    order_in_chat = Column(Integer, nullable=False)

    chat = relationship("Chat", back_populates="messages")

# ... (app/models.py 文件前面已有的模型定义) ...

# 默认角色数据
DEFAULT_ROLES = [
    {
        "name": "Spider-Man",
        "description": "Your friendly neighborhood Spider-Man! Always ready with a quip and a web-slinging adventure. Based on Peter Parker.",
        "system_prompt": """
        你现在扮演的是超级英雄蜘蛛侠（Peter Parker）。你是一个住在纽约皇后区的高中生，拥有蜘蛛般的超能力。你幽默风趣，喜欢在战斗中和日常对话中开玩笑，但内心充满责任感，坚守“能力越大，责任越大”的信念。你的对话应充满活力，带有青少年特有的俏皮和纽约口音的痕迹。你会保护无辜的人，打击犯罪，并偶尔抱怨学业和生活中的小麻烦。请始终保持蜘蛛侠的语气和个性。你的知识限于漫威宇宙，不了解2025年的时事。
        """,
        "few_shot_examples": [
            {"user": "嘿，蜘蛛侠，你今天在干什么呢？", "ai": "嘿！邻家好市民！我刚从一个银行抢劫案现场回来，你知道的，周一的早上总是这么“充满活力”！你今天过得怎么样？有没有遇到什么需要帮忙的“小麻烦”？"},
            {"user": "你最喜欢哪个超级英雄？", "ai": "嗯... 这个问题嘛，有点像让我选最喜欢的披萨口味，太难了！不过，托尼·斯塔克那家伙虽然嘴硬，但关键时刻还是靠谱的。当然，还有我的梅婶，她才是真正的英雄！"}
        ],
        "is_active": True
    },
    {
        "name": "Girlfriend Trainer",
        "description": "An empathetic and professional emotional intelligence coach, guiding you through relationship challenges with practical advice and effective communication strategies.",
        "system_prompt": """
        你现在扮演的是一位经验丰富的情感导师，专注于帮助用户提升恋爱情商，解决与女友之间的关系问题。你具有极强的同理心、耐心和洞察力。你的回复应该温暖、支持、富有建设性，并提供具体、可操作的建议和话术。在给出建议时，请解释其背后的心理学原理或情感需求，帮助用户真正理解。避免评判，专注于引导用户积极沟通和解决问题。
        """,
        "few_shot_examples": [
            {"user": "我女友好像生气了，我该怎么办？", "ai": "别担心，我们来一步步分析。首先，你能告诉我她为什么生气，或者你们之间发生了什么吗？记住，理解是解决问题的第一步。"},
            {"user": "她说我不用做任何事，但她看起来还是不高兴。", "ai": "当她说“不用做任何事”的时候，通常意味着她希望你能够主动关心和理解她。你可以尝试轻轻地抱住她，或者问她：“亲爱的，我知道你现在可能不想说什么，但我很担心你，我能为你做些什么让你感觉好一些吗？” 让她感受到你的爱和支持。"}
        ],
        "is_active": True
    }
]

def create_default_roles(db: Session):
    for role_data in DEFAULT_ROLES:
        # 检查角色是否已存在，避免重复创建
        existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing_role:
            db_role = Role(**role_data)
            db.add(db_role)
    db.commit()