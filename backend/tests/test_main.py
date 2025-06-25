"""
main.py のテスト
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.mark.integration
class TestMainApp:
    """メインアプリケーションの統合テスト"""
    
    def test_app_creation(self):
        """アプリケーション作成のテスト"""
        assert app is not None
        assert app.title == "Claude Code Client"
        assert app.version == "1.0.0"
        assert app.docs_url == "/api/docs"
        assert app.redoc_url == "/api/redoc"
    
    def test_root_endpoint(self, client: TestClient):
        """ルートエンドポイントのテスト"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Claude Code Client API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
    
    def test_health_endpoint(self, client: TestClient):
        """ヘルスチェックエンドポイントのテスト"""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_cors_headers(self, client: TestClient):
        """CORS設定のテスト"""
        # OPTIONSリクエストでCORSヘッダーを確認
        response = client.options("/api/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        
        # CORSが設定されていることを確認
        assert "access-control-allow-origin" in response.headers
    
    def test_openapi_docs_accessible(self, client: TestClient):
        """OpenAPI ドキュメントアクセス可能性のテスト"""
        response = client.get("/api/docs")
        assert response.status_code == 200
        
        response = client.get("/api/redoc")
        assert response.status_code == 200
    
    def test_openapi_json(self, client: TestClient):
        """OpenAPI JSON 仕様のテスト"""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert "paths" in openapi_data
        assert openapi_data["info"]["title"] == "Claude Code Client"
        assert openapi_data["info"]["version"] == "1.0.0"


@pytest.mark.integration
class TestRouterIntegration:
    """ルーター統合のテスト"""
    
    def test_auth_router_integration(self, client: TestClient):
        """認証ルーター統合のテスト"""
        # ユーザー登録
        register_data = {
            "username": "integration_test",
            "password": "password123",
            "email": "integration@example.com"
        }
        response = client.post("/api/auth/register", json=register_data)
        assert response.status_code == 200
        
        # ログイン
        login_data = {"username": "integration_test", "password": "password123"}
        response = client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        
        token = response.json()["access_token"]
        assert token is not None
    
    def test_users_router_integration(self, client: TestClient, auth_headers):
        """ユーザールーター統合のテスト"""
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        
        user_data = response.json()
        assert "username" in user_data
        assert "id" in user_data
    
    def test_sessions_router_integration(self, client: TestClient, auth_headers):
        """セッションルーター統合のテスト"""
        # セッション一覧取得
        response = client.get("/api/sessions/", headers=auth_headers)
        assert response.status_code == 200
        
        # セッション作成
        session_data = {"name": "Integration Test Session"}
        response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        assert response.status_code == 200
        
        session_id = response.json()["session_id"]
        
        # セッション取得
        response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert response.status_code == 200
    
    def test_terminal_router_integration(self, client: TestClient, auth_headers):
        """ターミナルルーター統合のテスト"""
        session_id = "test-terminal-session"
        
        response = client.get(f"/api/terminal/{session_id}/status", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["session_id"] == session_id
        assert "connected" in data
        assert "status" in data
    
    @patch('app.claude_integration.claude_manager')
    def test_claude_router_integration(self, mock_claude_manager, client: TestClient, auth_headers):
        """Claudeルーター統合のテスト"""
        # DBセッションを作成
        session_data = {"name": "Claude Integration Test"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        session_id = create_response.json()["session_id"]
        
        # Claude セッション状態取得
        mock_claude_manager.get_session.return_value = None
        
        response = client.get(f"/api/claude/sessions/{session_id}/status", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["session_id"] == session_id
        assert data["is_active"] is False


@pytest.mark.integration
class TestFullWorkflow:
    """完全なワークフローテスト"""
    
    def test_complete_user_session_workflow(self, client: TestClient):
        """完全なユーザーセッションワークフローのテスト"""
        # 1. ユーザー登録
        register_data = {
            "username": "workflow_user",
            "password": "workflow_password",
            "email": "workflow@example.com"
        }
        register_response = client.post("/api/auth/register", json=register_data)
        assert register_response.status_code == 200
        
        # 2. ログイン
        login_data = {"username": "workflow_user", "password": "workflow_password"}
        login_response = client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. ユーザー情報取得
        user_response = client.get("/api/users/me", headers=headers)
        assert user_response.status_code == 200
        user_data = user_response.json()
        assert user_data["username"] == "workflow_user"
        
        # 4. セッション作成
        session_data = {
            "name": "Workflow Test Session",
            "description": "Complete workflow test",
            "working_directory": "/test/workflow"
        }
        session_response = client.post("/api/sessions/", json=session_data, headers=headers)
        assert session_response.status_code == 200
        session_id = session_response.json()["session_id"]
        
        # 5. セッション開始
        start_response = client.post(f"/api/sessions/{session_id}/start", headers=headers)
        assert start_response.status_code == 200
        
        # 6. セッション状態確認
        status_response = client.get(f"/api/sessions/{session_id}", headers=headers)
        assert status_response.status_code == 200
        session_status = status_response.json()
        assert session_status["status"] == "running"
        
        # 7. ターミナル状態確認
        terminal_response = client.get(f"/api/terminal/{session_id}/status", headers=headers)
        assert terminal_response.status_code == 200
        
        # 8. Claude セッション状態確認
        claude_response = client.get(f"/api/claude/sessions/{session_id}/status", headers=headers)
        assert claude_response.status_code == 200
        
        # 9. セッション停止
        stop_response = client.post(f"/api/sessions/{session_id}/stop", headers=headers)
        assert stop_response.status_code == 200
        
        # 10. セッション削除
        delete_response = client.delete(f"/api/sessions/{session_id}", headers=headers)
        assert delete_response.status_code == 200


@pytest.mark.unit
class TestDatabaseInitialization:
    """データベース初期化のテスト"""
    
    @patch('app.main.init_database')
    def test_database_initialization_success(self, mock_init_db):
        """データベース初期化成功のテスト"""
        # init_database が成功することをモック
        mock_init_db.return_value = None
        
        # アプリケーションを再インポートして初期化をテスト
        import importlib
        from app import main
        importlib.reload(main)
        
        # init_database が呼ばれたことを確認
        mock_init_db.assert_called()
    
    @patch('app.main.init_database')
    @patch('app.main.logger')
    def test_database_initialization_failure(self, mock_logger, mock_init_db):
        """データベース初期化失敗のテスト"""
        # init_database でエラーを発生させる
        test_error = Exception("Database connection failed")
        mock_init_db.side_effect = test_error
        
        # アプリケーション初期化時に例外が発生することを確認
        with pytest.raises(Exception) as exc_info:
            import importlib
            from app import main
            importlib.reload(main)
        
        assert str(exc_info.value) == "Database connection failed"
        mock_logger.error.assert_called_with(f"Database initialization failed: {test_error}")


@pytest.mark.integration
class TestErrorHandling:
    """エラーハンドリングのテスト"""
    
    def test_404_handling(self, client: TestClient):
        """404エラーハンドリングのテスト"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client: TestClient):
        """Method Not Allowedエラーのテスト"""
        response = client.put("/")  # GETのみサポートするエンドポイントにPUT
        assert response.status_code == 405
    
    def test_invalid_json(self, client: TestClient):
        """無効なJSONのテスト"""
        response = client.post(
            "/api/auth/register",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_large_request_body(self, client: TestClient):
        """大きなリクエストボディのテスト"""
        # 非常に大きなデータを送信
        large_data = {"data": "x" * 10000}
        response = client.post("/api/auth/register", json=large_data)
        
        # バリデーションエラーまたはリクエストエラーが発生することを確認
        assert response.status_code in [400, 422, 413]


@pytest.mark.performance
class TestPerformance:
    """パフォーマンステスト"""
    
    def test_concurrent_requests(self, client: TestClient):
        """並行リクエストのテスト"""
        import threading
        import time
        
        results = []
        
        def make_request():
            start_time = time.time()
            response = client.get("/")
            end_time = time.time()
            results.append({
                "status_code": response.status_code,
                "response_time": end_time - start_time
            })
        
        # 10並行リクエスト
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # すべてのスレッドが完了するまで待機
        for thread in threads:
            thread.join()
        
        # すべてのリクエストが成功することを確認
        for result in results:
            assert result["status_code"] == 200
            assert result["response_time"] < 5.0  # 5秒以内
        
        assert len(results) == 10
    
    def test_health_endpoint_performance(self, client: TestClient):
        """ヘルスエンドポイントのパフォーマンステスト"""
        import time
        
        # 複数回実行して平均レスポンス時間を測定
        response_times = []
        
        for i in range(20):
            start_time = time.time()
            response = client.get("/api/health")
            end_time = time.time()
            
            assert response.status_code == 200
            response_times.append(end_time - start_time)
        
        average_time = sum(response_times) / len(response_times)
        assert average_time < 0.1  # 100ms以内の平均レスポンス時間