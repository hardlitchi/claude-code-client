"""
Claude Code統合のAPIルーター
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Session as SessionModel
from ..schemas import APIResponse
from ..claude_integration import claude_manager

router = APIRouter(prefix="/claude", tags=["Claude Code統合"])

@router.post("/sessions/{session_id}/start", response_model=APIResponse)
async def start_claude_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Claude Code セッションを開始"""
    # セッションの存在確認
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
        # Claude セッションを作成
        working_dir = session.working_directory or "/tmp"
        claude_session = await claude_manager.create_session(session_id, working_dir)
        
        # データベースのセッション状態を更新
        session.status = "running"
        db.commit()
        
        return APIResponse(
            message="Claude Code セッションを開始しました",
            data={"session_id": session_id, "status": "running"}
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claude セッション開始エラー: {str(e)}"
        )

@router.post("/sessions/{session_id}/stop", response_model=APIResponse)
async def stop_claude_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Claude Code セッションを停止"""
    # セッションの存在確認
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
        # Claude セッションを停止
        await claude_manager.remove_session(session_id)
        
        # データベースのセッション状態を更新
        session.status = "stopped"
        db.commit()
        
        return APIResponse(
            message="Claude Code セッションを停止しました",
            data={"session_id": session_id, "status": "stopped"}
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claude セッション停止エラー: {str(e)}"
        )

@router.post("/sessions/{session_id}/message")
async def send_message_to_claude(
    session_id: str,
    message_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Claudeにメッセージを送信"""
    # セッションの存在確認
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    message = message_data.get("message", "")
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="メッセージが空です"
        )
    
    try:
        # Claude セッションを取得
        claude_session = await claude_manager.get_session(session_id)
        if not claude_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Claude セッションが見つかりません。先にセッションを開始してください。"
            )
        
        # メッセージを送信
        response = await claude_session.send_message(message)
        
        return {
            "message": "メッセージを送信しました",
            "user_message": message,
            "claude_response": response,
            "timestamp": claude_session.messages[-1]["timestamp"] if claude_session.messages else None
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"メッセージ送信エラー: {str(e)}"
        )

@router.get("/sessions/{session_id}/messages")
async def get_claude_messages(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Claude セッションのメッセージ履歴を取得"""
    # セッションの存在確認
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
        # Claude セッションを取得
        claude_session = await claude_manager.get_session(session_id)
        if not claude_session:
            return {"messages": [], "total": 0}
        
        messages = claude_session.get_message_history()
        
        return {
            "messages": messages,
            "total": len(messages)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"メッセージ履歴取得エラー: {str(e)}"
        )

@router.get("/sessions/{session_id}/status")
async def get_claude_session_status(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Claude セッションの状態を取得"""
    try:
        claude_session = await claude_manager.get_session(session_id)
        
        if not claude_session:
            return {
                "session_id": session_id,
                "is_active": False,
                "message_count": 0
            }
        
        return {
            "session_id": session_id,
            "is_active": claude_session.is_active,
            "message_count": len(claude_session.messages),
            "created_at": claude_session.created_at.isoformat(),
            "working_directory": claude_session.working_directory
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッション状態取得エラー: {str(e)}"
        )