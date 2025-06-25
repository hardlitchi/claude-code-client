"""
Claude Code Client - メインアプリケーション
FastAPI アプリケーションのエントリーポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from .routers import auth, sessions, users, terminal, claude, websocket, files, projects
from .init_db import init_database
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース初期化（テスト時は無視）
import os
if not os.getenv("TESTING"):
    try:
        init_database()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

# アプリケーション作成
app = FastAPI(
    title="Claude Code Client",
    description="Webブラウザから Claude Code を操作可能にするアプリケーションサーバー",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS設定
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーター登録
app.include_router(auth.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(terminal.router, prefix="/api")
app.include_router(claude.router, prefix="/api")
app.include_router(websocket.router, prefix="/api")
app.include_router(files.router)
app.include_router(projects.router)

# 静的ファイル配信（将来のフロントエンドビルド用）
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Claude Code Client API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/health")
async def health():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )