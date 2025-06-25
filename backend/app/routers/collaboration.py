"""
マルチユーザー・コラボレーションAPI
共有セッション、権限管理、アクティビティ追跡機能を提供
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum

from ..database import get_db, Base, engine
from ..models import User, Session
from ..auth import get_current_user
from ..websocket_manager import manager

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])

# 権限レベル列挙型
class PermissionLevel(enum.Enum):
    VIEWER = "viewer"      # 読み取り専用
    COLLABORATOR = "collaborator"  # 編集可能
    ADMIN = "admin"        # 管理者

# セッション共有モデル
class SessionShare(Base):
    __tablename__ = "session_shares"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    shared_with_id = Column(Integer, ForeignKey("users.id"))
    permission_level = Column(Enum(PermissionLevel))
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # リレーション
    owner = relationship("User", foreign_keys=[owner_id])
    shared_with = relationship("User", foreign_keys=[shared_with_id])

# ユーザーアクティビティモデル
class UserActivity(Base):
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    activity_type = Column(String)  # "file_edit", "cursor_move", "selection", "chat"
    activity_data = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    
    # リレーション
    user = relationship("User")

# セッション参加者モデル
class SessionParticipant(Base):
    __tablename__ = "session_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    joined_at = Column(DateTime, default=datetime.now)
    last_seen = Column(DateTime, default=datetime.now)
    is_active = Column(Boolean, default=True)
    cursor_position = Column(Text, nullable=True)  # JSON形式
    
    # リレーション
    user = relationship("User")

# テーブル作成
Base.metadata.create_all(bind=engine)

# リクエストモデル
class ShareSessionRequest(BaseModel):
    username: str
    permission_level: PermissionLevel
    expires_hours: Optional[int] = None

class UpdatePermissionRequest(BaseModel):
    permission_level: PermissionLevel

class ActivityRequest(BaseModel):
    activity_type: str
    activity_data: Dict[str, Any]

class CursorPosition(BaseModel):
    file_path: Optional[str] = None
    line: int
    column: int
    selection: Optional[Dict[str, Any]] = None

# コラボレーション管理クラス
class CollaborationManager:
    """コラボレーション機能の管理"""
    
    @staticmethod
    async def check_session_permission(
        db: DBSession,
        session_id: str,
        user_id: int,
        required_permission: PermissionLevel = PermissionLevel.VIEWER
    ) -> bool:
        """セッションへのアクセス権限をチェック"""
        # セッション所有者チェック
        session = db.query(Session).filter(
            Session.session_id == session_id,
            Session.user_id == user_id
        ).first()
        
        if session:
            return True  # 所有者は常にフルアクセス
        
        # 共有権限チェック
        share = db.query(SessionShare).filter(
            SessionShare.session_id == session_id,
            SessionShare.shared_with_id == user_id,
            SessionShare.expires_at > datetime.now() if SessionShare.expires_at.isnot(None) else True
        ).first()
        
        if not share:
            return False
        
        # 権限レベルチェック
        permission_hierarchy = {
            PermissionLevel.VIEWER: 1,
            PermissionLevel.COLLABORATOR: 2,
            PermissionLevel.ADMIN: 3
        }
        
        return permission_hierarchy[share.permission_level] >= permission_hierarchy[required_permission]
    
    @staticmethod
    async def join_session(db: DBSession, session_id: str, user_id: int):
        """セッションに参加"""
        # 既存の参加記録をチェック
        participant = db.query(SessionParticipant).filter(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == user_id
        ).first()
        
        if participant:
            # 既存参加者の最終アクセス時刻を更新
            participant.last_seen = datetime.now()
            participant.is_active = True
        else:
            # 新規参加者を追加
            participant = SessionParticipant(
                session_id=session_id,
                user_id=user_id
            )
            db.add(participant)
        
        db.commit()
        
        # 他の参加者に通知
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            await manager.send_to_session(session_id, json.dumps({
                "type": "user_joined",
                "user": {
                    "id": user.id,
                    "username": user.username
                },
                "timestamp": datetime.now().isoformat()
            }))
    
    @staticmethod
    async def leave_session(db: DBSession, session_id: str, user_id: int):
        """セッションから離脱"""
        participant = db.query(SessionParticipant).filter(
            SessionParticipant.session_id == session_id,
            SessionParticipant.user_id == user_id
        ).first()
        
        if participant:
            participant.is_active = False
            db.commit()
            
            # 他の参加者に通知
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                await manager.send_to_session(session_id, json.dumps({
                    "type": "user_left",
                    "user": {
                        "id": user.id,
                        "username": user.username
                    },
                    "timestamp": datetime.now().isoformat()
                }))
    
    @staticmethod
    async def record_activity(
        db: DBSession,
        session_id: str,
        user_id: int,
        activity_type: str,
        activity_data: Dict[str, Any]
    ):
        """ユーザーアクティビティを記録"""
        activity = UserActivity(
            session_id=session_id,
            user_id=user_id,
            activity_type=activity_type,
            activity_data=json.dumps(activity_data, ensure_ascii=False)
        )
        
        db.add(activity)
        db.commit()
        
        # リアルタイム同期（カーソル移動以外）
        if activity_type != "cursor_move":
            user = db.query(User).filter(User.id == user_id).first()
            await manager.send_to_session(session_id, json.dumps({
                "type": "user_activity",
                "user": {
                    "id": user.id,
                    "username": user.username
                },
                "activity_type": activity_type,
                "activity_data": activity_data,
                "timestamp": datetime.now().isoformat()
            }))

# API エンドポイント
@router.post("/sessions/{session_id}/share")
async def share_session(
    session_id: str,
    request: ShareSessionRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """セッションを他のユーザーと共有"""
    # セッション所有者権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つからないか、共有権限がありません")
    
    # 共有対象ユーザーの存在確認
    shared_with_user = db.query(User).filter(User.username == request.username).first()
    if not shared_with_user:
        raise HTTPException(status_code=404, detail="指定されたユーザーが見つかりません")
    
    # 自分自身との共有は不可
    if shared_with_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="自分自身とは共有できません")
    
    # 既存の共有設定をチェック
    existing_share = db.query(SessionShare).filter(
        SessionShare.session_id == session_id,
        SessionShare.shared_with_id == shared_with_user.id
    ).first()
    
    if existing_share:
        # 既存共有を更新
        existing_share.permission_level = request.permission_level
        existing_share.expires_at = (
            datetime.now() + timedelta(hours=request.expires_hours)
            if request.expires_hours else None
        )
    else:
        # 新規共有を作成
        share = SessionShare(
            session_id=session_id,
            owner_id=current_user.id,
            shared_with_id=shared_with_user.id,
            permission_level=request.permission_level,
            expires_at=(
                datetime.now() + timedelta(hours=request.expires_hours)
                if request.expires_hours else None
            )
        )
        db.add(share)
    
    db.commit()
    
    return {
        "message": f"セッションを {request.username} と共有しました",
        "permission_level": request.permission_level.value,
        "expires_at": (
            datetime.now() + timedelta(hours=request.expires_hours)
            if request.expires_hours else None
        )
    }

@router.get("/sessions/{session_id}/shares")
async def get_session_shares(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """セッションの共有一覧を取得"""
    # セッション所有者権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つからないか、閲覧権限がありません")
    
    shares = db.query(SessionShare).filter(
        SessionShare.session_id == session_id
    ).all()
    
    return {
        "shares": [
            {
                "id": share.id,
                "shared_with": {
                    "id": share.shared_with.id,
                    "username": share.shared_with.username
                },
                "permission_level": share.permission_level.value,
                "expires_at": share.expires_at.isoformat() if share.expires_at else None,
                "created_at": share.created_at.isoformat()
            }
            for share in shares
        ]
    }

@router.put("/sessions/{session_id}/shares/{share_id}")
async def update_share_permission(
    session_id: str,
    share_id: int,
    request: UpdatePermissionRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """共有権限を更新"""
    # セッション所有者権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つからないか、編集権限がありません")
    
    share = db.query(SessionShare).filter(
        SessionShare.id == share_id,
        SessionShare.session_id == session_id
    ).first()
    
    if not share:
        raise HTTPException(status_code=404, detail="共有設定が見つかりません")
    
    share.permission_level = request.permission_level
    db.commit()
    
    return {"message": "権限を更新しました"}

@router.delete("/sessions/{session_id}/shares/{share_id}")
async def revoke_session_share(
    session_id: str,
    share_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """セッション共有を取り消し"""
    # セッション所有者権限チェック
    session = db.query(Session).filter(
        Session.session_id == session_id,
        Session.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="セッションが見つからないか、削除権限がありません")
    
    share = db.query(SessionShare).filter(
        SessionShare.id == share_id,
        SessionShare.session_id == session_id
    ).first()
    
    if not share:
        raise HTTPException(status_code=404, detail="共有設定が見つかりません")
    
    db.delete(share)
    db.commit()
    
    return {"message": "共有を取り消しました"}

@router.get("/sessions/shared")
async def get_shared_sessions(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """自分と共有されているセッション一覧を取得"""
    shares = db.query(SessionShare).filter(
        SessionShare.shared_with_id == current_user.id,
        SessionShare.expires_at > datetime.now() if SessionShare.expires_at.isnot(None) else True
    ).all()
    
    shared_sessions = []
    for share in shares:
        session = db.query(Session).filter(Session.session_id == share.session_id).first()
        if session:
            shared_sessions.append({
                "session_id": session.session_id,
                "name": session.name,
                "description": session.description,
                "owner": {
                    "id": share.owner.id,
                    "username": share.owner.username
                },
                "permission_level": share.permission_level.value,
                "shared_at": share.created_at.isoformat(),
                "expires_at": share.expires_at.isoformat() if share.expires_at else None
            })
    
    return {"shared_sessions": shared_sessions}

@router.post("/sessions/{session_id}/join")
async def join_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """セッションに参加"""
    # 権限チェック
    has_permission = await CollaborationManager.check_session_permission(
        db, session_id, current_user.id, PermissionLevel.VIEWER
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
    
    # バックグラウンドでセッション参加処理
    background_tasks.add_task(
        CollaborationManager.join_session,
        db, session_id, current_user.id
    )
    
    return {"message": "セッションに参加しました"}

@router.post("/sessions/{session_id}/leave")
async def leave_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """セッションから離脱"""
    # バックグラウンドでセッション離脱処理
    background_tasks.add_task(
        CollaborationManager.leave_session,
        db, session_id, current_user.id
    )
    
    return {"message": "セッションから離脱しました"}

@router.get("/sessions/{session_id}/participants")
async def get_session_participants(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """セッション参加者一覧を取得"""
    # 権限チェック
    has_permission = await CollaborationManager.check_session_permission(
        db, session_id, current_user.id, PermissionLevel.VIEWER
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
    
    # アクティブな参加者を取得
    participants = db.query(SessionParticipant).filter(
        SessionParticipant.session_id == session_id,
        SessionParticipant.is_active == True,
        SessionParticipant.last_seen > datetime.now() - timedelta(minutes=5)  # 5分以内
    ).all()
    
    return {
        "participants": [
            {
                "user": {
                    "id": p.user.id,
                    "username": p.user.username
                },
                "joined_at": p.joined_at.isoformat(),
                "last_seen": p.last_seen.isoformat(),
                "cursor_position": json.loads(p.cursor_position) if p.cursor_position else None
            }
            for p in participants
        ]
    }

@router.post("/sessions/{session_id}/activity")
async def record_user_activity(
    session_id: str,
    request: ActivityRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """ユーザーアクティビティを記録"""
    # 権限チェック（コラボレーター以上の権限が必要な活動もある）
    required_permission = PermissionLevel.COLLABORATOR if request.activity_type in [
        "file_edit", "file_create", "file_delete"
    ] else PermissionLevel.VIEWER
    
    has_permission = await CollaborationManager.check_session_permission(
        db, session_id, current_user.id, required_permission
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="この操作に必要な権限がありません")
    
    # バックグラウンドでアクティビティ記録
    background_tasks.add_task(
        CollaborationManager.record_activity,
        db, session_id, current_user.id, request.activity_type, request.activity_data
    )
    
    return {"message": "アクティビティを記録しました"}

@router.put("/sessions/{session_id}/cursor")
async def update_cursor_position(
    session_id: str,
    cursor: CursorPosition,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """カーソル位置を更新"""
    # 権限チェック
    has_permission = await CollaborationManager.check_session_permission(
        db, session_id, current_user.id, PermissionLevel.VIEWER
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
    
    # 参加者のカーソル位置を更新
    participant = db.query(SessionParticipant).filter(
        SessionParticipant.session_id == session_id,
        SessionParticipant.user_id == current_user.id
    ).first()
    
    if participant:
        participant.cursor_position = json.dumps(cursor.dict(), ensure_ascii=False)
        participant.last_seen = datetime.now()
        db.commit()
        
        # 他の参加者にカーソル位置をブロードキャスト
        await manager.send_to_session(session_id, json.dumps({
            "type": "cursor_update",
            "user": {
                "id": current_user.id,
                "username": current_user.username
            },
            "cursor": cursor.dict(),
            "timestamp": datetime.now().isoformat()
        }))
    
    return {"message": "カーソル位置を更新しました"}

@router.get("/sessions/{session_id}/activities")
async def get_session_activities(
    session_id: str,
    activity_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db)
):
    """セッションのアクティビティ履歴を取得"""
    # 権限チェック
    has_permission = await CollaborationManager.check_session_permission(
        db, session_id, current_user.id, PermissionLevel.VIEWER
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="セッションへのアクセス権限がありません")
    
    query = db.query(UserActivity).filter(UserActivity.session_id == session_id)
    
    if activity_type:
        query = query.filter(UserActivity.activity_type == activity_type)
    
    activities = query.order_by(UserActivity.timestamp.desc()).offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "activities": [
            {
                "id": activity.id,
                "user": {
                    "id": activity.user.id,
                    "username": activity.user.username
                },
                "activity_type": activity.activity_type,
                "activity_data": json.loads(activity.activity_data),
                "timestamp": activity.timestamp.isoformat()
            }
            for activity in activities
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }