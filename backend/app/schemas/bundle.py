from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class BundleSummaryResponse(BaseModel):
    document_count: int
    document_types: list[str]


class BundleResultsResponse(BaseModel):
    bundle_id: UUID
    name: str
    reference: str
    bundle_status: str
    anomalies: list[str]
    summary: BundleSummaryResponse
    crosscheck_path: str
