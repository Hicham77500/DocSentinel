from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DocumentResultResponse(BaseModel):
    document_id: UUID
    document_type: str
    bundle_id: UUID | None
    bundle_crosscheck_status: str | None
    bundle_anomalies: list[str]
    status: str
    fraud_score: float
    silver_path: str
    gold_path: str
    fields: dict[str, Any]
    anomalies: list[str]
    amounts: list[float]
