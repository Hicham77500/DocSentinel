import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.tenant import Tenant
from app.schemas.result import DocumentResultResponse
from app.security.tenant_context import get_current_tenant
from app.services.storage_service import storage_service


router = APIRouter()


def _as_float_list(values: object) -> list[float]:
    if not isinstance(values, list):
        return []
    result: list[float] = []
    for item in values:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            continue
    return result


def _as_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item) for item in values]


@router.get("/{document_id}/results", response_model=DocumentResultResponse)
def get_document_results(
    document_id: UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> DocumentResultResponse:
    document = db.get(Document, document_id)
    if document is None or document.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if document.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document processing is not completed.",
        )

    if not document.silver_path or not document.gold_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Processed results are not available yet.",
        )

    try:
        silver_raw = storage_service.download_file("silver", document.silver_path)
        gold_raw = storage_service.download_file("gold", document.gold_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to download result payloads: {exc}",
        ) from exc

    try:
        silver_payload: dict[str, Any] = json.loads(silver_raw.decode("utf-8"))
        gold_payload: dict[str, Any] = json.loads(gold_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid result payload format: {exc}",
        ) from exc

    fields: dict[str, Any] = {}
    if isinstance(silver_payload, dict):
        normalized = silver_payload.get("normalized")
        if isinstance(normalized, dict):
            fields = normalized
        else:
            candidate = silver_payload.get("fields")
            if isinstance(candidate, dict):
                fields = candidate

    anomalies: list[str] = []
    if isinstance(gold_payload, dict):
        raw_anomalies = gold_payload.get("anomalies", [])
        if isinstance(raw_anomalies, list):
            anomalies = [str(item) for item in raw_anomalies]

    amounts = _as_float_list(fields.get("montants", fields.get("amounts", [])))

    fraud_score = float(document.fraud_score or 0.0)
    if isinstance(gold_payload, dict) and gold_payload.get("fraud_score") is not None:
        try:
            fraud_score = float(gold_payload["fraud_score"])
        except (TypeError, ValueError):
            pass

    document_type = document.document_type or "unknown"
    if isinstance(silver_payload, dict):
        raw_document_type = silver_payload.get("document_type")
        if isinstance(raw_document_type, str) and raw_document_type:
            document_type = raw_document_type
    if isinstance(gold_payload, dict):
        raw_document_type = gold_payload.get("document_type")
        if isinstance(raw_document_type, str) and raw_document_type:
            document_type = raw_document_type

    bundle_crosscheck_status: str | None = None
    bundle_anomalies: list[str] = []
    if isinstance(gold_payload, dict):
        raw_status = gold_payload.get("bundle_crosscheck_status")
        if isinstance(raw_status, str) and raw_status:
            bundle_crosscheck_status = raw_status
        bundle_anomalies = _as_string_list(gold_payload.get("bundle_anomalies", []))

    bundle_id = document.bundle_id
    if bundle_id is not None and bundle_crosscheck_status is None:
        crosscheck_path = f"gold/{bundle_id}/crosscheck.json"
        try:
            crosscheck_raw = storage_service.download_file("gold", crosscheck_path)
            crosscheck_payload = json.loads(crosscheck_raw.decode("utf-8"))
            if isinstance(crosscheck_payload, dict):
                raw_status = crosscheck_payload.get("bundle_status")
                if isinstance(raw_status, str) and raw_status:
                    bundle_crosscheck_status = raw_status
                bundle_anomalies = _as_string_list(crosscheck_payload.get("anomalies", []))
        except Exception:
            pass

    return DocumentResultResponse(
        document_id=document.id,
        document_type=document_type,
        bundle_id=bundle_id,
        bundle_crosscheck_status=bundle_crosscheck_status,
        bundle_anomalies=bundle_anomalies,
        status=document.status,
        fraud_score=fraud_score,
        silver_path=document.silver_path,
        gold_path=document.gold_path,
        fields=fields,
        anomalies=anomalies,
        amounts=amounts,
    )
