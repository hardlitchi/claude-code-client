"""
sessions ルーターのテスト
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import Session as SessionModel
import uuid


@pytest.mark.api
class TestSessionsRouter:
    """セッションルーターのテスト"""
    
    def test_get_sessions_empty(self, client: TestClient, auth_headers):
        """空のセッション一覧取得のテスト"""
        response = client.get("/api/sessions/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert data["total"] == 0
        assert len(data["sessions"]) == 0
    
    def test_create_session_success(self, client: TestClient, auth_headers):
        """セッション作成成功のテスト"""
        session_data = {
            "name": "Test Session",
            "description": "Test Description",
            "working_directory": "/test/dir"
        }
        
        response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Session"
        assert data["description"] == "Test Description"
        assert data["working_directory"] == "/test/dir"
        assert data["status"] == "stopped"
        assert "session_id" in data
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data
    
    def test_create_session_minimal(self, client: TestClient, auth_headers):
        """最小限のデータでのセッション作成テスト"""
        session_data = {"name": "Minimal Session"}
        
        response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal Session"
        assert data["description"] is None
        assert data["working_directory"] is None
        assert data["status"] == "stopped"
    
    def test_create_session_missing_name(self, client: TestClient, auth_headers):
        """名前なしでのセッション作成テスト"""
        session_data = {"description": "Description without name"}
        
        response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        
        assert response.status_code == 422  # バリデーションエラー
    
    def test_create_session_no_auth(self, client: TestClient):
        """認証なしでのセッション作成テスト"""
        session_data = {"name": "Test Session"}
        
        response = client.post("/api/sessions/", json=session_data)
        
        assert response.status_code == 403
    
    def test_get_sessions_with_data(self, client: TestClient, auth_headers):
        """データ有りでのセッション一覧取得テスト"""
        # セッションを作成
        session_data = {"name": "Test Session 1"}
        client.post("/api/sessions/", json=session_data, headers=auth_headers)
        
        session_data = {"name": "Test Session 2"}
        client.post("/api/sessions/", json=session_data, headers=auth_headers)
        
        # セッション一覧を取得
        response = client.get("/api/sessions/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["sessions"]) == 2
        
        session_names = [s["name"] for s in data["sessions"]]
        assert "Test Session 1" in session_names
        assert "Test Session 2" in session_names
    
    def test_get_session_by_id_success(self, client: TestClient, auth_headers):
        """セッションID別取得成功のテスト"""
        # セッション作成
        session_data = {"name": "Get Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        created_session = create_response.json()
        session_id = created_session["session_id"]
        
        # セッション取得
        response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["name"] == "Get Test Session"
        assert "last_accessed" in data
    
    def test_get_session_not_found(self, client: TestClient, auth_headers):
        """存在しないセッション取得のテスト"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.get(f"/api/sessions/{fake_session_id}", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "セッションが見つかりません" in data["detail"]
    
    def test_get_session_other_user(self, client: TestClient, auth_headers, admin_headers):
        """他のユーザーのセッション取得テスト"""
        # 管理者でセッションを作成
        session_data = {"name": "Admin Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=admin_headers)
        admin_session = create_response.json()
        session_id = admin_session["session_id"]
        
        # 一般ユーザーで取得を試行
        response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        
        assert response.status_code == 404  # 他のユーザーのセッションは見つからない
    
    def test_update_session_success(self, client: TestClient, auth_headers):
        """セッション更新成功のテスト"""
        # セッション作成
        session_data = {"name": "Update Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        created_session = create_response.json()
        session_id = created_session["session_id"]
        
        # セッション更新
        update_data = {
            "name": "Updated Session",
            "description": "Updated Description",
            "status": "running"
        }
        response = client.put(f"/api/sessions/{session_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Session"
        assert data["description"] == "Updated Description"
        assert data["status"] == "running"
        assert "updated_at" in data
    
    def test_update_session_partial(self, client: TestClient, auth_headers):
        """セッション部分更新のテスト"""
        # セッション作成
        session_data = {"name": "Partial Update Test", "description": "Original Description"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        created_session = create_response.json()
        session_id = created_session["session_id"]
        
        # 名前のみ更新
        update_data = {"name": "Partially Updated"}
        response = client.put(f"/api/sessions/{session_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partially Updated"
        assert data["description"] == "Original Description"  # 変更されていない
    
    def test_update_session_not_found(self, client: TestClient, auth_headers):
        """存在しないセッション更新のテスト"""
        fake_session_id = str(uuid.uuid4())
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/api/sessions/{fake_session_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "セッションが見つかりません" in data["detail"]
    
    def test_delete_session_success(self, client: TestClient, auth_headers):
        """セッション削除成功のテスト"""
        # セッション作成
        session_data = {"name": "Delete Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        created_session = create_response.json()
        session_id = created_session["session_id"]
        
        # セッション削除
        response = client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "削除しました" in data["message"]
        
        # 削除後の確認
        get_response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert get_response.status_code == 404
    
    def test_delete_session_not_found(self, client: TestClient, auth_headers):
        """存在しないセッション削除のテスト"""
        fake_session_id = str(uuid.uuid4())
        
        response = client.delete(f"/api/sessions/{fake_session_id}", headers=auth_headers)
        
        assert response.status_code == 404
        data = response.json()
        assert "セッションが見つかりません" in data["detail"]
    
    def test_start_session_success(self, client: TestClient, auth_headers):
        """セッション開始成功のテスト"""
        # セッション作成
        session_data = {"name": "Start Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        created_session = create_response.json()
        session_id = created_session["session_id"]
        
        # セッション開始
        response = client.post(f"/api/sessions/{session_id}/start", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "開始しました" in data["message"]
        
        # ステータス確認
        get_response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        session_data = get_response.json()
        assert session_data["status"] == "running"
    
    def test_stop_session_success(self, client: TestClient, auth_headers):
        """セッション停止成功のテスト"""
        # セッション作成と開始
        session_data = {"name": "Stop Test Session"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        created_session = create_response.json()
        session_id = created_session["session_id"]
        
        client.post(f"/api/sessions/{session_id}/start", headers=auth_headers)
        
        # セッション停止
        response = client.post(f"/api/sessions/{session_id}/stop", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "停止しました" in data["message"]
        
        # ステータス確認
        get_response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        session_data = get_response.json()
        assert session_data["status"] == "stopped"
    
    def test_start_stop_session_not_found(self, client: TestClient, auth_headers):
        """存在しないセッションの開始/停止テスト"""
        fake_session_id = str(uuid.uuid4())
        
        # 開始試行
        start_response = client.post(f"/api/sessions/{fake_session_id}/start", headers=auth_headers)
        assert start_response.status_code == 404
        
        # 停止試行
        stop_response = client.post(f"/api/sessions/{fake_session_id}/stop", headers=auth_headers)
        assert stop_response.status_code == 404


@pytest.mark.api
class TestSessionsRouterIntegration:
    """セッションルーターの統合テスト"""
    
    def test_session_lifecycle(self, client: TestClient, auth_headers):
        """セッションライフサイクルの統合テスト"""
        # 1. セッション作成
        session_data = {"name": "Lifecycle Test", "description": "Full lifecycle test"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["session_id"]
        
        # 2. セッション取得
        get_response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert get_response.status_code == 200
        
        # 3. セッション更新
        update_data = {"description": "Updated description"}
        update_response = client.put(f"/api/sessions/{session_id}", json=update_data, headers=auth_headers)
        assert update_response.status_code == 200
        
        # 4. セッション開始
        start_response = client.post(f"/api/sessions/{session_id}/start", headers=auth_headers)
        assert start_response.status_code == 200
        
        # 5. セッション停止
        stop_response = client.post(f"/api/sessions/{session_id}/stop", headers=auth_headers)
        assert stop_response.status_code == 200
        
        # 6. セッション削除
        delete_response = client.delete(f"/api/sessions/{session_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        
        # 7. 削除確認
        final_get_response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert final_get_response.status_code == 404
    
    def test_multiple_sessions_isolation(self, client: TestClient, auth_headers, admin_headers):
        """複数セッションの分離テスト"""
        # ユーザー1のセッション
        user1_session = {"name": "User1 Session"}
        user1_response = client.post("/api/sessions/", json=user1_session, headers=auth_headers)
        assert user1_response.status_code == 200
        user1_session_id = user1_response.json()["session_id"]
        
        # ユーザー2（管理者）のセッション
        admin_session = {"name": "Admin Session"}
        admin_response = client.post("/api/sessions/", json=admin_session, headers=admin_headers)
        assert admin_response.status_code == 200
        admin_session_id = admin_response.json()["session_id"]
        
        # ユーザー1は自分のセッションのみ見える
        user1_list = client.get("/api/sessions/", headers=auth_headers)
        assert user1_list.status_code == 200
        user1_sessions = user1_list.json()["sessions"]
        assert len(user1_sessions) == 1
        assert user1_sessions[0]["session_id"] == user1_session_id
        
        # 管理者は自分のセッションのみ見える
        admin_list = client.get("/api/sessions/", headers=admin_headers)
        assert admin_list.status_code == 200
        admin_sessions = admin_list.json()["sessions"]
        assert len(admin_sessions) == 1
        assert admin_sessions[0]["session_id"] == admin_session_id
        
        # ユーザー1は管理者のセッションにアクセスできない
        user1_access_admin = client.get(f"/api/sessions/{admin_session_id}", headers=auth_headers)
        assert user1_access_admin.status_code == 404
    
    def test_session_uuid_uniqueness(self, client: TestClient, auth_headers):
        """セッションUUIDの一意性テスト"""
        session_ids = set()
        
        for i in range(10):
            session_data = {"name": f"UUID Test Session {i}"}
            response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
            assert response.status_code == 200
            
            session_id = response.json()["session_id"]
            assert session_id not in session_ids  # 重複していない
            session_ids.add(session_id)
            
            # UUID形式の検証
            uuid.UUID(session_id)  # 例外が発生しなければ有効なUUID
    
    def test_session_timestamps(self, client: TestClient, auth_headers):
        """セッションタイムスタンプのテスト"""
        import time
        from datetime import datetime
        
        # セッション作成
        session_data = {"name": "Timestamp Test"}
        create_response = client.post("/api/sessions/", json=session_data, headers=auth_headers)
        assert create_response.status_code == 200
        session = create_response.json()
        session_id = session["session_id"]
        
        # created_at の検証
        created_at = datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))
        assert created_at is not None
        
        # 少し待ってから更新
        time.sleep(1)
        
        # セッション更新
        update_data = {"description": "Updated for timestamp test"}
        update_response = client.put(f"/api/sessions/{session_id}", json=update_data, headers=auth_headers)
        assert update_response.status_code == 200
        updated_session = update_response.json()
        
        # updated_at の検証
        updated_at = datetime.fromisoformat(updated_session["updated_at"].replace("Z", "+00:00"))
        assert updated_at > created_at
        
        # セッション取得（last_accessed更新）
        time.sleep(1)
        get_response = client.get(f"/api/sessions/{session_id}", headers=auth_headers)
        assert get_response.status_code == 200
        accessed_session = get_response.json()
        
        # last_accessed の検証
        last_accessed = datetime.fromisoformat(accessed_session["last_accessed"].replace("Z", "+00:00"))
        assert last_accessed >= updated_at