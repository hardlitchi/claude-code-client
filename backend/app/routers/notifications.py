"""
通知・WebhookシステムAPI
プッシュ通知、外部Webhook連携、イベント追跡機能を提供
"""

import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer

from ..database import get_db, Base, engine
from ..models import User, Session
from ..auth import get_current_user
from ..websocket_manager import manager

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# 通知設定モデル
class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(String, nullable=True)
    type = Column(String)  # "browser", "webhook", "email"
    config = Column(Text)  # JSON形式の設定
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# Webhookログモデル
class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(String, nullable=True)
    webhook_url = Column(String)
    event_type = Column(String)
    payload = Column(Text)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

# イベントログモデル
class EventLog(Base):
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(String, nullable=True)
    event_type = Column(String)
    event_data = Column(Text)
    severity = Column(String, default="info")  # "info", "warning", "error", "success"
    created_at = Column(DateTime, default=datetime.now)

# テーブル作成
Base.metadata.create_all(bind=engine)

# リクエストモデル
class NotificationSettingRequest(BaseModel):
    type: str  # "browser", "webhook", "slack", "discord", "line"
    config: Dict[str, Any]
    enabled: bool = True
    session_id: Optional[str] = None

class WebhookRequest(BaseModel):
    url: HttpUrl
    events: List[str]
    headers: Optional[Dict[str, str]] = None
    secret: Optional[str] = None

class TestNotificationRequest(BaseModel):
    type: str
    config: Dict[str, Any]
    message: str = "テスト通知"

# 通知サービスクラス
class NotificationService:
    """統合通知サービス"""
    
    @staticmethod
    async def send_browser_notification(
        session_id: str,
        title: str,
        message: str,
        icon: str = "info",
        actions: List[Dict[str, str]] = None
    ):
        """ブラウザプッシュ通知を送信"""
        notification_data = {
            "type": "browser_notification",
            "title": title,
            "message": message,
            "icon": icon,
            "actions": actions or [],
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.send_to_session(session_id, json.dumps(notification_data))
    
    @staticmethod
    async def send_webhook(
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str] = None,
        secret: str = None
    ) -> Dict[str, Any]:
        """Webhook通知を送信"""
        try:
            # ペイロードの準備
            webhook_payload = {
                "timestamp": datetime.now().isoformat(),
                "source": "claude-code-client",
                **payload
            }
            
            # ヘッダーの準備
            request_headers = {
                "Content-Type": "application/json",
                "User-Agent": "Claude-Code-Client/1.0"
            }
            
            if headers:
                request_headers.update(headers)
            
            if secret:
                # シンプルなシークレットヘッダー追加
                request_headers["X-Claude-Secret"] = secret
            
            # HTTP POSTリクエスト送信
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(
                    str(url),
                    json=webhook_payload,
                    headers=request_headers
                ) as response:
                    response_text = await response.text()
                    
                    return {
                        "success": 200 <= response.status < 300,
                        "status_code": response.status,
                        "response_body": response_text,
                        "headers": dict(response.headers)
                    }
                    
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "タイムアウト",
                "status_code": 408
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": 500
            }
    
    @staticmethod
    async def send_slack_notification(
        webhook_url: str,
        text: str,
        channel: str = None,
        username: str = "Claude Code Client",
        icon_emoji: str = ":robot_face:",
        attachments: List[Dict[str, Any]] = None
    ):
        """Slack通知を送信"""
        payload = {
            "text": text,
            "username": username,
            "icon_emoji": icon_emoji
        }
        
        if channel:
            payload["channel"] = channel
        
        if attachments:
            payload["attachments"] = attachments
        
        return await NotificationService.send_webhook(webhook_url, payload)
    
    @staticmethod
    async def send_discord_notification(
        webhook_url: str,
        content: str,
        username: str = "Claude Code Client",
        avatar_url: str = None,
        embeds: List[Dict[str, Any]] = None
    ):
        """Discord通知を送信"""
        payload = {
            "content": content,
            "username": username
        }
        
        if avatar_url:
            payload["avatar_url"] = avatar_url
        
        if embeds:
            payload["embeds"] = embeds
        
        return await NotificationService.send_webhook(webhook_url, payload)

