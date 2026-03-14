from fastapi import Depends, FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.db.base import Base
from app.db.session import engine
from app.metrics.metrics import api_requests_total, safe_inc
from app.models.api_key import ApiKey
from app.models.document import Document
from app.models.document_bundle import DocumentBundle
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.tenant import Tenant
from app.models.usage_event import UsageEvent
from app.routes.admin import router as admin_router
from app.routes.billing import router as billing_router
from app.routes.bundles import router as bundles_router
from app.routes.health import router as health_router
from app.routes.results import router as results_router
from app.routes.status import router as status_router
from app.routes.upload import router as upload_router
from app.routes.usage import router as usage_router
from app.security.tenant_context import get_current_tenant


app = FastAPI(title="DocSentinel", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Plan.__table__,
            Tenant.__table__,
            Subscription.__table__,
            ApiKey.__table__,
            DocumentBundle.__table__,
            Document.__table__,
            UsageEvent.__table__,
        ],
    )


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    safe_inc(api_requests_total)
    return await call_next(request)


@app.get("/metrics")
def metrics(_: Tenant = Depends(get_current_tenant)) -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(health_router)
app.include_router(upload_router, prefix="/documents", tags=["documents"])
app.include_router(status_router, prefix="/documents", tags=["documents"])
app.include_router(results_router, prefix="/documents", tags=["documents"])
app.include_router(bundles_router, prefix="/bundles", tags=["bundles"])
app.include_router(usage_router, prefix="/usage", tags=["usage"])
app.include_router(billing_router, prefix="/billing", tags=["billing"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
