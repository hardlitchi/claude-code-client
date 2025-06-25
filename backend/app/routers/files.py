"""
ファイル管理API
セッション内のファイル操作（CRUD、ディレクトリ操作、ファイル監視）を提供
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from fastapi.responses import FileResponse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
import json
from datetime import datetime

from ..database import get_db
from ..models import User, Session
from ..auth import get_current_user
from ..websocket_manager import manager
from sqlalchemy.orm import Session as DBSession

router = APIRouter(prefix="/api/files", tags=["files"])

# ファイル変更監視ハンドラー
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__()
    
    def on_modified(self, event):
        if not event.is_directory:
            asyncio.create_task(self._notify_file_change("modified", event.src_path))
    
    def on_created(self, event):
        asyncio.create_task(self._notify_file_change("created", event.src_path))
    
    def on_deleted(self, event):
        asyncio.create_task(self._notify_file_change("deleted", event.src_path))
    
    def on_moved(self, event):
        asyncio.create_task(self._notify_file_change("moved", event.dest_path, event.src_path))
    
    async def _notify_file_change(self, event_type: str, file_path: str, old_path: str = None):
        """ファイル変更をWebSocket経由で通知"""
        message = {
            "type": "file_change",
            "event_type": event_type,
            "file_path": file_path,
            "old_path": old_path,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_to_session(self.session_id, json.dumps(message))

# セッション別ファイル監視オブザーバー
file_observers: Dict[str, Observer] = {}

class FileTree:
    """ファイルツリー構造を生成するクラス"""
    
    @staticmethod
    def get_file_tree(path: Path, max_depth: int = 5, current_depth: int = 0) -> Dict[str, Any]:
        """指定パスのファイルツリーを取得"""
        if current_depth >= max_depth:
            return {"type": "directory", "name": path.name, "children": [], "truncated": True}
        
        try:
            if path.is_file():
                return {
                    "type": "file",
                    "name": path.name,
                    "size": path.stat().st_size,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                    "extension": path.suffix
                }
            elif path.is_dir():
                children = []
                try:
                    for item in sorted(path.iterdir()):
                        # 隠しファイルやシステムファイルをスキップ
                        if item.name.startswith('.') and item.name not in ['.env', '.gitignore']:
                            continue
                        children.append(FileTree.get_file_tree(item, max_depth, current_depth + 1))
                except PermissionError:
                    pass
                
                return {
                    "type": "directory",
                    "name": path.name,
                    "children": children,
                    "size": len(children)
                }
        except (OSError, PermissionError):
            return {"type": "error", "name": path.name, "error": "アクセス権限がありません"}

@router.get("/tree/{session_id}")
async def get_file_tree(
    session_id: str,
    path: str = "",
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """セッションのファイルツリーを取得"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # ベースパスの設定
    base_path = Path(session.working_directory)
    if path:
        target_path = base_path / path
    else:
        target_path = base_path
    
    # セキュリティチェック: ベースパス外へのアクセスを防止
    try:
        target_path = target_path.resolve()
        base_path = base_path.resolve()
        if not str(target_path).startswith(str(base_path)):
            raise HTTPException(status_code=403, detail="アクセス権限がありません")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="無効なパスです")
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="ファイルまたはディレクトリが見つかりません")
    
    return FileTree.get_file_tree(target_path)

@router.get("/content/{session_id}")
async def get_file_content(
    session_id: str,
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ファイル内容を取得"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # ファイルパスの検証
    base_path = Path(session.working_directory).resolve()
    target_path = (base_path / file_path).resolve()
    
    if not str(target_path).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="アクセス権限がありません")
    
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    try:
        # ファイルサイズチェック（10MB制限）
        if target_path.stat().st_size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="ファイルサイズが大きすぎます（10MB制限）")
        
        # バイナリファイルの検出
        with open(target_path, 'rb') as f:
            sample = f.read(1024)
            if b'\x00' in sample:
                return {
                    "type": "binary",
                    "message": "バイナリファイルのため表示できません",
                    "size": target_path.stat().st_size
                }
        
        # テキストファイルの読み込み
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "type": "text",
            "content": content,
            "size": target_path.stat().st_size,
            "modified": datetime.fromtimestamp(target_path.stat().st_mtime).isoformat()
        }
        
    except UnicodeDecodeError:
        # UTF-8でデコードできない場合は他のエンコーディングを試行
        encodings = ['shift_jis', 'euc-jp', 'iso-2022-jp']
        for encoding in encodings:
            try:
                with open(target_path, 'r', encoding=encoding) as f:
                    content = f.read()
                return {
                    "type": "text",
                    "content": content,
                    "encoding": encoding,
                    "size": target_path.stat().st_size,
                    "modified": datetime.fromtimestamp(target_path.stat().st_mtime).isoformat()
                }
            except UnicodeDecodeError:
                continue
        
        raise HTTPException(status_code=415, detail="ファイルエンコーディングがサポートされていません")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイル読み込みエラー: {str(e)}")

