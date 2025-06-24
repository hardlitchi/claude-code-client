"""
データベース初期化とシードデータ投入
"""

from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models import User
from .auth import get_password_hash
import logging

logger = logging.getLogger(__name__)

def create_tables():
    """データベーステーブルを作成"""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")

def create_default_users():
    """デフォルトユーザーを作成"""
    db = SessionLocal()
    try:
        # 管理者ユーザーをチェック
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            logger.info("Creating default admin user...")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_admin=True
            )
            db.add(admin_user)
            logger.info("Default admin user created")
        else:
            logger.info("Admin user already exists")

        # テストユーザーをチェック
        test_user = db.query(User).filter(User.username == "testuser").first()
        if not test_user:
            logger.info("Creating default test user...")
            test_user = User(
                username="testuser",
                email="test@example.com",
                hashed_password=get_password_hash("test123"),
                is_active=True,
                is_admin=False
            )
            db.add(test_user)
            logger.info("Default test user created")
        else:
            logger.info("Test user already exists")

        db.commit()
        logger.info("Default users setup completed")
    
    except Exception as e:
        logger.error(f"Error creating default users: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def init_database():
    """データベースを初期化"""
    logger.info("Initializing database...")
    create_tables()
    create_default_users()
    logger.info("Database initialization completed")