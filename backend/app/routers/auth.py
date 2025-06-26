"""
認証関連のAPIルーター
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import (
    authenticate_user, create_token_pair, refresh_access_token, 
    revoke_token, revoke_all_user_tokens, create_user, get_current_user,
    ACCESS_TOKEN_EXPIRE_HOURS
)
from ..schemas import Token, TokenPair, RefreshTokenRequest, User, UserCreate, UserLogin, APIResponse

router = APIRouter(prefix="/auth", tags=["認証"])

@router.post("/login", response_model=TokenPair)
async def login(user_credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """ユーザーログイン（アクセストークン + リフレッシュトークン）"""
    user = authenticate_user(db, user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが間違っています",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # クライアント情報を取得
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    # トークンペアを作成
    token_pair = create_token_pair(user, db, ip_address, user_agent)
    
    return token_pair

@router.post("/register", response_model=APIResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """ユーザー登録"""
    try:
        user = create_user(db, user_data.username, user_data.password, user_data.email)
        return APIResponse(
            message="ユーザー登録が完了しました",
            data={"user_id": user.id, "username": user.username}
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ユーザー登録に失敗しました"
        )

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2準拠のトークン取得（Swagger UI用）"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが間違っています",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_HOURS * 3600
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """リフレッシュトークンを使用してアクセストークンを更新"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    token_data = refresh_access_token(
        refresh_request.refresh_token, 
        db, 
        ip_address, 
        user_agent
    )
    
    return token_data

@router.post("/logout", response_model=APIResponse)
async def logout(
    refresh_request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ログアウト（リフレッシュトークンを無効化）"""
    success = revoke_token(refresh_request.refresh_token, db)
    
    if success:
        return APIResponse(message="ログアウトしました")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ログアウトに失敗しました"
        )

@router.post("/logout-all", response_model=APIResponse)
async def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """全デバイスからログアウト（全リフレッシュトークンを無効化）"""
    success = revoke_all_user_tokens(current_user.id, db)
    
    if success:
        return APIResponse(message="全デバイスからログアウトしました")
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ログアウトに失敗しました"
        )