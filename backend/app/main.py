"""
Claude Code Client - メインアプリケーション
FastAPI アプリケーションのエントリーポイント
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from .database import Base, engine
from .routers import auth, sessions, users, terminal, claude

# データベーステーブル作成
Base.metadata.create_all(bind=engine)

# アプリケーション作成
app = FastAPI(
    title="Claude Code Client",
    description="Webブラウザから Claude Code を操作可能にするアプリケーションサーバー",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Vue.js開発サーバー
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