from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ScanStatus = Literal["queued", "running", "completed", "failed"]
FindingStatus = Literal["pending", "approved", "denied"]


@dataclass(slots=True)
class Watch:
    id: str
    query: str
    created_at: datetime


@dataclass(slots=True)
class Scan:
    id: str
    watch_id: str
    status: ScanStatus
    created_at: datetime
    error: str | None = None
    finding_count: int = 0


@dataclass(slots=True)
class Finding:
    id: str
    watch_id: str
    scan_id: str
    title: str
    url: str
    snippet: str
    status: FindingStatus
    created_at: datetime


@dataclass(slots=True)
class Candidate:
    title: str
    url: str
    snippet: str


@dataclass(slots=True)
class ScanEvent:
    type: Literal["scan.started", "scan.finding", "scan.completed", "scan.failed"]
    scan_id: str
    payload: dict = field(default_factory=dict)
