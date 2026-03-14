from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentStatusResponse(BaseModel):
    id: UUID
    status: str
    document_type: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
