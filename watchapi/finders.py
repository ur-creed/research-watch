from __future__ import annotations

from typing import Protocol
from urllib.parse import quote

from watchapi.models import Candidate, Watch


class Finder(Protocol):
    async def find(self, watch: Watch, *, blocked_urls: set[str]) -> list[Candidate]: ...


class DummyFinder:
    """Deterministic finder for local demos and tests. No network."""

    async def find(self, watch: Watch, *, blocked_urls: set[str]) -> list[Candidate]:
        slug = quote(watch.query.strip().lower().replace(" ", "-") or "research", safe="-")
        candidates = [
            Candidate(
                title=f"{watch.query}: overview",
                url=f"https://example.com/library/{slug}",
                snippet=f"A high-level survey of sources related to {watch.query}.",
            ),
            Candidate(
                title=f"{watch.query}: primary text",
                url=f"https://example.com/texts/{slug}",
                snippet=f"A primary-text excerpt used as a starting point for {watch.query}.",
            ),
            Candidate(
                title=f"{watch.query}: commentary",
                url=f"https://example.com/notes/{slug}",
                snippet=f"Notes and commentary adjacent to {watch.query}.",
            ),
        ]
        return [item for item in candidates if item.url not in blocked_urls]
