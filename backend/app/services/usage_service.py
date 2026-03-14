from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.usage_event import UsageEvent


def _get_month_bounds_utc(reference: datetime | None = None) -> tuple[datetime, datetime]:
    now = reference or datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12:
        next_month_start = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        next_month_start = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    return month_start, next_month_start


def record_usage_event(
    tenant_id: str,
    event_type: str,
    units: int = 1,
    document_id: str | None = None,
) -> None:
    db = SessionLocal()
    try:
        event = UsageEvent(
            tenant_id=UUID(tenant_id),
            document_id=UUID(document_id) if document_id else None,
            event_type=event_type,
            units=units,
        )
        db.add(event)
        db.commit()
    finally:
        db.close()


def get_monthly_usage(tenant_id: str) -> dict:
    month_start, next_month_start = _get_month_bounds_utc()
    db = SessionLocal()
    try:
        rows = db.execute(
            select(
                UsageEvent.event_type,
                func.coalesce(func.sum(UsageEvent.units), 0),
            )
            .where(
                UsageEvent.tenant_id == UUID(tenant_id),
                UsageEvent.created_at >= month_start,
                UsageEvent.created_at < next_month_start,
            )
            .group_by(UsageEvent.event_type)
        ).all()
    finally:
        db.close()

    usage = {
        "uploaded_documents": 0,
        "api_requests": 0,
        "ocr_processed": 0,
        "fraud_scored": 0,
    }

    mapping = {
        "document_uploaded": "uploaded_documents",
        "api_request": "api_requests",
        "ocr_processed": "ocr_processed",
        "fraud_scored": "fraud_scored",
    }

    for event_type, units in rows:
        key = mapping.get(event_type)
        if key:
            usage[key] = int(units or 0)

    return usage
