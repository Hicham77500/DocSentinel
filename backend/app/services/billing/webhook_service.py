from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.services.audit_service import log_event


SUPPORTED_EVENT_TYPES = {
    "subscription.created",
    "subscription.updated",
    "subscription.deleted",
}
SUPPORTED_STATUSES = {"trial", "active", "past_due", "canceled"}


def _parse_iso_datetime(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}.",
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def apply_billing_event(event: dict) -> dict:
    provider = str(event.get("provider", ""))
    event_type = str(event.get("event_type", ""))

    if event_type not in SUPPORTED_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported billing event type.",
        )

    tenant_id_raw = event.get("tenant_id")
    plan_code_raw = event.get("plan_code")
    external_id_raw = event.get("subscription_external_id")
    status_raw = event.get("status")
    period_start_raw = event.get("current_period_start")
    period_end_raw = event.get("current_period_end")

    if not all(
        isinstance(v, str) and v
        for v in [tenant_id_raw, plan_code_raw, external_id_raw, status_raw]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed billing event payload.",
        )

    if not isinstance(period_start_raw, str) or not isinstance(period_end_raw, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed billing period fields.",
        )

    tenant_id = tenant_id_raw
    plan_code = plan_code_raw
    external_id = external_id_raw
    subscription_status = status_raw

    if subscription_status not in SUPPORTED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription status.",
        )

    period_start = _parse_iso_datetime(period_start_raw, "current_period_start")
    period_end = _parse_iso_datetime(period_end_raw, "current_period_end")

    db = SessionLocal()
    try:
        try:
            tenant_uuid = UUID(tenant_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id.",
            ) from exc

        tenant = db.get(Tenant, tenant_uuid)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown tenant.",
            )

        plan = db.execute(
            select(Plan).where(
                Plan.code == plan_code,
                Plan.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown plan.",
            )

        subscription = db.execute(
            select(Subscription).where(Subscription.external_id == external_id)
        ).scalar_one_or_none()

        if subscription is None:
            subscription = Subscription(
                tenant_id=tenant.id,
                external_id=external_id,
                plan_id=plan.id,
                status=subscription_status,
                current_period_start=period_start,
                current_period_end=period_end,
            )
            db.add(subscription)
            db.flush()
        else:
            subscription.tenant_id = tenant.id
            subscription.plan_id = plan.id
            subscription.status = subscription_status
            subscription.current_period_start = period_start
            subscription.current_period_end = period_end
            db.add(subscription)
            db.flush()

        if subscription.status in {"active", "trial"}:
            tenant.current_subscription_id = subscription.id
            db.add(tenant)
        elif (
            subscription.status == "canceled"
            and tenant.current_subscription_id == subscription.id
        ):
            tenant.current_subscription_id = None
            db.add(tenant)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    summary = {
        "provider": provider,
        "received": True,
        "verified": True,
        "event_type": event_type,
        "tenant_id": tenant_id,
        "subscription_id": str(subscription.id),
        "status": subscription.status,
        "ignored": False,
    }
    log_event(
        event="billing_subscription_updated",
        tenant_id=tenant_id,
        document_id="",
        status=subscription.status,
        provider=provider,
        event_type=event_type,
    )
    return summary