@router.put("/content/{session_id}")
async def update_file_content(
    session_id: str,
    file_path: str,
    content: str,
    encoding: str = "utf-8",
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ファイル内容を更新"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # ファイルパスの検証
    base_path = Path(session.working_directory).resolve()
    target_path = (base_path / file_path).resolve()
    
    if not str(target_path).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="アクセス権限がありません")
    
    try:
        # ディレクトリが存在しない場合は作成
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ファイル保存
        with open(target_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        # WebSocket経由で変更を通知
        message = {
            "type": "file_updated",
            "file_path": str(target_path.relative_to(base_path)),
            "user": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_to_session(session_id, json.dumps(message))
        
        return {
            "success": True,
            "message": "ファイルが正常に保存されました",
            "size": target_path.stat().st_size,
            "modified": datetime.fromtimestamp(target_path.stat().st_mtime).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ファイル保存エラー: {str(e)}")

@router.post("/create/{session_id}")
async def create_file_or_directory(
    session_id: str,
    path: str,
    type: str,  # "file" または "directory"
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ファイルまたはディレクトリを作成"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # ファイルパスの検証
    base_path = Path(session.working_directory).resolve()
    target_path = (base_path / path).resolve()
    
    if not str(target_path).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="アクセス権限がありません")
    
    if target_path.exists():
        raise HTTPException(status_code=409, detail="ファイルまたはディレクトリが既に存在します")
    
    try:
        if type == "directory":
            target_path.mkdir(parents=True, exist_ok=True)
        elif type == "file":
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.touch()
        else:
            raise HTTPException(status_code=400, detail="typeは'file'または'directory'である必要があります")
        
        # WebSocket経由で作成を通知
        message = {
            "type": "file_created",
            "file_path": str(target_path.relative_to(base_path)),
            "file_type": type,
            "user": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_to_session(session_id, json.dumps(message))
        
        return {"success": True, "message": f"{type}が正常に作成されました"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"作成エラー: {str(e)}")

@router.delete("/delete/{session_id}")
async def delete_file_or_directory(
    session_id: str,
    path: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ファイルまたはディレクトリを削除"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # ファイルパスの検証
    base_path = Path(session.working_directory).resolve()
    target_path = (base_path / path).resolve()
    
    if not str(target_path).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="アクセス権限がありません")
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="ファイルまたはディレクトリが見つかりません")
    
    try:
        if target_path.is_dir():
            shutil.rmtree(target_path)
        else:
            target_path.unlink()
        
        # WebSocket経由で削除を通知
        message = {
            "type": "file_deleted",
            "file_path": str(target_path.relative_to(base_path)),
            "user": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_to_session(session_id, json.dumps(message))
        
        return {"success": True, "message": "正常に削除されました"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"削除エラー: {str(e)}")

@router.post("/upload/{session_id}")
async def upload_file(
    session_id: str,
    path: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ファイルをアップロード"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # ファイルサイズチェック（50MB制限）
    if file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="ファイルサイズが大きすぎます（50MB制限）")
    
    # ファイルパスの検証
    base_path = Path(session.working_directory).resolve()
    target_path = (base_path / path / file.filename).resolve()
    
    if not str(target_path).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="アクセス権限がありません")
    
    try:
        # ディレクトリが存在しない場合は作成
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ファイル保存
        with open(target_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # WebSocket経由でアップロードを通知
        message = {
            "type": "file_uploaded",
            "file_path": str(target_path.relative_to(base_path)),
            "filename": file.filename,
            "size": len(content),
            "user": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_to_session(session_id, json.dumps(message))
        
        return {
            "success": True,
            "message": "ファイルが正常にアップロードされました",
            "filename": file.filename,
            "size": len(content)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"アップロードエラー: {str(e)}")

@router.get("/download/{session_id}")
async def download_file(
    session_id: str,
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ファイルをダウンロード"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # ファイルパスの検証
    base_path = Path(session.working_directory).resolve()
    target_path = (base_path / file_path).resolve()
    
    if not str(target_path).startswith(str(base_path)):
        raise HTTPException(status_code=403, detail="アクセス権限がありません")
    
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    return FileResponse(
        path=target_path,
        filename=target_path.name,
        media_type='application/octet-stream'
    )

@router.post("/watch/{session_id}")
async def start_file_watching(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ファイル変更監視を開始"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # 既に監視中の場合は停止
    if session_id in file_observers:
        file_observers[session_id].stop()
        del file_observers[session_id]
    
    # 新しい監視を開始
    try:
        event_handler = FileChangeHandler(session_id)
        observer = Observer()
        observer.schedule(event_handler, session.working_directory, recursive=True)
        observer.start()
        
        file_observers[session_id] = observer
        
        return {"success": True, "message": "ファイル監視を開始しました"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"監視開始エラー: {str(e)}")

@router.delete("/watch/{session_id}")
async def stop_file_watching(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ファイル変更監視を停止"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    if session_id in file_observers:
        file_observers[session_id].stop()
        del file_observers[session_id]
        return {"success": True, "message": "ファイル監視を停止しました"}
    else:
        raise HTTPException(status_code=404, detail="監視中のセッションが見つかりません")