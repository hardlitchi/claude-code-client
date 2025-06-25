"""
models.py のテスト
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models import User, Session, AuthToken, SystemLog


@pytest.mark.unit
class TestUser:
    """Userモデルのテスト"""
    
    def test_create_user(self, db):
        """ユーザー作成のテスト"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
    
    def test_user_unique_username(self, db):
        """ユーザー名の一意制約のテスト"""
        user1 = User(username="testuser", hashed_password="password1")
        user2 = User(username="testuser", hashed_password="password2")
        
        db.add(user1)
        db.commit()
        
        db.add(user2)
        with pytest.raises(IntegrityError):
            db.commit()
    
    def test_user_unique_email(self, db):
        """メールアドレスの一意制約のテスト"""
        user1 = User(username="user1", email="test@example.com", hashed_password="password1")
        user2 = User(username="user2", email="test@example.com", hashed_password="password2")
        
        db.add(user1)
        db.commit()
        
        db.add(user2)
        with pytest.raises(IntegrityError):
            db.commit()
    
    def test_user_default_values(self, db):
        """デフォルト値のテスト"""
        user = User(username="testuser", hashed_password="password")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
    
    def test_user_sessions_relationship(self, db):
        """ユーザーとセッションのリレーションシップのテスト"""
        user = User(username="testuser", hashed_password="password")
        db.add(user)
        db.commit()
        db.refresh(user)
        
        session = Session(
            session_id="test-session-id",
            name="Test Session",
            user_id=user.id
        )
        db.add(session)
        db.commit()
        
        assert len(user.sessions) == 1
        assert user.sessions[0].name == "Test Session"


@pytest.mark.unit
class TestSession:
    """Sessionモデルのテスト"""
    
    def test_create_session(self, db, test_user):
        """セッション作成のテスト"""
        session = Session(
            session_id="test-session-id",
            name="Test Session",
            description="Test Description",
            working_directory="/test/dir",
            status="running",
            user_id=test_user.id
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        assert session.id is not None
        assert session.session_id == "test-session-id"
        assert session.name == "Test Session"
        assert session.description == "Test Description"
        assert session.working_directory == "/test/dir"
        assert session.status == "running"
        assert session.user_id == test_user.id
        assert session.created_at is not None
        assert session.last_accessed is not None
    
    def test_session_unique_session_id(self, db, test_user):
        """セッションIDの一意制約のテスト"""
        session1 = Session(
            session_id="test-session-id",
            name="Session 1",
            user_id=test_user.id
        )
        session2 = Session(
            session_id="test-session-id",
            name="Session 2",
            user_id=test_user.id
        )
        
        db.add(session1)
        db.commit()
        
        db.add(session2)
        with pytest.raises(IntegrityError):
            db.commit()
    
    def test_session_default_status(self, db, test_user):
        """セッションのデフォルトステータスのテスト"""
        session = Session(
            session_id="test-session-id",
            name="Test Session",
            user_id=test_user.id
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        assert session.status == "stopped"
    
    def test_session_user_relationship(self, db, test_user):
        """セッションとユーザーのリレーションシップのテスト"""
        session = Session(
            session_id="test-session-id",
            name="Test Session",
            user_id=test_user.id
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        assert session.user.username == test_user.username
        assert session.user.id == test_user.id


@pytest.mark.unit
class TestAuthToken:
    """AuthTokenモデルのテスト"""
    
    def test_create_auth_token(self, db, test_user):
        """認証トークン作成のテスト"""
        expires_at = datetime.utcnow()
        token = AuthToken(
            token_id="test-token-id",
            user_id=test_user.id,
            expires_at=expires_at,
            is_active=True
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        
        assert token.id is not None
        assert token.token_id == "test-token-id"
        assert token.user_id == test_user.id
        assert token.expires_at == expires_at
        assert token.is_active is True
        assert token.created_at is not None
    
    def test_auth_token_unique_token_id(self, db, test_user):
        """トークンIDの一意制約のテスト"""
        expires_at = datetime.utcnow()
        token1 = AuthToken(
            token_id="test-token-id",
            user_id=test_user.id,
            expires_at=expires_at
        )
        token2 = AuthToken(
            token_id="test-token-id",
            user_id=test_user.id,
            expires_at=expires_at
        )
        
        db.add(token1)
        db.commit()
        
        db.add(token2)
        with pytest.raises(IntegrityError):
            db.commit()
    
    def test_auth_token_default_is_active(self, db, test_user):
        """トークンのデフォルト有効状態のテスト"""
        token = AuthToken(
            token_id="test-token-id",
            user_id=test_user.id,
            expires_at=datetime.utcnow()
        )
        db.add(token)
        db.commit()
        db.refresh(token)
        
        assert token.is_active is True


@pytest.mark.unit
class TestSystemLog:
    """SystemLogモデルのテスト"""
    
    def test_create_system_log(self, db, test_user):
        """システムログ作成のテスト"""
        log = SystemLog(
            level="INFO",
            module="test_module",
            message="Test log message",
            user_id=test_user.id,
            session_id="test-session-id"
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        
        assert log.id is not None
        assert log.level == "INFO"
        assert log.module == "test_module"
        assert log.message == "Test log message"
        assert log.user_id == test_user.id
        assert log.session_id == "test-session-id"
        assert log.created_at is not None
    
    def test_system_log_without_user(self, db):
        """ユーザーなしのシステムログのテスト"""
        log = SystemLog(
            level="ERROR",
            module="system",
            message="System error"
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        
        assert log.user_id is None
        assert log.session_id is None
        assert log.level == "ERROR"
        assert log.module == "system"
        assert log.message == "System error"
    
    def test_system_log_levels(self, db):
        """各ログレベルのテスト"""
        levels = ["INFO", "WARN", "ERROR", "CRITICAL"]
        
        for level in levels:
            log = SystemLog(
                level=level,
                module="test",
                message=f"Test {level} message"
            )
            db.add(log)
        
        db.commit()
        
        logs = db.query(SystemLog).all()
        assert len(logs) == 4
        
        for i, level in enumerate(levels):
            assert logs[i].level == level
            assert logs[i].message == f"Test {level} message"