from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models.api_key import ApiKey
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.security.api_key_generator import generate_api_key, hash_api_key


def create_tenant_with_api_key(
    name: str,
    slug: str,
    plan_code: str,
    api_key_name: str = "default",
) -> dict:
    db = SessionLocal()
    try:
        existing_tenant = db.execute(select(Tenant.id).where(Tenant.slug == slug)).scalar_one_or_none()
        if existing_tenant is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tenant slug already exists.",
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
                detail="Plan not found or inactive.",
            )

        tenant = Tenant(
            name=name,
            slug=slug,
            is_active=True,
            monthly_document_quota=int(plan.monthly_document_quota),
            monthly_api_quota=int(plan.monthly_api_quota),
        )
        db.add(tenant)
        db.flush()

        period_start = datetime.now(timezone.utc)
        period_end = period_start + timedelta(days=30)
        subscription = Subscription(
            tenant_id=tenant.id,
            plan_id=plan.id,
            status="active",
            current_period_start=period_start,
            current_period_end=period_end,
        )
        db.add(subscription)
        db.flush()

        tenant.current_subscription_id = subscription.id
        db.add(tenant)

        raw_api_key = generate_api_key()
        api_key = ApiKey(
            tenant_id=tenant.id,
            key_hash=hash_api_key(raw_api_key),
            name=api_key_name,
            is_active=True,
        )
        db.add(api_key)

        db.commit()

        return {
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "plan_code": plan.code,
            "api_key_name": api_key.name,
            "api_key": raw_api_key,
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant bootstrap failed due to a conflicting resource.",
        ) from exc
    finally:
        db.close()


def create_tenant_api_key(tenant_id: UUID, api_key_name: str) -> dict:
    db = SessionLocal()
    try:
        tenant = db.get(Tenant, tenant_id)
        if tenant is None or not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found.",
            )

        raw_api_key = generate_api_key()
        api_key = ApiKey(
            tenant_id=tenant.id,
            key_hash=hash_api_key(raw_api_key),
            name=api_key_name,
            is_active=True,
        )
        db.add(api_key)
        db.commit()

        return {
            "tenant_id": str(tenant.id),
            "api_key_name": api_key.name,
            "api_key": raw_api_key,
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="API key provisioning failed due to a conflicting resource.",
        ) from exc
    finally:
        db.close()
