"""
Claude Code統合

Claude Code SDK/CLIを使用してブラウザベースでClaude開発セッションを提供します。
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

# Claude Code SDKの利用可能性をチェック
try:
    from claude_code_sdk import query, ClaudeCodeOptions
    SDK_AVAILABLE = True
    logging.info("Claude Code SDK found and loaded")
except ImportError:
    SDK_AVAILABLE = False
    logging.warning("Claude Code SDK not available")

# Claude Code CLIの利用可能性をチェック
try:
    result = subprocess.run(['which', 'claude'], capture_output=True, text=True)
    CLI_AVAILABLE = result.returncode == 0
    if CLI_AVAILABLE:
        # バージョン確認
        version_result = subprocess.run(['claude', '--version'], capture_output=True, text=True)
        logging.info(f"Claude Code CLI found: {version_result.stdout.strip()}")
    else:
        logging.warning("Claude Code CLI not found in PATH")
except Exception as e:
    CLI_AVAILABLE = False
    logging.warning(f"Claude Code CLI check failed: {e}")

# 使用する方法を決定（SDK優先）
USE_SDK = SDK_AVAILABLE
USE_CLI = CLI_AVAILABLE and not SDK_AVAILABLE

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
        self.cli_env = self._create_cli_env()
    
    def _create_cli_env(self) -> Dict[str, str]:
        """Claude Code CLI用の環境変数を作成"""
        env = os.environ.copy()
        if self.working_directory.exists():
            env['PWD'] = str(self.working_directory)
        return env
    
    def _create_sdk_options(self) -> Optional["ClaudeCodeOptions"]:
        """Claude Code SDK用のオプションを作成"""
        if not SDK_AVAILABLE:
            return None
        try:
            return ClaudeCodeOptions(
                system_prompt=self.system_prompt,
                cwd=str(self.working_directory),
                allowed_tools=["Read", "Write", "Bash", "Glob", "Grep", "Edit", "MultiEdit"],
                permission_mode="acceptEdits",
                max_turns=10
            )
        except Exception as e:
            logger.error(f"SDK options creation failed: {e}")
            return None
    
    def _optimize_prompt_for_cost(self, message: str) -> str:
        """開発用: API コストを最小化するためプロンプトを最適化"""
        # 短い応答を要求することでコストを削減
        if len(message) > 200:
            # 長いメッセージは要約
            return f"簡潔に回答してください: {message[:200]}..."
        
        # 開発専用の指示を追加
        optimized = f"{message}\n\n[開発モード: 簡潔で実用的な回答をお願いします]"
        return optimized
    
    async def start_session(self) -> bool:
        """Claude Code セッションを開始"""
        try:
            if not (USE_SDK or USE_CLI):
                logger.warning("Claude Code SDK/CLI not available, using mock mode")
                self.is_active = True
                self.add_message("system", "Claude Code セッション（モックモード）が開始されました")
                return True
            
            # 作業ディレクトリの存在確認
            if not self.working_directory.exists():
                self.working_directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"作業ディレクトリを作成しました: {self.working_directory}")
            
            method = "SDK" if USE_SDK else "CLI"
            self.is_active = True
            self.add_message("system", f"Claude Code セッション（{method}）が開始されました（作業ディレクトリ: {self.working_directory}）")
            logger.info(f"Claude Code session started using {method}: {self.session_id}")
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
            
            # モック応答
            if not (USE_SDK or USE_CLI):
                if "hello" in message.lower() or "こんにちは" in message.lower():
                    mock_response = "こんにちは！Claude Code（モック）です。プロジェクトの開発をお手伝いします。ファイルの作成、編集、コマンド実行などをサポートできます。"
                elif "file" in message.lower() or "ファイル" in message:
                    mock_response = f"ファイル操作について承知しました。現在の作業ディレクトリは {self.working_directory} です。ファイルの作成や編集をお手伝いできます。（モックモード）"
                elif "code" in message.lower() or "コード" in message:
                    mock_response = "コード生成・編集をお手伝いします。どのような言語で、どのような機能を実装したいですか？（モックモード）"
                else:
                    mock_response = f"Claude（モック）: 「{message}」についてお答えします。実際のClaude Code SDK/CLI統合が完了すると、ファイル操作、コード生成、ターミナル操作など、より高度な開発支援が可能になります。\n\n現在は API クレジット不足のため、モックモードで動作しています。"
                
                self.add_message("claude", mock_response)
                yield mock_response
                return

            # SDKを使用する場合（開発者モード）
            if USE_SDK:
                try:
                    # 開発効率化: 短縮プロンプトで課金最小化
                    optimized_message = self._optimize_prompt_for_cost(message)
                    
                    options = self._create_sdk_options()
                    if not options:
                        raise Exception("SDK options creation failed")
                    
                    full_response = ""
                    
                    # TaskGroup例外を適切に処理するためtry-except内でasyncループを実行
                    try:
                        async for response_chunk in query(prompt=optimized_message, options=options):
                            if hasattr(response_chunk, 'content') and response_chunk.content:
                                chunk = str(response_chunk.content)
                                full_response += chunk
                                yield chunk
                    except* Exception as exc_group:
                        # TaskGroupのExceptionGroupを処理
                        for exc in exc_group.exceptions:
                            logger.error(f"SDK TaskGroup exception: {exc}")
                        raise Exception(f"SDK TaskGroup error: {len(exc_group.exceptions)} sub-exceptions")
                    
                    if full_response:
                        self.add_message("claude", full_response)
                    return
                    
                except Exception as e:
                    logger.error(f"SDK error: {e}")
                    error_msg = f"Claude Code SDK エラー: {str(e)}"
                    self.add_message("error", error_msg)
                    yield error_msg
                    return

            # CLIを使用する場合
            if USE_CLI:
                try:
                    # Claude Code CLIを実行（非対話型）
                    cmd = ['claude', '--print', message]
                    
                    # プロセスを開始
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=str(self.working_directory),
                        env=self.cli_env
                    )
                    
                    # プロセス完了を待機
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        # 成功時の応答を処理
                        response = stdout.decode('utf-8')
                        self.add_message("claude", response)
                        yield response
                    else:
                        # エラー時の処理
                        error_output = stderr.decode('utf-8').strip()
                        if "Credit balance is too low" in error_output:
                            error_msg = "Claude API クレジット残高が不足しています。Anthropic Console でクレジットを追加してください。"
                        elif "API key" in error_output.lower():
                            error_msg = "Claude API キーが無効または未設定です。ANTHROPIC_API_KEY 環境変数を確認してください。"
                        elif "rate limit" in error_output.lower():
                            error_msg = "Claude API のレート制限に達しました。しばらく待ってから再試行してください。"
                        else:
                            error_msg = f"Claude Code CLI エラー: {error_output}"
                        
                        logger.error(error_msg)
                        self.add_message("error", error_msg)
                        yield error_msg
                        
                except FileNotFoundError:
                    error_msg = "Claude Code CLIが見つかりません。npm install -g @anthropic-ai/claude-code でインストールしてください。"
                    logger.error(error_msg)
                    self.add_message("error", error_msg)
                    yield error_msg
                    
                except Exception as e:
                    error_msg = f"Claude Code プロセスエラー: {str(e)}"
                    logger.error(error_msg)
                    self.add_message("error", error_msg)
                    yield error_msg
                
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