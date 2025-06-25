"""
プロジェクト管理・デプロイAPI
プロジェクトテンプレート、ビルド、デプロイ機能を提供
"""

import os
import shutil
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
import asyncio
import yaml
from datetime import datetime

from ..database import get_db
from ..models import User, Session
from ..auth import get_current_user
from ..websocket_manager import manager
from sqlalchemy.orm import Session as DBSession

router = APIRouter(prefix="/api/projects", tags=["projects"])

# プロジェクトテンプレート定義
PROJECT_TEMPLATES = {
    "fastapi": {
        "name": "FastAPI アプリケーション",
        "description": "FastAPI + SQLAlchemy + Alembic の Web API プロジェクト",
        "files": {
            "main.py": '''from fastapi import FastAPI

app = FastAPI(title="My API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
''',
            "requirements.txt": '''fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
pytest==7.4.3
''',
            "Dockerfile": '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
''',
            ".gitignore": '''__pycache__/
*.py[cod]
*$py.class
*.so
.env
.venv/
venv/
ENV/
''',
            "README.md": '''# My FastAPI Project

## セットアップ

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

## API ドキュメント

http://localhost:8000/docs
'''
        },
        "directories": ["tests", "api", "models", "schemas"],
        "build_command": "pip install -r requirements.txt",
        "run_command": "uvicorn main:app --reload",
        "test_command": "pytest"
    },
    "react": {
        "name": "React アプリケーション",
        "description": "React 18 + TypeScript + Vite のフロントエンドプロジェクト",
        "files": {
            "package.json": '''{
  "name": "my-react-app",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "@typescript-eslint/eslint-plugin": "^6.10.0",
    "@typescript-eslint/parser": "^6.10.0",
    "@vitejs/plugin-react": "^4.1.0",
    "eslint": "^8.53.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.4",
    "typescript": "^5.2.2",
    "vite": "^4.4.5"
  }
}''',
            "index.html": '''<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>My React App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>''',
            "src/main.tsx": '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)''',
            "src/App.tsx": '''import { useState } from 'react'
import './App.css'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="App">
      <h1>My React App</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
      </div>
    </div>
  )
}

export default App''',
            "src/App.css": '''.App {
  text-align: center;
  padding: 2rem;
}

.card {
  padding: 2em;
}

button {
  border-radius: 8px;
  border: 1px solid transparent;
  padding: 0.6em 1.2em;
  font-size: 1em;
  font-weight: 500;
  font-family: inherit;
  background-color: #1a1a1a;
  color: white;
  cursor: pointer;
  transition: border-color 0.25s;
}

button:hover {
  border-color: #646cff;
}''',
            "src/index.css": '''body {
  margin: 0;
  display: flex;
  place-items: center;
  min-width: 320px;
  min-height: 100vh;
}''',
            "vite.config.ts": '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})''',
            "tsconfig.json": '''{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}''',
            ".gitignore": '''node_modules/
dist/
.env
.env.local
.env.production
'''
        },
        "directories": ["src/components", "public"],
        "build_command": "npm install",
        "run_command": "npm run dev",
        "test_command": "npm run lint"
    },
    "vue": {
        "name": "Vue.js アプリケーション",
        "description": "Vue 3 + TypeScript + Vite のフロントエンドプロジェクト",
        "files": {
            "package.json": '''{
  "name": "my-vue-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.3.8",
    "vue-router": "^4.2.5"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.4.1",
    "typescript": "~5.2.0",
    "vite": "^4.5.0",
    "vue-tsc": "^1.8.22"
  }
}''',
            "index.html": '''<!DOCTYPE html>
<html lang="ja">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Vue App</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>''',
            "src/main.ts": '''import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')''',
            "src/App.vue": '''<template>
  <div id="app">
    <h1>My Vue App</h1>
    <p>カウント: {{ count }}</p>
    <button @click="count++">クリック</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const count = ref(0)
</script>

<style>
#app {
  text-align: center;
  padding: 2rem;
}

button {
  padding: 0.6em 1.2em;
  font-size: 1em;
  border-radius: 8px;
  border: 1px solid #ccc;
  background-color: #f9f9f9;
  cursor: pointer;
}

button:hover {
  background-color: #e9e9e9;
}
</style>''',
            "vite.config.ts": '''import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
})''',
            "tsconfig.json": '''{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "exclude": ["node_modules"]
}''',
            ".gitignore": '''node_modules/
dist/
.env
.env.local
.env.production
'''
        },
        "directories": ["src/components", "src/views", "public"],
        "build_command": "npm install",
        "run_command": "npm run dev",
        "test_command": "npm run build"
    },
    "express": {
        "name": "Express.js アプリケーション",
        "description": "Express.js + TypeScript の Node.js Web API プロジェクト",
        "files": {
            "package.json": '''{
  "name": "my-express-app",
  "version": "1.0.0",
  "scripts": {
    "dev": "nodemon src/app.ts",
    "build": "tsc",
    "start": "node dist/app.js",
    "test": "jest"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "morgan": "^1.10.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/cors": "^2.8.17",
    "@types/morgan": "^1.9.9",
    "@types/node": "^20.9.0",
    "nodemon": "^3.0.1",
    "ts-node": "^10.9.1",
    "typescript": "^5.2.2",
    "jest": "^29.7.0"
  }
}''',
            "src/app.ts": '''import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';

const app = express();
const port = process.env.PORT || 3000;

// ミドルウェア
app.use(helmet());
app.use(cors());
app.use(morgan('combined'));
app.use(express.json());

// ルート
app.get('/', (req, res) => {
  res.json({ message: 'Hello World!' });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

// サーバー起動
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});

export default app;''',
            "tsconfig.json": '''{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}''',
            "nodemon.json": '''{
  "watch": ["src"],
  "ext": "ts",
  "exec": "ts-node src/app.ts"
}''',
            ".gitignore": '''node_modules/
dist/
.env
.env.local
npm-debug.log*
'''
        },
        "directories": ["src/routes", "src/middleware", "src/models"],
        "build_command": "npm install",
        "run_command": "npm run dev",
        "test_command": "npm test"
    }
}

