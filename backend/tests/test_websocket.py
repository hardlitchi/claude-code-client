"""
WebSocket機能のテスト
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.websocket_manager import ConnectionManager, MessageType, WebSocketMessage
from app.main import app
from app.models import User, Session

class TestConnectionManager:
    """ConnectionManagerのテスト"""
    
    def test_init(self):
        """ConnectionManagerの初期化テスト"""
        manager = ConnectionManager()
        assert len(manager.active_connections) == 0
        assert len(manager.user_sessions) == 0
        assert len(manager.session_connections) == 0
        
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """WebSocket接続と切断のテスト"""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        
        # 接続テスト
        connection_id = await manager.connect(mock_websocket, "user1", "session1")
        
        assert connection_id in manager.active_connections
        assert manager.user_sessions["user1"] == "session1"
        assert "user1" in manager.session_connections["session1"]
        assert manager.get_connection_count() == 1
        
        # 切断テスト
        manager.disconnect(connection_id, "user1", "session1")
        
        assert connection_id not in manager.active_connections
        assert "user1" not in manager.user_sessions
        assert len(manager.session_connections) == 0
        assert manager.get_connection_count() == 0
        
    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """Personalメッセージ送信テスト"""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()
        
        connection_id = await manager.connect(mock_websocket, "user1", "session1")
        message = {"type": "test", "data": "hello"}
        
        await manager.send_personal_message(message, connection_id)
        
        mock_websocket.send_text.assert_called_once_with(json.dumps(message, ensure_ascii=False))
        
    @pytest.mark.asyncio
    async def test_broadcast_to_session(self):
        """Sessionブロードキャストテスト"""
        manager = ConnectionManager()
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        
        # 複数ユーザーを同じセッションに接続
        connection_id1 = await manager.connect(mock_websocket1, "user1", "session1")
        connection_id2 = await manager.connect(mock_websocket2, "user2", "session1")
        
        message = {"type": "test", "data": "broadcast"}
        await manager.broadcast_to_session(message, "session1")
        
        expected_call = json.dumps(message, ensure_ascii=False)
        mock_websocket1.send_text.assert_called_with(expected_call)
        mock_websocket2.send_text.assert_called_with(expected_call)
        
    def test_get_active_sessions(self):
        """アクティブセッション取得テスト"""
        manager = ConnectionManager()
        manager.session_connections["session1"] = ["user1"]
        manager.session_connections["session2"] = ["user2"]
        
        active_sessions = manager.get_active_sessions()
        assert "session1" in active_sessions
        assert "session2" in active_sessions
        assert len(active_sessions) == 2
        
    def test_get_session_users(self):
        """セッションユーザー取得テスト"""
        manager = ConnectionManager()
        manager.session_connections["session1"] = ["user1", "user2"]
        
        users = manager.get_session_users("session1")
        assert "user1" in users
        assert "user2" in users
        assert len(users) == 2
        
        # 存在しないセッション
        empty_users = manager.get_session_users("nonexistent")
        assert len(empty_users) == 0

class TestWebSocketMessage:
    """WebSocketMessageのテスト"""
    
    def test_create_message(self):
        """WebSocketMessage作成テスト"""
        message = WebSocketMessage(
            MessageType.CHAT,
            {"text": "hello"},
            user_id="user1",
            session_id="session1"
        )
        
        assert message.type == MessageType.CHAT
        assert message.data["text"] == "hello"
        assert message.user_id == "user1"
        assert message.session_id == "session1"
        assert message.timestamp is not None
        
    def test_to_dict(self):
        """to_dictメソッドテスト"""
        message = WebSocketMessage(
            MessageType.TERMINAL,
            {"command": "ls"},
            user_id="user1"
        )
        
        dict_data = message.to_dict()
        
        assert dict_data["type"] == MessageType.TERMINAL
        assert dict_data["data"]["command"] == "ls"
        assert dict_data["user_id"] == "user1"
        assert "timestamp" in dict_data
        
    def test_from_dict(self):
        """from_dictメソッドテスト"""
        data = {
            "type": MessageType.SYSTEM,
            "data": {"status": "connected"},
            "user_id": "user1",
            "session_id": "session1"
        }
        
        message = WebSocketMessage.from_dict(data)
        
        assert message.type == MessageType.SYSTEM
        assert message.data["status"] == "connected"
        assert message.user_id == "user1"
        assert message.session_id == "session1"

class TestWebSocketAPI:
    """WebSocket APIのテスト"""
    
    def test_websocket_status_endpoint(self, client):
        """WebSocketステータスエンドポイントテスト"""
        response = client.get("/api/ws/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "active_sessions" in data
        assert "status" in data
        assert data["status"] == "running"

# MessageTypeのテスト
class TestMessageType:
    """MessageType定数のテスト"""
    
    def test_message_types(self):
        """メッセージタイプ定数のテスト"""
        assert MessageType.CHAT == "chat"
        assert MessageType.TERMINAL == "terminal"
        assert MessageType.SYSTEM == "system"
        assert MessageType.STATUS == "status"
        assert MessageType.ERROR == "error"
