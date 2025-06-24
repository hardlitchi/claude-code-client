"""
セッション管理のAPIルーター
"""

import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Session as SessionModel
from ..schemas import Session as SessionSchema, SessionCreate, SessionUpdate, SessionList, APIResponse

router = APIRouter(prefix="/sessions", tags=["セッション管理"])

@router.get("/", response_model=SessionList)
async def get_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ユーザーのセッション一覧取得"""
    sessions = db.query(SessionModel).filter(SessionModel.user_id == current_user.id).all()
    return SessionList(sessions=sessions, total=len(sessions))

@router.post("/", response_model=SessionSchema)
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """新しいセッション作成"""
    session_id = str(uuid.uuid4())
    
    db_session = SessionModel(
        session_id=session_id,
        name=session_data.name,
        description=session_data.description,
        working_directory=session_data.working_directory,
        user_id=current_user.id,
        status="stopped"
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    
    return db_session

@router.get("/{session_id}", response_model=SessionSchema)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """特定のセッション取得"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    # 最終アクセス時刻を更新
    session.last_accessed = datetime.utcnow()
    db.commit()
    
    return session

@router.put("/{session_id}", response_model=SessionSchema)
async def update_session(
    session_id: str,
    session_update: SessionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セッション更新"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    # 更新可能なフィールドのみ更新
    update_data = session_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)
    
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    return session

@router.delete("/{session_id}", response_model=APIResponse)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セッション削除"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    db.delete(session)
    db.commit()
    
    return APIResponse(message="セッションを削除しました")

@router.post("/{session_id}/start", response_model=APIResponse)
async def start_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セッション開始"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    # TODO: 実際のClaude Code セッション開始処理
    session.status = "running"
    session.last_accessed = datetime.utcnow()
    db.commit()
    
    return APIResponse(message="セッションを開始しました")

@router.post("/{session_id}/stop", response_model=APIResponse)
async def stop_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セッション停止"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    # TODO: 実際のClaude Code セッション停止処理
    session.status = "stopped"
    db.commit()
    
    return APIResponse(message="セッションを停止しました")