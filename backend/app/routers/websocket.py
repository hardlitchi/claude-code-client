"""
WebSocketルーター
リアルタイム通信のエンドポイント
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Optional
import json
import logging
from datetime import datetime

from ..websocket_manager import manager, MessageType, WebSocketMessage
from ..auth import get_current_user_ws
from ..claude_integration import ClaudeIntegration
from ..database import get_db
from ..models import User, Session
from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter()

class ClaudeWebSocketHandler:
    """
Claude CodeとのWebSocket通信を処理するクラス
    """
    
    def __init__(self):
        self.claude_integration = ClaudeIntegration()
        
    async def handle_chat_message(self, message: WebSocketMessage, db: DBSession):
        """チャットメッセージを処理"""
        try:
            user_message = message.data.get("message", "")
            if not user_message:
                return
                
            # ユーザーメッセージをセッション内にブロードキャスト
            user_msg = WebSocketMessage(
                MessageType.CHAT,
                {
                    "message": user_message,
                    "sender": "user",
                    "user_id": message.user_id
                },
                user_id=message.user_id,
                session_id=message.session_id
            )
            await manager.broadcast_to_session(user_msg.to_dict(), message.session_id)
            
            # Claude Codeにメッセージを送信（暂定実装）
            claude_response = await self._get_claude_response(user_message)
            
            # Claudeのレスポンスをセッション内にブロードキャスト
            claude_msg = WebSocketMessage(
                MessageType.CHAT,
                {
                    "message": claude_response,
                    "sender": "claude",
                    "model": "claude-3-sonnet"
                },
                session_id=message.session_id
            )
            await manager.broadcast_to_session(claude_msg.to_dict(), message.session_id)
            
        except Exception as e:
            logger.error(f"チャットメッセージ処理エラー: {e}")
            error_msg = WebSocketMessage(
                MessageType.ERROR,
                {"error": "メッセージの処理中にエラーが発生しました"},
                session_id=message.session_id
            )
            await manager.broadcast_to_session(error_msg.to_dict(), message.session_id)
            
    async def handle_terminal_message(self, message: WebSocketMessage, db: DBSession):
        """ターミナルメッセージを処理"""
        try:
            command = message.data.get("command", "")
            if not command:
                return
                
            # コマンド実行（暂定実装）
            output = await self._execute_command(command)
            
            # 結果をセッション内にブロードキャスト
            terminal_msg = WebSocketMessage(
                MessageType.TERMINAL,
                {
                    "command": command,
                    "output": output,
                    "exit_code": 0
                },
                user_id=message.user_id,
                session_id=message.session_id
            )
            await manager.broadcast_to_session(terminal_msg.to_dict(), message.session_id)
            
        except Exception as e:
            logger.error(f"ターミナルメッセージ処理エラー: {e}")
            error_msg = WebSocketMessage(
                MessageType.ERROR,
                {"error": "コマンドの実行中にエラーが発生しました"},
                session_id=message.session_id
            )
            await manager.broadcast_to_session(error_msg.to_dict(), message.session_id)
            
    async def _get_claude_response(self, message: str) -> str:
        """
Claude Codeからレスポンスを取得（暂定実装）
        """
        # 実際の実装ではClaude Code APIを呼び出し
        # 現在はモックレスポンスを返す
        await self.claude_integration.send_message(message)  # 準備中
        return f"Claude: {message}に対するレスポンスです。（暂定実装）"
        
    async def _execute_command(self, command: str) -> str:
        """
コマンドを実行（暂定実装）
        """
        # 実際の実装ではシステムコマンドを安全に実行
        return f"$ {command}\nコマンドの結果がここに表示されます。（暂定実装）"

# グローバルハンドラー
websocket_handler = ClaudeWebSocketHandler()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = None,
    db: DBSession = Depends(get_db)
):
    """
WebSocketエンドポイント
    """
    connection_id = None
    user_id = None
    
    try:
        # 認証確認
        if not token:
            await websocket.close(code=4001, reason="認証トークンが必要です")
            return
            
        try:
            user = await get_current_user_ws(token, db)
            user_id = str(user.id)
        except Exception as e:
            logger.error(f"認証エラー: {e}")
            await websocket.close(code=4003, reason="認証に失敗しました")
            return
            
        # セッションの存在確認
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            await websocket.close(code=4004, reason="セッションが見つかりません")
            return
            
        # WebSocket接続を確立
        connection_id = await manager.connect(websocket, user_id, session_id)
        
        # 接続成功メッセージを送信
        welcome_msg = WebSocketMessage(
            MessageType.SYSTEM,
            {
                "message": f"セッション {session.name} に接続しました",
                "connection_id": connection_id,
                "session_info": {
                    "id": session.id,
                    "name": session.name,
                    "status": session.status
                }
            },
            user_id=user_id,
            session_id=session_id
        )
        await manager.send_personal_message(welcome_msg.to_dict(), connection_id)
        
        # メッセージループ
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                message = WebSocketMessage.from_dict(message_data)
                message.user_id = user_id
                message.session_id = session_id
                
                # メッセージタイプに応じて処理
                if message.type == MessageType.CHAT:
                    await websocket_handler.handle_chat_message(message, db)
                elif message.type == MessageType.TERMINAL:
                    await websocket_handler.handle_terminal_message(message, db)
                else:
                    logger.warning(f"未対応のメッセージタイプ: {message.type}")
                    
            except json.JSONDecodeError:
                error_msg = WebSocketMessage(
                    MessageType.ERROR,
                    {"error": "無効なJSONフォーマットです"},
                    session_id=session_id
                )
                await manager.send_personal_message(error_msg.to_dict(), connection_id)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket接続が切断されました: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocketエラー: {e}")
    finally:
        if connection_id and user_id:
            manager.disconnect(connection_id, user_id, session_id)

@router.get("/ws/status")
async def websocket_status():
    """
WebSocketサービスの状態を取得
    """
    return {
        "active_connections": manager.get_connection_count(),
        "active_sessions": manager.get_active_sessions(),
        "status": "running"
    }
