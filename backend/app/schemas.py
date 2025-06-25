"""
Pydantic スキーマ定義（API リクエスト/レスポンス）
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# ユーザー関連スキーマ
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# 認証関連スキーマ
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class TokenData(BaseModel):
    username: Optional[str] = None

# セッション関連スキーマ
class SessionBase(BaseModel):
    name: str
    description: Optional[str] = None
    working_directory: Optional[str] = None

class SessionCreate(SessionBase):
    pass

class SessionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    working_directory: Optional[str] = None
    status: Optional[str] = None

class Session(SessionBase):
    id: int
    session_id: str
    status: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_accessed: datetime

    class Config:
        from_attributes = True

# API レスポンス用スキーマ
class APIResponse(BaseModel):
    message: str
    status: str = "success"
    data: Optional[dict] = None

class SessionList(BaseModel):
    sessions: List[Session]
    total: int

# システム情報スキーマ
class SystemStatus(BaseModel):
    status: str
    version: str
    active_sessions: int
    total_users: int
    uptime: str