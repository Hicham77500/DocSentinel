from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.session import get_db
from app.models.billing_webhook_event import BillingWebhookEvent
from app.models.plan import Plan
from app.models.tenant import Tenant
from app.schemas.billing import CheckoutRequest, CheckoutResponse, PortalResponse, WebhookResponse
from app.security.tenant_context import get_current_tenant
from app.services.billing.service import get_billing_provider
from app.services.billing.webhook_service import apply_billing_event
from app.services.audit_service import log_event


router = APIRouter()
WEBHOOK_STATUS_RECEIVED = "received"
WEBHOOK_STATUS_PROCESSED = "processed"
WEBHOOK_STATUS_REJECTED = "rejected"


def _set_webhook_event_status(
    db: Session,
    event_record: BillingWebhookEvent,
    status_value: str,
) -> None:
    event_record.status = status_value
    event_record.processed_at = datetime.now(timezone.utc)
    db.add(event_record)
    db.commit()


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
    db: Session = Depends(get_db),
) -> WebhookResponse:
    payload = await request.body()
    provider = get_billing_provider()
    try:
        normalized_event = provider.handle_webhook(payload=payload, signature=stripe_signature)
    except HTTPException as exc:
        log_event(
            event="billing_webhook_rejected",
            tenant_id="",
            document_id="",
            status=str(exc.status_code),
            provider=settings.BILLING_PROVIDER.strip().lower(),
            event_type="",
        )
        raise

    tenant_id = str(normalized_event.get("tenant_id", "")) if normalized_event.get("tenant_id") else ""
    provider_name = str(normalized_event.get("provider", ""))
    external_event_id_raw = normalized_event.get("external_event_id")
    if not isinstance(external_event_id_raw, str) or not external_event_id_raw:
        log_event(
            event="billing_webhook_rejected",
            tenant_id=tenant_id,
            document_id="",
            status=WEBHOOK_STATUS_REJECTED,
            provider=provider_name,
            event_type=str(normalized_event.get("event_type", "")),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing external event identifier.",
        )
    external_event_id = external_event_id_raw
    event_type = str(normalized_event.get("event_type", ""))
    event_status = str(normalized_event.get("status", WEBHOOK_STATUS_RECEIVED))
    log_event(
        event="billing_webhook_received",
        tenant_id=tenant_id,
        document_id="",
        status=event_status,
        provider=provider_name,
        event_type=event_type,
    )

    event_record = BillingWebhookEvent(
        provider=provider_name,
        external_event_id=external_event_id,
        event_type=event_type,
        status=WEBHOOK_STATUS_RECEIVED,
    )
    db.add(event_record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_event = db.execute(
            select(BillingWebhookEvent).where(
                BillingWebhookEvent.provider == provider_name,
                BillingWebhookEvent.external_event_id == external_event_id,
            )
        ).scalar_one_or_none()
        if existing_event is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate webhook event conflict.",
            )
        return WebhookResponse(
            provider=provider_name,
            received=True,
            verified=bool(normalized_event.get("verified", False)),
            event_type=event_type,
            tenant_id=tenant_id or None,
            status=existing_event.status,
            ignored=True,
        )

    try:
        if normalized_event.get("ignored"):
            _set_webhook_event_status(
                db=db,
                event_record=event_record,
                status_value=WEBHOOK_STATUS_PROCESSED,
            )
            log_event(
                event="billing_webhook_processed",
                tenant_id=tenant_id,
                document_id="",
                status=WEBHOOK_STATUS_PROCESSED,
                provider=provider_name,
                event_type=event_type,
            )
            return WebhookResponse(**normalized_event)

        application_result = apply_billing_event(normalized_event)
        _set_webhook_event_status(
            db=db,
            event_record=event_record,
            status_value=WEBHOOK_STATUS_PROCESSED,
        )
        log_event(
            event="billing_webhook_processed",
            tenant_id=tenant_id,
            document_id="",
            status=WEBHOOK_STATUS_PROCESSED,
            provider=provider_name,
            event_type=event_type,
        )
        return WebhookResponse(**application_result)
    except HTTPException:
        db.rollback()
        _set_webhook_event_status(
            db=db,
            event_record=event_record,
            status_value=WEBHOOK_STATUS_REJECTED,
        )
        log_event(
            event="billing_webhook_rejected",
            tenant_id=tenant_id,
            document_id="",
            status=WEBHOOK_STATUS_REJECTED,
            provider=provider_name,
            event_type=event_type,
        )
        raise
    except Exception:
        db.rollback()
        _set_webhook_event_status(
            db=db,
            event_record=event_record,
            status_value=WEBHOOK_STATUS_REJECTED,
        )
        log_event(
            event="billing_webhook_rejected",
            tenant_id=tenant_id,
            document_id="",
            status=WEBHOOK_STATUS_REJECTED,
            provider=provider_name,
            event_type=event_type,
        )
        raise
