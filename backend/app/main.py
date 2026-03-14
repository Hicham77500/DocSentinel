import logging

from fastapi import Depends, FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.metrics.metrics import api_requests_total, safe_inc
from app.routes.admin import router as admin_router
from app.routes.admin_recovery import router as admin_recovery_router
from app.routes.billing import router as billing_router
from app.routes.bundles import router as bundles_router
from app.routes.health import router as health_router
from app.routes.results import router as results_router
from app.routes.status import router as status_router
from app.routes.upload import router as upload_router
from app.routes.usage import router as usage_router
from app.security.admin_auth import require_admin_token


app = FastAPI(title="DocSentinel", version="0.1.0")
logger = logging.getLogger(__name__)


@app.on_event("startup")
def on_startup() -> None:
    logger.info(
        "Automatic schema creation is disabled. Ensure Alembic migrations are applied."
    )


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    safe_inc(api_requests_total)
    return await call_next(request)


@app.get("/metrics")
def metrics(_: None = Depends(require_admin_token)) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(health_router)
app.include_router(upload_router, prefix="/documents", tags=["documents"])
app.include_router(status_router, prefix="/documents", tags=["documents"])
app.include_router(results_router, prefix="/documents", tags=["documents"])
app.include_router(bundles_router, prefix="/bundles", tags=["bundles"])
app.include_router(usage_router, prefix="/usage", tags=["usage"])
app.include_router(billing_router, prefix="/billing", tags=["billing"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(admin_recovery_router, prefix="/admin/recovery", tags=["admin"])
