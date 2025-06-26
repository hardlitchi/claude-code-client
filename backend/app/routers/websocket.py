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
            stream = message.data.get("stream", True)  # デフォルトでストリーミング
            
            if not user_message:
                return
                
            # ユーザーメッセージをセッション内にブロードキャスト
            user_msg = WebSocketMessage(
                MessageType.CHAT,
                {
                    "message": user_message,
                    "sender": "user",
                    "user_id": message.user_id,
                    "timestamp": datetime.now().isoformat()
                },
                user_id=message.user_id,
                session_id=message.session_id
            )
            await manager.broadcast_to_session(user_msg.to_dict(), message.session_id)
            
            # Claude Code統合でストリーミング応答を処理
            if stream:
                await self._handle_claude_streaming(user_message, message.session_id)
            else:
                claude_response = await self._get_claude_response(user_message, message.session_id)
                # Claudeのレスポンスをセッション内にブロードキャスト
                claude_msg = WebSocketMessage(
                    MessageType.CHAT,
                    {
                        "message": claude_response,
                        "sender": "claude",
                        "model": "claude-code",
                        "timestamp": datetime.now().isoformat()
                    },
                    session_id=message.session_id
                )
                await manager.broadcast_to_session(claude_msg.to_dict(), message.session_id)
            
        except Exception as e:
            logger.error(f"チャットメッセージ処理エラー: {e}")
            error_msg = WebSocketMessage(
                MessageType.ERROR,
                {"error": f"メッセージの処理中にエラーが発生しました: {str(e)}"},
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
            
    async def _get_claude_response(self, message: str, session_id: str) -> str:
        """Claude Codeからレスポンスを取得"""
        try:
            response = await self.claude_integration.send_message(message, session_id)
            return response
        except Exception as e:
            logger.error(f"Claude応答取得エラー: {e}")
            return f"エラー: Claude Code統合でエラーが発生しました - {str(e)}"
    
    async def _handle_claude_streaming(self, message: str, session_id: str):
        """Claude Codeからのストリーミング応答を処理"""
        try:
            chunk_buffer = ""
            async for chunk in self.claude_integration.send_message_stream(message, session_id):
                chunk_buffer += chunk
                
                # チャンクをWebSocketでブロードキャスト
                stream_msg = WebSocketMessage(
                    MessageType.CHAT,
                    {
                        "message_chunk": chunk,
                        "sender": "claude",
                        "model": "claude-code",
                        "streaming": True,
                        "timestamp": datetime.now().isoformat()
                    },
                    session_id=session_id
                )
                await manager.broadcast_to_session(stream_msg.to_dict(), session_id)
            
            # ストリーミング完了メッセージ
            complete_msg = WebSocketMessage(
                MessageType.CHAT,
                {
                    "message": chunk_buffer,
                    "sender": "claude",
                    "model": "claude-code",
                    "streaming": False,
                    "complete": True,
                    "timestamp": datetime.now().isoformat()
                },
                session_id=session_id
            )
            await manager.broadcast_to_session(complete_msg.to_dict(), session_id)
            
        except Exception as e:
            logger.error(f"Claude ストリーミング処理エラー: {e}")
            error_msg = WebSocketMessage(
                MessageType.ERROR,
                {"error": f"Claude ストリーミング処理でエラーが発生しました: {str(e)}"},
                session_id=session_id
            )
            await manager.broadcast_to_session(error_msg.to_dict(), session_id)
        
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
        client_info = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "不明"
        logger.info(f"WebSocket接続試行: session_id={session_id}, client={client_info}, token={'有り' if token else '無し'}")
        
        # 事前検証（acceptする前に実行）
        # 認証確認
        if not token:
            logger.warning("認証トークンが提供されていません")
            return  # acceptせずに終了
            
        try:
            user = await get_current_user_ws(token, db)
            user_id = str(user.id)
        except Exception as e:
            logger.error(f"認証エラー: {e}")
            return  # acceptせずに終了
            
        # セッションの存在確認（session_idで検索）
        session = db.query(Session).filter(Session.session_id == session_id).first()
        if not session:
            logger.warning(f"セッションが見つかりません: session_id={session_id}")
            return  # acceptせずに終了
            
        # すべての検証が通った場合のみWebSocket接続を受け入れ
        await websocket.accept()
        logger.info(f"WebSocket接続を受け入れました: session_id={session_id}, user_id={user_id}")
            
        # WebSocket接続を確立
        connection_id = await manager.connect(websocket, user_id, session_id)
        logger.info(f"WebSocket接続成功: connection_id={connection_id}, user_id={user_id}, session_id={session_id}")
        
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
        # エラーが発生した場合、接続が確立されていればcloseする
        try:
            if connection_id:  # 接続が確立されていた場合
                await websocket.close(code=1011, reason="内部サーバーエラー")
        except Exception:
            pass  # すでに閉じられている場合は無視
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
