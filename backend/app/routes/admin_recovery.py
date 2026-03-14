from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.security.admin_auth import require_admin_token
from app.services.audit_service import log_event
from app.services.pipeline_recovery_service import recover_stale_documents


router = APIRouter(dependencies=[Depends(require_admin_token)])


@router.post("/stale-documents")
def trigger_stale_document_recovery(max_age_minutes: int = 30) -> dict[str, int]:
    if max_age_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_age_minutes must be greater than zero.",
        )

    summary = recover_stale_documents(max_age_minutes=max_age_minutes)
    log_event(
        event="pipeline_recovery_run",
        tenant_id="",
        document_id="",
        status=f"checked={summary['checked']},recovered={summary['recovered']}",
        anomaly_count=summary["recovered"],
    )
    return summary
