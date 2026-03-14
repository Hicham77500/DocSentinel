from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

from fastapi import HTTPException, status

from app.config.settings import settings
from app.services.billing.base import BillingProvider


SUPPORTED_WEBHOOK_EVENTS = {
    "subscription.created",
    "subscription.updated",
    "subscription.deleted",
}
SUPPORTED_SUBSCRIPTION_STATUSES = {"trial", "active", "past_due", "canceled"}


def _to_iso8601_utc(value: object, field_name: str) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name}.",
            ) from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Missing or invalid {field_name}.",
    )


def _read_data_object(payload: dict) -> dict:
    data = payload.get("data")
    if isinstance(data, dict):
        obj = data.get("object")
        if isinstance(obj, dict):
            return obj
        return data
    return payload


def _get_field(payload: dict, data_object: dict, field_name: str) -> object:
    if field_name in data_object:
        return data_object[field_name]
    if field_name in payload:
        return payload[field_name]
    return None


def _extract_tenant_id(payload: dict, data_object: dict) -> str:
    tenant_id = _get_field(payload, data_object, "tenant_id")
    if isinstance(tenant_id, str) and tenant_id:
        return tenant_id

    metadata = data_object.get("metadata")
    if isinstance(metadata, dict):
        metadata_tenant_id = metadata.get("tenant_id")
        if isinstance(metadata_tenant_id, str) and metadata_tenant_id:
            return metadata_tenant_id

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Missing tenant_id in webhook payload.",
    )


def _extract_plan_code(payload: dict, data_object: dict) -> str:
    plan_code = _get_field(payload, data_object, "plan_code")
    if isinstance(plan_code, str) and plan_code:
        return plan_code

    plan_obj = data_object.get("plan")
    if isinstance(plan_obj, dict):
        nested_code = plan_obj.get("code")
        if isinstance(nested_code, str) and nested_code:
            return nested_code

    metadata = data_object.get("metadata")
    if isinstance(metadata, dict):
        metadata_plan_code = metadata.get("plan_code")
        if isinstance(metadata_plan_code, str) and metadata_plan_code:
            return metadata_plan_code

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Missing plan_code in webhook payload.",
    )


def _extract_external_id(payload: dict, data_object: dict) -> str:
    external_id = _get_field(payload, data_object, "subscription_external_id")
    if isinstance(external_id, str) and external_id:
        return external_id

    candidate_id = data_object.get("id")
    if isinstance(candidate_id, str) and candidate_id:
        return candidate_id

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Missing subscription external identifier.",
    )


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

        if not isinstance(parsed_payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed webhook payload.",
            )

        event_type = parsed_payload.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook event type.",
            )

        verified = bool(signature) or not bool(settings.STRIPE_WEBHOOK_SECRET)
        if event_type not in SUPPORTED_WEBHOOK_EVENTS:
            return {
                "provider": "stripe",
                "received": True,
                "verified": verified,
                "event_type": event_type,
                "ignored": True,
            }

        data_object = _read_data_object(parsed_payload)
        tenant_id = _extract_tenant_id(parsed_payload, data_object)
        plan_code = _extract_plan_code(parsed_payload, data_object)
        subscription_external_id = _extract_external_id(parsed_payload, data_object)

        raw_status = _get_field(parsed_payload, data_object, "status")
        if event_type == "subscription.deleted" and not raw_status:
            raw_status = "canceled"
        if not isinstance(raw_status, str) or raw_status not in SUPPORTED_SUBSCRIPTION_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid subscription status.",
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        raw_period_start = _get_field(parsed_payload, data_object, "current_period_start")
        raw_period_end = _get_field(parsed_payload, data_object, "current_period_end")
        if event_type == "subscription.deleted":
            raw_period_start = raw_period_start or now_iso
            raw_period_end = raw_period_end or now_iso

        current_period_start = _to_iso8601_utc(raw_period_start, "current_period_start")
        current_period_end = _to_iso8601_utc(raw_period_end, "current_period_end")

        return {
            "provider": "stripe",
            "received": True,
            "verified": verified,
            "event_type": event_type,
            "tenant_id": tenant_id,
            "plan_code": plan_code,
            "subscription_external_id": subscription_external_id,
            "status": raw_status,
            "current_period_start": current_period_start,
            "current_period_end": current_period_end,
            "ignored": False,
        }
