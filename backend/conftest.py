"""
テスト設定ファイル
"""

import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.auth import get_password_hash


# テスト環境フラグを設定
import os
os.environ["TESTING"] = "1"

# テスト用インメモリSQLiteデータベース設定
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """イベントループのスコープをセッション全体に設定"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db():
    """テスト用データベースセッション"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """テスト用HTTPクライアント"""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    """テスト用ユーザー"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db):
    """テスト用管理者ユーザー"""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpassword"),
        is_active=True,
        is_admin=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(client, test_user):
    """テスト用ユーザートークン"""
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    return response.json()["access_token"]


@pytest.fixture
def admin_token(client, admin_user):
    """テスト用管理者トークン"""
    response = client.post(
        "/api/auth/login", 
        data={"username": "admin", "password": "adminpassword"}
    )
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(user_token):
    """認証ヘッダー"""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def admin_headers(admin_token):
    """管理者認証ヘッダー"""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def mock_claude_manager():
    """モック Claude 統合マネージャー"""
    from app.claude_integration import claude_manager
    original_create_session = claude_manager.create_session
    original_get_session = claude_manager.get_session
    original_remove_session = claude_manager.remove_session
    
    # モック関数を設定
    claude_manager.create_session = AsyncMock()
    claude_manager.get_session = AsyncMock()
    claude_manager.remove_session = AsyncMock()
    
    yield claude_manager
    
    # 元の関数を復元
    claude_manager.create_session = original_create_session
    claude_manager.get_session = original_get_session
    claude_manager.remove_session = original_remove_session