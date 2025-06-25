"""
users ルーターのテスト
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestUsersRouter:
    """ユーザールーターのテスト"""
    
    def test_get_current_user_success(self, client: TestClient, auth_headers):
        """現在のユーザー情報取得成功のテスト"""
        response = client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["is_active"] is True
        assert data["is_admin"] is False
        assert "created_at" in data
    
    def test_get_current_user_no_auth(self, client: TestClient):
        """認証なしでの現在のユーザー情報取得テスト"""
        response = client.get("/api/users/me")
        
        assert response.status_code == 403  # HTTPBearerによる認証エラー
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """無効なトークンでの現在のユーザー情報取得テスト"""
        headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/api/users/me", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert "無効なトークンです" in data["detail"]
    
    def test_get_current_user_expired_token(self, client: TestClient):
        """期限切れトークンでの現在のユーザー情報取得テスト"""
        from jose import jwt
        from datetime import datetime, timedelta
        from app.auth import SECRET_KEY, ALGORITHM
        
        # 期限切れトークンを作成
        past_time = datetime.utcnow() - timedelta(hours=1)
        expired_payload = {"sub": "testuser", "exp": past_time}
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/users/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_get_user_by_id_own_user(self, client: TestClient, auth_headers, test_user):
        """自分のユーザー情報をIDで取得するテスト"""
        response = client.get(f"/api/users/{test_user.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
    
    def test_get_user_by_id_admin_access(self, client: TestClient, admin_headers, test_user):
        """管理者が他のユーザー情報を取得するテスト"""
        response = client.get(f"/api/users/{test_user.id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
    
    def test_get_user_by_id_forbidden(self, client: TestClient, auth_headers, admin_user):
        """一般ユーザーが他のユーザー情報を取得しようとするテスト"""
        response = client.get(f"/api/users/{admin_user.id}", headers=auth_headers)
        
        assert response.status_code == 403
        data = response.json()
        assert "権限がありません" in data["detail"]
    
    def test_get_user_by_id_not_found(self, client: TestClient, admin_headers):
        """存在しないユーザーIDでの取得テスト"""
        response = client.get("/api/users/999999", headers=admin_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "ユーザーが見つかりません" in data["detail"]
    
    def test_get_user_by_id_no_auth(self, client: TestClient, test_user):
        """認証なしでのユーザー情報取得テスト"""
        response = client.get(f"/api/users/{test_user.id}")
        
        assert response.status_code == 403
    
    def test_get_user_by_id_invalid_id_format(self, client: TestClient, auth_headers):
        """無効なID形式での取得テスト"""
        response = client.get("/api/users/invalid", headers=auth_headers)
        
        assert response.status_code == 422  # バリデーションエラー


@pytest.mark.api
class TestUsersRouterPermissions:
    """ユーザールーターの権限テスト"""
    
    def test_admin_can_access_any_user(self, client: TestClient, admin_headers, test_user, db):
        """管理者が任意のユーザーにアクセスできることのテスト"""
        # 追加のテストユーザーを作成
        from app.models import User
        from app.auth import get_password_hash
        
        another_user = User(
            username="another_user",
            email="another@example.com",
            hashed_password=get_password_hash("password"),
            is_active=True,
            is_admin=False
        )
        db.add(another_user)
        db.commit()
        db.refresh(another_user)
        
        # 管理者として他のユーザーの情報を取得
        response = client.get(f"/api/users/{another_user.id}", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "another_user"
    
    def test_user_cannot_access_other_users(self, client: TestClient, auth_headers, admin_user):
        """一般ユーザーが他のユーザーにアクセスできないことのテスト"""
        response = client.get(f"/api/users/{admin_user.id}", headers=auth_headers)
        
        assert response.status_code == 403
        data = response.json()
        assert "権限がありません" in data["detail"]
    
    def test_inactive_user_cannot_access(self, client: TestClient, db):
        """非アクティブユーザーがアクセスできないことのテスト"""
        from app.models import User
        from app.auth import get_password_hash, create_access_token
        
        # 非アクティブユーザーを作成
        inactive_user = User(
            username="inactive_user",
            hashed_password=get_password_hash("password"),
            is_active=False
        )
        db.add(inactive_user)
        db.commit()
        
        # 非アクティブユーザーのトークンを作成
        token = create_access_token({"sub": "inactive_user"})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/api/users/me", headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "無効なユーザーです" in data["detail"]


@pytest.mark.api
class TestUsersRouterIntegration:
    """ユーザールーターの統合テスト"""
    
    def test_user_info_consistency(self, client: TestClient, auth_headers, test_user):
        """ユーザー情報の一貫性テスト"""
        # /me エンドポイントでユーザー情報を取得
        me_response = client.get("/api/users/me", headers=auth_headers)
        assert me_response.status_code == 200
        me_data = me_response.json()
        
        # 同じユーザーをIDで取得
        id_response = client.get(f"/api/users/{test_user.id}", headers=auth_headers)
        assert id_response.status_code == 200
        id_data = id_response.json()
        
        # 両方のレスポンスが同じであることを確認
        assert me_data == id_data
    
    def test_user_data_format(self, client: TestClient, auth_headers):
        """ユーザーデータフォーマットのテスト"""
        response = client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # 必須フィールドの存在確認
        required_fields = ["id", "username", "is_active", "is_admin", "created_at"]
        for field in required_fields:
            assert field in data
        
        # データ型の確認
        assert isinstance(data["id"], int)
        assert isinstance(data["username"], str)
        assert isinstance(data["is_active"], bool)
        assert isinstance(data["is_admin"], bool)
        assert isinstance(data["created_at"], str)
        
        # 日時フォーマットの確認
        from datetime import datetime
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    
    def test_user_privacy(self, client: TestClient, auth_headers):
        """ユーザープライバシーのテスト（パスワードが含まれていないことを確認）"""
        response = client.get("/api/users/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # パスワード関連のフィールドが含まれていないことを確認
        privacy_fields = ["password", "hashed_password"]
        for field in privacy_fields:
            assert field not in data
    
    def test_multiple_concurrent_requests(self, client: TestClient, auth_headers):
        """複数の並行リクエストのテスト"""
        import threading
        import time
        
        results = []
        
        def make_request():
            try:
                response = client.get("/api/users/me", headers=auth_headers)
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))
        
        # 複数のスレッドで同時にリクエスト
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # すべてのスレッドが完了するまで待機
        for thread in threads:
            thread.join()
        
        # すべてのリクエストが成功することを確認
        for status_code in results:
            assert status_code == 200
    
    def test_token_reuse(self, client: TestClient, auth_headers):
        """トークンの再利用テスト"""
        # 同じトークンで複数回リクエスト
        for i in range(5):
            response = client.get("/api/users/me", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["username"] == "testuser"