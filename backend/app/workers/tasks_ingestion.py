import json
import logging
from pathlib import Path
import tempfile
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.session import SessionLocal
from app.metrics.metrics import (
    bundle_crosschecks_total,
    documents_classified_total,
    documents_failed_total,
    documents_processed_total,
    ocr_failures_total,
    ocr_requests_total,
    pipeline_retry_total,
    safe_inc,
)
from app.models.document import Document
from app.services.audit_service import log_event
from app.services.classifier import classify_document
from app.services.crosscheck_service import cross_check_documents
from app.services.extractor import extract_fields
from app.services.fraud_detector import compute_fraud_score
from app.services.normalizer import normalize_fields
from app.services.ocr_engine import extract_text
from app.services.storage_service import storage_service
from app.services.usage_service import record_usage_event
from app.workers.celery_app import celery_app
from app.workers.retry_policies import MAX_BACKOFF, MAX_RETRIES, compute_backoff


logger = logging.getLogger(__name__)


def _mark_document_failed(document_id: str) -> None:
    db = SessionLocal()
    try:
        parsed_id = UUID(document_id)
        document = db.get(Document, parsed_id)
        if document is None:
            return

        document.status = "failed"
        db.add(document)
        db.commit()
        safe_inc(documents_failed_total)
        log_event(
            event="pipeline_failure",
            tenant_id=str(document.tenant_id),
            document_id=str(document.id),
            status=document.status,
            fraud_score=document.fraud_score,
        )
    except Exception:
        logger.exception(
            "Failed to update document to failed status after retry exhaustion: %s",
            document_id,
        )
    finally:
        db.close()