# イベント処理クラス
class EventProcessor:
    """イベント処理とログ記録"""
    
    @staticmethod
    async def log_event(
        db: DBSession,
        user_id: int,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str = "info"
    ):
        """イベントをログに記録"""
        event_log = EventLog(
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            event_data=json.dumps(event_data, ensure_ascii=False),
            severity=severity
        )
        
        db.add(event_log)
        db.commit()
        
        return event_log
    
    @staticmethod
    async def process_event(
        db: DBSession,
        user_id: int,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        severity: str = "info"
    ):
        """イベント処理（ログ記録 + 通知送信）"""
        # イベントログ記録
        await EventProcessor.log_event(db, user_id, session_id, event_type, event_data, severity)
        
        # 該当ユーザーの通知設定を取得
        settings = db.query(NotificationSetting).filter(
            NotificationSetting.user_id == user_id,
            NotificationSetting.enabled == True
        ).all()
        
        # 各通知設定に従って通知を送信
        for setting in settings:
            if setting.session_id and setting.session_id != session_id:
                continue
                
            try:
                config = json.loads(setting.config)
                await EventProcessor._send_notification(
                    setting.type, config, event_type, event_data, session_id
                )
            except Exception as e:
                print(f"通知送信エラー: {e}")
    
    @staticmethod
    async def _send_notification(
        notification_type: str,
        config: Dict[str, Any],
        event_type: str,
        event_data: Dict[str, Any],
        session_id: str
    ):
        """個別通知送信"""
        if notification_type == "browser":
            await NotificationService.send_browser_notification(
                session_id,
                title=f"Claude Code: {event_type}",
                message=event_data.get("message", "新しいイベントが発生しました"),
                icon=event_data.get("severity", "info")
            )
        
        elif notification_type == "slack":
            if "webhook_url" in config:
                await NotificationService.send_slack_notification(
                    webhook_url=config["webhook_url"],
                    text=f"🤖 *{event_type}*\n{event_data.get('message', '')}",
                    channel=config.get("channel"),
                    attachments=[{
                        "color": {"success": "good", "error": "danger", "warning": "warning"}.get(
                            event_data.get("severity", "info"), "#36a64f"
                        ),
                        "fields": [
                            {"title": "セッション", "value": session_id, "short": True},
                            {"title": "時刻", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "short": True}
                        ]
                    }]
                )
        
        elif notification_type == "discord":
            if "webhook_url" in config:
                embed_color = {
                    "success": 0x00ff00,
                    "error": 0xff0000,
                    "warning": 0xffff00,
                    "info": 0x0099ff
                }.get(event_data.get("severity", "info"), 0x0099ff)
                
                await NotificationService.send_discord_notification(
                    webhook_url=config["webhook_url"],
                    content=f"**{event_type}**",
                    embeds=[{
                        "title": event_type,
                        "description": event_data.get("message", ""),
                        "color": embed_color,
                        "fields": [
                            {"name": "セッション", "value": session_id, "inline": True},
                            {"name": "時刻", "value": datetime.now().isoformat(), "inline": True}
                        ],
                        "footer": {"text": "Claude Code Client"}
                    }]
                )

# API エンドポイント
@router.get("/settings")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """通知設定一覧を取得"""
    settings = db.query(NotificationSetting).filter(
        NotificationSetting.user_id == current_user.id
    ).all()
    
    return {
        "settings": [
            {
                "id": setting.id,
                "type": setting.type,
                "config": json.loads(setting.config),
                "enabled": setting.enabled,
                "session_id": setting.session_id,
                "created_at": setting.created_at.isoformat(),
                "updated_at": setting.updated_at.isoformat()
            }
            for setting in settings
        ]
    }

