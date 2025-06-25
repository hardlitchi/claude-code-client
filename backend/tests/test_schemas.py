"""
schemas.py のテスト
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas import (
    UserBase, UserCreate, UserLogin, User, Token, TokenData,
    SessionBase, SessionCreate, SessionUpdate, Session,
    APIResponse, SessionList, SystemStatus
)


@pytest.mark.unit
class TestUserSchemas:
    """ユーザー関連スキーマのテスト"""
    
    def test_user_base(self):
        """UserBaseスキーマのテスト"""
        user_data = {"username": "testuser", "email": "test@example.com"}
        user = UserBase(**user_data)
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
    
    def test_user_base_without_email(self):
        """メールアドレスなしのUserBaseのテスト"""
        user_data = {"username": "testuser"}
        user = UserBase(**user_data)
        
        assert user.username == "testuser"
        assert user.email is None
    
    def test_user_base_validation_error(self):
        """UserBaseのバリデーションエラーのテスト"""
        with pytest.raises(ValidationError):
            UserBase()  # username が必須
    
    def test_user_create(self):
        """UserCreateスキーマのテスト"""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        }
        user = UserCreate(**user_data)
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password == "password123"
    
    def test_user_create_without_email(self):
        """メールアドレスなしのUserCreateのテスト"""
        user_data = {"username": "testuser", "password": "password123"}
        user = UserCreate(**user_data)
        
        assert user.username == "testuser"
        assert user.email is None
        assert user.password == "password123"
    
    def test_user_create_validation_error(self):
        """UserCreateのバリデーションエラーのテスト"""
        with pytest.raises(ValidationError):
            UserCreate(username="testuser")  # password が必須
    
    def test_user_login(self):
        """UserLoginスキーマのテスト"""
        login_data = {"username": "testuser", "password": "password123"}
        login = UserLogin(**login_data)
        
        assert login.username == "testuser"
        assert login.password == "password123"
    
    def test_user_login_validation_error(self):
        """UserLoginのバリデーションエラーのテスト"""
        with pytest.raises(ValidationError):
            UserLogin(username="testuser")  # password が必須
        
        with pytest.raises(ValidationError):
            UserLogin(password="password123")  # username が必須
    
    def test_user_response(self):
        """Userレスポンススキーマのテスト"""
        now = datetime.now()
        user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
            "is_admin": False,
            "created_at": now,
            "updated_at": now
        }
        user = User(**user_data)
        
        assert user.id == 1
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at == now
        assert user.updated_at == now
    
    def test_user_response_without_updated_at(self):
        """updated_atなしのUserレスポンスのテスト"""
        now = datetime.now()
        user_data = {
            "id": 1,
            "username": "testuser",
            "is_active": True,
            "is_admin": False,
            "created_at": now
        }
        user = User(**user_data)
        
        assert user.updated_at is None


@pytest.mark.unit
class TestAuthSchemas:
    """認証関連スキーマのテスト"""
    
    def test_token(self):
        """Tokenスキーマのテスト"""
        token_data = {
            "access_token": "token123",
            "token_type": "bearer",
            "expires_in": 3600
        }
        token = Token(**token_data)
        
        assert token.access_token == "token123"
        assert token.token_type == "bearer"
        assert token.expires_in == 3600
    
    def test_token_default_type(self):
        """Tokenのデフォルトタイプのテスト"""
        token_data = {"access_token": "token123", "expires_in": 3600}
        token = Token(**token_data)
        
        assert token.token_type == "bearer"
    
    def test_token_data(self):
        """TokenDataスキーマのテスト"""
        token_data = {"username": "testuser"}
        token = TokenData(**token_data)
        
        assert token.username == "testuser"
    
    def test_token_data_optional(self):
        """TokenDataの任意フィールドのテスト"""
        token = TokenData()
        assert token.username is None


@pytest.mark.unit
class TestSessionSchemas:
    """セッション関連スキーマのテスト"""
    
    def test_session_base(self):
        """SessionBaseスキーマのテスト"""
        session_data = {
            "name": "Test Session",
            "description": "Test Description",
            "working_directory": "/test/dir"
        }
        session = SessionBase(**session_data)
        
        assert session.name == "Test Session"
        assert session.description == "Test Description"
        assert session.working_directory == "/test/dir"
    
    def test_session_base_minimal(self):
        """最小限のSessionBaseのテスト"""
        session_data = {"name": "Test Session"}
        session = SessionBase(**session_data)
        
        assert session.name == "Test Session"
        assert session.description is None
        assert session.working_directory is None
    
    def test_session_create(self):
        """SessionCreateスキーマのテスト"""
        session_data = {
            "name": "Test Session",
            "description": "Test Description",
            "working_directory": "/test/dir"
        }
        session = SessionCreate(**session_data)
        
        assert session.name == "Test Session"
        assert session.description == "Test Description"
        assert session.working_directory == "/test/dir"
    
    def test_session_update(self):
        """SessionUpdateスキーマのテスト"""
        update_data = {
            "name": "Updated Session",
            "description": "Updated Description",
            "working_directory": "/updated/dir",
            "status": "running"
        }
        session_update = SessionUpdate(**update_data)
        
        assert session_update.name == "Updated Session"
        assert session_update.description == "Updated Description"
        assert session_update.working_directory == "/updated/dir"
        assert session_update.status == "running"
    
    def test_session_update_partial(self):
        """部分的なSessionUpdateのテスト"""
        update_data = {"status": "stopped"}
        session_update = SessionUpdate(**update_data)
        
        assert session_update.name is None
        assert session_update.description is None
        assert session_update.working_directory is None
        assert session_update.status == "stopped"
    
    def test_session_update_empty(self):
        """空のSessionUpdateのテスト"""
        session_update = SessionUpdate()
        
        assert session_update.name is None
        assert session_update.description is None
        assert session_update.working_directory is None
        assert session_update.status is None
    
    def test_session_response(self):
        """Sessionレスポンススキーマのテスト"""
        now = datetime.now()
        session_data = {
            "id": 1,
            "session_id": "session-uuid",
            "name": "Test Session",
            "description": "Test Description",
            "working_directory": "/test/dir",
            "status": "running",
            "user_id": 1,
            "created_at": now,
            "updated_at": now,
            "last_accessed": now
        }
        session = Session(**session_data)
        
        assert session.id == 1
        assert session.session_id == "session-uuid"
        assert session.name == "Test Session"
        assert session.description == "Test Description"
        assert session.working_directory == "/test/dir"
        assert session.status == "running"
        assert session.user_id == 1
        assert session.created_at == now
        assert session.updated_at == now
        assert session.last_accessed == now


@pytest.mark.unit
class TestAPIResponseSchemas:
    """APIレスポンス関連スキーマのテスト"""
    
    def test_api_response(self):
        """APIResponseスキーマのテスト"""
        response_data = {
            "message": "Success",
            "status": "success",
            "data": {"key": "value"}
        }
        response = APIResponse(**response_data)
        
        assert response.message == "Success"
        assert response.status == "success"
        assert response.data == {"key": "value"}
    
    def test_api_response_defaults(self):
        """APIResponseのデフォルト値のテスト"""
        response_data = {"message": "Success"}
        response = APIResponse(**response_data)
        
        assert response.message == "Success"
        assert response.status == "success"
        assert response.data is None
    
    def test_session_list(self):
        """SessionListスキーマのテスト"""
        now = datetime.now()
        sessions_data = [
            {
                "id": 1,
                "session_id": "session-1",
                "name": "Session 1",
                "status": "running",
                "user_id": 1,
                "created_at": now,
                "last_accessed": now
            },
            {
                "id": 2,
                "session_id": "session-2",
                "name": "Session 2",
                "status": "stopped",
                "user_id": 1,
                "created_at": now,
                "last_accessed": now
            }
        ]
        
        sessions = [Session(**session_data) for session_data in sessions_data]
        session_list_data = {"sessions": sessions, "total": 2}
        session_list = SessionList(**session_list_data)
        
        assert len(session_list.sessions) == 2
        assert session_list.total == 2
        assert session_list.sessions[0].name == "Session 1"
        assert session_list.sessions[1].name == "Session 2"
    
    def test_system_status(self):
        """SystemStatusスキーマのテスト"""
        status_data = {
            "status": "healthy",
            "version": "1.0.0",
            "active_sessions": 5,
            "total_users": 10,
            "uptime": "2 hours"
        }
        status = SystemStatus(**status_data)
        
        assert status.status == "healthy"
        assert status.version == "1.0.0"
        assert status.active_sessions == 5
        assert status.total_users == 10
        assert status.uptime == "2 hours"


@pytest.mark.unit
class TestSchemaValidation:
    """スキーマバリデーションのテスト"""
    
    def test_user_create_empty_username(self):
        """空のユーザー名のバリデーションエラー"""
        with pytest.raises(ValidationError):
            UserCreate(username="", password="password123")
    
    def test_user_create_empty_password(self):
        """空のパスワードのバリデーションエラー"""
        with pytest.raises(ValidationError):
            UserCreate(username="testuser", password="")
    
    def test_session_create_empty_name(self):
        """空のセッション名のバリデーションエラー"""
        with pytest.raises(ValidationError):
            SessionCreate(name="")
    
    def test_token_negative_expires_in(self):
        """負の有効期限のバリデーション"""
        # Pydanticは負の数値を受け入れるが、ビジネスロジックで検証する必要がある
        token_data = {"access_token": "token123", "expires_in": -1}
        token = Token(**token_data)
        assert token.expires_in == -1  # スキーマレベルでは通る
    
    def test_api_response_empty_message(self):
        """空のメッセージのAPIResponse"""
        with pytest.raises(ValidationError):
            APIResponse(message="")  # messageは必須でかつ空文字列は無効