from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from watchapi.dependencies import get_finder, get_hub, get_store
from watchapi.finders import Finder
from watchapi.hub import ScanHub
from watchapi.models import FindingStatus
from watchapi.runner import run_scan
from watchapi.schemas import (
    CreateWatchRequest,
    FindingListResponse,
    FindingResponse,
    ScanResponse,
    StatsResponse,
    WatchResponse,
)
from watchapi.store import WatchStore

router = APIRouter()
TERMINAL = {"completed", "failed"}


def _track_task(request: Request, task: asyncio.Task) -> None:
    tasks: set[asyncio.Task] = request.app.state.tasks
    tasks.add(task)
    task.add_done_callback(tasks.discard)


@router.post("/watches/", status_code=status.HTTP_201_CREATED, response_model=WatchResponse, tags=["watches"])
async def create_watch(
    payload: CreateWatchRequest,
    store: Annotated[WatchStore, Depends(get_store)],
) -> Watch:
    return await store.create_watch(payload.query)


@router.get("/watches/", response_model=list[WatchResponse], tags=["watches"])
async def list_watches(store: Annotated[WatchStore, Depends(get_store)]) -> list:
    return await store.list_watches()


@router.get("/watches/{watch_id}", response_model=WatchResponse, tags=["watches"])
async def get_watch(
    watch_id: str,
    store: Annotated[WatchStore, Depends(get_store)],
) -> Watch:
    watch = await store.get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found")
    return watch


@router.post(
    "/watches/{watch_id}/scans",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ScanResponse,
    tags=["scans"],
)
async def start_scan(
    watch_id: str,
    request: Request,
    store: Annotated[WatchStore, Depends(get_store)],
    finder: Annotated[Finder, Depends(get_finder)],
    hub: Annotated[ScanHub, Depends(get_hub)],
) -> Scan:
    watch = await store.get_watch(watch_id)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found")
    scan = await store.create_scan(watch_id)
    task = asyncio.create_task(run_scan(scan.id, store, finder, hub))
    _track_task(request, task)
    return scan


@router.get("/scans/{scan_id}", response_model=ScanResponse, tags=["scans"])
async def get_scan(
    scan_id: str,
    store: Annotated[WatchStore, Depends(get_store)],
) -> Scan:
    scan = await store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/scans/{scan_id}/events", tags=["scans"], summary="SSE scan progress")
async def scan_events(
    scan_id: str,
    store: Annotated[WatchStore, Depends(get_store)],
    hub: Annotated[ScanHub, Depends(get_hub)],
) -> StreamingResponse:
    scan = await store.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    async def stream():
        if scan.status in TERMINAL:
            yield _sse("scan.started", {"scan_id": scan_id, "watch_id": scan.watch_id})
            findings = await store.list_findings(scan_id=scan_id)
            for finding in findings:
                yield _sse(
                    "scan.finding",
                    {
                        "id": finding.id,
                        "title": finding.title,
                        "url": finding.url,
                        "snippet": finding.snippet,
                    },
                )
            if scan.status == "failed":
                yield _sse("scan.failed", {"scan_id": scan_id, "error": scan.error})
            else:
                yield _sse("scan.completed", {"scan_id": scan_id, "count": len(findings)})
            return

        queue = hub.subscribe(scan_id)
        try:
            while True:
                event = await queue.get()
                body = {"scan_id": event.scan_id, **event.payload}
                yield _sse(event.type, body)
                if event.type in {"scan.completed", "scan.failed"}:
                    break
        finally:
            hub.unsubscribe(scan_id, queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/findings/", response_model=FindingListResponse, tags=["findings"])
async def list_findings(
    store: Annotated[WatchStore, Depends(get_store)],
    status_filter: Annotated[
        FindingStatus | None,
        Query(alias="status", description="pending, approved, or denied"),
    ] = None,
    watch_id: str | None = None,
    scan_id: str | None = None,
) -> FindingListResponse:
    findings = await store.list_findings(
        watch_id=watch_id, scan_id=scan_id, status=status_filter
    )
    return FindingListResponse(
        findings=[FindingResponse.model_validate(item) for item in findings]
    )


@router.post(
    "/findings/{finding_id}/approve",
    response_model=FindingResponse,
    tags=["findings"],
)
async def approve_finding(
    finding_id: str,
    store: Annotated[WatchStore, Depends(get_store)],
) -> Finding:
    finding = await store.set_finding_status(finding_id, "approved")
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.post(
    "/findings/{finding_id}/deny",
    response_model=FindingResponse,
    tags=["findings"],
)
async def deny_finding(
    finding_id: str,
    store: Annotated[WatchStore, Depends(get_store)],
) -> Finding:
    finding = await store.set_finding_status(finding_id, "denied")
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return finding


@router.get("/stats", response_model=StatsResponse, tags=["stats"])
async def stats(store: Annotated[WatchStore, Depends(get_store)]) -> dict:
    return await store.stats()
