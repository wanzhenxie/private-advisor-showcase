from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime
    model_config = {"from_attributes": True}

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    locale: str = Field(default="zh-CN", max_length=20)
    timezone: str = Field(default="America/New_York", max_length=80)
    advisor_preferences: dict[str, Any] = Field(default_factory=dict)

class ProfileOut(ProfileUpdate):
    id: str
    user_id: str
    updated_at: datetime
    model_config = {"from_attributes": True}

class MemoryCreate(BaseModel):
    category: str = Field(default="other", max_length=60)
    content: str = Field(min_length=1, max_length=2000)
    source: str = Field(default="user_statement", max_length=40)
    confidence: float = Field(default=1.0, ge=0, le=1)
    status: str = Field(default="active", pattern="^(pending|active|archived)$")
    keywords: list[str] = Field(default_factory=list)

class MemoryUpdate(BaseModel):
    category: str | None = Field(default=None, max_length=60)
    content: str | None = Field(default=None, min_length=1, max_length=2000)
    status: str | None = Field(default=None, pattern="^(pending|active|archived)$")
    keywords: list[str] | None = None

class MemoryOut(BaseModel):
    id: str
    user_id: str
    category: str
    content: str
    source: str
    confidence: float
    status: str
    keywords: list[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", min_length=1, max_length=200)

class ConversationOut(BaseModel):
    id: str
    title: str
    summary: str | None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    model_config = {"from_attributes": True}

class ChatReply(BaseModel):
    assistant_message: MessageOut
    memory_candidates: list[MemoryOut]

class UsageOut(BaseModel):
    input_tokens: int
    output_tokens: int
    calls: int
