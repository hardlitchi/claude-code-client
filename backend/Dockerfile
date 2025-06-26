FROM python:3.11-slim

WORKDIR /app

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    ca-certificates \
    gnupg \
    lsb-release \
    git \
    && rm -rf /var/lib/apt/lists/*

# Node.js（LTS版）のインストール
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Claude Code CLIのインストール
RUN npm install -g @anthropic-ai/claude-code

# Claude Code CLI用のディレクトリ作成と権限設定
RUN mkdir -p /app/claude-sessions \
    && mkdir -p /root/.config/claude-code \
    && chmod -R 755 /app/claude-sessions

# Claude Code CLIの動作確認
RUN which claude && claude --version || echo "Claude Code CLI installed"

# Claude Code CLIの初期設定用環境変数
ENV CLAUDE_CODE_CONFIG_DIR=/root/.config/claude-code
ENV CLAUDE_CODE_SESSIONS_DIR=/app/claude-sessions
ENV PATH="/usr/local/bin:$PATH"

# Claude認証のための環境変数（実行時に設定）
ENV ANTHROPIC_API_KEY=""

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# wait-for-postgresスクリプトをコピー
COPY wait-for-postgres.py .
RUN chmod +x wait-for-postgres.py

# アプリケーションコードのコピー
COPY . .

# ポート公開
EXPOSE 8000

# PostgreSQL待機 + アプリケーション実行
CMD ["sh", "-c", "python wait-for-postgres.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]