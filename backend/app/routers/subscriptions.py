"""
サブスクリプション管理のAPIルーター
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import get_db
from ..auth import get_current_active_user
from ..models import User, Subscription, SubscriptionPlan, UsageLog
from ..schemas import (
    SubscriptionSchema, SubscriptionCreate, SubscriptionUpdate,
    SubscriptionPlanSchema, UsageLogSchema
)

router = APIRouter(prefix="/subscriptions", tags=["サブスクリプション管理"])

# デフォルトプラン設定
DEFAULT_PLANS = {
    "free": {
        "name": "free",
        "display_name": "無料プラン",
        "description": "基本ターミナル機能のみ利用可能",
        "monthly_price": 0,
        "yearly_price": 0,
        "features": {
            "claude_sessions": 0,
            "claude_tokens_per_month": 0,
            "storage_gb": 1,
            "concurrent_sessions": 3,
            "api_calls_per_hour": 100,
            "priority_support": False,
            "collaboration": False,
            "webhook_integrations": False
        }
    },
    "pro": {
        "name": "pro",
        "display_name": "Proプラン",
        "description": "Claude統合ターミナル＋高度な開発支援",
        "monthly_price": 1980,
        "yearly_price": 19800,
        "features": {
            "claude_sessions": 5,
            "claude_tokens_per_month": 100000,
            "storage_gb": 10,
            "concurrent_sessions": 10,
            "api_calls_per_hour": 1000,
            "priority_support": True,
            "collaboration": True,
            "webhook_integrations": True
        }
    },
    "enterprise": {
        "name": "enterprise",
        "display_name": "Enterpriseプラン",
        "description": "チーム開発・企業向け無制限プラン",
        "monthly_price": 9800,
        "yearly_price": 98000,
        "features": {
            "claude_sessions": 50,
            "claude_tokens_per_month": 1000000,
            "storage_gb": 100,
            "concurrent_sessions": 50,
            "api_calls_per_hour": 10000,
            "priority_support": True,
            "collaboration": True,
            "webhook_integrations": True
        }
    }
}

@router.get("/plans", response_model=List[SubscriptionPlanSchema])
async def get_available_plans(db: Session = Depends(get_db)):
    """利用可能なサブスクリプションプラン一覧を取得"""
    plans = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.is_active == True,
        SubscriptionPlan.is_visible == True
    ).order_by(SubscriptionPlan.sort_order).all()
    
    # プランが存在しない場合はデフォルトプランを返す
    if not plans:
        return [
            SubscriptionPlanSchema(
                plan_id=f"default-{plan_type}",
                name=plan_data["name"],
                display_name=plan_data["display_name"],
                description=plan_data["description"],
                plan_type=plan_type,
                monthly_price=plan_data["monthly_price"],
                yearly_price=plan_data["yearly_price"],
                features=plan_data["features"],
                is_active=True,
                is_visible=True,
                sort_order=i
            )
            for i, (plan_type, plan_data) in enumerate(DEFAULT_PLANS.items())
        ]
    
    return plans

@router.get("/current", response_model=SubscriptionSchema)
async def get_current_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """現在のサブスクリプション情報を取得"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        # 管理者ユーザーには Enterprise相当の権限を付与
        if current_user.is_admin:
            admin_plan = DEFAULT_PLANS["enterprise"]
            return SubscriptionSchema(
                subscription_id="admin-enterprise",
                user_id=current_user.id,
                plan_type="enterprise",
                plan_name="管理者プラン",
                status="active",
                monthly_price=0,
                billing_cycle="monthly",
                limits=admin_plan["features"],
                usage={
                    "claude_tokens_used": 0,
                    "storage_used_gb": 0,
                    "current_sessions": 0,
                    "api_calls_today": 0
                },
                starts_at=datetime.utcnow(),
                auto_renew=False,
                created_at=datetime.utcnow()
            )
        
        # 一般ユーザーはデフォルトでFreeプランを返す
        default_plan = DEFAULT_PLANS["free"]
        return SubscriptionSchema(
            subscription_id="default-free",
            user_id=current_user.id,
            plan_type="free",
            plan_name=default_plan["display_name"],
            status="active",
            monthly_price=0,
            billing_cycle="monthly",
            limits=default_plan["features"],
            usage={
                "claude_tokens_used": 0,
                "storage_used_gb": 0,
                "current_sessions": 0,
                "api_calls_today": 0
            },
            starts_at=datetime.utcnow(),
            auto_renew=False,
            created_at=datetime.utcnow()
        )
    
    return subscription

