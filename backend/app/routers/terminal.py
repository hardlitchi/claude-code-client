"""
Terminal WebSocket 接続のAPIルーター
基本ターミナル（無料版）とClaudeターミナル（有料版）をサポート
"""

import asyncio
import logging
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Session as SessionModel, Subscription
from ..terminal_managers import (
    get_terminal_manager, 
    has_active_terminal, 
    get_active_terminal, 
    set_active_terminal, 
    remove_active_terminal,
    ClaudeTerminalManager
)

router = APIRouter(prefix="/terminal", tags=["Terminal"])
logger = logging.getLogger(__name__)

def check_claude_access(user: User, db: Session) -> bool:
    """ユーザーがClaudeターミナルにアクセス可能かチェック"""
    # 管理者ユーザーは常にアクセス可能
    if user.is_admin:
        return True
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user.id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        return False
    
    # Freeプランは基本ターミナルのみ
    if subscription.plan_type == "free":
        return False
    
    # Pro/Enterpriseプランの制限をチェック
    limits = subscription.limits or {}
    claude_sessions = limits.get("claude_sessions", 0)
    
    return claude_sessions > 0

@router.websocket("/ws/{session_id}")
async def websocket_terminal(
    websocket: WebSocket,
    session_id: str,
    terminal_type: str = Query(default="basic", description="Terminal type: basic or claude"),
    db: Session = Depends(get_db)
):
    """Terminal WebSocket接続"""
    await websocket.accept()
    
    try:
        logger.info(f"Terminal WebSocket接続試行: session_id={session_id}, terminal_type={terminal_type}")
        # TODO: 認証チェック（WebSocketでの認証は複雑なので後で実装）
        # 現在は簡単な実装
        
        # セッション情報を取得
        session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if not session:
            await websocket.send_text("ERROR: セッションが見つかりません")
            await websocket.close()
            return
        
        # ユーザー情報を取得（本来はWebSocket認証から）
        user = db.query(User).filter(User.id == session.user_id).first()
        if not user:
            await websocket.send_text("ERROR: ユーザーが見つかりません")
            await websocket.close()
            return
        
        # Claudeターミナルのアクセス権限をチェック
        if terminal_type == "claude" and not check_claude_access(user, db):
            await websocket.send_text("ERROR: Claudeターミナルの利用にはProプラン以上のサブスクリプションが必要です")
            await websocket.close()
            return
        
        # セッション設定を更新
        session.terminal_type = terminal_type
        db.commit()
        
        # ターミナルタイプ別のセッションIDを作成
        terminal_session_id = f"{session_id}_{terminal_type}"
        
        # 既存のターミナルセッションがあるかチェック
        if has_active_terminal(terminal_session_id):
            # 既存セッションを使用
            terminal = get_active_terminal(terminal_session_id)
            await websocket.send_text(f"Terminal reconnected to existing {terminal_type} session: {session.name}\n")
            logger.info(f"Terminal session restored: {terminal_session_id}")
        else:
            # 新しいターミナルマネージャーを作成
            working_dir = session.working_directory or "/tmp"
            terminal = get_terminal_manager(
                session_id=terminal_session_id,
                terminal_type=terminal_type,
                working_directory=working_dir
            )
            
            # ターミナルを開始
            await terminal.start_terminal()
            set_active_terminal(terminal_session_id, terminal)
            
            # 初期メッセージを送信
            terminal_name = "Claude統合" if terminal_type == "claude" else "基本"
            await websocket.send_text(f"{terminal_name}ターミナルに接続しました: {session.name}\n")
        
        # 出力読み取りタスクを開始
        async def read_terminal_output():
            while True:
                try:
                    output = await terminal.read_output()
                    if output:
                        await websocket.send_text(output)
                    await asyncio.sleep(0.01)  # 10ms間隔
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    print(f"Output read error: {e}")
                    break
        
        # 出力読み取りタスクを開始
        output_task = asyncio.create_task(read_terminal_output())
        
        try:
            # 入力を処理
            while True:
                data = await websocket.receive_text()
                await terminal.write_input(data)
        
        except WebSocketDisconnect:
            print(f"Terminal WebSocket disconnected: {session_id}")
        
        finally:
            # クリーンアップ（ただし、ターミナルプロセスは保持）
            output_task.cancel()
            # WebSocket切断時もターミナルプロセスは継続実行
            logger.info(f"Terminal WebSocket disconnected but session preserved: {session_id}")
    
    except Exception as e:
        logger.error(f"Terminal WebSocket error: {e}")
        await websocket.send_text(f"ERROR: {str(e)}")
        await websocket.close()

@router.get("/{session_id}/status")
async def get_terminal_status(
    session_id: str,
    terminal_type: str = Query(default="basic", description="Terminal type: basic or claude"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ターミナル接続状態を取得"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    terminal_session_id = f"{session_id}_{terminal_type}"
    is_connected = has_active_terminal(terminal_session_id)
    terminal = get_active_terminal(terminal_session_id) if is_connected else None
    
    return {
        "session_id": session_id,
        "terminal_session_id": terminal_session_id,
        "terminal_type": terminal_type,
        "connected": is_connected,
        "status": "active" if is_connected else "inactive",
        "manager_type": terminal.__class__.__name__ if terminal else None
    }

@router.delete("/{session_id}")
async def terminate_terminal_session(
    session_id: str,
    terminal_type: str = Query(default="all", description="Terminal type: basic, claude, or all"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """ターミナルセッションを完全に終了"""
    session = db.query(SessionModel).filter(
        SessionModel.session_id == session_id,
        SessionModel.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="セッションが見つかりません"
        )
    
    terminated_sessions = []
    
    if terminal_type == "all":
        # 全てのターミナルタイプを終了
        for t_type in ["basic", "claude"]:
            terminal_session_id = f"{session_id}_{t_type}"
            if has_active_terminal(terminal_session_id):
                remove_active_terminal(terminal_session_id)
                terminated_sessions.append(terminal_session_id)
    else:
        # 指定されたタイプのみ終了
        terminal_session_id = f"{session_id}_{terminal_type}"
        if has_active_terminal(terminal_session_id):
            remove_active_terminal(terminal_session_id)
            terminated_sessions.append(terminal_session_id)
    
    if terminated_sessions:
        return {"message": f"Terminal sessions terminated: {', '.join(terminated_sessions)}"}
    else:
        return {"message": f"No active terminal sessions found for {session_id}"}

