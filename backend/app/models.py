"""
データベースモデル定義
Claude Code Client の全テーブル定義
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    """ユーザーモデル"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # 拡張情報
    preferences = Column(JSONB, default=lambda: {})
    resource_quota = Column(JSONB, default=lambda: {
        "max_sessions": 5,
        "max_worktrees": 10,
        "storage_limit_gb": 5,
        "api_calls_per_hour": 1000
    })
    
    # 統計情報
    last_login = Column(DateTime(timezone=True))
    login_count = Column(Integer, default=0)
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # リレーション
    sessions = relationship("Session", back_populates="user")
    projects = relationship("Project", back_populates="owner")
    worktrees = relationship("Worktree", back_populates="user")
    auth_tokens = relationship("AuthToken", back_populates="user")
    notification_settings = relationship("NotificationSetting", back_populates="user")
    notification_history = relationship("NotificationHistory", back_populates="user")
    file_operations = relationship("FileOperation", back_populates="user")

class Session(Base):
    """Claude Code セッションモデル"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="stopped")  # running, stopped, error, starting, stopping
    
    # 技術情報
    working_directory = Column(String(500))
    container_id = Column(String(64))
    port_mapping = Column(JSONB, default=lambda: {})
    
    # Claude 統合
    context_data = Column(JSONB)
    claude_session_id = Column(String(64))
    total_tokens_used = Column(Integer, default=0)
    
    # リソース管理
    resource_limits = Column(JSONB, default=lambda: {
        "cpu_limit": 1.0,
        "memory_limit_mb": 512,
        "storage_limit_mb": 1024,
        "process_limit": 50
    })
    
    # 関連情報
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    worktree_id = Column(String(36), ForeignKey("worktrees.worktree_id"))
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed = Column(DateTime(timezone=True), server_default=func.now())

    # リレーション
    user = relationship("User", back_populates="sessions")
    project = relationship("Project", back_populates="sessions")
    worktree = relationship("Worktree", back_populates="sessions")
    collaboration_sessions = relationship("CollaborationSession", back_populates="session")
    file_operations = relationship("FileOperation", back_populates="session")

class AuthToken(Base):
    """認証トークンモデル"""
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(String(36), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_type = Column(String(20), default="access")  # access, refresh
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # セキュリティ情報
    ip_address = Column(INET)
    user_agent = Column(Text)
    last_used = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    user = relationship("User", back_populates="auth_tokens")

class Project(Base):
    """プロジェクトモデル"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String(36), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    project_type = Column(String(50), default="general")
    
    # リポジトリ情報
    repository_url = Column(String(500))
    local_path = Column(String(500))
    default_branch = Column(String(100), default="main")
    
    # 技術スタック
    tech_stack = Column(JSONB, default=lambda: [])
    build_config = Column(JSONB, default=lambda: {})
    deploy_config = Column(JSONB, default=lambda: {})
    environment_vars = Column(JSONB, default=lambda: {})
    
    # 権限管理
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=False)
    collaborators = Column(JSONB, default=lambda: [])
    
    # 統計情報
    total_sessions = Column(Integer, default=0)
    total_commits = Column(Integer, default=0)
    total_worktrees = Column(Integer, default=0)
    last_activity = Column(DateTime(timezone=True))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    owner = relationship("User", back_populates="projects")
    sessions = relationship("Session", back_populates="project")
    worktrees = relationship("Worktree", back_populates="project")

class Worktree(Base):
    """Worktreeモデル"""
    __tablename__ = "worktrees"

    id = Column(Integer, primary_key=True, index=True)
    worktree_id = Column(String(36), unique=True, index=True, nullable=False)
    
    # Git 情報
    repository_path = Column(String(500), nullable=False)
    worktree_path = Column(String(500), nullable=False, unique=True)
    branch_name = Column(String(100), nullable=False)
    commit_hash = Column(String(40))
    remote_url = Column(String(500))
    
    # ステータス
    status = Column(String(20), default="active")  # active, inactive, error
    sync_status = Column(String(20), default="clean")  # clean, dirty, conflicted, syncing
    last_sync = Column(DateTime(timezone=True))
    
    # 統計情報
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)
    uncommitted_changes = Column(Boolean, default=False)
    untracked_files = Column(Integer, default=0)
    
    # 関連情報
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    user = relationship("User", back_populates="worktrees")
    project = relationship("Project", back_populates="worktrees")
    sessions = relationship("Session", back_populates="worktree")

