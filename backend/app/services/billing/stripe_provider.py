from __future__ import annotations

import json
import uuid

from fastapi import HTTPException, status

from app.config.settings import settings
from app.services.billing.base import BillingProvider


class StripeBillingProvider(BillingProvider):
    def __init__(self) -> None:
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe provider is not configured.",
            )
        if not settings.APP_BASE_URL:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Application base URL is not configured.",
            )

    def create_checkout_session(
        self,
        tenant_id: str,
        plan_code: str,
        success_url: str,
        cancel_url: str,
    ) -> dict:
        session_id = f"cs_test_{uuid.uuid4().hex}"
        return {
            "provider": "stripe",
            "session_id": session_id,
            "checkout_url": (
                f"{settings.APP_BASE_URL.rstrip('/')}/billing/mock/checkout/"
                f"{session_id}?tenant_id={tenant_id}&plan={plan_code}"
            ),
            "success_url": success_url,
            "cancel_url": cancel_url,
        }

    def create_customer_portal_session(self, tenant_id: str, return_url: str) -> dict:
        portal_session_id = f"bps_test_{uuid.uuid4().hex}"
        return {
            "provider": "stripe",
            "session_id": portal_session_id,
            "portal_url": (
                f"{settings.APP_BASE_URL.rstrip('/')}/billing/mock/portal/"
                f"{portal_session_id}?tenant_id={tenant_id}"
            ),
            "return_url": return_url,
        }

    def handle_webhook(self, payload: bytes, signature: str | None) -> dict:
        if settings.STRIPE_WEBHOOK_SECRET and not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing webhook signature.",
            )

        try:
            parsed_payload = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook payload.",
            ) from exc

        event_type = parsed_payload.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook event.",
            )

        return {
            "provider": "stripe",
            "received": True,
            "verified": bool(signature) or not bool(settings.STRIPE_WEBHOOK_SECRET),
            "event_type": event_type,
        }
