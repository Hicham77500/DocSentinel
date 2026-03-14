from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.db.session import SessionLocal
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.tenant import Tenant


ACTIVE_STATUSES = {"active", "trial"}


def _is_subscription_current(subscription: Subscription, now: datetime) -> bool:
    if subscription.status not in ACTIVE_STATUSES:
        return False
    if subscription.current_period_start > now:
        return False
    if subscription.current_period_end <= now:
        return False
    return True


def get_active_subscription(tenant_id: str) -> dict | None:
    db = SessionLocal()
    try:
        tenant = db.get(Tenant, UUID(tenant_id))
        if tenant is None or not tenant.is_active:
            return None
        if tenant.current_subscription_id is None:
            return None

        subscription = db.get(Subscription, tenant.current_subscription_id)
        if subscription is None or subscription.tenant_id != tenant.id:
            return None

        plan = db.get(Plan, subscription.plan_id)
        if plan is None or not plan.is_active:
            return None

        now = datetime.now(timezone.utc)
        if not _is_subscription_current(subscription, now):
            return None

        return {
            "subscription_id": str(subscription.id),
            "tenant_id": str(tenant.id),
            "plan_id": str(plan.id),
            "plan_code": plan.code,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat(),
            "current_period_end": subscription.current_period_end.isoformat(),
            "monthly_document_quota": int(plan.monthly_document_quota),
            "monthly_api_quota": int(plan.monthly_api_quota),
        }
    finally:
        db.close()


def get_current_plan_limits(tenant_id: str) -> dict:
    active_subscription = get_active_subscription(tenant_id)
    if active_subscription is None:
        return {}
    return {
        "plan_code": active_subscription["plan_code"],
        "monthly_document_quota": active_subscription["monthly_document_quota"],
        "monthly_api_quota": active_subscription["monthly_api_quota"],
    }
