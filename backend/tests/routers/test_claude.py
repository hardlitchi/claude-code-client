"""
claude ルーターのテスト
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import uuid


@pytest.mark.api
class TestClaudeRouter:
    """Claudeルーターのテスト"""
    
    def test_start_claude_session_success(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude セッション開始成功のテスト"""
        # まずDBセッションを作成
        session_data = {"name": "Claude Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]
        
        # Claude セッション開始をモック
        mock_claude_session = AsyncMock()
        mock_claude_manager.create_session.return_value = mock_claude_session
        
        # Claude セッション開始
        response = client.post(f"/api/claude/sessions/{session_id}/start", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "開始しました" in data["message"]
        assert data["data"]["session_id"] == session_id
        assert data["data"]["status"] == "running"
        
        # モックが呼ばれたことを確認
        mock_claude_manager.create_session.assert_called_once()
    
    def test_start_claude_session_not_found(self, client: TestClient, auth_headers):
        """存在しないセッションでのClaude セッション開始テスト"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.post(f"/api/claude/sessions/{fake_session_id}/start", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "セッションが見つかりません" in data["detail"]
    
    def test_start_claude_session_no_auth(self, client: TestClient):
        """認証なしでのClaude セッション開始テスト"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.post(f"/api/claude/sessions/{fake_session_id}/start")
        
        assert response.status_code == 403
    
    def test_start_claude_session_error(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude セッション開始エラーのテスト"""
        # DBセッションを作成
        session_data = {"name": "Error Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # Claude セッション開始でエラーを発生させる
        mock_claude_manager.create_session.side_effect = Exception("Claude session error")
        
        response = client.post(f"/api/claude/sessions/{session_id}/start", headers=auth_headers)
        
        assert response.status_code == 500
        data = response.json()
        assert "Claude セッション開始エラー" in data["detail"]
    
    def test_stop_claude_session_success(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude セッション停止成功のテスト"""
        # DBセッションを作成
        session_data = {"name": "Stop Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # Claude セッション停止をモック
        mock_claude_manager.remove_session.return_value = True
        
        response = client.post(f"/api/claude/sessions/{session_id}/stop", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "停止しました" in data["message"]
        assert data["data"]["session_id"] == session_id
        assert data["data"]["status"] == "stopped"
        
        # モックが呼ばれたことを確認
        mock_claude_manager.remove_session.assert_called_once_with(session_id)
    
    def test_stop_claude_session_not_found(self, client: TestClient, auth_headers):
        """存在しないセッションでのClaude セッション停止テスト"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.post(f"/api/claude/sessions/{fake_session_id}/stop", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "セッションが見つかりません" in data["detail"]
    
    def test_send_message_success(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude メッセージ送信成功のテスト"""
        # DBセッションを作成
        session_data = {"name": "Message Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # Claude セッションをモック
        mock_claude_session = AsyncMock()
        mock_claude_session.send_message.return_value = "Claude: Hello response"
        mock_claude_session.messages = [
            {"sender": "user", "content": "Hello", "timestamp": "2023-01-01T00:00:00"},
            {"sender": "claude", "content": "Claude: Hello response", "timestamp": "2023-01-01T00:00:01"}
        ]
        mock_claude_manager.get_session.return_value = mock_claude_session
        
        # メッセージ送信
        message_data = {"message": "Hello Claude"}
        response = client.post(
            f"/api/claude/sessions/{session_id}/message",
            json=message_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "送信しました" in data["message"]
        assert data["user_message"] == "Hello Claude"
        assert data["claude_response"] == "Claude: Hello response"
        assert "timestamp" in data
        
        # モックが呼ばれたことを確認
        mock_claude_session.send_message.assert_called_once_with("Hello Claude")
    
    def test_send_message_empty(self, client: TestClient, auth_headers):
        """空メッセージ送信のテスト"""
        # DBセッションを作成
        session_data = {"name": "Empty Message Test"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # 空メッセージ送信
        message_data = {"message": ""}
        response = client.post(
            f"/api/claude/sessions/{session_id}/message",
            json=message_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "メッセージが空です" in data["detail"]
    
    def test_send_message_no_claude_session(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude セッションが存在しない場合のメッセージ送信テスト"""
        # DBセッションを作成
        session_data = {"name": "No Claude Session Test"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # Claude セッションが存在しないことをモック
        mock_claude_manager.get_session.return_value = None
        
        message_data = {"message": "Hello"}
        response = client.post(
            f"/api/claude/sessions/{session_id}/message",
            json=message_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Claude セッションが見つかりません" in data["detail"]
    
    def test_get_claude_messages_success(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude メッセージ履歴取得成功のテスト"""
        # DBセッションを作成
        session_data = {"name": "Messages Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # Claude セッションをモック
        mock_claude_session = AsyncMock()
        mock_messages = [
            {"sender": "user", "content": "Hello", "timestamp": "2023-01-01T00:00:00"},
            {"sender": "claude", "content": "Hi there!", "timestamp": "2023-01-01T00:00:01"},
            {"sender": "user", "content": "How are you?", "timestamp": "2023-01-01T00:00:02"}
        ]
        mock_claude_session.get_message_history.return_value = mock_messages
        mock_claude_manager.get_session.return_value = mock_claude_session
        
        response = client.get(f"/api/claude/sessions/{session_id}/messages", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "total" in data
        assert data["total"] == 3
        assert len(data["messages"]) == 3
        assert data["messages"][0]["sender"] == "user"
        assert data["messages"][1]["sender"] == "claude"
    
    def test_get_claude_messages_no_session(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude セッションが存在しない場合のメッセージ履歴取得テスト"""
        # DBセッションを作成
        session_data = {"name": "No Messages Test"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # Claude セッションが存在しないことをモック
        mock_claude_manager.get_session.return_value = None
        
        response = client.get(f"/api/claude/sessions/{session_id}/messages", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["total"] == 0
    
    def test_get_claude_session_status_active(self, client: TestClient, auth_headers, mock_claude_manager):
        """アクティブなClaude セッション状態取得のテスト"""
        session_id = str(uuid.uuid4())
        
        # Claude セッションをモック
        mock_claude_session = AsyncMock()
        mock_claude_session.is_active = True
        mock_claude_session.messages = [{"msg": "test"}]
        mock_claude_session.created_at.isoformat.return_value = "2023-01-01T00:00:00"
        mock_claude_session.working_directory = "/test/dir"
        mock_claude_manager.get_session.return_value = mock_claude_session
        
        response = client.get(f"/api/claude/sessions/{session_id}/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["is_active"] is True
        assert data["message_count"] == 1
        assert data["created_at"] == "2023-01-01T00:00:00"
        assert data["working_directory"] == "/test/dir"
    
    def test_get_claude_session_status_inactive(self, client: TestClient, auth_headers, mock_claude_manager):
        """非アクティブなClaude セッション状態取得のテスト"""
        session_id = str(uuid.uuid4())
        
        # Claude セッションが存在しないことをモック
        mock_claude_manager.get_session.return_value = None
        
        response = client.get(f"/api/claude/sessions/{session_id}/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["is_active"] is False
        assert data["message_count"] == 0


@pytest.mark.api
class TestClaudeRouterIntegration:
    """Claudeルーターの統合テスト"""
    
    def test_claude_session_lifecycle(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude セッションライフサイクルの統合テスト"""
        # 1. DBセッション作成
        session_data = {"name": "Lifecycle Test"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]
        
        # 2. Claude セッション開始
        mock_claude_session = AsyncMock()
        mock_claude_manager.create_session.return_value = mock_claude_session
        
        start_response = client.post(f"/api/claude/sessions/{session_id}/start", headers=auth_headers)
        assert start_response.status_code == 200
        
        # 3. メッセージ送信
        mock_claude_session.send_message.return_value = "Response"
        mock_claude_session.messages = [{"timestamp": "2023-01-01T00:00:00"}]
        mock_claude_manager.get_session.return_value = mock_claude_session
        
        message_response = client.post(
            f"/api/claude/sessions/{session_id}/message",
            json={"message": "Hello"},
            headers=auth_headers
        )
        assert message_response.status_code == 200
        
        # 4. メッセージ履歴取得
        mock_claude_session.get_message_history.return_value = [
            {"sender": "user", "content": "Hello", "timestamp": "2023-01-01T00:00:00"}
        ]
        
        messages_response = client.get(f"/api/claude/sessions/{session_id}/messages", headers=auth_headers)
        assert messages_response.status_code == 200
        
        # 5. セッション状態確認
        mock_claude_session.is_active = True
        mock_claude_session.created_at.isoformat.return_value = "2023-01-01T00:00:00"
        mock_claude_session.working_directory = "/test"
        
        status_response = client.get(f"/api/claude/sessions/{session_id}/status", headers=auth_headers)
        assert status_response.status_code == 200
        
        # 6. Claude セッション停止
        mock_claude_manager.remove_session.return_value = True
        
        stop_response = client.post(f"/api/claude/sessions/{session_id}/stop", headers=auth_headers)
        assert stop_response.status_code == 200
    
    def test_claude_session_permission_isolation(self, client: TestClient, auth_headers, admin_headers, mock_claude_manager):
        """Claude セッションの権限分離テスト"""
        # ユーザー1のDBセッション作成
        user1_session = {"name": "User1 Claude Session"}
        user1_response = client.post("/api/sessions/", json=user1_session, headers=auth_headers)
        user1_session_id = user1_response.json()["session_id"]
        
        # 管理者のDBセッション作成
        admin_session = {"name": "Admin Claude Session"}
        admin_response = client.post("/api/sessions/", json=admin_session, headers=admin_headers)
        admin_session_id = admin_response.json()["session_id"]
        
        # ユーザー1は自分のセッションのみ操作可能
        mock_claude_manager.create_session.return_value = AsyncMock()
        
        # 自分のセッション開始（成功）
        user1_start = client.post(f"/api/claude/sessions/{user1_session_id}/start", headers=auth_headers)
        assert user1_start.status_code == 200
        
        # 管理者のセッション開始試行（失敗）
        user1_start_admin = client.post(f"/api/claude/sessions/{admin_session_id}/start", headers=auth_headers)
        assert user1_start_admin.status_code == 404  # セッションが見つからない
    
    def test_claude_error_handling(self, client: TestClient, auth_headers, mock_claude_manager):
        """Claude エラーハンドリングのテスト"""
        # DBセッション作成
        session_data = {"name": "Error Handling Test"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # 様々なエラーケースをテスト
        error_cases = [
            ("create_session", Exception("Creation failed")),
            ("remove_session", Exception("Removal failed")),
            ("get_session", Exception("Get session failed"))
        ]
        
        for method_name, error in error_cases:
            # エラーを設定
            getattr(mock_claude_manager, method_name).side_effect = error
            
            if method_name == "create_session":
                response = client.post(f"/api/claude/sessions/{session_id}/start", headers=auth_headers)
            elif method_name == "remove_session":
                response = client.post(f"/api/claude/sessions/{session_id}/stop", headers=auth_headers)
            else:  # get_session
                response = client.get(f"/api/claude/sessions/{session_id}/status", headers=auth_headers)
            
            assert response.status_code == 500
            assert "エラー" in response.json()["detail"]
            
            # エラーをリセット
            getattr(mock_claude_manager, method_name).side_effect = None