from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from watchapi.config import DATA_DIR, settings
from watchapi.db import Base, make_engine, make_session_factory
from watchapi.finders import DummyFinder, Finder
from watchapi.hub import ScanHub
from watchapi.routers import router
from watchapi.store import SqlStore, WatchStore


def create_app(
    *,
    database_url: str | None = None,
    finder: Finder | None = None,
    store: WatchStore | None = None,
) -> FastAPI:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = make_engine(database_url or settings.database_url)
    sessions = make_session_factory(engine)
    app_store = store or SqlStore(sessions)
    app_finder = finder or DummyFinder()
    hub = ScanHub()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.state.store = app_store
        app.state.finder = app_finder
        app.state.hub = hub
        app.state.tasks = set()
        yield
        await engine.dispose()

    app = FastAPI(
        title="Research Watch",
        version="1.0.0",
        description=(
            "Background research scans with SSE progress and a human review queue. "
            "The HTTP layer depends on a store protocol and a finder protocol — "
            "SQLite and DummyFinder ship in-box; swap either without touching routes. "
            "Docs at **/docs**."
        ),
        lifespan=lifespan,
    )
    app.state.store = app_store
    app.state.finder = app_finder
    app.state.hub = hub
    app.state.engine = engine
    app.state.tasks = set()
    app.include_router(router)

    @app.get("/", include_in_schema=False)
    def home() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return app


app = create_app()
