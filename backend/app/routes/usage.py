from fastapi import APIRouter, Depends

from app.models.tenant import Tenant
from app.security.tenant_context import get_current_tenant
from app.services.usage_service import get_monthly_usage


router = APIRouter()


@router.get("/current-month")
def get_current_month_usage(
    tenant: Tenant = Depends(get_current_tenant),
) -> dict[str, int | str]:
    usage = get_monthly_usage(str(tenant.id))
    return {
        "tenant_id": str(tenant.id),
        "uploaded_documents": int(usage["uploaded_documents"]),
        "api_requests": int(usage["api_requests"]),
        "ocr_processed": int(usage["ocr_processed"]),
        "fraud_scored": int(usage["fraud_scored"]),
        "monthly_document_quota": int(tenant.monthly_document_quota),
        "monthly_api_quota": int(tenant.monthly_api_quota),
    }
