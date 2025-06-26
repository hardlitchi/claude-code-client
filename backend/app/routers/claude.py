"""
Claude Code統合のAPIルーター
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Session as SessionModel
from ..schemas import APIResponse
from ..claude_integration import ClaudeIntegration

# Claude統合インスタンス
claude_integration = ClaudeIntegration()

class ClaudeMessageRequest(BaseModel):
    message: str
    stream: bool = False

class ClaudeSessionCreateRequest(BaseModel):
    working_directory: Optional[str] = None
    system_prompt: Optional[str] = None

router = APIRouter(prefix="/claude", tags=["Claude Code統合"])

@router.post("/sessions/{session_id}/start", response_model=APIResponse)
async def start_claude_session(
    session_id: str,
    request: ClaudeSessionCreateRequest = ClaudeSessionCreateRequest(),
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
        working_dir = request.working_directory or session.working_directory or f"/tmp/claude-sessions/{session_id}"
        result = await claude_integration.create_session(
            session_id, 
            working_dir, 
            request.system_prompt
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Claude セッション開始エラー: {result['error']}"
            )
        
        # データベースのセッション状態を更新
        session.status = "running"
        session.working_directory = working_dir
        db.commit()
        
        return APIResponse(
            message="Claude Code セッションを開始しました",
            data=result
        )
    
    except HTTPException:
        raise
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
        success = await claude_integration.remove_session(session_id)
        
        # データベースのセッション状態を更新
        session.status = "stopped"
        db.commit()
        
        return APIResponse(
            message="Claude Code セッションを停止しました",
            data={"session_id": session_id, "status": "stopped", "success": success}
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claude セッション停止エラー: {str(e)}"
        )

@router.post("/sessions/{session_id}/message")
async def send_message_to_claude(
    session_id: str,
    request: ClaudeMessageRequest,
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
    
    if not request.message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="メッセージが空です"
        )
    
    try:
        # Claude セッション情報を取得
        session_info = await claude_integration.get_session_info(session_id)
        if not session_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Claude セッションが見つかりません。先にセッションを開始してください。"
            )
        
        if request.stream:
            # ストリーミング応答
            async def stream_response():
                async for chunk in claude_integration.send_message_stream(request.message, session_id):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                stream_response(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        else:
            # 通常の応答
            response = await claude_integration.send_message(request.message, session_id)
            
            return {
                "message": "メッセージを送信しました",
                "user_message": request.message,
                "claude_response": response,
                "session_id": session_id
            }
    
    except HTTPException:
        raise
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
        # Claude セッションのメッセージ履歴を取得
        messages = await claude_integration.get_session_history(session_id)
        if not messages:
            return {"messages": [], "total": 0}
        
        return {
            "messages": messages,
            "total": len(messages),
            "session_id": session_id
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
        session_info = await claude_integration.get_session_info(session_id)
        
        if not session_info:
            return {
                "session_id": session_id,
                "is_active": False,
                "message_count": 0,
                "exists": False
            }
        
        return {
            **session_info,
            "exists": True
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッション状態取得エラー: {str(e)}"
        )

@router.get("/sessions")
async def list_claude_sessions(
    current_user: User = Depends(get_current_active_user)
):
    """すべてのClaude セッション一覧を取得"""
    try:
        sessions = await claude_integration.list_sessions()
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッション一覧取得エラー: {str(e)}"
        )

@router.post("/sessions/cleanup", response_model=APIResponse)
async def cleanup_claude_sessions(
    current_user: User = Depends(get_current_active_user)
):
    """非アクティブなClaude セッションをクリーンアップ"""
    try:
        cleanup_count = await claude_integration.cleanup_sessions()
        return APIResponse(
            message=f"{cleanup_count}個の非アクティブセッションをクリーンアップしました",
            data={"cleanup_count": cleanup_count}
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"セッションクリーンアップエラー: {str(e)}"
        )