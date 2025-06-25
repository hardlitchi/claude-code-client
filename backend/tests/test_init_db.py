"""
init_db.py のテスト
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from app.init_db import create_tables, create_default_users, init_database
from app.models import User


@pytest.mark.unit
class TestCreateTables:
    """create_tables関数のテスト"""
    
    @patch('app.init_db.Base')
    @patch('app.init_db.logger')
    def test_create_tables_success(self, mock_logger, mock_base):
        """テーブル作成成功のテスト"""
        # メタデータをモック
        mock_metadata = MagicMock()
        mock_base.metadata = mock_metadata
        
        create_tables()
        
        # create_allが呼ばれたことを確認
        mock_metadata.create_all.assert_called_once()
        
        # ログが出力されたことを確認
        mock_logger.info.assert_any_call("Creating database tables...")
        mock_logger.info.assert_any_call("Database tables created successfully")
    
    @patch('app.init_db.Base')
    @patch('app.init_db.logger')
    def test_create_tables_error(self, mock_logger, mock_base):
        """テーブル作成エラーのテスト"""
        # create_allでエラーを発生させる
        mock_metadata = MagicMock()
        mock_metadata.create_all.side_effect = Exception("Table creation error")
        mock_base.metadata = mock_metadata
        
        with pytest.raises(Exception) as exc_info:
            create_tables()
        
        assert "Table creation error" in str(exc_info.value)
        mock_logger.info.assert_called_with("Creating database tables...")


@pytest.mark.unit
class TestCreateDefaultUsers:
    """create_default_users関数のテスト"""
    
    @patch('app.init_db.SessionLocal')
    @patch('app.init_db.logger')
    def test_create_default_users_new_users(self, mock_logger, mock_session_local):
        """新規ユーザー作成のテスト"""
        # セッションをモック
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # ユーザーが存在しないことをモック
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        create_default_users()
        
        # ユーザーが追加されたことを確認
        assert mock_db.add.call_count == 2  # admin + testuser
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()
        
        # ログメッセージの確認
        mock_logger.info.assert_any_call("Creating default admin user...")
        mock_logger.info.assert_any_call("Default admin user created")
        mock_logger.info.assert_any_call("Creating default test user...")
        mock_logger.info.assert_any_call("Default test user created")
    
    @patch('app.init_db.SessionLocal')
    @patch('app.init_db.logger')
    def test_create_default_users_existing_users(self, mock_logger, mock_session_local):
        """既存ユーザーが存在する場合のテスト"""
        # セッションをモック
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # ユーザーが既に存在することをモック
        mock_existing_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing_user
        
        create_default_users()
        
        # ユーザーが追加されていないことを確認
        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()
        
        # ログメッセージの確認
        mock_logger.info.assert_any_call("Admin user already exists")
        mock_logger.info.assert_any_call("Test user already exists")
    
    @patch('app.init_db.SessionLocal')
    @patch('app.init_db.logger')
    def test_create_default_users_partial_existing(self, mock_logger, mock_session_local):
        """一部のユーザーのみ存在する場合のテスト"""
        # セッションをモック
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # 管理者は存在するが、テストユーザーは存在しない
        def mock_filter_first(*args, **kwargs):
            # 2回目の呼び出し（testuser）でNoneを返す
            if mock_db.query.return_value.filter.return_value.first.call_count == 1:
                return MagicMock()  # admin exists
            else:
                return None  # testuser doesn't exist
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            MagicMock(),  # admin exists
            None  # testuser doesn't exist
        ]
        
        create_default_users()
        
        # 1つのユーザー（testuser）のみが追加されることを確認
        assert mock_db.add.call_count == 1
        mock_db.commit.assert_called_once()
        
        # ログメッセージの確認
        mock_logger.info.assert_any_call("Admin user already exists")
        mock_logger.info.assert_any_call("Creating default test user...")
    
    @patch('app.init_db.SessionLocal')
    @patch('app.init_db.logger')
    def test_create_default_users_error(self, mock_logger, mock_session_local):
        """ユーザー作成エラーのテスト"""
        # セッションをモック
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        
        # エラーを発生させる
        mock_db.query.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            create_default_users()
        
        assert "Database error" in str(exc_info.value)
        mock_db.rollback.assert_called_once()
        mock_db.close.assert_called_once()
        mock_logger.error.assert_called()


@pytest.mark.unit
class TestInitDatabase:
    """init_database関数のテスト"""
    
    @patch('app.init_db.create_default_users')
    @patch('app.init_db.create_tables')
    @patch('app.init_db.logger')
    def test_init_database_success(self, mock_logger, mock_create_tables, mock_create_default_users):
        """データベース初期化成功のテスト"""
        init_database()
        
        # 両方の関数が呼ばれたことを確認
        mock_create_tables.assert_called_once()
        mock_create_default_users.assert_called_once()
        
        # ログメッセージの確認
        mock_logger.info.assert_any_call("Initializing database...")
        mock_logger.info.assert_any_call("Database initialization completed")
    
    @patch('app.init_db.create_default_users')
    @patch('app.init_db.create_tables')
    @patch('app.init_db.logger')
    def test_init_database_create_tables_error(self, mock_logger, mock_create_tables, mock_create_default_users):
        """テーブル作成でエラーが発生する場合のテスト"""
        mock_create_tables.side_effect = Exception("Table creation failed")
        
        with pytest.raises(Exception) as exc_info:
            init_database()
        
        assert "Table creation failed" in str(exc_info.value)
        mock_create_tables.assert_called_once()
        mock_create_default_users.assert_not_called()  # エラーで停止するため呼ばれない
    
    @patch('app.init_db.create_default_users')
    @patch('app.init_db.create_tables')
    @patch('app.init_db.logger')
    def test_init_database_create_users_error(self, mock_logger, mock_create_tables, mock_create_default_users):
        """ユーザー作成でエラーが発生する場合のテスト"""
        mock_create_default_users.side_effect = Exception("User creation failed")
        
        with pytest.raises(Exception) as exc_info:
            init_database()
        
        assert "User creation failed" in str(exc_info.value)
        mock_create_tables.assert_called_once()
        mock_create_default_users.assert_called_once()


@pytest.mark.integration
class TestInitDatabaseIntegration:
    """init_database統合テスト"""
    
    def test_init_database_real_execution(self, db):
        """実際のデータベースでの初期化テスト"""
        # init_databaseを実行
        init_database()
        
        # データベースにユーザーが作成されていることを確認
        admin_user = db.query(User).filter(User.username == "admin").first()
        test_user = db.query(User).filter(User.username == "testuser").first()
        
        assert admin_user is not None
        assert admin_user.is_admin is True
        assert admin_user.is_active is True
        assert admin_user.email == "admin@example.com"
        
        assert test_user is not None
        assert test_user.is_admin is False
        assert test_user.is_active is True
        assert test_user.email == "test@example.com"
    
    def test_init_database_idempotent(self, db):
        """init_databaseの冪等性テスト（複数回実行しても安全）"""
        # 1回目の実行
        init_database()
        
        # ユーザー数を確認
        user_count_1 = db.query(User).count()
        
        # 2回目の実行
        init_database()
        
        # ユーザー数が変わらないことを確認
        user_count_2 = db.query(User).count()
        assert user_count_1 == user_count_2
        
        # 管理者ユーザーが重複していないことを確認
        admin_users = db.query(User).filter(User.username == "admin").all()
        assert len(admin_users) == 1
        
        # テストユーザーが重複していないことを確認
        test_users = db.query(User).filter(User.username == "testuser").all()
        assert len(test_users) == 1


@pytest.mark.unit
class TestDefaultUserCreation:
    """デフォルトユーザー作成の詳細テスト"""
    
    def test_admin_user_properties(self):
        """管理者ユーザーのプロパティテスト"""
        from app.auth import verify_password
        
        # テスト用にユーザーを作成
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=True
        )
        
        assert admin_user.username == "admin"
        assert admin_user.email == "admin@example.com"
        assert admin_user.is_active is True
        assert admin_user.is_admin is True
    
    def test_test_user_properties(self):
        """テストユーザーのプロパティテスト"""
        # テスト用にユーザーを作成
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            is_admin=False
        )
        
        assert test_user.username == "testuser"
        assert test_user.email == "test@example.com"
        assert test_user.is_active is True
        assert test_user.is_admin is False
    
    def test_password_hashing(self):
        """パスワードハッシュ化のテスト"""
        from app.auth import get_password_hash, verify_password
        
        # 管理者パスワード
        admin_password = "admin123"
        admin_hashed = get_password_hash(admin_password)
        assert verify_password(admin_password, admin_hashed)
        assert admin_hashed != admin_password
        
        # テストユーザーパスワード
        test_password = "test123"
        test_hashed = get_password_hash(test_password)
        assert verify_password(test_password, test_hashed)
        assert test_hashed != test_password
        
        # 異なるパスワードのハッシュは異なる
        assert admin_hashed != test_hashed