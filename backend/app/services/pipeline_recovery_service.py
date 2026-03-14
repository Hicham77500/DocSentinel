from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.metrics.metrics import (
    pipeline_recovery_runs_total,
    safe_inc,
    stale_documents_recovered_total,
)
from app.models.document import Document
from app.services.audit_service import log_event


RECOVERABLE_STATUSES = (
    "processing",
    "ocr_done",
    "extracted",
    "normalized",
    "fraud_checked",
)


def recover_stale_documents(max_age_minutes: int = 30) -> dict[str, int]:
    if max_age_minutes <= 0:
        raise ValueError("max_age_minutes must be greater than zero.")

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
    db = SessionLocal()
    checked = 0
    recovered_documents: list[Document] = []

    try:
        stale_documents = db.execute(
            select(Document).where(
                Document.status.in_(RECOVERABLE_STATUSES),
                Document.updated_at < cutoff,
            )
        ).scalars().all()

        checked = len(stale_documents)

        for document in stale_documents:
            document.status = "failed"
            db.add(document)
            recovered_documents.append(document)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        safe_inc(pipeline_recovery_runs_total)

    recovered_count = len(recovered_documents)
    if recovered_count > 0:
        safe_inc(stale_documents_recovered_total, float(recovered_count))
        for document in recovered_documents:
            log_event(
                event="stale_document_recovered",
                tenant_id=str(document.tenant_id),
                document_id=str(document.id),
                status=document.status,
                fraud_score=document.fraud_score,
            )

    return {
        "checked": checked,
        "recovered": recovered_count,
    }