@router.post("/subscribe", response_model=SubscriptionSchema)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """新しいサブスクリプションを作成"""
    # 既存のアクティブなサブスクリプションをチェック
    existing = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="既にアクティブなサブスクリプションが存在します"
        )
    
    # プラン情報を取得
    plan_info = DEFAULT_PLANS.get(subscription_data.plan_type)
    if not plan_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無効なプランタイプです"
        )
    
    # サブスクリプションを作成
    subscription_id = str(uuid.uuid4())
    
    # 請求期間を計算
    if subscription_data.billing_cycle == "yearly":
        ends_at = datetime.utcnow() + timedelta(days=365)
        next_billing = ends_at
        price = plan_info["yearly_price"]
    else:
        ends_at = datetime.utcnow() + timedelta(days=30)
        next_billing = ends_at
        price = plan_info["monthly_price"]
    
    db_subscription = Subscription(
        subscription_id=subscription_id,
        user_id=current_user.id,
        plan_type=subscription_data.plan_type,
        plan_name=plan_info["name"],
        status="active",
        monthly_price=price,
        billing_cycle=subscription_data.billing_cycle,
        limits=plan_info["features"],
        usage={
            "claude_tokens_used": 0,
            "storage_used_gb": 0,
            "current_sessions": 0,
            "api_calls_today": 0
        },
        payment_method=subscription_data.payment_method,
        starts_at=datetime.utcnow(),
        ends_at=ends_at,
        next_billing_date=next_billing,
        auto_renew=True
    )
    
    try:
        db.add(db_subscription)
        db.commit()
        db.refresh(db_subscription)
        
        # 使用量ログを作成
        usage_log = UsageLog(
            user_id=current_user.id,
            usage_type="subscription_start",
            amount=1,
            billing_period=datetime.utcnow().strftime("%Y-%m"),
            usage_metadata={
                "plan_type": subscription_data.plan_type,
                "billing_cycle": subscription_data.billing_cycle,
                "subscription_id": subscription_id
            }
        )
        db.add(usage_log)
        db.commit()
        
        return db_subscription
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"サブスクリプションの作成に失敗しました: {str(e)}"
        )

@router.put("/update", response_model=SubscriptionSchema)
async def update_subscription(
    subscription_update: SubscriptionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """サブスクリプションを更新"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="アクティブなサブスクリプションが見つかりません"
        )
    
    # 更新可能なフィールドのみ更新
    update_data = subscription_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(subscription, field):
            setattr(subscription, field, value)
    
    subscription.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(subscription)
    
    return subscription

@router.post("/cancel")
async def cancel_subscription(
    cancellation_reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """サブスクリプションをキャンセル"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="アクティブなサブスクリプションが見つかりません"
        )
    
    # キャンセル処理
    subscription.status = "cancelled"
    subscription.cancelled_at = datetime.utcnow()
    subscription.auto_renew = False
    if cancellation_reason:
        subscription.cancellation_reason = cancellation_reason
    
    db.commit()
    
    return {"message": "サブスクリプションをキャンセルしました"}

@router.get("/usage", response_model=List[UsageLogSchema])
async def get_usage_history(
    limit: int = 100,
    offset: int = 0,
    usage_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """使用量履歴を取得"""
    query = db.query(UsageLog).filter(UsageLog.user_id == current_user.id)
    
    if usage_type:
        query = query.filter(UsageLog.usage_type == usage_type)
    
    usage_logs = query.order_by(desc(UsageLog.created_at)).offset(offset).limit(limit).all()
    return usage_logs

@router.get("/usage/summary")
async def get_usage_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """現在月の使用量サマリーを取得"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status == "active"
    ).first()
    
    current_month = datetime.utcnow().strftime("%Y-%m")
    
    # 今月の使用量を集計
    usage_summary = {}
    usage_logs = db.query(UsageLog).filter(
        UsageLog.user_id == current_user.id,
        UsageLog.billing_period == current_month
    ).all()
    
    for log in usage_logs:
        usage_type = log.usage_type
        if usage_type not in usage_summary:
            usage_summary[usage_type] = {
                "total_amount": 0,
                "total_cost": 0,
                "count": 0
            }
        
        usage_summary[usage_type]["total_amount"] += log.amount
        usage_summary[usage_type]["total_cost"] += log.cost_yen
        usage_summary[usage_type]["count"] += 1
    
    # サブスクリプション制限と比較
    limits = subscription.limits if subscription else DEFAULT_PLANS["free"]["features"]
    current_usage = subscription.usage if subscription else {}
    
    return {
        "billing_period": current_month,
        "subscription": {
            "plan_type": subscription.plan_type if subscription else "free",
            "limits": limits,
            "current_usage": current_usage
        },
        "usage_summary": usage_summary,
        "limit_warnings": {
            "claude_tokens": current_usage.get("claude_tokens_used", 0) >= limits.get("claude_tokens_per_month", 0) * 0.8,
            "storage": current_usage.get("storage_used_gb", 0) >= limits.get("storage_gb", 0) * 0.8,
            "api_calls": current_usage.get("api_calls_today", 0) >= limits.get("api_calls_per_hour", 0) * 20  # 20時間分
        }
    }