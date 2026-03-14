from __future__ import annotations

from pydantic import BaseModel, Field


class TenantBootstrapRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    plan_code: str = Field(min_length=1, max_length=64)
    api_key_name: str = Field(default="default", min_length=1, max_length=255)


class TenantBootstrapResponse(BaseModel):
    tenant_id: str
    tenant_slug: str
    plan_code: str
    api_key_name: str
    api_key: str


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ApiKeyCreateResponse(BaseModel):
    tenant_id: str
    api_key_name: str
    api_key: str
