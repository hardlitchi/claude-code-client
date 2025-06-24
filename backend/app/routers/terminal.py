"""
Terminal WebSocket 接続のAPIルーター
"""

import asyncio
import os
import pty
import subprocess
import select
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Session as SessionModel

router = APIRouter(prefix="/terminal", tags=["Terminal"])

# アクティブなターミナル接続を管理
active_terminals: Dict[str, dict] = {}

class TerminalManager:
    def __init__(self, session_id: str, working_directory: str = "/tmp"):
        self.session_id = session_id
        self.working_directory = working_directory
        self.master_fd = None
        self.slave_fd = None
        self.process = None
        
    async def start_terminal(self):
        """ターミナルプロセスを開始"""
        try:
            # 作業ディレクトリが存在しない場合は作成
            os.makedirs(self.working_directory, exist_ok=True)
            
            # pseudoterminal を作成
            self.master_fd, self.slave_fd = pty.openpty()
            
            # シェルプロセスを開始
            self.process = subprocess.Popen(
                ['/bin/bash'],
                stdin=self.slave_fd,
                stdout=self.slave_fd,
                stderr=self.slave_fd,
                cwd=self.working_directory,
                env=os.environ.copy(),
                preexec_fn=os.setsid
            )
            
            # 初期化コマンドを送信
            initial_commands = [
                f"cd {self.working_directory}",
                "export PS1='\\u@\\h:\\w$ '",
                "clear"
            ]
            
            for cmd in initial_commands:
                os.write(self.master_fd, f"{cmd}\n".encode())
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"Terminal start error: {e}")
            raise e
    
    async def read_output(self):
        """ターミナル出力を読み取り"""
        try:
            # ノンブロッキング読み取り
            ready, _, _ = select.select([self.master_fd], [], [], 0.1)
            if ready:
                data = os.read(self.master_fd, 1024)
                return data.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Terminal read error: {e}")
        return None
    
    async def write_input(self, data: str):
        """ターミナルに入力を送信"""
        try:
            os.write(self.master_fd, data.encode())
        except Exception as e:
            print(f"Terminal write error: {e}")
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=5)
        except:
            pass
        
        try:
            if self.master_fd:
                os.close(self.master_fd)
            if self.slave_fd:
                os.close(self.slave_fd)
        except:
            pass

@router.websocket("/ws/{session_id}")
async def websocket_terminal(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    """Terminal WebSocket接続"""
    await websocket.accept()
    
    try:
        # TODO: 認証チェック（WebSocketでの認証は複雑なので後で実装）
        # 現在は簡単な実装
        
        # セッション情報を取得
        session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
        if not session:
            await websocket.send_text("ERROR: セッションが見つかりません")
            await websocket.close()
            return
        
        # ターミナルマネージャーを作成
        working_dir = session.working_directory or "/tmp"
        terminal = TerminalManager(session_id, working_dir)
        
        # ターミナルを開始
        await terminal.start_terminal()
        active_terminals[session_id] = {
            'terminal': terminal,
            'websocket': websocket
        }
        
        # 初期メッセージを送信
        await websocket.send_text(f"Terminal connected to session: {session.name}\n")
        
        # 出力読み取りタスクを開始
        async def read_terminal_output():
            while True:
                try:
                    output = await terminal.read_output()
                    if output:
                        await websocket.send_text(output)
                    await asyncio.sleep(0.01)  # 10ms間隔
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    print(f"Output read error: {e}")
                    break
        
        # 出力読み取りタスクを開始
        output_task = asyncio.create_task(read_terminal_output())
        
        try:
            # 入力を処理
            while True:
                data = await websocket.receive_text()
                await terminal.write_input(data)
        
        except WebSocketDisconnect:
            print(f"Terminal WebSocket disconnected: {session_id}")
        
        finally:
            # クリーンアップ
            output_task.cancel()
            terminal.cleanup()
            if session_id in active_terminals:
                del active_terminals[session_id]
    
    except Exception as e:
        print(f"Terminal WebSocket error: {e}")
        await websocket.send_text(f"ERROR: {str(e)}")
        await websocket.close()

@router.get("/{session_id}/status")
async def get_terminal_status(
    session_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """ターミナル接続状態を取得"""
    is_connected = session_id in active_terminals
    return {
        "session_id": session_id,
        "connected": is_connected,
        "status": "active" if is_connected else "inactive"
    }