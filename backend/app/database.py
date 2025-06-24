"""
データベース設定とセッション管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

# データベースURL設定
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://claude_user:claude_password@db:5432/claude_db"
)

# SQLite を開発時のフォールバックとして使用
if "postgresql" not in DATABASE_URL:
    DATABASE_URL = "sqlite:///./claude_client.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """データベースセッションを取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()