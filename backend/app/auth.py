"""
認証・認可機能
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
import uuid

from .database import get_db
from .models import User, AuthToken
from .schemas import TokenData

# 設定
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 1  # アクセストークンは1時間
REFRESH_TOKEN_EXPIRE_DAYS = 30  # リフレッシュトークンは30日

# パスワードハッシュ化
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 認証
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """パスワード検証"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """パスワードハッシュ化"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """アクセストークン作成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """リフレッシュトークン作成"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_token_pair(user: User, db: Session, ip_address: str = None, user_agent: str = None):
    """アクセストークンとリフレッシュトークンのペアを作成"""
    token_data = {"sub": user.username, "user_id": user.id}
    
    # アクセストークン作成
    access_token = create_access_token(token_data)
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    # リフレッシュトークン作成
    refresh_token = create_refresh_token(token_data)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # リフレッシュトークンをデータベースに保存
    token_id = str(uuid.uuid4())
    db_token = AuthToken(
        token_id=token_id,
        user_id=user.id,
        token_type="refresh",
        expires_at=datetime.utcnow() + refresh_token_expires,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(db_token)
    db.commit()
    
    # ユーザーの最終ログイン時刻を更新
    user.last_login = datetime.utcnow()
    user.login_count += 1
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "refresh_expires_in": int(refresh_token_expires.total_seconds())
    }

def verify_token(token: str, expected_type: str = "access") -> TokenData:
    """トークン検証"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なトークンです",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = TokenData(username=username)
        return token_data
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )

def refresh_access_token(refresh_token: str, db: Session, ip_address: str = None, user_agent: str = None):
    """リフレッシュトークンを使用してアクセストークンを更新"""
    try:
        # リフレッシュトークンを検証
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なリフレッシュトークンです",
            )
        
        # ユーザーを取得
        user = db.query(User).filter(User.username == username).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ユーザーが見つからないか無効です",
            )
        
        # データベース内のリフレッシュトークンを確認（セキュリティ強化）
        db_token = db.query(AuthToken).filter(
            AuthToken.user_id == user.id,
            AuthToken.token_type == "refresh",
            AuthToken.is_active == True,
            AuthToken.expires_at > datetime.utcnow()
        ).first()
        
        if not db_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="リフレッシュトークンが無効または期限切れです",
            )
        
        # 新しいアクセストークンを作成
        token_data = {"sub": user.username, "user_id": user.id}
        access_token = create_access_token(token_data)
        access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        
        # トークンの最終使用時刻を更新
        db_token.last_used = datetime.utcnow()
        if ip_address:
            db_token.ip_address = ip_address
        if user_agent:
            db_token.user_agent = user_agent
        db.commit()
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds())
        }
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なリフレッシュトークンです",
        )

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """ユーザー認証"""
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """現在のユーザー取得"""
    token_data = verify_token(credentials.credentials)
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """アクティブユーザー取得"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="無効なユーザーです"
        )
    return current_user

async def get_current_user_ws(token: str, db: Session) -> User:
    """WebSocket用の現在のユーザー取得"""
    try:
        token_data = verify_token(token)
        user = db.query(User).filter(User.username == token_data.username).first()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証に失敗しました"
            )
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証に失敗しました"
        )

def create_user(db: Session, username: str, password: str, email: Optional[str] = None) -> User:
    """ユーザー作成"""
    # 既存ユーザーチェック
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ユーザー名が既に使用されています"
        )
    
    # パスワードハッシュ化
    hashed_password = get_password_hash(password)
    
    # ユーザー作成
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def revoke_token(refresh_token: str, db: Session) -> bool:
    """リフレッシュトークンを取り消し"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if username is None or token_type != "refresh":
            return False
        
        # ユーザーを取得
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        
        # データベース内のリフレッシュトークンを無効化
        db_token = db.query(AuthToken).filter(
            AuthToken.user_id == user.id,
            AuthToken.token_type == "refresh",
            AuthToken.is_active == True
        ).first()
        
        if db_token:
            db_token.is_active = False
            db.commit()
            return True
        
        return False
        
    except JWTError:
        return False

def revoke_all_user_tokens(user_id: int, db: Session) -> bool:
    """ユーザーの全トークンを取り消し（ログアウト全デバイス）"""
    try:
        # ユーザーの全リフレッシュトークンを無効化
        db.query(AuthToken).filter(
            AuthToken.user_id == user_id,
            AuthToken.is_active == True
        ).update({"is_active": False})
        db.commit()
        return True
    except Exception:
        return False