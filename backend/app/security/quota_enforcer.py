from __future__ import annotations

from fastapi import HTTPException, status
from uuid import UUID

from app.db.session import SessionLocal
from app.models.tenant import Tenant
from app.services.usage_service import get_monthly_usage


def _get_active_tenant(tenant_id: str) -> Tenant:
    try:
        parsed_tenant_id = UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant context.",
        ) from exc

    db = SessionLocal()
    try:
        tenant = db.get(Tenant, parsed_tenant_id)
    finally:
        db.close()

    if tenant is None or not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant context.",
        )
    return tenant


def enforce_document_quota(tenant_id: str) -> None:
    tenant = _get_active_tenant(tenant_id)
    usage = get_monthly_usage(tenant_id)
    if usage["uploaded_documents"] >= int(tenant.monthly_document_quota):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly document quota exceeded.",
        )


def enforce_api_quota(tenant_id: str) -> None:
    tenant = _get_active_tenant(tenant_id)
    usage = get_monthly_usage(tenant_id)
    if usage["api_requests"] >= int(tenant.monthly_api_quota):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly API quota exceeded.",
        )
