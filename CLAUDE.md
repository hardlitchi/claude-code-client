# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 言語設定

**重要**: このプロジェクトでは日本語を使用してください。
- すべてのやり取り、コメント、ドキュメント出力は日本語で行う
- コード内のコメントも日本語で記述する
- エラーメッセージやログ出力も可能な限り日本語で提供する

## Project Overview

This is **claude-code-client** (in development) - a web application server that enables browser-based interaction with Claude Code. It allows users to operate Claude Code from anywhere via web browser.

### Purpose
The application provides remote access to Claude Code development sessions, enabling:
- Browser-based terminal operations
- Chat-based interaction with Claude for development tasks  
- Session persistence across connections
- Multi-session management
- Deployment capabilities for applications under development
- Push notifications for Claude work updates
- Webhook integration with LINE, Slack, Discord, etc.

## Project Status

This is an **early-stage project** with only basic scaffolding in place:
- Contains only README.md and .gitignore files
- No source code, dependencies, or build system yet implemented
- Python-based project (indicated by Python .gitignore patterns)
- Uses git for version control

## Development Commands

**Note**: No build, test, or lint commands are available yet as the project structure is not implemented.

Common commands to expect once development progresses:
- `python -m pip install -r requirements.txt` - Install dependencies
- `python app.py` or similar - Run the application server
- `pytest` - テスト実行（テストフレームワーク追加後）
- `ruff check` - Lint code (ruff cache directory is in .gitignore)

## Architecture Notes

The application will serve as a bridge between:
1. **Browser clients** - Web interface for user interaction
2. **Claude Code sessions** - Backend integration with Claude Code CLI
3. **Terminal access** - Web-based terminal functionality  
4. **Notification system** - Push notifications and webhook integrations

Key architectural components expected:
- Web server framework (Flask/FastAPI likely)
- WebSocket connections for real-time terminal/chat
- Session management and persistence
- Authentication system
- Integration with Claude Code CLI tools
- Deployment pipeline management

## 開発環境

- Python プロジェクト（ruff、各種パッケージマネージャー対応）
- Git リポジトリ（リモートはまだ未設定）
- IDE 統合準備済み（.vscode、.idea パターンを gitignore に含む）
- Abstra フレームワーク統合予定（.abstra/ ディレクトリを無視）