@router.post("/settings")
async def create_notification_setting(
    request: NotificationSettingRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """新しい通知設定を作成"""
    setting = NotificationSetting(
        user_id=current_user.id,
        session_id=request.session_id,
        type=request.type,
        config=json.dumps(request.config, ensure_ascii=False),
        enabled=request.enabled
    )
    
    db.add(setting)
    db.commit()
    db.refresh(setting)
    
    return {
        "id": setting.id,
        "message": "通知設定が作成されました"
    }

@router.put("/settings/{setting_id}")
async def update_notification_setting(
    setting_id: int,
    request: NotificationSettingRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """通知設定を更新"""
    setting = db.query(NotificationSetting).filter(
        NotificationSetting.id == setting_id,
        NotificationSetting.user_id == current_user.id
    ).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail="通知設定が見つかりません")
    
    setting.type = request.type
    setting.config = json.dumps(request.config, ensure_ascii=False)
    setting.enabled = request.enabled
    setting.session_id = request.session_id
    setting.updated_at = datetime.now()
    
    db.commit()
    
    return {"message": "通知設定が更新されました"}

@router.delete("/settings/{setting_id}")
async def delete_notification_setting(
    setting_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """通知設定を削除"""
    setting = db.query(NotificationSetting).filter(
        NotificationSetting.id == setting_id,
        NotificationSetting.user_id == current_user.id
    ).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail="通知設定が見つかりません")
    
    db.delete(setting)
    db.commit()
    
    return {"message": "通知設定が削除されました"}

@router.post("/test")
async def test_notification(
    request: TestNotificationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """通知テスト送信"""
    # バックグラウンドでテスト通知を送信
    background_tasks.add_task(
        _send_test_notification,
        request.type,
        request.config,
        request.message,
        current_user.username
    )
    
    return {"message": "テスト通知を送信しました"}

async def _send_test_notification(
    notification_type: str,
    config: Dict[str, Any],
    message: str,
    username: str
):
    """テスト通知送信（バックグラウンドタスク）"""
    try:
        if notification_type == "slack":
            await NotificationService.send_slack_notification(
                webhook_url=config["webhook_url"],
                text=f"🧪 *テスト通知*\n{message}\n\n送信者: {username}",
                channel=config.get("channel")
            )
        elif notification_type == "discord":
            await NotificationService.send_discord_notification(
                webhook_url=config["webhook_url"],
                content=f"🧪 **テスト通知**\n{message}\n\n送信者: {username}"
            )
        elif notification_type == "webhook":
            await NotificationService.send_webhook(
                url=config["url"],
                payload={
                    "event_type": "test_notification",
                    "message": message,
                    "user": username
                },
                headers=config.get("headers"),
                secret=config.get("secret")
            )
    except Exception as e:
        print(f"テスト通知送信エラー: {e}")

@router.get("/events")
async def get_event_logs(
    session_id: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """イベントログを取得"""
    query = db.query(EventLog).filter(EventLog.user_id == current_user.id)
    
    if session_id:
        query = query.filter(EventLog.session_id == session_id)
    
    if event_type:
        query = query.filter(EventLog.event_type == event_type)
    
    if severity:
        query = query.filter(EventLog.severity == severity)
    
    events = query.order_by(EventLog.created_at.desc()).offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "events": [
            {
                "id": event.id,
                "session_id": event.session_id,
                "event_type": event.event_type,
                "event_data": json.loads(event.event_data),
                "severity": event.severity,
                "created_at": event.created_at.isoformat()
            }
            for event in events
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.post("/events/{session_id}")
async def trigger_event(
    session_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
    severity: str = "info"
):
    """イベントを手動でトリガー"""
    # セッションの存在確認と権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    
    # バックグラウンドでイベント処理
    background_tasks.add_task(
        EventProcessor.process_event,
        db,
        current_user.id,
        session_id,
        event_type,
        event_data,
        severity
    )
    
    return {"message": "イベントが処理されました"}

@router.get("/webhook-logs")
async def get_webhook_logs(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """Webhookログを取得"""
    logs = db.query(WebhookLog).filter(
        WebhookLog.user_id == current_user.id
    ).order_by(WebhookLog.created_at.desc()).offset(offset).limit(limit).all()
    
    total = db.query(WebhookLog).filter(WebhookLog.user_id == current_user.id).count()
    
    return {
        "logs": [
            {
                "id": log.id,
                "session_id": log.session_id,
                "webhook_url": log.webhook_url,
                "event_type": log.event_type,
                "payload": json.loads(log.payload),
                "response_status": log.response_status,
                "response_body": log.response_body,
                "success": log.success,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }