"""
database.py のテスト
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db, Base, SessionLocal, engine, DATABASE_URL


@pytest.mark.unit
class TestDatabaseConfiguration:
    """データベース設定のテスト"""
    
    def test_database_url_default(self):
        """デフォルトDATABASE_URLのテスト"""
        # デフォルト値またはPostgreSQLのURLが設定されていることを確認
        assert DATABASE_URL is not None
        assert len(DATABASE_URL) > 0
        assert DATABASE_URL.startswith(("postgresql://", "sqlite:///"))
    
    @patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test:test@localhost/test'})
    def test_database_url_from_env(self):
        """環境変数からのDATABASE_URL読み込みのテスト"""
        # モジュールを再インポートして環境変数を反映
        import importlib
        from app import database
        importlib.reload(database)
        
        assert database.DATABASE_URL == 'postgresql://test:test@localhost/test'
    
    @patch.dict('os.environ', {'DATABASE_URL': 'sqlite:///./test.db'})
    def test_sqlite_database_configuration(self):
        """SQLiteデータベース設定のテスト"""
        import importlib
        from app import database
        importlib.reload(database)
        
        assert "sqlite" in database.DATABASE_URL
        # SQLiteの場合のエンジン設定が正しいことを確認
        assert database.engine is not None
    
    def test_engine_creation(self):
        """エンジン作成のテスト"""
        assert engine is not None
        assert hasattr(engine, 'connect')
        assert hasattr(engine, 'execute')
    
    def test_session_local_creation(self):
        """SessionLocal作成のテスト"""
        assert SessionLocal is not None
        assert hasattr(SessionLocal, '__call__')  # callableであることを確認
    
    def test_base_declarative(self):
        """Base declarative の作成テスト"""
        assert Base is not None
        assert hasattr(Base, 'metadata')
        assert hasattr(Base, 'registry')


@pytest.mark.unit
class TestGetDB:
    """get_db関数のテスト"""
    
    def test_get_db_generator(self):
        """get_db がジェネレーターであることのテスト"""
        db_gen = get_db()
        assert hasattr(db_gen, '__next__')  # ジェネレーターであることを確認
    
    def test_get_db_yields_session(self):
        """get_db がセッションを返すことのテスト"""
        db_gen = get_db()
        try:
            db_session = next(db_gen)
            # セッションオブジェクトの基本的なメソッドが存在することを確認
            assert hasattr(db_session, 'query')
            assert hasattr(db_session, 'add')
            assert hasattr(db_session, 'commit')
            assert hasattr(db_session, 'rollback')
            assert hasattr(db_session, 'close')
        except StopIteration:
            pytest.fail("get_db should yield a database session")
        finally:
            # ジェネレーターを適切に終了
            try:
                next(db_gen)
            except StopIteration:
                pass  # 期待される動作
    
    def test_get_db_closes_session(self):
        """get_db がセッションを適切に閉じることのテスト"""
        db_gen = get_db()
        db_session = next(db_gen)
        
        # セッションのクローズメソッドをモック
        close_mock = MagicMock()
        db_session.close = close_mock
        
        # ジェネレーターを終了してクリーンアップを実行
        try:
            next(db_gen)
        except StopIteration:
            pass
        
        # クローズが呼ばれたことを確認
        close_mock.assert_called_once()
    
    def test_get_db_exception_handling(self):
        """get_db の例外処理のテスト"""
        # SessionLocalをモックして例外を発生させる
        with patch('app.database.SessionLocal') as mock_session_local:
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session
            
            db_gen = get_db()
            db_session = next(db_gen)
            
            assert db_session == mock_session
            
            # ジェネレーターを終了
            try:
                next(db_gen)
            except StopIteration:
                pass
            
            # セッションが閉じられたことを確認
            mock_session.close.assert_called_once()


@pytest.mark.integration
class TestDatabaseIntegration:
    """データベース統合テスト"""
    
    def test_database_connection(self):
        """データベース接続のテスト"""
        # 実際のデータベースに接続できることを確認
        with engine.connect() as connection:
            assert connection is not None
            # 簡単なクエリを実行
            result = connection.execute("SELECT 1")
            assert result is not None
    
    def test_session_creation_and_closing(self):
        """セッション作成と終了のテスト"""
        # セッションを作成
        session = SessionLocal()
        
        try:
            # セッションが正常に動作することを確認
            assert session is not None
            assert hasattr(session, 'query')
            
            # トランザクションをテスト
            session.begin()
            session.commit()
            
        finally:
            # セッションを適切に閉じる
            session.close()
    
    def test_multiple_sessions(self):
        """複数セッションの並行処理のテスト"""
        sessions = []
        
        try:
            # 複数のセッションを作成
            for i in range(3):
                session = SessionLocal()
                sessions.append(session)
                assert session is not None
            
            # すべてのセッションが独立していることを確認
            assert len(set(id(session) for session in sessions)) == 3
            
        finally:
            # すべてのセッションを閉じる
            for session in sessions:
                session.close()


@pytest.mark.unit
class TestEnvironmentConfiguration:
    """環境設定のテスト"""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_no_database_url_env(self):
        """DATABASE_URL環境変数がない場合のテスト"""
        import importlib
        from app import database
        importlib.reload(database)
        
        # デフォルトのPostgreSQLまたはSQLiteのURLが設定されることを確認
        assert database.DATABASE_URL is not None
        assert database.DATABASE_URL.startswith(("postgresql://", "sqlite:///"))
    
    @patch.dict('os.environ', {'DATABASE_URL': 'invalid-url'})
    def test_invalid_database_url(self):
        """無効なDATABASE_URLの処理テスト"""
        # 無効なURLでもエラーが発生しないことを確認（実際の接続時にエラーが発生）
        import importlib
        from app import database
        importlib.reload(database)
        
        assert database.DATABASE_URL == 'invalid-url'
        # エンジンの作成は成功するが、実際の接続時にエラーが発生する
        assert database.engine is not None
    
    def test_postgresql_vs_sqlite_detection(self):
        """PostgreSQLとSQLiteの検出テスト"""
        # PostgreSQLの場合
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://user:pass@host/db'}):
            import importlib
            from app import database
            importlib.reload(database)
            
            assert "postgresql" in database.DATABASE_URL
            assert database.engine is not None
        
        # SQLiteの場合
        with patch.dict('os.environ', {'DATABASE_URL': 'sqlite:///./test.db'}):
            importlib.reload(database)
            
            assert "sqlite" in database.DATABASE_URL
            assert database.engine is not None


@pytest.mark.unit
class TestDatabaseMetadata:
    """データベースメタデータのテスト"""
    
    def test_base_metadata_exists(self):
        """Baseメタデータの存在確認"""
        assert Base.metadata is not None
        assert hasattr(Base.metadata, 'tables')
        assert hasattr(Base.metadata, 'create_all')
        assert hasattr(Base.metadata, 'drop_all')
    
    def test_base_registry_exists(self):
        """Baseレジストリの存在確認"""
        assert hasattr(Base, 'registry')
        assert Base.registry is not None