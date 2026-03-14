from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document_bundle import DocumentBundle
from app.models.tenant import Tenant
from app.schemas.bundle import BundleResultsResponse, BundleSummaryResponse
from app.security.tenant_context import get_current_tenant
from app.services.storage_service import storage_service


router = APIRouter()


@router.get("/{bundle_id}/results", response_model=BundleResultsResponse)
def get_bundle_results(
    bundle_id: UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> BundleResultsResponse:
    bundle = db.get(DocumentBundle, bundle_id)
    if bundle is None or bundle.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found.",
        )

    crosscheck_path = f"gold/{bundle.id}/crosscheck.json"
    try:
        crosscheck_raw = storage_service.download_file("gold", crosscheck_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bundle cross-check results are not available yet: {exc}",
        ) from exc

    try:
        payload = json.loads(crosscheck_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid bundle cross-check payload format: {exc}",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid bundle cross-check payload format.",
        )

    bundle_status = str(payload.get("bundle_status", "unknown"))
    anomalies_raw = payload.get("anomalies", [])
    anomalies = [str(item) for item in anomalies_raw] if isinstance(anomalies_raw, list) else []

    summary_payload = payload.get("summary", {})
    if not isinstance(summary_payload, dict):
        summary_payload = {}
    raw_document_count = summary_payload.get("document_count", 0)
    try:
        document_count = int(raw_document_count)
    except (TypeError, ValueError):
        document_count = 0
    document_types_raw = summary_payload.get("document_types", [])
    document_types = (
        [str(item) for item in document_types_raw]
        if isinstance(document_types_raw, list)
        else []
    )

    return BundleResultsResponse(
        bundle_id=bundle.id,
        name=bundle.name,
        reference=bundle.reference,
        bundle_status=bundle_status,
        anomalies=anomalies,
        summary=BundleSummaryResponse(
            document_count=document_count,
            document_types=document_types,
        ),
        crosscheck_path=crosscheck_path,
    )
