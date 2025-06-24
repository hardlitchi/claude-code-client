-- Claude Code Client データベース初期化SQL

-- デフォルト管理者ユーザーの作成（パスワード: admin123）
-- パスワードハッシュは bcrypt で生成されている
INSERT INTO users (username, email, hashed_password, is_active, is_admin, created_at) 
VALUES (
    'admin', 
    'admin@localhost', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewsY2qJJQhEKpXO.', 
    true, 
    true, 
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- 開発用テストユーザーの作成（パスワード: test123）
INSERT INTO users (username, email, hashed_password, is_active, is_admin, created_at) 
VALUES (
    'testuser', 
    'test@localhost', 
    '$2b$12$9Kz.tLzR1QEakXNKKgE.UOUz6TtxMQJqhN8/LewsY2qJJQhEKpXO.', 
    true, 
    false, 
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- インデックスの作成
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id ON auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level);