class WorktreeSyncHistory(Base):
    """Worktree同期履歴モデル"""
    __tablename__ = "worktree_sync_history"

    id = Column(Integer, primary_key=True, index=True)
    source_worktree_id = Column(String(36), ForeignKey("worktrees.worktree_id"), nullable=False)
    target_worktree_id = Column(String(36), ForeignKey("worktrees.worktree_id"))
    
    # 同期情報
    sync_type = Column(String(20), nullable=False)  # merge, cherry-pick, rebase, pull, push
    sync_direction = Column(String(10), default="push")  # push, pull, bidirectional
    status = Column(String(20), nullable=False)  # success, failed, partial, cancelled
    
    # 実行結果
    files_changed = Column(Integer, default=0)
    lines_added = Column(Integer, default=0)
    lines_deleted = Column(Integer, default=0)
    conflicts_count = Column(Integer, default=0)
    commit_hash = Column(String(40))
    
    # エラー情報
    error_message = Column(Text)
    error_code = Column(String(20))
    
    # 実行情報
    executed_by = Column(Integer, ForeignKey("users.id"))
    execution_time_ms = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CollaborationSession(Base):
    """コラボレーションセッションモデル"""
    __tablename__ = "collaboration_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    host_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 共有設定
    share_mode = Column(String(20), default="read_only")  # read_only, edit, full_control
    max_participants = Column(Integer, default=5)
    requires_approval = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    
    # アクセス制御
    access_token = Column(String(64), unique=True)
    expires_at = Column(DateTime(timezone=True))
    allowed_users = Column(JSONB, default=lambda: [])
    
    # 統計情報
    current_participants = Column(Integer, default=0)
    total_joins = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    session = relationship("Session", back_populates="collaboration_sessions")

class NotificationSetting(Base):
    """通知設定モデル"""
    __tablename__ = "notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(50), nullable=False)
    service_type = Column(String(20), nullable=False)
    is_enabled = Column(Boolean, default=True)
    
    # Web Push設定
    push_subscription = Column(JSONB)
    push_endpoint = Column(String(500))
    
    # Webhook設定
    webhook_url = Column(String(500))
    webhook_secret = Column(String(100))
    webhook_headers = Column(JSONB, default=lambda: {})
    
    # サービス固有設定
    service_config = Column(JSONB, default=lambda: {})
    filter_rules = Column(JSONB, default=lambda: {})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user = relationship("User", back_populates="notification_settings")

class NotificationHistory(Base):
    """通知履歴モデル"""
    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(36), ForeignKey("sessions.session_id"))
    
    notification_type = Column(String(50), nullable=False)
    service_type = Column(String(20), nullable=False)
    
    # 内容
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    payload = Column(JSONB)
    priority = Column(String(10), default="normal")  # low, normal, high, urgent
    
    # 配信情報
    status = Column(String(20), default="pending")  # pending, sent, failed, cancelled
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # 結果情報
    response_code = Column(Integer)
    response_body = Column(Text)
    error_message = Column(Text)
    
    scheduled_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    user = relationship("User", back_populates="notification_history")

class FileOperation(Base):
    """ファイル操作履歴モデル"""
    __tablename__ = "file_operations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("sessions.session_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # 操作情報
    operation_type = Column(String(20), nullable=False)  # create, read, update, delete, rename, move, copy
    file_path = Column(String(1000), nullable=False)
    old_file_path = Column(String(1000))
    
    # ファイル情報
    content_hash = Column(String(64))
    file_size_bytes = Column(BigInteger, default=0)
    mime_type = Column(String(100))
    encoding = Column(String(20), default="utf-8")
    
    # メタデータ
    is_binary = Column(Boolean, default=False)
    language = Column(String(50))
    line_count = Column(Integer)
    
    # 実行情報
    execution_time_ms = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # リレーション
    session = relationship("Session", back_populates="file_operations")
    user = relationship("User", back_populates="file_operations")

class SystemLog(Base):
    """システムログモデル"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(10), nullable=False)  # DEBUG, INFO, WARN, ERROR, CRITICAL
    category = Column(String(50), nullable=False)
    module = Column(String(50), nullable=False)
    
    # 関連情報
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(36), ForeignKey("sessions.session_id"))
    
    # ログ内容
    message = Column(Text, nullable=False)
    details = Column(JSONB)
    
    # 実行情報
    request_id = Column(String(36))
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemSetting(Base):
    """システム設定モデル"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String(100), unique=True, nullable=False)
    setting_value = Column(JSONB, nullable=False)
    data_type = Column(String(20), default="json")  # string, number, boolean, json, array
    
    # メタデータ
    category = Column(String(50), default="general")
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    is_readonly = Column(Boolean, default=False)
    
    # バージョン管理
    version = Column(Integer, default=1)
    previous_value = Column(JSONB)
    
    # 変更情報
    updated_by = Column(Integer, ForeignKey("users.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class WebhookLog(Base):
    """Webhookログモデル（一時的）"""
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(36), ForeignKey("sessions.session_id"))
    webhook_url = Column(String(500), nullable=False)
    event_type = Column(String(50), nullable=False)
    payload = Column(Text)
    response_status = Column(Integer)
    response_body = Column(Text)
    success = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EventLog(Base):
    """イベントログモデル（一時的）"""
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(36), ForeignKey("sessions.session_id"))
    event_type = Column(String(50), nullable=False)
    event_data = Column(Text)
    severity = Column(String(10), default="info")  # info, warning, error, success
    created_at = Column(DateTime(timezone=True), server_default=func.now())