from __future__ import annotations

from app.services.audit_service import log_event
from app.services.pipeline_recovery_service import recover_stale_documents
from app.workers.celery_app import celery_app


@celery_app.task(
    name="app.workers.tasks_recovery.recover_stale_documents_task",
)
def recover_stale_documents_task(max_age_minutes: int = 30) -> dict[str, int]:
    summary = recover_stale_documents(max_age_minutes=max_age_minutes)
    log_event(
        event="pipeline_recovery_run",
        tenant_id="",
        document_id="",
        status=f"checked={summary['checked']},recovered={summary['recovered']}",
        anomaly_count=summary["recovered"],
    )
    return summary
