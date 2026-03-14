from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.tenant import Tenant
from app.schemas.status import DocumentStatusResponse
from app.security.tenant_context import get_current_tenant


router = APIRouter()


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_document_status(
    document_id: UUID,
    db: Session = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
) -> DocumentStatusResponse:
    document = db.get(Document, document_id)
    if document is None or document.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return DocumentStatusResponse.model_validate(document)
