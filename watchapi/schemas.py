from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateWatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(..., min_length=1, max_length=300, examples=["stoic cosmology"])


class WatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query: str
    created_at: datetime


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    watch_id: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: datetime
    error: str | None = None
    finding_count: int = 0


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    watch_id: str
    scan_id: str
    title: str
    url: str
    snippet: str
    status: Literal["pending", "approved", "denied"]
    created_at: datetime


class FindingListResponse(BaseModel):
    findings: list[FindingResponse]


class StatsResponse(BaseModel):
    watches: int
    scans: int
    pending: int
    approved: int
    denied: int
