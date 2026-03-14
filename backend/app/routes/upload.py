from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.session import get_db
from app.metrics.metrics import documents_uploaded_total, safe_inc
from app.models.document_bundle import DocumentBundle
from app.models.document import Document
from app.models.tenant import Tenant
from app.security.quota_enforcer import enforce_document_quota
from app.security.file_hash import compute_sha256
from app.schemas.upload import UploadResponse
from app.security.antivirus import scan_file
from app.security.file_validator import validate_file
from app.security.tenant_context import get_current_tenant
from app.services.audit_service import log_event
from app.services.pipeline_orchestrator import enqueue_document_pipeline
from app.services.storage_service import storage_service
from app.services.usage_service import record_usage_event


router = APIRouter()
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    bundle_reference: str | None = Form(default=None),
    bundle_name: str | None = Form(default=None),
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> UploadResponse:
    content = await file.read()

    file_hash = compute_sha256(content)
    existing_document = db.execute(
        select(Document).where(
            Document.tenant_id == tenant.id,
            Document.file_hash == file_hash,
        )
    ).scalar_one_or_none()
    if existing_document is not None:
        log_event(
            event="duplicate_document_upload",
            tenant_id=str(tenant.id),
            document_id=str(existing_document.id),
            status=existing_document.status,
            fraud_score=existing_document.fraud_score,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": "Duplicate document already uploaded",
                "document_id": str(existing_document.id),
            },
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds the 20MB size limit.",
        )

    enforce_document_quota(str(tenant.id))

    detected_mime = validate_file(content)
    scan_file(content)

    if file.content_type and file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Declared content type is not allowed.",
        )

    document_id = uuid.uuid4()
    filename = Path(file.filename or "document.bin").name
    raw_path = f"raw/{document_id}/{filename}"
    reference = (bundle_reference or "").strip()
    name = (bundle_name or "").strip()
    bundle: DocumentBundle | None = None
    if reference:
        bundle = db.execute(
            select(DocumentBundle).where(
                DocumentBundle.tenant_id == tenant.id,
                DocumentBundle.reference == reference,
            )
        ).scalar_one_or_none()
        if bundle is None:
            bundle = DocumentBundle(
                tenant_id=tenant.id,
                reference=reference,
                name=name or reference,
            )
            db.add(bundle)
            db.flush()

    try:
        storage_service.upload_file(
            bucket=settings.MINIO_RAW_BUCKET,
            object_name=raw_path,
            file_bytes=content,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Storage upload failed: {exc}",
        ) from exc

    document = Document(
        id=document_id,
        tenant_id=tenant.id,
        original_filename=filename,
        content_type=detected_mime,
        file_hash=file_hash,
        raw_path=raw_path,
        status="queued",
        bundle_id=bundle.id if bundle else None,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    log_event(
        event="document_upload",
        tenant_id=str(tenant.id),
        document_id=str(document.id),
        status=document.status,
        fraud_score=document.fraud_score,
    )

    enqueue_document_pipeline(str(document.id))
    record_usage_event(
        tenant_id=str(tenant.id),
        event_type="document_uploaded",
        units=1,
        document_id=str(document.id),
    )
    safe_inc(documents_uploaded_total)

    return UploadResponse.model_validate(document)
