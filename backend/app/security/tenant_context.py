from __future__ import annotations

from fastapi import Depends

from app.models.tenant import Tenant
from app.security.api_key import require_api_key


def get_current_tenant(tenant: Tenant = Depends(require_api_key)) -> Tenant:
    return tenant
