from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from watchapi.db import FindingRow, ScanRow, WatchRow
from watchapi.models import Finding, FindingStatus, Scan, ScanStatus, Watch


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _watch(row: WatchRow) -> Watch:
    return Watch(id=row.id, query=row.query, created_at=row.created_at)


def _scan(row: ScanRow, finding_count: int = 0) -> Scan:
    return Scan(
        id=row.id,
        watch_id=row.watch_id,
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
        error=row.error,
        finding_count=finding_count,
    )


def _finding(row: FindingRow) -> Finding:
    return Finding(
        id=row.id,
        watch_id=row.watch_id,
        scan_id=row.scan_id,
        title=row.title,
        url=row.url,
        snippet=row.snippet,
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
    )


class WatchStore(Protocol):
    async def create_watch(self, query: str) -> Watch: ...

    async def list_watches(self) -> list[Watch]: ...

    async def get_watch(self, watch_id: str) -> Watch | None: ...

    async def create_scan(self, watch_id: str) -> Scan: ...

    async def get_scan(self, scan_id: str) -> Scan | None: ...

    async def set_scan_status(
        self, scan_id: str, status: ScanStatus, error: str | None = None
    ) -> Scan | None: ...

    async def add_finding(
        self, *, watch_id: str, scan_id: str, title: str, url: str, snippet: str
    ) -> Finding: ...

    async def list_findings(
        self,
        *,
        watch_id: str | None = None,
        scan_id: str | None = None,
        status: FindingStatus | None = None,
    ) -> list[Finding]: ...

    async def get_finding(self, finding_id: str) -> Finding | None: ...

    async def set_finding_status(
        self, finding_id: str, status: FindingStatus
    ) -> Finding | None: ...

    async def denied_urls(self, watch_id: str) -> set[str]: ...

    async def stats(self) -> dict[str, int]: ...


class SqlStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def create_watch(self, query: str) -> Watch:
        async with self._sessions() as session:
            row = WatchRow(id=uuid4().hex, query=query.strip(), created_at=_utcnow())
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _watch(row)

    async def list_watches(self) -> list[Watch]:
        async with self._sessions() as session:
            rows = (await session.scalars(select(WatchRow).order_by(WatchRow.created_at))).all()
            return [_watch(row) for row in rows]

    async def get_watch(self, watch_id: str) -> Watch | None:
        async with self._sessions() as session:
            row = await session.get(WatchRow, watch_id)
            return _watch(row) if row else None

    async def create_scan(self, watch_id: str) -> Scan:
        async with self._sessions() as session:
            row = ScanRow(
                id=uuid4().hex,
                watch_id=watch_id,
                status="queued",
                created_at=_utcnow(),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _scan(row)

    async def get_scan(self, scan_id: str) -> Scan | None:
        async with self._sessions() as session:
            row = await session.get(ScanRow, scan_id)
            if row is None:
                return None
            count = await session.scalar(
                select(func.count()).select_from(FindingRow).where(FindingRow.scan_id == scan_id)
            )
            return _scan(row, int(count or 0))

    async def set_scan_status(
        self, scan_id: str, status: ScanStatus, error: str | None = None
    ) -> Scan | None:
        async with self._sessions() as session:
            row = await session.get(ScanRow, scan_id)
            if row is None:
                return None
            row.status = status
            row.error = error
            await session.commit()
            await session.refresh(row)
            count = await session.scalar(
                select(func.count()).select_from(FindingRow).where(FindingRow.scan_id == scan_id)
            )
            return _scan(row, int(count or 0))

    async def add_finding(
        self, *, watch_id: str, scan_id: str, title: str, url: str, snippet: str
    ) -> Finding:
        async with self._sessions() as session:
            row = FindingRow(
                id=uuid4().hex,
                watch_id=watch_id,
                scan_id=scan_id,
                title=title,
                url=url,
                snippet=snippet,
                status="pending",
                created_at=_utcnow(),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _finding(row)

    async def list_findings(
        self,
        *,
        watch_id: str | None = None,
        scan_id: str | None = None,
        status: FindingStatus | None = None,
    ) -> list[Finding]:
        async with self._sessions() as session:
            stmt = select(FindingRow).order_by(FindingRow.created_at)
            if watch_id:
                stmt = stmt.where(FindingRow.watch_id == watch_id)
            if scan_id:
                stmt = stmt.where(FindingRow.scan_id == scan_id)
            if status:
                stmt = stmt.where(FindingRow.status == status)
            rows = (await session.scalars(stmt)).all()
            return [_finding(row) for row in rows]

    async def get_finding(self, finding_id: str) -> Finding | None:
        async with self._sessions() as session:
            row = await session.get(FindingRow, finding_id)
            return _finding(row) if row else None

    async def set_finding_status(
        self, finding_id: str, status: FindingStatus
    ) -> Finding | None:
        async with self._sessions() as session:
            row = await session.get(FindingRow, finding_id)
            if row is None:
                return None
            row.status = status
            await session.commit()
            await session.refresh(row)
            return _finding(row)

    async def denied_urls(self, watch_id: str) -> set[str]:
        async with self._sessions() as session:
            rows = (
                await session.scalars(
                    select(FindingRow.url).where(
                        FindingRow.watch_id == watch_id,
                        FindingRow.status == "denied",
                    )
                )
            ).all()
            return set(rows)

    async def stats(self) -> dict[str, int]:
        async with self._sessions() as session:
            watches = await session.scalar(select(func.count()).select_from(WatchRow))
            scans = await session.scalar(select(func.count()).select_from(ScanRow))
            pending = await session.scalar(
                select(func.count()).select_from(FindingRow).where(FindingRow.status == "pending")
            )
            approved = await session.scalar(
                select(func.count()).select_from(FindingRow).where(FindingRow.status == "approved")
            )
            denied = await session.scalar(
                select(func.count()).select_from(FindingRow).where(FindingRow.status == "denied")
            )
            return {
                "watches": int(watches or 0),
                "scans": int(scans or 0),
                "pending": int(pending or 0),
                "approved": int(approved or 0),
                "denied": int(denied or 0),
            }
