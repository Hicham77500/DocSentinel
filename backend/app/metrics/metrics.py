from __future__ import annotations

import logging

from prometheus_client import Counter


logger = logging.getLogger(__name__)


documents_uploaded_total = Counter(
    "documents_uploaded_total",
    "Total number of uploaded documents.",
)
documents_processed_total = Counter(
    "documents_processed_total",
    "Total number of successfully processed documents.",
)
documents_classified_total = Counter(
    "documents_classified_total",
    "Total number of classified documents.",
)
bundle_crosschecks_total = Counter(
    "bundle_crosschecks_total",
    "Total number of bundle cross-check executions.",
)
documents_failed_total = Counter(
    "documents_failed_total",
    "Total number of failed document pipelines.",
)
pipeline_retry_total = Counter(
    "pipeline_retry_total",
    "Total number of pipeline retry attempts.",
)
stale_documents_recovered_total = Counter(
    "stale_documents_recovered_total",
    "Total number of stale documents recovered to failed status.",
)
pipeline_recovery_runs_total = Counter(
    "pipeline_recovery_runs_total",
    "Total number of stale document recovery runs.",
)
ocr_requests_total = Counter(
    "ocr_requests_total",
    "Total number of OCR requests sent by the worker.",
)
ocr_failures_total = Counter(
    "ocr_failures_total",
    "Total number of OCR failures.",
)
api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests.",
)


def safe_inc(counter: Counter, amount: float = 1.0) -> None:
    try:
        counter.inc(amount)
    except Exception:
        logger.exception("Failed to increment metric: %s", getattr(counter, "_name", "unknown"))
