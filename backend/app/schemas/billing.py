from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=64)
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutResponse(BaseModel):
    provider: str
    session_id: str
    checkout_url: str
    success_url: str
    cancel_url: str


class PortalResponse(BaseModel):
    provider: str
    session_id: str
    portal_url: str
    return_url: str


class WebhookResponse(BaseModel):
    provider: str
    received: bool
    verified: bool
    event_type: str
    tenant_id: str | None = None
    subscription_id: str | None = None
    status: str | None = None
    ignored: bool = False
