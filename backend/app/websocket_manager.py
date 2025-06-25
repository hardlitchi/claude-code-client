"""
WebSocket接続マネージャー
リアルタイム通信を管理するクラス
"""

from typing import Dict, List, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket接続を管理するクラス"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.session_connections: Dict[str, List[str]] = {}  # session_id -> [user_ids]
        
    async def connect(self, websocket: WebSocket, user_id: str, session_id: str):
        """WebSocket接続を受け入れ"""
        await websocket.accept()
        connection_id = f"{user_id}_{session_id}_{datetime.now().timestamp()}"
        
        self.active_connections[connection_id] = websocket
        self.user_sessions[user_id] = session_id
        
        if session_id not in self.session_connections:
            self.session_connections[session_id] = []
        if user_id not in self.session_connections[session_id]:
            self.session_connections[session_id].append(user_id)
            
        logger.info(f"WebSocket接続が確立されました: {connection_id}")
        return connection_id
        
    def disconnect(self, connection_id: str, user_id: str, session_id: str):
        """WebSocket接続を切断"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            
        if session_id in self.session_connections:
            if user_id in self.session_connections[session_id]:
                self.session_connections[session_id].remove(user_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
                
        logger.info(f"WebSocket接続が切断されました: {connection_id}")
        
    async def send_personal_message(self, message: dict, connection_id: str):
        """特定の接続にメッセージを送信"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(json.dumps(message, ensure_ascii=False))
            except Exception as e:
                logger.error(f"メッセージ送信エラー: {e}")
                
    async def send_to_user(self, message: dict, user_id: str):
        """特定のユーザーにメッセージを送信"""
        user_connections = [conn_id for conn_id in self.active_connections.keys() 
                           if conn_id.startswith(f"{user_id}_")]
        
        for connection_id in user_connections:
            await self.send_personal_message(message, connection_id)
            
    async def broadcast_to_session(self, message: dict, session_id: str):
        """セッション内の全ユーザーにメッセージをブロードキャスト"""
        if session_id in self.session_connections:
            for user_id in self.session_connections[session_id]:
                await self.send_to_user(message, user_id)
                
    async def broadcast_to_all(self, message: dict):
        """全接続にメッセージをブロードキャスト"""
        for connection_id in self.active_connections:
            await self.send_personal_message(message, connection_id)
            
    def get_active_sessions(self) -> List[str]:
        """アクティブなセッション一覧を取得"""
        return list(self.session_connections.keys())
        
    def get_session_users(self, session_id: str) -> List[str]:
        """セッション内のユーザー一覧を取得"""
        return self.session_connections.get(session_id, [])
        
    def get_connection_count(self) -> int:
        """アクティブな接続数を取得"""
        return len(self.active_connections)

# グローバルインスタンス
manager = ConnectionManager()

class MessageType:
    """メッセージタイプの定数"""
    CHAT = "chat"
    TERMINAL = "terminal"
    SYSTEM = "system"
    STATUS = "status"
    ERROR = "error"
    
class WebSocketMessage:
    """WebSocketメッセージの構造"""
    
    def __init__(self, message_type: str, data: dict, user_id: str = None, session_id: str = None):
        self.type = message_type
        self.data = data
        self.user_id = user_id
        self.session_id = session_id
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "data": self.data,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp
        }
        
    @classmethod
    def from_dict(cls, data: dict) -> 'WebSocketMessage':
        return cls(
            message_type=data.get("type"),
            data=data.get("data", {}),
            user_id=data.get("user_id"),
            session_id=data.get("session_id")
        )
