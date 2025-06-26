# Claude Code CLI セットアップ手順

## 前提条件

Claude Code CLIをバックエンドコンテナで使用するには、以下が必要です：

1. **Anthropic API キー**: [Anthropic Console](https://console.anthropic.com/) でアカウント作成
2. **API クレジット**: 十分なクレジット残高（最低 $5 程度推奨）
3. **API キーの権限**: Claude モデルへのアクセス権限

## セットアップ手順

### 1. 環境変数ファイルの作成

プロジェクトルートに `.env` ファイルを作成し、以下を追加：

```bash
# .env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 2. コンテナの再ビルド

Claude Code CLIをインストールするため、バックエンドコンテナを再ビルドします：

```bash
docker-compose down
docker-compose build --no-cache backend
docker-compose up -d
```

### 3. Claude Code CLIの初期設定確認

バックエンドコンテナ内でClaude Code CLIが正しくインストールされているか確認：

```bash
docker-compose exec backend claude --version
```

### 4. API キーの設定確認

環境変数が正しく設定されているか確認：

```bash
docker-compose exec backend printenv | grep ANTHROPIC
```

## ファイル保存場所

- **セッションファイル**: `/app/claude-sessions/{session_id}/`
- **Claude設定**: `/app/.config/claude-code/`
- **ユーザーファイル**: `/home/{username}/{session-name}/`

## トラブルシューティング

### Claude Code CLIが見つからない場合

```bash
# コンテナ内で確認
docker-compose exec backend which claude
docker-compose exec backend npm list -g @anthropic-ai/claude-code
```

### API キーエラーの場合

1. `.env` ファイルに正しいAPI キーが設定されているか確認
2. [Anthropic Console](https://console.anthropic.com/) でAPI キーが有効か確認
3. クレジット残高が十分にあるか確認
4. コンテナを再起動： `docker-compose restart backend`

### クレジット残高エラーの場合

```
Claude API クレジット残高が不足しています
```

1. [Anthropic Console](https://console.anthropic.com/) にログイン
2. Billing セクションでクレジットを追加
3. 通常は $5-10 程度で十分な開発・テストが可能

### 権限エラーの場合

```bash
# コンテナ内で権限確認
docker-compose exec backend ls -la /app/claude-sessions
docker-compose exec backend ls -la /app/.config/claude-code
```

## 使用方法

1. ブラウザで http://localhost:3001 にアクセス
2. ログイン後、新しいセッションを作成
3. Workspace画面でClaude Code チャットを開始
4. ターミナルとClaude Codeの統合開発環境を利用

## 注意事項

- Claude Code CLIの使用には有効なAnthropicアカウントとAPIキーが必要です
- ファイルはコンテナ内のボリュームに永続化されます
- セッション削除時もファイルは保持されます（手動削除が必要）