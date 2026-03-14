from __future__ import annotations

from fastapi import HTTPException, status

from app.services.subscription_service import get_current_plan_limits
from app.services.usage_service import get_monthly_usage


def _get_plan_limits_or_forbidden(tenant_id: str) -> dict:
    limits = get_current_plan_limits(tenant_id)
    if not limits:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription plan.",
        )
    return limits


def enforce_document_quota(tenant_id: str) -> None:
    limits = _get_plan_limits_or_forbidden(tenant_id)
    usage = get_monthly_usage(tenant_id)
    if usage["uploaded_documents"] >= int(limits["monthly_document_quota"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly document quota exceeded.",
        )


def enforce_api_quota(tenant_id: str) -> None:
    limits = _get_plan_limits_or_forbidden(tenant_id)
    usage = get_monthly_usage(tenant_id)
    if usage["api_requests"] >= int(limits["monthly_api_quota"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly API quota exceeded.",
        )
