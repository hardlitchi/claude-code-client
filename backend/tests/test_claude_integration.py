"""
claude_integration.py のテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.claude_integration import (
    ClaudeCodeSession, ClaudeIntegrationManager, claude_manager
)


@pytest.mark.unit
class TestClaudeCodeSession:
    """ClaudeCodeSessionクラスのテスト"""
    
    def test_session_initialization(self):
        """セッション初期化のテスト"""
        session_id = "test-session-123"
        working_dir = "/test/directory"
        
        session = ClaudeCodeSession(session_id, working_dir)
        
        assert session.session_id == session_id
        assert session.working_directory == working_dir
        assert session.is_active is False
        assert isinstance(session.created_at, datetime)
        assert session.messages == []
    
    @pytest.mark.asyncio
    async def test_start_session_success(self):
        """セッション開始成功のテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        
        result = await session.start_session()
        
        assert result is True
        assert session.is_active is True
        assert len(session.messages) == 1
        assert session.messages[0]["sender"] == "system"
        assert "開始されました" in session.messages[0]["content"]
    
    @pytest.mark.asyncio
    async def test_start_session_failure(self):
        """セッション開始失敗のテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        
        # start_sessionメソッドで例外を発生させるようにモック
        with patch.object(session, 'add_message', side_effect=Exception("Test error")):
            result = await session.start_session()
            
            assert result is False
            assert session.is_active is False
    
    @pytest.mark.asyncio
    async def test_stop_session_success(self):
        """セッション停止成功のテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        session.is_active = True
        
        result = await session.stop_session()
        
        assert result is True
        assert session.is_active is False
        assert len(session.messages) == 1
        assert session.messages[0]["sender"] == "system"
        assert "停止されました" in session.messages[0]["content"]
    
    @pytest.mark.asyncio
    async def test_stop_session_failure(self):
        """セッション停止失敗のテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        session.is_active = True
        
        # stop_sessionメソッドで例外を発生させるようにモック
        with patch.object(session, 'add_message', side_effect=Exception("Test error")):
            result = await session.stop_session()
            
            assert result is False
            assert session.is_active is True
    
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """メッセージ送信成功のテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        message = "Hello Claude"
        
        response = await session.send_message(message)
        
        assert isinstance(response, str)
        assert "Claude:" in response
        assert message in response
        assert len(session.messages) == 2  # user message + claude response
        assert session.messages[0]["sender"] == "user"
        assert session.messages[0]["content"] == message
        assert session.messages[1]["sender"] == "claude"
        assert session.messages[1]["content"] == response
    
    @pytest.mark.asyncio
    async def test_send_message_failure(self):
        """メッセージ送信失敗のテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        
        # add_messageメソッドで例外を発生させる
        with patch.object(session, 'add_message', side_effect=Exception("Test error")):
            response = await session.send_message("test message")
            
            assert "エラー" in response
            assert "Test error" in response
    
    def test_add_message(self):
        """メッセージ追加のテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        
        session.add_message("user", "Test message")
        
        assert len(session.messages) == 1
        message = session.messages[0]
        assert message["sender"] == "user"
        assert message["content"] == "Test message"
        assert "timestamp" in message
        assert isinstance(message["timestamp"], str)
    
    def test_get_message_history(self):
        """メッセージ履歴取得のテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        
        # メッセージを追加
        session.add_message("user", "Message 1")
        session.add_message("claude", "Response 1")
        session.add_message("user", "Message 2")
        
        history = session.get_message_history()
        
        assert len(history) == 3
        assert history[0]["content"] == "Message 1"
        assert history[1]["content"] == "Response 1"
        assert history[2]["content"] == "Message 2"
        
        # コピーが返されることを確認（元の配列は変更されない）
        history.clear()
        assert len(session.messages) == 3
    
    def test_message_timestamp_format(self):
        """メッセージタイムスタンプフォーマットのテスト"""
        session = ClaudeCodeSession("test-session", "/test/dir")
        
        session.add_message("user", "Test message")
        
        timestamp = session.messages[0]["timestamp"]
        # ISO フォーマットの確認
        datetime.fromisoformat(timestamp)  # 例外が発生しなければOK


@pytest.mark.unit
class TestClaudeIntegrationManager:
    """ClaudeIntegrationManagerクラスのテスト"""
    
    def test_manager_initialization(self):
        """マネージャー初期化のテスト"""
        manager = ClaudeIntegrationManager()
        
        assert isinstance(manager.active_sessions, dict)
        assert len(manager.active_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """セッション作成成功のテスト"""
        manager = ClaudeIntegrationManager()
        session_id = "test-session-123"
        working_dir = "/test/dir"
        
        session = await manager.create_session(session_id, working_dir)
        
        assert isinstance(session, ClaudeCodeSession)
        assert session.session_id == session_id
        assert session.working_directory == working_dir
        assert session.is_active is True
        assert session_id in manager.active_sessions
        assert manager.active_sessions[session_id] == session
    
    @pytest.mark.asyncio
    async def test_create_session_duplicate(self):
        """重複セッション作成のテスト"""
        manager = ClaudeIntegrationManager()
        session_id = "test-session-123"
        
        # 最初のセッションを作成
        await manager.create_session(session_id, "/test/dir1")
        
        # 同じIDでセッションを作成しようとすると例外が発生
        with pytest.raises(ValueError) as exc_info:
            await manager.create_session(session_id, "/test/dir2")
        
        assert "既に存在します" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_session_exists(self):
        """存在するセッション取得のテスト"""
        manager = ClaudeIntegrationManager()
        session_id = "test-session-123"
        
        # セッションを作成
        created_session = await manager.create_session(session_id, "/test/dir")
        
        # セッションを取得
        retrieved_session = await manager.get_session(session_id)
        
        assert retrieved_session == created_session
        assert retrieved_session.session_id == session_id
    
    @pytest.mark.asyncio
    async def test_get_session_not_exists(self):
        """存在しないセッション取得のテスト"""
        manager = ClaudeIntegrationManager()
        
        session = await manager.get_session("nonexistent-session")
        
        assert session is None
    
    @pytest.mark.asyncio
    async def test_remove_session_success(self):
        """セッション削除成功のテスト"""
        manager = ClaudeIntegrationManager()
        session_id = "test-session-123"
        
        # セッションを作成
        await manager.create_session(session_id, "/test/dir")
        assert session_id in manager.active_sessions
        
        # セッションを削除
        result = await manager.remove_session(session_id)
        
        assert result is True
        assert session_id not in manager.active_sessions
    
    @pytest.mark.asyncio
    async def test_remove_session_not_exists(self):
        """存在しないセッション削除のテスト"""
        manager = ClaudeIntegrationManager()
        
        result = await manager.remove_session("nonexistent-session")
        
        assert result is False
    
    def test_get_active_sessions_empty(self):
        """アクティブセッション一覧取得（空）のテスト"""
        manager = ClaudeIntegrationManager()
        
        sessions = manager.get_active_sessions()
        
        assert isinstance(sessions, list)
        assert len(sessions) == 0
    
    @pytest.mark.asyncio
    async def test_get_active_sessions_with_sessions(self):
        """アクティブセッション一覧取得（セッション有り）のテスト"""
        manager = ClaudeIntegrationManager()
        
        # 複数のセッションを作成
        session_ids = ["session-1", "session-2", "session-3"]
        for session_id in session_ids:
            await manager.create_session(session_id, f"/test/dir/{session_id}")
        
        active_sessions = manager.get_active_sessions()
        
        assert len(active_sessions) == 3
        assert set(active_sessions) == set(session_ids)
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        """セッションライフサイクルの統合テスト"""
        manager = ClaudeIntegrationManager()
        session_id = "lifecycle-test-session"
        
        # 1. セッション作成
        session = await manager.create_session(session_id, "/test/dir")
        assert session.is_active is True
        assert len(manager.get_active_sessions()) == 1
        
        # 2. メッセージ送信
        response = await session.send_message("Hello")
        assert "Claude:" in response
        assert len(session.get_message_history()) == 2
        
        # 3. セッション停止
        stop_result = await session.stop_session()
        assert stop_result is True
        assert session.is_active is False
        
        # 4. セッション削除
        remove_result = await manager.remove_session(session_id)
        assert remove_result is True
        assert len(manager.get_active_sessions()) == 0


@pytest.mark.unit
class TestGlobalClaudeManager:
    """グローバルclaude_managerのテスト"""
    
    def test_global_manager_exists(self):
        """グローバルマネージャーの存在確認"""
        assert claude_manager is not None
        assert isinstance(claude_manager, ClaudeIntegrationManager)
    
    def test_global_manager_singleton(self):
        """グローバルマネージャーがシングルトンであることの確認"""
        from app.claude_integration import claude_manager as manager2
        assert claude_manager is manager2
    
    @pytest.mark.asyncio
    async def test_global_manager_functionality(self):
        """グローバルマネージャーの機能テスト"""
        # テスト用にクリーンアップ
        for session_id in list(claude_manager.active_sessions.keys()):
            await claude_manager.remove_session(session_id)
        
        session_id = "global-test-session"
        
        # セッション作成
        session = await claude_manager.create_session(session_id, "/test/dir")
        assert session is not None
        
        # セッション取得
        retrieved = await claude_manager.get_session(session_id)
        assert retrieved == session
        
        # クリーンアップ
        await claude_manager.remove_session(session_id)


@pytest.mark.integration
class TestClaudeIntegrationError:
    """Claude統合エラー処理のテスト"""
    
    @pytest.mark.asyncio
    async def test_session_creation_with_invalid_directory(self):
        """無効なディレクトリでのセッション作成テスト"""
        manager = ClaudeIntegrationManager()
        
        # 現在の実装では無効なディレクトリでもセッションが作成される
        # （実際のClaude Code統合時にバリデーションが必要）
        session = await manager.create_session("test", "/invalid/directory")
        assert session is not None
        assert session.working_directory == "/invalid/directory"
        
        # クリーンアップ
        await manager.remove_session("test")
    
    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self):
        """並行セッション操作のテスト"""
        import asyncio
        
        manager = ClaudeIntegrationManager()
        
        # 複数のセッションを並行で作成
        session_ids = [f"concurrent-{i}" for i in range(5)]
        
        async def create_session(session_id):
            return await manager.create_session(session_id, f"/test/{session_id}")
        
        # 並行でセッション作成
        sessions = await asyncio.gather(*[create_session(sid) for sid in session_ids])
        
        assert len(sessions) == 5
        assert len(manager.get_active_sessions()) == 5
        
        # クリーンアップ
        for session_id in session_ids:
            await manager.remove_session(session_id)