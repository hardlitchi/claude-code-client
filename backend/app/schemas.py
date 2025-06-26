"""
Pydantic スキーマ定義（API リクエスト/レスポンス）
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any

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

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

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

# メッセージ関連スキーマ
class MessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    response: str
    session_id: str
    timestamp: datetime
    
class MessageHistory(BaseModel):
    messages: List[dict]
    session_id: str

# システム情報スキーマ
class SystemStatus(BaseModel):
    status: str
    version: str
    active_sessions: int
    total_users: int
    uptime: str

# サブスクリプション関連スキーマ
class SubscriptionBase(BaseModel):
    plan_type: str
    plan_name: str
    billing_cycle: str = "monthly"

class SubscriptionCreate(SubscriptionBase):
    payment_method: Optional[str] = None

class SubscriptionUpdate(BaseModel):
    auto_renew: Optional[bool] = None
    payment_method: Optional[str] = None

class SubscriptionSchema(SubscriptionBase):
    subscription_id: str
    user_id: int
    status: str
    monthly_price: int
    currency: str = "JPY"
    limits: Dict[str, Any]
    usage: Dict[str, Any]
    starts_at: datetime
    ends_at: Optional[datetime] = None
    next_billing_date: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    auto_renew: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SubscriptionPlanBase(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    plan_type: str

class SubscriptionPlanSchema(SubscriptionPlanBase):
    plan_id: str
    monthly_price: int
    yearly_price: int
    currency: str = "JPY"
    features: Dict[str, Any]
    is_active: bool = True
    is_visible: bool = True
    sort_order: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UsageLogBase(BaseModel):
    usage_type: str
    amount: int = 0
    unit: str = "count"

class UsageLogSchema(UsageLogBase):
    id: int
    user_id: int
    session_id: Optional[str] = None
    cost_yen: int = 0
    billing_period: Optional[str] = None
    usage_metadata: Optional[Dict[str, Any]] = None
    terminal_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True