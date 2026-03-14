from app.workers.celery_app import celery_app


def enqueue_document_pipeline(document_id: str) -> str:
    async_result = celery_app.send_task(
        "app.workers.tasks_ingestion.start_document_pipeline",
        args=[document_id],
    )
    return async_result.id
