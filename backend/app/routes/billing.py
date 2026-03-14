from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.session import get_db
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.schemas.billing import CheckoutRequest, CheckoutResponse, PortalResponse, WebhookResponse
from app.security.tenant_context import get_current_tenant
from app.services.billing.service import get_billing_provider


router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> CheckoutResponse:
    plan = db.execute(
        select(Plan).where(
            Plan.code == payload.plan_code,
            Plan.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found.",
        )

    success_url = payload.success_url or f"{settings.APP_BASE_URL.rstrip('/')}/billing/success"
    cancel_url = payload.cancel_url or f"{settings.APP_BASE_URL.rstrip('/')}/billing/cancel"

    provider = get_billing_provider()
    session = provider.create_checkout_session(
        tenant_id=str(tenant.id),
        plan_code=plan.code,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return CheckoutResponse(**session)


@router.post("/portal", response_model=PortalResponse)
def create_portal(
    return_url: str | None = Body(default=None, embed=True),
    tenant: Tenant = Depends(get_current_tenant),
) -> PortalResponse:
    resolved_return_url = return_url or f"{settings.APP_BASE_URL.rstrip('/')}/billing/return"
    provider = get_billing_provider()
    session = provider.create_customer_portal_session(
        tenant_id=str(tenant.id),
        return_url=resolved_return_url,
    )
    return PortalResponse(**session)


@router.post("/webhook", response_model=WebhookResponse)
async def billing_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> WebhookResponse:
    payload = await request.body()
    provider = get_billing_provider()
    result = provider.handle_webhook(payload=payload, signature=stripe_signature)
    return WebhookResponse(**result)
