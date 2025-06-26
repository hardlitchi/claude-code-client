"""
ターミナルマネージャー
基本ターミナル（無料版）とClaudeターミナル（有料版）の管理
"""

import asyncio
import json
import logging
import os
import pty
import select
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

from .claude_integration import ClaudeCodeSession

logger = logging.getLogger(__name__)

class BaseTerminalManager(ABC):
    """ターミナルマネージャーの基底クラス"""
    
    def __init__(self, session_id: str, working_directory: str = "/tmp"):
        self.session_id = session_id
        self.working_directory = working_directory
        self.master_fd = None
        self.slave_fd = None
        self.process = None
        self.is_initialized = False
        self.created_at = datetime.now()
        
    @abstractmethod
    async def start_terminal(self):
        """ターミナルプロセスを開始"""
        pass
    
    async def read_output(self):
        """ターミナル出力を読み取り"""
        try:
            if not self.master_fd:
                return None
                
            # ノンブロッキング読み取り
            ready, _, _ = select.select([self.master_fd], [], [], 0.1)
            if ready:
                data = os.read(self.master_fd, 1024)
                return data.decode('utf-8', errors='ignore')
        except Exception as e:
            logger.error(f"Terminal read error: {e}")
        return None
    
    async def write_input(self, data: str):
        """ターミナルに入力を送信"""
        try:
            if self.master_fd:
                os.write(self.master_fd, data.encode())
        except Exception as e:
            logger.error(f"Terminal write error: {e}")
    
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

class BasicTerminalManager(BaseTerminalManager):
    """基本ターミナルマネージャー（無料版）"""
    
    def __init__(self, session_id: str, working_directory: str = "/tmp"):
        super().__init__(session_id, working_directory)
        self.terminal_type = "basic"
        
    async def start_terminal(self):
        """基本ターミナルプロセスを開始"""
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
            
            # 初期化は新規セッションの場合のみ実行
            if not self.is_initialized:
                initial_commands = [
                    f"cd {self.working_directory}",
                    "export PS1='[Basic] \\u@\\h:\\w$ '"
                ]
                
                for cmd in initial_commands:
                    os.write(self.master_fd, f"{cmd}\n".encode())
                    await asyncio.sleep(0.1)
                
                self.is_initialized = True
                logger.info(f"Basic terminal initialized for session {self.session_id}")
                
        except Exception as e:
            logger.error(f"Basic terminal start error: {e}")
            raise e

class ClaudeTerminalManager(BaseTerminalManager):
    """Claudeターミナルマネージャー（有料版）"""
    
    def __init__(self, session_id: str, working_directory: str = "/tmp", system_prompt: Optional[str] = None):
        super().__init__(session_id, working_directory)
        self.terminal_type = "claude"
        self.claude_session = None
        self.system_prompt = system_prompt or "あなたは専門的なソフトウェア開発アシスタントです。ターミナル環境で作業しているユーザーをサポートしてください。常に日本語で応答してください。"
        
    async def start_terminal(self):
        """Claudeターミナルプロセスを開始"""
        try:
            # 基本ターミナル機能を初期化
            await self._initialize_basic_terminal()
            
            # Claude統合セッションを初期化
            await self._initialize_claude_session()
            
            logger.info(f"Claude terminal initialized for session {self.session_id}")
                
        except Exception as e:
            logger.error(f"Claude terminal start error: {e}")
            raise e
    
    async def _initialize_basic_terminal(self):
        """基本ターミナル機能を初期化"""
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
        
        # 初期化は新規セッションの場合のみ実行
        if not self.is_initialized:
            initial_commands = [
                f"cd {self.working_directory}",
                "export PS1='[Claude] \\u@\\h:\\w$ '"
            ]
            
            for cmd in initial_commands:
                os.write(self.master_fd, f"{cmd}\n".encode())
                await asyncio.sleep(0.1)
            
            self.is_initialized = True
    
    async def _initialize_claude_session(self):
        """Claude統合セッションを初期化"""
        try:
            self.claude_session = ClaudeCodeSession(
                session_id=self.session_id,
                working_directory=self.working_directory,
                system_prompt=self.system_prompt
            )
            await self.claude_session.start_session()
        except Exception as e:
            logger.warning(f"Claude session initialization failed: {e}")
            # Claude統合が失敗してもターミナルは使用可能
    
    def cleanup(self):
        """リソースをクリーンアップ"""
        if self.claude_session:
            # Claude セッションのクリーンアップ
            # TODO: claude_session.cleanup() が実装されている場合は呼び出し
            pass
        
        super().cleanup()

# アクティブなターミナルセッションを管理
active_terminals: Dict[str, BaseTerminalManager] = {}

def get_terminal_manager(session_id: str, terminal_type: str, working_directory: str = "/tmp", **kwargs) -> BaseTerminalManager:
    """ターミナルマネージャーを取得・作成"""
    if terminal_type == "claude":
        return ClaudeTerminalManager(
            session_id=session_id,
            working_directory=working_directory,
            system_prompt=kwargs.get('system_prompt')
        )
    else:
        return BasicTerminalManager(
            session_id=session_id,
            working_directory=working_directory
        )

def has_active_terminal(session_id: str) -> bool:
    """アクティブなターミナルセッションが存在するかチェック"""
    return session_id in active_terminals

def get_active_terminal(session_id: str) -> Optional[BaseTerminalManager]:
    """アクティブなターミナルセッションを取得"""
    return active_terminals.get(session_id)

def set_active_terminal(session_id: str, terminal: BaseTerminalManager):
    """アクティブなターミナルセッションを設定"""
    active_terminals[session_id] = terminal

def remove_active_terminal(session_id: str):
    """アクティブなターミナルセッションを削除"""
    if session_id in active_terminals:
        terminal = active_terminals[session_id]
        terminal.cleanup()
        del active_terminals[session_id]