"""
auth ルーターのテスト
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.auth import get_password_hash


@pytest.mark.api
class TestAuthRouter:
    """認証ルーターのテスト"""
    
    def test_login_success(self, client: TestClient, test_user):
        """正常ログインのテスト"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["expires_in"] == 24 * 3600  # 24時間
    
    def test_login_invalid_credentials(self, client: TestClient, test_user):
        """無効な認証情報でのログインテスト"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "間違っています" in data["detail"]
    
    def test_login_nonexistent_user(self, client: TestClient):
        """存在しないユーザーでのログインテスト"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "password"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_login_missing_fields(self, client: TestClient):
        """必須フィールド不足のログインテスト"""
        # パスワード不足
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser"}
        )
        assert response.status_code == 422
        
        # ユーザー名不足
        response = client.post(
            "/api/auth/login",
            json={"password": "password"}
        )
        assert response.status_code == 422
    
    def test_register_success(self, client: TestClient):
        """正常ユーザー登録のテスト"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": "password123",
                "email": "new@example.com"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "ユーザー登録が完了しました"
        assert "data" in data
        assert data["data"]["username"] == "newuser"
        assert "user_id" in data["data"]
    
    def test_register_without_email(self, client: TestClient):
        """メールアドレスなしでのユーザー登録テスト"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser2",
                "password": "password123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "ユーザー登録が完了しました"
        assert data["data"]["username"] == "newuser2"
    
    def test_register_duplicate_username(self, client: TestClient, test_user):
        """重複ユーザー名での登録テスト"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",  # 既存ユーザー名
                "password": "password123",
                "email": "another@example.com"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "既に使用されています" in data["detail"]
    
    def test_register_missing_fields(self, client: TestClient):
        """必須フィールド不足の登録テスト"""
        # パスワード不足
        response = client.post(
            "/api/auth/register",
            json={"username": "newuser"}
        )
        assert response.status_code == 422
        
        # ユーザー名不足
        response = client.post(
            "/api/auth/register",
            json={"password": "password123"}
        )
        assert response.status_code == 422
    
    def test_register_empty_username(self, client: TestClient):
        """空のユーザー名での登録テスト"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "",
                "password": "password123"
            }
        )
        assert response.status_code == 422
    
    def test_register_empty_password(self, client: TestClient):
        """空のパスワードでの登録テスト"""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "password": ""
            }
        )
        assert response.status_code == 422
    
    def test_oauth2_token_success(self, client: TestClient, test_user):
        """OAuth2形式のトークン取得成功テスト"""
        response = client.post(
            "/api/auth/token",
            data={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_oauth2_token_invalid_credentials(self, client: TestClient, test_user):
        """OAuth2形式の無効な認証情報テスト"""
        response = client.post(
            "/api/auth/token",
            data={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_oauth2_token_missing_fields(self, client: TestClient):
        """OAuth2形式の必須フィールド不足テスト"""
        # パスワード不足
        response = client.post(
            "/api/auth/token",
            data={"username": "testuser"}
        )
        assert response.status_code == 422
        
        # ユーザー名不足
        response = client.post(
            "/api/auth/token",
            data={"password": "password"}
        )
        assert response.status_code == 422


@pytest.mark.api
class TestAuthRouterIntegration:
    """認証ルーターの統合テスト"""
    
    def test_login_register_flow(self, client: TestClient):
        """ユーザー登録→ログインのフローテスト"""
        # 1. ユーザー登録
        register_response = client.post(
            "/api/auth/register",
            json={
                "username": "flowtest",
                "password": "password123",
                "email": "flow@example.com"
            }
        )
        assert register_response.status_code == 200
        
        # 2. 登録したユーザーでログイン
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "flowtest",
                "password": "password123"
            }
        )
        assert login_response.status_code == 200
        
        login_data = login_response.json()
        assert "access_token" in login_data
        assert login_data["token_type"] == "bearer"
    
    def test_multiple_login_attempts(self, client: TestClient, test_user):
        """複数回ログイン試行のテスト"""
        # 正常ログイン
        response1 = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        assert response1.status_code == 200
        token1 = response1.json()["access_token"]
        
        # 再度ログイン（異なるトークンが生成される）
        response2 = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        assert response2.status_code == 200
        token2 = response2.json()["access_token"]
        
        # トークンは異なる
        assert token1 != token2
    
    def test_case_sensitive_username(self, client: TestClient, test_user):
        """ユーザー名の大文字小文字区別テスト"""
        # 正しいケース
        response1 = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        assert response1.status_code == 200
        
        # 大文字ケース（失敗）
        response2 = client.post(
            "/api/auth/login",
            json={
                "username": "TESTUSER",
                "password": "testpassword"
            }
        )
        assert response2.status_code == 401
    
    def test_token_format_validation(self, client: TestClient, test_user):
        """トークンフォーマットの検証テスト"""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # トークンの形式チェック（JWT形式）
        token = data["access_token"]
        parts = token.split(".")
        assert len(parts) == 3  # header.payload.signature
        
        # expires_in の値チェック
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0
    
    def test_concurrent_registrations(self, client: TestClient):
        """並行ユーザー登録のテスト"""
        import threading
        import time
        
        results = []
        
        def register_user(username):
            try:
                response = client.post(
                    "/api/auth/register",
                    json={
                        "username": username,
                        "password": "password123"
                    }
                )
                results.append((username, response.status_code))
            except Exception as e:
                results.append((username, str(e)))
        
        # 異なるユーザー名で並行登録
        threads = []
        for i in range(5):
            thread = threading.Thread(target=register_user, args=(f"concurrent_user_{i}",))
            threads.append(thread)
            thread.start()
        
        # すべてのスレッドが完了するまで待機
        for thread in threads:
            thread.join()
        
        # すべて成功することを確認
        for username, status_code in results:
            assert status_code == 200