class ProjectCreateRequest(BaseModel):
    template: str
    name: str
    description: Optional[str] = None

class BuildRequest(BaseModel):
    command: Optional[str] = None
    environment: Optional[Dict[str, str]] = None

class DeployRequest(BaseModel):
    target: str  # "local", "docker", "vercel", "netlify"
    environment: Optional[Dict[str, str]] = None
    config: Optional[Dict[str, Any]] = None

@router.get("/templates")
async def get_project_templates():
    """利用可能なプロジェクトテンプレート一覧を取得"""
    return {
        "templates": {
            template_id: {
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
                "build_command": template["build_command"],
                "run_command": template["run_command"],
                "test_command": template["test_command"]
            }
            for template_id, template in PROJECT_TEMPLATES.items()
        }
    }

@router.post("/create/{session_id}")
async def create_project_from_template(
    session_id: str,
    request: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """テンプレートからプロジェクトを作成"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # テンプレートの存在確認
    if request.template not in PROJECT_TEMPLATES:
        raise HTTPException(status_code=404, detail="指定されたテンプレートが見つかりません")
    
    template = PROJECT_TEMPLATES[request.template]
    base_path = Path(session.working_directory)
    project_path = base_path / request.name
    
    # プロジェクトディレクトリが既に存在する場合はエラー
    if project_path.exists():
        raise HTTPException(status_code=409, detail="同名のプロジェクトが既に存在します")
    
    try:
        # プロジェクトディレクトリを作成
        project_path.mkdir(parents=True, exist_ok=True)
        
        # ディレクトリ構造を作成
        for directory in template.get("directories", []):
            (project_path / directory).mkdir(parents=True, exist_ok=True)
        
        # ファイルを作成
        for file_path, content in template["files"].items():
            target_file = project_path / file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # テンプレート変数の置換
            content = content.replace("{{PROJECT_NAME}}", request.name)
            if request.description:
                content = content.replace("{{PROJECT_DESCRIPTION}}", request.description)
            
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # プロジェクト設定ファイルを作成
        project_config = {
            "name": request.name,
            "description": request.description,
            "template": request.template,
            "created_at": datetime.now().isoformat(),
            "created_by": current_user.username,
            "build_command": template["build_command"],
            "run_command": template["run_command"],
            "test_command": template["test_command"]
        }
        
        with open(project_path / ".claudeproject", 'w', encoding='utf-8') as f:
            json.dump(project_config, f, indent=2, ensure_ascii=False)
        
        # WebSocket経由で通知
        message = {
            "type": "project_created",
            "project_name": request.name,
            "template": request.template,
            "path": str(project_path.relative_to(base_path)),
            "user": current_user.username,
            "timestamp": datetime.now().isoformat()
        }
        await manager.send_to_session(session_id, json.dumps(message))
        
        return {
            "success": True,
            "message": f"プロジェクト '{request.name}' が正常に作成されました",
            "project_path": str(project_path.relative_to(base_path)),
            "template": request.template,
            "config": project_config
        }
        
    except Exception as e:
        # エラー時はクリーンアップ
        if project_path.exists():
            shutil.rmtree(project_path, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"プロジェクト作成エラー: {str(e)}")

@router.post("/build/{session_id}")
async def build_project(
    session_id: str,
    request: BuildRequest,
    background_tasks: BackgroundTasks,
    project_path: str = "",
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """プロジェクトをビルド"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    base_path = Path(session.working_directory)
    target_path = base_path / project_path if project_path else base_path
    
    # パス検証
    try:
        target_path = target_path.resolve()
        if not str(target_path).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="アクセス権限がありません")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="無効なパスです")
    
    # プロジェクト設定を読み込み
    config_file = target_path / ".claudeproject"
    build_command = request.command
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                project_config = json.load(f)
                if not build_command:
                    build_command = project_config.get("build_command")
        except Exception:
            pass
    
    if not build_command:
        raise HTTPException(status_code=400, detail="ビルドコマンドが指定されていません")
    
    # バックグラウンドでビルド実行
    background_tasks.add_task(
        _execute_build,
        session_id,
        str(target_path),
        build_command,
        request.environment or {},
        current_user.username
    )
    
    return {
        "success": True,
        "message": "ビルドを開始しました",
        "command": build_command,
        "project_path": str(target_path.relative_to(base_path))
    }

