# Claude Code Client

Webブラウザから Claude Code を操作可能にするアプリケーションサーバー

## 概要

Claude Code Client は、Claude Code をWebブラウザから操作できるようにするアプリケーションです。いつでもどこでもClaude Codeの開発セッションにアクセスできる環境を提供します。

## 機能

### フェーズ1（現在実装済み）
- ✅ 基本Web UI構築
- ✅ 単一ユーザー向けTerminal機能（UI）
- ✅ Claude Code SDK基本統合（準備）
- ✅ 簡単な認証機能

### 将来の機能
- マルチユーザー対応
- Git Worktree管理
- 通知・Webhook連携
- リアルタイムTerminal操作
- Claude Code セッション永続化

## 技術スタック

### バックエンド
- **FastAPI** - Webフレームワーク
- **PostgreSQL** - データベース
- **SQLAlchemy** - ORM
- **JWT** - 認証
- **WebSocket** - リアルタイム通信（予定）

### フロントエンド
- **Vue.js 3** - フロントエンドフレームワーク
- **TypeScript** - 型安全性
- **Pinia** - 状態管理
- **Tailwind CSS** - スタイリング
- **xterm.js** - ターミナルエミュレーター（予定）

### インフラ
- **Docker & Docker Compose** - コンテナ化
- **Nginx** - リバースプロキシ（予定）

## 開発環境セットアップ

### 前提条件
- Docker & Docker Compose
- Node.js 18+ (フロントエンド開発用)
- Python 3.11+ (バックエンド開発用)

### 1. リポジトリのクローン
```bash
git clone https://github.com/hardlitchi/claude-code-client.git
cd claude-code-client
```

### 2. 環境変数の設定
```bash
cp .env.example .env
# .env ファイルを編集して適切な値を設定
```

### 3. Docker Composeでの起動
```bash
docker-compose up -d
```

これにより以下のサービスが起動します：
- バックエンドAPI: http://localhost:8000
- フロントエンド: http://localhost:3000
- PostgreSQL: localhost:5432

### 4. 個別での開発

#### バックエンド開発
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### フロントエンド開発
```bash
cd frontend
npm install
npm run dev
```

## API ドキュメント

バックエンドが起動している状態で以下のURLにアクセス：
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## デフォルトユーザー

開発用のデフォルトユーザーが作成されます：

**管理者**
- ユーザー名: `admin`
- パスワード: `admin123`
- メール: `admin@example.com`

**一般ユーザー**
- ユーザー名: `testuser`
- パスワード: `test123`
- メール: `test@example.com`

## プロジェクト構造

```
claude-code-client/
├── backend/                 # FastAPI バックエンド
│   ├── app/
│   │   ├── routers/        # API ルーター
│   │   ├── models.py       # データベースモデル
│   │   ├── schemas.py      # Pydantic スキーマ
│   │   ├── auth.py         # 認証機能
│   │   ├── database.py     # データベース設定
│   │   └── main.py         # アプリケーションエントリーポイント
│   ├── requirements.txt    # Python依存関係
│   └── Dockerfile         # バックエンド用Dockerファイル
├── frontend/               # Vue.js フロントエンド
│   ├── src/
│   │   ├── views/         # ページコンポーネント
│   │   ├── stores/        # Pinia ストア
│   │   ├── router/        # Vue Router設定
│   │   └── main.ts        # アプリケーションエントリーポイント
│   ├── package.json       # Node.js依存関係
│   └── Dockerfile.dev     # フロントエンド開発用Dockerファイル
├── prototypes/             # UI プロトタイプ
├── docker-compose.yml      # Docker Compose設定
└── README.md              # このファイル
```

## 開発の進め方

### ブランチ戦略
- `main`: プロダクション環境
- `phase1-development`: フェーズ1開発ブランチ
- `feature/*`: 機能別ブランチ

### コミット規約
日本語でのコミットメッセージを推奨：
```
機能: 新しい機能を追加

- 具体的な変更内容1
- 具体的な変更内容2

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## テスト

### バックエンドテスト
```bash
cd backend
pytest
```

### フロントエンドテスト
```bash
cd frontend
npm run test
```

### 型チェック
```bash
cd frontend
npm run type-check
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

プルリクエストや課題報告をお待ちしています。貢献する前にプロジェクトの方針を確認してください。

## サポート

質問や問題がある場合は、GitHubのIssuesで報告してください。
