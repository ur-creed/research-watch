from __future__ import annotations

import asyncio

from watchapi.models import ScanEvent


class ScanHub:
    """In-process pub/sub for scan SSE. Swap for Redis pub/sub under load."""

    def __init__(self) -> None:
        self._subs: dict[str, list[asyncio.Queue[ScanEvent]]] = {}

    def subscribe(self, scan_id: str) -> asyncio.Queue[ScanEvent]:
        queue: asyncio.Queue[ScanEvent] = asyncio.Queue()
        self._subs.setdefault(scan_id, []).append(queue)
        return queue

    def unsubscribe(self, scan_id: str, queue: asyncio.Queue[ScanEvent]) -> None:
        listeners = self._subs.get(scan_id, [])
        if queue in listeners:
            listeners.remove(queue)
        if not listeners:
            self._subs.pop(scan_id, None)

    async def publish(self, event: ScanEvent) -> None:
        for queue in list(self._subs.get(event.scan_id, [])):
            await queue.put(event)
