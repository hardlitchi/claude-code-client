"""
ユーザー管理のAPIルーター
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..auth import get_current_active_user, get_password_hash, verify_password
from ..models import User
from ..schemas import User as UserSchema, PasswordChangeRequest, APIResponse

router = APIRouter(prefix="/users", tags=["ユーザー管理"])

@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """現在のユーザー情報取得"""
    return current_user

@router.get("/{user_id}", response_model=UserSchema)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """指定ユーザーの情報取得（管理者のみ）"""
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このユーザーの情報にアクセスする権限がありません"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    return user

@router.post("/me/change-password", response_model=APIResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """現在のユーザーのパスワード変更"""
    # 現在のパスワードを確認
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません"
        )
    
    # 新しいパスワードをハッシュ化
    new_hashed_password = get_password_hash(password_data.new_password)
    
    # パスワードを更新
    current_user.hashed_password = new_hashed_password
    db.commit()
    
    return APIResponse(message="パスワードが正常に変更されました")

@router.get("/", response_model=List[UserSchema])
async def get_all_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """全ユーザー一覧取得（管理者のみ）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )
    
    users = db.query(User).all()
    return users

@router.put("/{user_id}/admin", response_model=APIResponse)
async def toggle_admin_status(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ユーザーの管理者権限を切り替え（管理者のみ）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自分の管理者権限は変更できません"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    user.is_admin = not user.is_admin
    db.commit()
    
    action = "付与" if user.is_admin else "削除"
    return APIResponse(message=f"ユーザー '{user.username}' の管理者権限を{action}しました")

@router.put("/{user_id}/status", response_model=APIResponse)
async def toggle_user_status(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ユーザーのアクティブ状態を切り替え（管理者のみ）"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )
    
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="自分のアカウント状態は変更できません"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    user.is_active = not user.is_active
    db.commit()
    
    action = "有効化" if user.is_active else "無効化"
    return APIResponse(message=f"ユーザー '{user.username}' のアカウントを{action}しました")