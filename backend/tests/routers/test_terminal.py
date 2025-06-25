"""
terminal ルーターのテスト
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import uuid


@pytest.mark.api
class TestTerminalRouter:
    """Terminalルーターのテスト"""
    
    def test_get_terminal_status_inactive(self, client: TestClient, auth_headers):
        """非アクティブターミナル状態取得のテスト"""
        session_id = str(uuid.uuid4())
        
        response = client.get(f"/api/terminal/{session_id}/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["connected"] is False
        assert data["status"] == "inactive"
    
    def test_get_terminal_status_no_auth(self, client: TestClient):
        """認証なしでのターミナル状態取得テスト"""
        session_id = str(uuid.uuid4())
        
        response = client.get(f"/api/terminal/{session_id}/status")
        
        assert response.status_code == 403


@pytest.mark.unit
class TestTerminalManager:
    """TerminalManagerクラスのテスト"""
    
    def test_terminal_manager_init(self):
        """TerminalManager初期化のテスト"""
        from app.routers.terminal import TerminalManager
        
        session_id = "test-session"
        working_dir = "/test/dir"
        
        manager = TerminalManager(session_id, working_dir)
        
        assert manager.session_id == session_id
        assert manager.working_directory == working_dir
        assert manager.master_fd is None
        assert manager.slave_fd is None
        assert manager.process is None
    
    def test_terminal_manager_default_working_dir(self):
        """TerminalManagerデフォルト作業ディレクトリのテスト"""
        from app.routers.terminal import TerminalManager
        
        manager = TerminalManager("test-session")
        
        assert manager.working_directory == "/tmp"
    
    @patch('os.makedirs')
    @patch('pty.openpty')
    @patch('subprocess.Popen')
    @patch('os.write')
    @patch('asyncio.sleep')
    async def test_start_terminal_success(self, mock_sleep, mock_write, mock_popen, mock_openpty, mock_makedirs):
        """ターミナル開始成功のテスト"""
        from app.routers.terminal import TerminalManager
        
        # モック設定
        mock_openpty.return_value = (1, 2)  # master_fd, slave_fd
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_sleep.return_value = None
        
        manager = TerminalManager("test-session", "/test/dir")
        
        await manager.start_terminal()
        
        # ディレクトリ作成が呼ばれたことを確認
        mock_makedirs.assert_called_once_with("/test/dir", exist_ok=True)
        
        # pty.openpty が呼ばれたことを確認
        mock_openpty.assert_called_once()
        
        # プロセスが作成されたことを確認
        mock_popen.assert_called_once()
        
        # 初期化コマンドが送信されたことを確認
        assert mock_write.call_count >= 3  # 少なくとも3つのコマンド
        
        # TerminalManagerの状態確認
        assert manager.master_fd == 1
        assert manager.slave_fd == 2
        assert manager.process == mock_process
    
    @patch('os.makedirs')
    @patch('pty.openpty')
    async def test_start_terminal_error(self, mock_openpty, mock_makedirs):
        """ターミナル開始エラーのテスト"""
        from app.routers.terminal import TerminalManager
        
        # openptyでエラーを発生させる
        mock_openpty.side_effect = Exception("pty error")
        
        manager = TerminalManager("test-session")
        
        with pytest.raises(Exception) as exc_info:
            await manager.start_terminal()
        
        assert "pty error" in str(exc_info.value)
    
    @patch('select.select')
    @patch('os.read')
    async def test_read_output_success(self, mock_read, mock_select):
        """ターミナル出力読み取り成功のテスト"""
        from app.routers.terminal import TerminalManager
        
        # モック設定
        mock_select.return_value = ([1], [], [])  # master_fdが読み取り可能
        mock_read.return_value = b"test output"
        
        manager = TerminalManager("test-session")
        manager.master_fd = 1
        
        output = await manager.read_output()
        
        assert output == "test output"
        mock_select.assert_called_once_with([1], [], [], 0.1)
        mock_read.assert_called_once_with(1, 1024)
    
    @patch('select.select')
    async def test_read_output_no_data(self, mock_select):
        """ターミナル出力読み取り（データなし）のテスト"""
        from app.routers.terminal import TerminalManager
        
        # データなし
        mock_select.return_value = ([], [], [])
        
        manager = TerminalManager("test-session")
        manager.master_fd = 1
        
        output = await manager.read_output()
        
        assert output is None
    
    @patch('select.select')
    async def test_read_output_error(self, mock_select):
        """ターミナル出力読み取りエラーのテスト"""
        from app.routers.terminal import TerminalManager
        
        # selectでエラーを発生させる
        mock_select.side_effect = Exception("select error")
        
        manager = TerminalManager("test-session")
        manager.master_fd = 1
        
        output = await manager.read_output()
        
        assert output is None  # エラー時はNoneを返す
    
    @patch('os.write')
    async def test_write_input_success(self, mock_write):
        """ターミナル入力書き込み成功のテスト"""
        from app.routers.terminal import TerminalManager
        
        manager = TerminalManager("test-session")
        manager.master_fd = 1
        
        await manager.write_input("test command\n")
        
        mock_write.assert_called_once_with(1, b"test command\n")
    
    @patch('os.write')
    async def test_write_input_error(self, mock_write):
        """ターミナル入力書き込みエラーのテスト"""
        from app.routers.terminal import TerminalManager
        
        # writeでエラーを発生させる
        mock_write.side_effect = Exception("write error")
        
        manager = TerminalManager("test-session")
        manager.master_fd = 1
        
        # エラーが発生しても例外が上がらないことを確認
        await manager.write_input("test command")
    
    @patch('os.close')
    def test_cleanup_success(self, mock_close):
        """リソースクリーンアップ成功のテスト"""
        from app.routers.terminal import TerminalManager
        
        manager = TerminalManager("test-session")
        manager.master_fd = 1
        manager.slave_fd = 2
        
        # プロセスをモック
        mock_process = MagicMock()
        manager.process = mock_process
        
        manager.cleanup()
        
        # プロセス終了が呼ばれたことを確認
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        
        # ファイルディスクリプタが閉じられたことを確認
        assert mock_close.call_count == 2
        mock_close.assert_any_call(1)
        mock_close.assert_any_call(2)
    
    @patch('os.close')
    def test_cleanup_with_errors(self, mock_close):
        """エラーありでのリソースクリーンアップのテスト"""
        from app.routers.terminal import TerminalManager
        
        manager = TerminalManager("test-session")
        manager.master_fd = 1
        manager.slave_fd = 2
        
        # プロセス終了でエラーを発生させる
        mock_process = MagicMock()
        mock_process.terminate.side_effect = Exception("terminate error")
        mock_process.wait.side_effect = Exception("wait error")
        manager.process = mock_process
        
        # ファイルクローズでもエラーを発生させる
        mock_close.side_effect = Exception("close error")
        
        # エラーが発生しても例外が上がらないことを確認
        manager.cleanup()


@pytest.mark.integration
class TestTerminalWebSocket:
    """Terminal WebSocketの統合テスト"""
    
    def test_websocket_session_not_found(self, client: TestClient):
        """存在しないセッションでのWebSocket接続テスト"""
        fake_session_id = str(uuid.uuid4())
        
        with client.websocket_connect(f"/api/terminal/ws/{fake_session_id}") as websocket:
            data = websocket.receive_text()
            assert "セッションが見つかりません" in data
    
    @patch('app.routers.terminal.TerminalManager')
    def test_websocket_terminal_manager_creation(self, mock_terminal_manager_class, client: TestClient, db):
        """WebSocketでのTerminalManager作成テスト"""
        from app.models import Session as SessionModel
        
        # テストセッションをDBに作成
        db_session = SessionModel(
            session_id="test-session-id",
            name="WebSocket Test Session",
            working_directory="/test/dir",
            user_id=1,
            status="stopped"
        )
        db.add(db_session)
        db.commit()
        
        # TerminalManagerをモック
        mock_terminal = MagicMock()
        mock_terminal.start_terminal = AsyncMock()
        mock_terminal.read_output = AsyncMock(return_value=None)
        mock_terminal.write_input = AsyncMock()
        mock_terminal.cleanup = MagicMock()
        mock_terminal_manager_class.return_value = mock_terminal
        
        with client.websocket_connect("/api/terminal/ws/test-session-id") as websocket:
            # 初期メッセージを受信
            initial_message = websocket.receive_text()
            assert "Terminal connected to session" in initial_message
            
            # TerminalManagerが作成されたことを確認
            mock_terminal_manager_class.assert_called_once_with("test-session-id", "/test/dir")
            
            # start_terminalが呼ばれたことを確認
            mock_terminal.start_terminal.assert_called_once()


@pytest.mark.unit
class TestTerminalActiveConnections:
    """アクティブターミナル接続の管理テスト"""
    
    def test_active_terminals_dict(self):
        """active_terminals辞書の存在確認"""
        from app.routers.terminal import active_terminals
        
        assert isinstance(active_terminals, dict)
    
    def test_terminal_status_with_active_session(self, client: TestClient, auth_headers):
        """アクティブセッションありでのターミナル状態テスト"""
        from app.routers.terminal import active_terminals
        
        session_id = "active-test-session"
        
        # アクティブセッションを手動で追加
        active_terminals[session_id] = {
            'terminal': MagicMock(),
            'websocket': MagicMock()
        }
        
        try:
            response = client.get(f"/api/terminal/{session_id}/status", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert data["connected"] is True
            assert data["status"] == "active"
        
        finally:
            # クリーンアップ
            if session_id in active_terminals:
                del active_terminals[session_id]