async def _execute_build(
    session_id: str,
    project_path: str,
    command: str,
    environment: Dict[str, str],
    username: str
):
    """ビルド実行（バックグラウンドタスク）"""
    try:
        # WebSocket経由でビルド開始を通知
        start_message = {
            "type": "build_started",
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "user": username
        }
        await manager.send_to_session(session_id, json.dumps(start_message))
        
        # 環境変数設定
        env = os.environ.copy()
        env.update(environment)
        
        # ビルド実行
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=project_path,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            text=True
        )
        
        # リアルタイム出力
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            output_message = {
                "type": "build_output",
                "output": line.rstrip(),
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_to_session(session_id, json.dumps(output_message))
        
        # プロセス終了待機
        return_code = await process.wait()
        
        # ビルド完了通知
        complete_message = {
            "type": "build_completed",
            "success": return_code == 0,
            "return_code": return_code,
            "timestamp": datetime.now().isoformat(),
            "user": username
        }
        await manager.send_to_session(session_id, json.dumps(complete_message))
        
    except Exception as e:
        # ビルドエラー通知
        error_message = {
            "type": "build_error",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "user": username
        }
        await manager.send_to_session(session_id, json.dumps(error_message))

@router.post("/deploy/{session_id}")
async def deploy_project(
    session_id: str,
    request: DeployRequest,
    background_tasks: BackgroundTasks,
    project_path: str = "",
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """プロジェクトをデプロイ"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    base_path = Path(session.working_directory)
    target_path = base_path / project_path if project_path else base_path
    
    # パス検証
    try:
        target_path = target_path.resolve()
        if not str(target_path).startswith(str(base_path.resolve())):
            raise HTTPException(status_code=403, detail="アクセス権限がありません")
    except (OSError, ValueError):
        raise HTTPException(status_code=400, detail="無効なパスです")
    
    # デプロイターゲット別の処理
    if request.target == "docker":
        # Dockerビルド・実行
        background_tasks.add_task(
            _execute_docker_deploy,
            session_id,
            str(target_path),
            request.environment or {},
            request.config or {},
            current_user.username
        )
    elif request.target == "local":
        # ローカル実行
        background_tasks.add_task(
            _execute_local_deploy,
            session_id,
            str(target_path),
            request.environment or {},
            current_user.username
        )
    else:
        raise HTTPException(status_code=400, detail=f"サポートされていないデプロイターゲット: {request.target}")
    
    return {
        "success": True,
        "message": f"{request.target} デプロイを開始しました",
        "target": request.target,
        "project_path": str(target_path.relative_to(base_path))
    }

async def _execute_docker_deploy(
    session_id: str,
    project_path: str,
    environment: Dict[str, str],
    config: Dict[str, Any],
    username: str
):
    """Dockerデプロイ実行"""
    try:
        # デプロイ開始通知
        start_message = {
            "type": "deploy_started",
            "target": "docker",
            "timestamp": datetime.now().isoformat(),
            "user": username
        }
        await manager.send_to_session(session_id, json.dumps(start_message))
        
        project_name = Path(project_path).name.lower()
        
        # Dockerイメージビルド
        build_command = f"docker build -t {project_name} ."
        process = await asyncio.create_subprocess_shell(
            build_command,
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            text=True
        )
        
        # ビルド出力をリアルタイム配信
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            output_message = {
                "type": "deploy_output",
                "output": line.rstrip(),
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_to_session(session_id, json.dumps(output_message))
        
        build_return_code = await process.wait()
        
        if build_return_code == 0:
            # コンテナ実行
            port = config.get("port", "8000")
            container_name = f"{project_name}-container"
            
            # 既存のコンテナを停止・削除
            await asyncio.create_subprocess_shell(f"docker stop {container_name}", cwd=project_path)
            await asyncio.create_subprocess_shell(f"docker rm {container_name}", cwd=project_path)
            
            # 新しいコンテナを実行
            run_command = f"docker run -d --name {container_name} -p {port}:8000 {project_name}"
            run_process = await asyncio.create_subprocess_shell(
                run_command,
                cwd=project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )
            
            await run_process.wait()
            
            # デプロイ完了通知
            complete_message = {
                "type": "deploy_completed",
                "success": True,
                "target": "docker",
                "url": f"http://localhost:{port}",
                "container_name": container_name,
                "timestamp": datetime.now().isoformat(),
                "user": username
            }
        else:
            complete_message = {
                "type": "deploy_completed",
                "success": False,
                "target": "docker",
                "error": "Dockerビルドに失敗しました",
                "timestamp": datetime.now().isoformat(),
                "user": username
            }
        
        await manager.send_to_session(session_id, json.dumps(complete_message))
        
    except Exception as e:
        error_message = {
            "type": "deploy_error",
            "target": "docker",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "user": username
        }
        await manager.send_to_session(session_id, json.dumps(error_message))

async def _execute_local_deploy(
    session_id: str,
    project_path: str,
    environment: Dict[str, str],
    username: str
):
    """ローカルデプロイ実行"""
    try:
        # プロジェクト設定を読み込み
        config_file = Path(project_path) / ".claudeproject"
        run_command = "python main.py"  # デフォルト
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    project_config = json.load(f)
                    run_command = project_config.get("run_command", run_command)
            except Exception:
                pass
        
        # デプロイ開始通知
        start_message = {
            "type": "deploy_started",
            "target": "local",
            "command": run_command,
            "timestamp": datetime.now().isoformat(),
            "user": username
        }
        await manager.send_to_session(session_id, json.dumps(start_message))
        
        # 環境変数設定
        env = os.environ.copy()
        env.update(environment)
        
        # アプリケーション実行
        process = await asyncio.create_subprocess_shell(
            run_command,
            cwd=project_path,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            text=True
        )
        
        # 出力をリアルタイム配信
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            
            output_message = {
                "type": "deploy_output",
                "output": line.rstrip(),
                "timestamp": datetime.now().isoformat()
            }
            await manager.send_to_session(session_id, json.dumps(output_message))
        
        return_code = await process.wait()
        
        # デプロイ完了通知
        complete_message = {
            "type": "deploy_completed",
            "success": return_code == 0,
            "target": "local",
            "return_code": return_code,
            "timestamp": datetime.now().isoformat(),
            "user": username
        }
        await manager.send_to_session(session_id, json.dumps(complete_message))
        
    except Exception as e:
        error_message = {
            "type": "deploy_error",
            "target": "local",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "user": username
        }
        await manager.send_to_session(session_id, json.dumps(error_message))

@router.get("/status/{session_id}")
async def get_project_status(
    session_id: str,
    project_path: str = "",
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """プロジェクトの状態を取得"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    base_path = Path(session.working_directory)
    target_path = base_path / project_path if project_path else base_path
    
    # プロジェクト設定ファイルの確認
    config_file = target_path / ".claudeproject"
    
    if not config_file.exists():
        return {
            "is_project": False,
            "message": "プロジェクト設定ファイルが見つかりません"
        }
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            project_config = json.load(f)
        
        # Dockerコンテナ状態確認
        container_name = f"{project_config['name'].lower()}-container"
        docker_status = await _check_docker_status(container_name)
        
        return {
            "is_project": True,
            "config": project_config,
            "docker_status": docker_status,
            "project_path": str(target_path.relative_to(base_path))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プロジェクト状態取得エラー: {str(e)}")

async def _check_docker_status(container_name: str) -> Dict[str, Any]:
    """Dockerコンテナの状態を確認"""
    try:
        # コンテナの存在確認
        process = await asyncio.create_subprocess_shell(
            f"docker ps -a --filter name={container_name} --format '{{{{.Status}}}}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            text=True
        )
        
        stdout, _ = await process.communicate()
        
        if stdout.strip():
            status = stdout.strip()
            is_running = "Up" in status
            
            return {
                "exists": True,
                "running": is_running,
                "status": status,
                "container_name": container_name
            }
        else:
            return {
                "exists": False,
                "running": False,
                "container_name": container_name
            }
            
    except Exception:
        return {
            "exists": False,
            "running": False,
            "error": "Docker状態確認に失敗しました",
            "container_name": container_name
        }