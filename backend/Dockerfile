FROM python:3.11-slim

WORKDIR /app

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

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