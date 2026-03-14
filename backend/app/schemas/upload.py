from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UploadResponse(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    raw_path: str
    status: str

    model_config = ConfigDict(from_attributes=True)
