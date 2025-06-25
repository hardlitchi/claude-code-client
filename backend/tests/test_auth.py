"""
auth.py のテスト
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from jose import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth import (
    verify_password, get_password_hash, create_access_token, verify_token,
    authenticate_user, get_current_user, get_current_active_user, create_user,
    SECRET_KEY, ALGORITHM
)
from app.models import User
from app.schemas import TokenData


@pytest.mark.unit
class TestPasswordFunctions:
    """パスワード関連関数のテスト"""
    
    def test_get_password_hash(self):
        """パスワードハッシュ化のテスト"""
        password = "testpassword"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcryptハッシュの特徴
    
    def test_verify_password_correct(self):
        """正しいパスワード検証のテスト"""
        password = "testpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """間違ったパスワード検証のテスト"""
        password = "testpassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty(self):
        """空のパスワード検証のテスト"""
        password = "testpassword"
        hashed = get_password_hash(password)
        
        assert verify_password("", hashed) is False


@pytest.mark.unit
class TestTokenFunctions:
    """トークン関連関数のテスト"""
    
    def test_create_access_token(self):
        """アクセストークン作成のテスト"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # トークンをデコードして内容を確認
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert "exp" in payload
    
    def test_create_access_token_with_expires_delta(self):
        """有効期限指定でのアクセストークン作成のテスト"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + expires_delta
        
        # 多少の時間差を許容
        assert abs((exp_time - expected_exp).total_seconds()) < 5
    
    def test_verify_token_valid(self):
        """有効なトークン検証のテスト"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        token_data = verify_token(token)
        assert isinstance(token_data, TokenData)
        assert token_data.username == "testuser"
    
    def test_verify_token_invalid(self):
        """無効なトークン検証のテスト"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)
        
        assert exc_info.value.status_code == 401
        assert "無効なトークンです" in exc_info.value.detail
    
    def test_verify_token_no_sub(self):
        """subが含まれていないトークンのテスト"""
        data = {"user": "testuser"}  # "sub" ではなく "user"
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        
        assert exc_info.value.status_code == 401
        assert "無効なトークンです" in exc_info.value.detail
    
    def test_verify_token_expired(self):
        """期限切れトークンのテスト"""
        past_time = datetime.utcnow() - timedelta(hours=1)
        data = {"sub": "testuser", "exp": past_time}
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        
        assert exc_info.value.status_code == 401


@pytest.mark.unit
class TestAuthenticateUser:
    """ユーザー認証のテスト"""
    
    def test_authenticate_user_success(self, db, test_user):
        """正常なユーザー認証のテスト"""
        user = authenticate_user(db, "testuser", "testpassword")
        
        assert user is not None
        assert user.username == "testuser"
        assert user.id == test_user.id
    
    def test_authenticate_user_wrong_password(self, db, test_user):
        """間違ったパスワードでの認証のテスト"""
        user = authenticate_user(db, "testuser", "wrongpassword")
        
        assert user is None
    
    def test_authenticate_user_nonexistent(self, db):
        """存在しないユーザーでの認証のテスト"""
        user = authenticate_user(db, "nonexistent", "password")
        
        assert user is None
    
    def test_authenticate_user_empty_credentials(self, db):
        """空の認証情報のテスト"""
        user = authenticate_user(db, "", "")
        
        assert user is None


@pytest.mark.unit  
class TestCurrentUserFunctions:
    """現在のユーザー取得関数のテスト"""
    
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, db, test_user, user_token):
        """正常な現在のユーザー取得のテスト"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=user_token
        )
        
        user = await get_current_user(credentials, db)
        
        assert user is not None
        assert user.username == "testuser"
        assert user.id == test_user.id
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, db):
        """無効なトークンでの現在のユーザー取得のテスト"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, db)
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(self, db):
        """存在しないユーザーのトークンでのテスト"""
        data = {"sub": "nonexistent"}
        token = create_access_token(data)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, db)
        
        assert exc_info.value.status_code == 401
        assert "ユーザーが見つかりません" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self, test_user):
        """アクティブユーザー取得成功のテスト"""
        user = await get_current_active_user(test_user)
        
        assert user == test_user
    
    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self, db):
        """非アクティブユーザーのテスト"""
        inactive_user = User(
            username="inactive",
            hashed_password=get_password_hash("password"),
            is_active=False
        )
        db.add(inactive_user)
        db.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(inactive_user)
        
        assert exc_info.value.status_code == 400
        assert "無効なユーザーです" in exc_info.value.detail


@pytest.mark.unit
class TestCreateUser:
    """ユーザー作成のテスト"""
    
    def test_create_user_success(self, db):
        """正常なユーザー作成のテスト"""
        user = create_user(db, "newuser", "password123", "new@example.com")
        
        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.is_active is True
        assert user.is_admin is False
        assert verify_password("password123", user.hashed_password)
    
    def test_create_user_without_email(self, db):
        """メールアドレスなしでのユーザー作成のテスト"""
        user = create_user(db, "newuser", "password123")
        
        assert user is not None
        assert user.username == "newuser"
        assert user.email is None
        assert verify_password("password123", user.hashed_password)
    
    def test_create_user_duplicate_username(self, db, test_user):
        """重複ユーザー名での作成のテスト"""
        with pytest.raises(HTTPException) as exc_info:
            create_user(db, "testuser", "password123")
        
        assert exc_info.value.status_code == 400
        assert "ユーザー名が既に使用されています" in exc_info.value.detail
    
    def test_create_user_empty_username(self, db):
        """空のユーザー名でのユーザー作成のテスト"""
        # SQLAlchemyでIntegrityErrorが発生する
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            create_user(db, "", "password123")
    
    def test_create_user_empty_password(self, db):
        """空のパスワードでのユーザー作成のテスト"""
        user = create_user(db, "newuser", "")
        
        # 空のパスワードでもハッシュ化は実行される
        assert user is not None
        assert user.username == "newuser"
        assert len(user.hashed_password) > 0


@pytest.mark.unit
class TestEnvironmentVariables:
    """環境変数関連のテスト"""
    
    @patch.dict('os.environ', {'SECRET_KEY': 'test-secret-key'})
    def test_secret_key_from_env(self):
        """環境変数からのSECRET_KEY読み込みのテスト"""
        # モジュールを再インポートして環境変数を反映
        import importlib
        from app import auth
        importlib.reload(auth)
        
        assert auth.SECRET_KEY == 'test-secret-key'
    
    def test_secret_key_default(self):
        """デフォルトSECRET_KEYのテスト"""
        # デフォルト値が設定されていることを確認
        assert SECRET_KEY is not None
        assert len(SECRET_KEY) > 0