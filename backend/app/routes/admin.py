from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.schemas.admin import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    TenantBootstrapRequest,
    TenantBootstrapResponse,
)
from app.security.admin_auth import require_admin_token
from app.services.admin_onboarding_service import create_tenant_api_key, create_tenant_with_api_key


router = APIRouter(dependencies=[Depends(require_admin_token)])


@router.post("/tenants/bootstrap", response_model=TenantBootstrapResponse)
def bootstrap_tenant(payload: TenantBootstrapRequest) -> TenantBootstrapResponse:
    result = create_tenant_with_api_key(
        name=payload.name,
        slug=payload.slug,
        plan_code=payload.plan_code,
        api_key_name=payload.api_key_name,
    )
    return TenantBootstrapResponse(**result)


@router.post("/tenants/{tenant_id}/api-keys", response_model=ApiKeyCreateResponse)
def create_api_key_for_tenant(
    tenant_id: UUID,
    payload: ApiKeyCreateRequest,
) -> ApiKeyCreateResponse:
    result = create_tenant_api_key(
        tenant_id=tenant_id,
        api_key_name=payload.name,
    )
    return ApiKeyCreateResponse(**result)