def _load_json_payload(bucket: str, path: str) -> dict | None:
    try:
        payload_raw = storage_service.download_file(bucket=bucket, object_name=path)
        payload = json.loads(payload_raw.decode("utf-8"))
    except Exception:
        logger.exception("Failed to read JSON payload from storage: %s/%s", bucket, path)
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _run_bundle_crosscheck(db: Session, document: Document) -> None:
    if document.bundle_id is None:
        return

    completed_documents = db.execute(
        select(Document).where(
            Document.bundle_id == document.bundle_id,
            Document.tenant_id == document.tenant_id,
            Document.status == "completed",
            Document.silver_path.is_not(None),
            Document.gold_path.is_not(None),
        )
    ).scalars().all()
    if not completed_documents:
        return

    crosscheck_inputs: list[dict] = []
    for item in completed_documents:
        if not item.silver_path:
            continue
        silver_payload = _load_json_payload(bucket="silver", path=item.silver_path)
        if silver_payload is None:
            continue

        normalized = silver_payload.get("normalized")
        if not isinstance(normalized, dict):
            normalized = {}

        document_type = item.document_type or str(silver_payload.get("document_type") or "unknown")
        crosscheck_inputs.append(
            {
                "document_id": str(item.id),
                "document_type": document_type,
                "normalized": normalized,
            }
        )

    if not crosscheck_inputs:
        return

    crosscheck_result = cross_check_documents(crosscheck_inputs)
    crosscheck_result["bundle_id"] = str(document.bundle_id)

    crosscheck_path = f"gold/{document.bundle_id}/crosscheck.json"
    storage_service.upload_file(
        bucket="gold",
        object_name=crosscheck_path,
        file_bytes=json.dumps(crosscheck_result, ensure_ascii=False, indent=2).encode("utf-8"),
    )

    bundle_status = str(crosscheck_result.get("bundle_status", "unknown"))
    bundle_anomalies_raw = crosscheck_result.get("anomalies", [])
    bundle_anomalies = [str(item) for item in bundle_anomalies_raw] if isinstance(bundle_anomalies_raw, list) else []

    for item in completed_documents:
        if not item.gold_path:
            continue
        gold_payload = _load_json_payload(bucket="gold", path=item.gold_path) or {}
        gold_payload["bundle_id"] = str(document.bundle_id)
        gold_payload["bundle_crosscheck_status"] = bundle_status
        gold_payload["bundle_anomalies"] = bundle_anomalies
        storage_service.upload_file(
            bucket="gold",
            object_name=item.gold_path,
            file_bytes=json.dumps(gold_payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    safe_inc(bundle_crosschecks_total)
    log_event(
        event="bundle_crosscheck_completed",
        tenant_id=str(document.tenant_id),
        document_id="",
        status=bundle_status,
        bundle_id=str(document.bundle_id),
        anomaly_count=len(bundle_anomalies),
    )


@celery_app.task(
    bind=True,
    name="app.workers.tasks_ingestion.start_document_pipeline",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=MAX_BACKOFF,
    retry_jitter=True,
    max_retries=MAX_RETRIES,
)
def start_document_pipeline(self, document_id: str) -> None:
    db = SessionLocal()
    document: Document | None = None
    try:
        parsed_id = UUID(document_id)
        document = db.get(Document, parsed_id)
        if document is None:
            return

        document.status = "processing"
        db.add(document)
        db.commit()
        log_event(
            event="pipeline_start",
            tenant_id=str(document.tenant_id),
            document_id=str(document.id),
            status=document.status,
            fraud_score=document.fraud_score,
        )

        raw_bytes = storage_service.download_file(
            bucket=settings.MINIO_RAW_BUCKET,
            object_name=document.raw_path,
        )

        suffix = Path(document.original_filename).suffix or ".bin"
        with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp_file:
            tmp_file.write(raw_bytes)
            tmp_file.flush()
            safe_inc(ocr_requests_total)
            try:
                extracted_text = extract_text(tmp_file.name)
            except Exception:
                safe_inc(ocr_failures_total)
                raise

        if not extracted_text:
            safe_inc(ocr_failures_total)
            raise RuntimeError("OCR extraction failed or returned empty text.")

        bronze_bucket = "bronze"
        bronze_path = f"bronze/{document.id}/ocr.txt"
        storage_service.upload_file(
            bucket=bronze_bucket,
            object_name=bronze_path,
            file_bytes=extracted_text.encode("utf-8"),
        )

        document.bronze_path = bronze_path
        document.status = "ocr_done"
        db.add(document)
        db.commit()

        document.document_type = classify_document(extracted_text, document.original_filename)
        db.add(document)
        db.commit()
        safe_inc(documents_classified_total)
        log_event(
            event="document_classified",
            tenant_id=str(document.tenant_id),
            document_id=str(document.id),
            status=document.status,
            document_type=document.document_type,
        )

        record_usage_event(
            tenant_id=str(document.tenant_id),
            event_type="ocr_processed",
            units=1,
            document_id=str(document.id),
        )

        extracted_data = extract_fields(extracted_text)
        document.status = "extracted"
        db.add(document)
        db.commit()

        normalized_data = normalize_fields(extracted_data)
        document.status = "normalized"
        db.add(document)
        db.commit()

        fraud_score, anomalies = compute_fraud_score(normalized_data)
        document.fraud_score = fraud_score
        document.status = "fraud_checked"
        db.add(document)
        db.commit()
        record_usage_event(
            tenant_id=str(document.tenant_id),
            event_type="fraud_scored",
            units=1,
            document_id=str(document.id),
        )
        log_event(
            event="fraud_detection_result",
            tenant_id=str(document.tenant_id),
            document_id=str(document.id),
            status=document.status,
            fraud_score=document.fraud_score,
        )

        silver_bucket = "silver"
        silver_path = f"silver/{document.id}/fields.json"
        silver_payload = {
            "document_id": str(document.id),
            "document_type": document.document_type,
            "raw_path": document.raw_path,
            "bronze_path": document.bronze_path,
            "extracted": extracted_data,
            "normalized": normalized_data,
        }
        storage_service.upload_file(
            bucket=silver_bucket,
            object_name=silver_path,
            file_bytes=json.dumps(silver_payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )

        gold_bucket = "gold"
        gold_path = f"gold/{document.id}/fraud.json"
        gold_payload = {
            "document_id": str(document.id),
            "document_type": document.document_type,
            "fraud_score": fraud_score,
            "anomalies": anomalies,
            "normalized": normalized_data,
        }
        storage_service.upload_file(
            bucket=gold_bucket,
            object_name=gold_path,
            file_bytes=json.dumps(gold_payload, ensure_ascii=False, indent=2).encode("utf-8"),
        )

        document.silver_path = silver_path
        document.gold_path = gold_path
        document.status = "completed"
        db.add(document)
        db.commit()
        safe_inc(documents_processed_total)

        if document.bundle_id is not None:
            try:
                _run_bundle_crosscheck(db, document)
            except Exception:
                logger.exception("Bundle cross-check failed for document %s", document_id)

        log_event(
            event="pipeline_completion",
            tenant_id=str(document.tenant_id),
            document_id=str(document.id),
            status=document.status,
            fraud_score=document.fraud_score,
        )
    except Exception:
        retry_count = int(getattr(self.request, "retries", 0))
        if retry_count < MAX_RETRIES:
            safe_inc(pipeline_retry_total)
            logger.warning(
                json.dumps(
                    {
                        "event": "pipeline_retry",
                        "document_id": document_id,
                        "retry": retry_count + 1,
                        "backoff_seconds": compute_backoff(retry_count + 1),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            _mark_document_failed(document_id)
        raise
    finally:
        db.close()
