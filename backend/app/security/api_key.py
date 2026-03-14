from __future__ import annotations

import hashlib

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.tenant import Tenant
from app.security.quota_enforcer import enforce_api_quota
from app.security.rate_limiter import enforce_rate_limit
from app.services.usage_service import record_usage_event


def _hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Tenant:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

    key_hash = _hash_api_key(x_api_key)
    statement = (
        select(Tenant)
        .join(ApiKey, ApiKey.tenant_id == Tenant.id)
        .where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
    )
    tenant = db.execute(statement).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )

    enforce_rate_limit(key_hash)
    enforce_api_quota(str(tenant.id))
    record_usage_event(
        tenant_id=str(tenant.id),
        event_type="api_request",
        units=1,
    )
    return tenant
