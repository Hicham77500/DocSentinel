from __future__ import annotations

from datetime import datetime, timezone
import json
import logging


logger = logging.getLogger("docsentinel.audit")


def log_event(
    event: str,
    tenant_id: str,
    document_id: str,
    status: str,
    fraud_score: float | None = None,
    document_type: str | None = None,
    provider: str | None = None,
    event_type: str | None = None,
) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "tenant_id": tenant_id,
        "document_id": document_id,
        "status": status,
        "fraud_score": fraud_score,
        "document_type": document_type,
        "provider": provider,
        "event_type": event_type,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))
