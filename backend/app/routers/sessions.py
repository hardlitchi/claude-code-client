"""
セッション管理のAPIルーター
"""

import uuid
import os
from datetime import datetime
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Session as SessionModel
from ..schemas import Session as SessionSchema, SessionCreate, SessionUpdate, SessionList, APIResponse, MessageRequest, MessageResponse, MessageHistory
from ..claude_integration import claude_manager

router = APIRouter(prefix="/sessions", tags=["セッション管理"])

def validate_working_directory(working_dir: str, username: str) -> str:
    """ワーキングディレクトリのバリデーション"""
    if not working_dir:
        return None
    
    # パス長チェック
    if len(working_dir) > 500:
        raise ValueError("パスが長すぎます（500文字以内）")
    
    # 危険なパターンのチェック
    dangerous_patterns = ['../', '/etc', '/root', '/sys', '/proc', '/bin', '/sbin', '/usr/bin', '/usr/sbin']
    working_dir_lower = working_dir.lower()
    for pattern in dangerous_patterns:
        if pattern in working_dir_lower:
            raise ValueError(f"セキュリティ上許可されないパス: {pattern}")
    
    # パスを正規化
    try:
        path = Path(working_dir).resolve()
        
        # ユーザーのホームディレクトリ以下に制限
        allowed_base = Path(f"/home/{username}").resolve()
        if not str(path).startswith(str(allowed_base)):
            raise ValueError(f"ユーザーのホームディレクトリ以下のみ許可されています: {allowed_base}")
        
        return str(path)
    except Exception as e:
        raise ValueError(f"無効なパス形式: {str(e)}")
    
    return str(path)

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
    
    # ワーキングディレクトリの検証
    validated_working_directory = None
    if session_data.working_directory:
        try:
            validated_working_directory = validate_working_directory(
                session_data.working_directory, 
                current_user.username
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無効なワーキングディレクトリです: {str(e)}"
            )
    
    db_session = SessionModel(
        session_id=session_id,
        name=session_data.name,
        description=session_data.description,
        working_directory=validated_working_directory,
        user_id=current_user.id,
        status="stopped"
    )
    
    try:
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッションの作成に失敗しました: {str(e)}"
        )
    
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
    
    try:
        # Claude Code セッションも削除
        await claude_manager.remove_session(session.session_id)
    except Exception as e:
        # Claude セッションの削除に失敗してもDBから削除は続行
        pass
    
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
    
    try:
        # Claude Code セッション開始処理
        claude_session = await claude_manager.create_session(
            session_id=session.session_id,
            working_directory=session.working_directory or "."
        )
        
        session.status = "running"
        session.last_accessed = datetime.utcnow()
        db.commit()
        
        return APIResponse(message="セッションを開始しました")
    except ValueError as e:
        # セッションが既に存在する場合
        if "既に存在" in str(e):
            session.status = "running"
            session.last_accessed = datetime.utcnow()
            db.commit()
            return APIResponse(message="セッションは既に実行中です")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッション開始に失敗しました: {str(e)}"
        )

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
    
    try:
        # Claude Code セッション停止処理
        await claude_manager.remove_session(session.session_id)
        
        session.status = "stopped"
        db.commit()
        
        return APIResponse(message="セッションを停止しました")
    except Exception as e:
        # エラーが発生してもセッション状態は停止にする
        session.status = "stopped"
        db.commit()
        
        return APIResponse(message=f"セッションを停止しました（警告: {str(e)}）")

@router.post("/{session_id}/message", response_model=MessageResponse)
async def send_message_to_session(
    session_id: str,
    message_request: MessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セッションにメッセージ送信"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    if session.status != "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="セッションが実行中ではありません"
        )
    
    try:
        # Claude統合からメッセージ送信
        claude_session = await claude_manager.get_session(session_id)
        if not claude_session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Claude セッションが見つかりません"
            )
        
        response = await claude_session.send_message(message_request.message)
        
        # 最終アクセス時刻を更新
        session.last_accessed = datetime.utcnow()
        db.commit()
        
        return MessageResponse(
            response=response,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"メッセージ送信に失敗しました: {str(e)}"
        )

@router.get("/{session_id}/messages", response_model=MessageHistory)
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """セッションのメッセージ履歴取得"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    try:
        # Claude統合からメッセージ履歴取得
        claude_session = await claude_manager.get_session(session_id)
        if not claude_session:
            return MessageHistory(messages=[], session_id=session_id)
        
        messages = claude_session.get_message_history()
        
        return MessageHistory(
            messages=messages,
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"メッセージ履歴の取得に失敗しました: {str(e)}"
        )