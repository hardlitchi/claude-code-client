"""
Claude Code SDK統合

Claude Code SDKを使用してブラウザベースでClaude開発セッションを提供します。
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

try:
    from claude_code_sdk import query, ClaudeCodeOptions, Message
    from claude_code_sdk import (
        CLINotFoundError,
        ProcessError,
        CLIJSONDecodeError,
        CLIConnectionError
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    logging.warning("Claude Code SDK not available. Using mock implementation.")

logger = logging.getLogger(__name__)

class ClaudeCodeSession:
    """Claude Code セッション管理クラス"""
    
    def __init__(self, session_id: str, working_directory: str, system_prompt: Optional[str] = None):
        self.session_id = session_id
        self.working_directory = Path(working_directory)
        self.system_prompt = system_prompt or "あなたは専門的なソフトウェア開発アシスタントです。常に日本語で応答してください。"
        self.is_active = False
        self.created_at = datetime.now()
        self.messages: List[Dict] = []
        self.options = self._create_options()
    
    def _create_options(self) -> "ClaudeCodeOptions":
        """Claude Code SDKオプションを作成"""
        if not SDK_AVAILABLE:
            return None
            
        return ClaudeCodeOptions(
            system_prompt=self.system_prompt,
            cwd=self.working_directory,
            allowed_tools=["Read", "Write", "Bash", "Glob", "Grep", "Edit", "MultiEdit"],
            permission_mode="acceptEdits",
            max_turns=10
        )
    
    async def start_session(self) -> bool:
        """Claude Code セッションを開始"""
        try:
            if not SDK_AVAILABLE:
                logger.warning("Claude Code SDK not available, using mock mode")
                self.is_active = True
                self.add_message("system", "Claude Code セッション（モックモード）が開始されました")
                return True
            
            # 作業ディレクトリの存在確認
            if not self.working_directory.exists():
                self.working_directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"作業ディレクトリを作成しました: {self.working_directory}")
            
            self.is_active = True
            self.add_message("system", f"Claude Code セッションが開始されました（作業ディレクトリ: {self.working_directory}）")
            logger.info(f"Claude Code session started: {self.session_id}")
            return True
            
        except Exception as e:
            error_msg = f"セッション開始エラー: {str(e)}"
            logger.error(error_msg)
            self.add_message("error", error_msg)
            return False
    
    async def stop_session(self) -> bool:
        """Claude Code セッションを停止"""
        try:
            self.is_active = False
            self.add_message("system", "Claude Code セッションが停止されました")
            logger.info(f"Claude Code session stopped: {self.session_id}")
            return True
        except Exception as e:
            error_msg = f"セッション停止エラー: {str(e)}"
            logger.error(error_msg)
            self.add_message("error", error_msg)
            return False
    
    async def send_message(self, message: str) -> AsyncGenerator[str, None]:
        """Claudeにメッセージを送信（ストリーミング応答）"""
        try:
            self.add_message("user", message)
            
            if not SDK_AVAILABLE:
                # モック応答
                mock_response = f"Claude（モック）: {message} に対する応答です。実際のClaude Code SDK統合が完了すると、より高度な開発支援が可能になります。"
                self.add_message("claude", mock_response)
                yield mock_response
                return
            
            full_response = ""
            try:
                async for response_message in query(prompt=message, options=self.options):
                    content = ""
                    
                    # メッセージタイプに応じて内容を抽出
                    if hasattr(response_message, 'content'):
                        if isinstance(response_message.content, str):
                            content = response_message.content
                        elif isinstance(response_message.content, list):
                            # AssistantMessageの場合はcontentブロックのリスト
                            for block in response_message.content:
                                if hasattr(block, 'text'):
                                    content += block.text
                    elif hasattr(response_message, 'data'):
                        # SystemMessageの場合
                        content = str(response_message.data)
                    
                    if content:
                        full_response += content
                        yield content
                    
            except CLINotFoundError:
                error_msg = "Claude Code CLIが見つかりません。npm install -g @anthropic-ai/claude-code で インストールしてください。"
                logger.error(error_msg)
                self.add_message("error", error_msg)
                yield error_msg
                
            except ProcessError as e:
                error_msg = f"Claude Code プロセスエラー: {str(e)}"
                logger.error(error_msg)
                self.add_message("error", error_msg)
                yield error_msg
                
            except CLIJSONDecodeError as e:
                error_msg = f"Claude Code 応答解析エラー: {str(e)}"
                logger.error(error_msg)
                self.add_message("error", error_msg)
                yield error_msg
                
            except CLIConnectionError as e:
                error_msg = f"Claude Code 接続エラー: {str(e)}"
                logger.error(error_msg)
                self.add_message("error", error_msg)
                yield error_msg
            
            if full_response:
                self.add_message("claude", full_response)
                
        except Exception as e:
            error_msg = f"予期しないエラー: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.add_message("error", error_msg)
            yield error_msg
    
    def add_message(self, sender: str, content: str):
        """メッセージを履歴に追加"""
        self.messages.append({
            "sender": sender,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_message_history(self) -> List[Dict]:
        """メッセージ履歴を取得"""
        return self.messages.copy()

class ClaudeIntegrationManager:
    """Claude Code統合管理クラス"""
    
    def __init__(self):
        self.active_sessions: Dict[str, ClaudeCodeSession] = {}
        self.default_working_dir = Path("/tmp/claude-sessions")
        self._ensure_working_dir()
    
    def _ensure_working_dir(self):
        """デフォルト作業ディレクトリの作成"""
        self.default_working_dir.mkdir(parents=True, exist_ok=True)
    
    async def create_session(
        self, 
        session_id: str, 
        working_directory: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> ClaudeCodeSession:
        """新しいClaude Code セッションを作成"""
        if session_id in self.active_sessions:
            raise ValueError(f"セッション {session_id} は既に存在します")
        
        # 作業ディレクトリが指定されていない場合はデフォルトを使用
        if not working_directory:
            working_directory = str(self.default_working_dir / session_id)
        
        session = ClaudeCodeSession(session_id, working_directory, system_prompt)
        self.active_sessions[session_id] = session
        
        # セッション開始
        success = await session.start_session()
        if not success:
            del self.active_sessions[session_id]
            raise RuntimeError(f"セッション {session_id} の開始に失敗しました")
        
        logger.info(f"新しいClaude Codeセッションを作成しました: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[ClaudeCodeSession]:
        """セッションを取得"""
        session = self.active_sessions.get(session_id)
        if session and not session.is_active:
            logger.warning(f"非アクティブなセッションが要求されました: {session_id}")
        return session
    
    async def remove_session(self, session_id: str) -> bool:
        """セッションを削除"""
        if session_id not in self.active_sessions:
            logger.warning(f"存在しないセッション削除が要求されました: {session_id}")
            return False
        
        session = self.active_sessions[session_id]
        await session.stop_session()
        del self.active_sessions[session_id]
        
        logger.info(f"Claude Codeセッションを削除しました: {session_id}")
        return True
    
    def get_active_sessions(self) -> List[Dict[str, any]]:
        """アクティブなセッション一覧を取得"""
        return [
            {
                "session_id": session_id,
                "working_directory": str(session.working_directory),
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat(),
                "message_count": len(session.messages)
            }
            for session_id, session in self.active_sessions.items()
        ]
    
    async def cleanup_inactive_sessions(self) -> int:
        """非アクティブなセッションをクリーンアップ"""
        inactive_sessions = [
            session_id for session_id, session in self.active_sessions.items()
            if not session.is_active
        ]
        
        for session_id in inactive_sessions:
            await self.remove_session(session_id)
        
        if inactive_sessions:
            logger.info(f"{len(inactive_sessions)}個の非アクティブセッションをクリーンアップしました")
        
        return len(inactive_sessions)

class ClaudeIntegration:
    """WebSocket用のClaude統合クラス"""
    
    def __init__(self):
        self.manager = ClaudeIntegrationManager()
    
    async def send_message_stream(self, message: str, session_id: str) -> AsyncGenerator[str, None]:
        """メッセージをClaude Codeに送信（ストリーミング）"""
        session = await self.manager.get_session(session_id)
        if not session:
            yield f"エラー: セッション {session_id} が見つかりません"
            return
        
        if not session.is_active:
            yield f"エラー: セッション {session_id} が非アクティブです"
            return
        
        async for response_chunk in session.send_message(message):
            yield response_chunk
    
    async def send_message(self, message: str, session_id: str = None) -> str:
        """メッセージをClaude Codeに送信（非ストリーミング、下位互換性のため）"""
        if not session_id:
            return "エラー: セッションIDが必要です"
        
        full_response = ""
        async for chunk in self.send_message_stream(message, session_id):
            full_response += chunk
        
        return full_response
    
    async def create_session(
        self, 
        session_id: str, 
        working_directory: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> Dict[str, any]:
        """新しいセッションを作成"""
        try:
            session = await self.manager.create_session(session_id, working_directory, system_prompt)
            return {
                "success": True,
                "session_id": session.session_id,
                "working_directory": str(session.working_directory),
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat()
            }
        except Exception as e:
            logger.error(f"セッション作成エラー: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, any]]:
        """セッション情報を取得"""
        session = await self.manager.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "working_directory": str(session.working_directory),
            "is_active": session.is_active,
            "created_at": session.created_at.isoformat(),
            "message_count": len(session.messages)
        }
    
    async def get_session_history(self, session_id: str) -> Optional[List[Dict]]:
        """セッションのメッセージ履歴を取得"""
        session = await self.manager.get_session(session_id)
        if not session:
            return None
        
        return session.get_message_history()
    
    async def remove_session(self, session_id: str) -> bool:
        """セッションを削除"""
        return await self.manager.remove_session(session_id)
    
    async def list_sessions(self) -> List[Dict[str, any]]:
        """すべてのアクティブセッションを一覧表示"""
        return self.manager.get_active_sessions()
    
    async def cleanup_sessions(self) -> int:
        """非アクティブセッションをクリーンアップ"""
        return await self.manager.cleanup_inactive_sessions()

# グローバルインスタンス
claude_manager = ClaudeIntegrationManager()