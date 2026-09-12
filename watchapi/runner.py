from __future__ import annotations

import logging

from watchapi.finders import Finder
from watchapi.hub import ScanHub
from watchapi.models import ScanEvent
from watchapi.store import WatchStore

logger = logging.getLogger(__name__)


async def run_scan(
    scan_id: str,
    store: WatchStore,
    finder: Finder,
    hub: ScanHub,
) -> None:
    scan = await store.get_scan(scan_id)
    if scan is None:
        return
    watch = await store.get_watch(scan.watch_id)
    if watch is None:
        await store.set_scan_status(scan_id, "failed", error="watch not found")
        await hub.publish(ScanEvent(type="scan.failed", scan_id=scan_id, payload={"error": "watch not found"}))
        return

    await store.set_scan_status(scan_id, "running")
    await hub.publish(ScanEvent(type="scan.started", scan_id=scan_id, payload={"watch_id": watch.id}))

    try:
        blocked = await store.denied_urls(watch.id)
        candidates = await finder.find(watch, blocked_urls=blocked)
        for candidate in candidates:
            finding = await store.add_finding(
                watch_id=watch.id,
                scan_id=scan_id,
                title=candidate.title,
                url=candidate.url,
                snippet=candidate.snippet,
            )
            await hub.publish(
                ScanEvent(
                    type="scan.finding",
                    scan_id=scan_id,
                    payload={
                        "id": finding.id,
                        "title": finding.title,
                        "url": finding.url,
                        "snippet": finding.snippet,
                    },
                )
            )
        updated = await store.set_scan_status(scan_id, "completed")
        count = updated.finding_count if updated else len(candidates)
        await hub.publish(
            ScanEvent(type="scan.completed", scan_id=scan_id, payload={"count": count})
        )
    except Exception:
        logger.exception("Scan %s failed", scan_id)
        await store.set_scan_status(scan_id, "failed", error="scan failed")
        await hub.publish(
            ScanEvent(type="scan.failed", scan_id=scan_id, payload={"error": "scan failed"})
        )
