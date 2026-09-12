# Research Watch

An async FastAPI service for **background research scans**, **SSE progress**, and a **human review queue**.

The books catalog showed typed CRUD. This one shows the next layer: a job you start, watch live, then judge. HTTP depends on two protocols — `WatchStore` and `Finder` — so SQLite and the dummy finder are implementations, not the API.

No live scraping in the default finder. `DummyFinder` returns deterministic `example.com` hits so demos and CI stay offline. A real HTTP finder would implement the same protocol. Denied URLs are skipped on the next scan for that watch.

## What it shows

- App factory + `Depends()` for store, finder, and an in-process scan hub
- SQLAlchemy 2 **async** + SQLite (`aiosqlite`)
- `POST /watches/{id}/scans` returns **202** and runs the job on the event loop
- `GET /scans/{id}/events` is **SSE** (`scan.started`, `scan.finding`, `scan.completed`)
- Review: pending → approve / deny
- Tests use a temp DB and never touch the network

Swap SQLite for Postgres by changing `WATCH_DATABASE_URL`. Swap the in-process hub for Redis pub/sub if you have more than one worker. A later classifier (SpaceXAI / `XAI_API_KEY`) can sit behind the same finding pipeline without changing routes.

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/watches/` | Create a watch (`query`) |
| `GET` | `/watches/` | List watches |
| `GET` | `/watches/{id}` | Fetch one |
| `POST` | `/watches/{id}/scans` | Start a scan (202) |
| `GET` | `/scans/{id}` | Scan status |
| `GET` | `/scans/{id}/events` | SSE progress |
| `GET` | `/findings/?status=` | Review queue |
| `POST` | `/findings/{id}/approve` | Keep |
| `POST` | `/findings/{id}/deny` | Drop (blocked on later scans) |
| `GET` | `/stats` | Counts |

`GET /` redirects to `/docs`. Default port **8001** so it can sit next to the book catalog.

## Run

Python 3.12+.

```
python -m venv .venv
```

Windows: `.venv\Scripts\activate`  
macOS/Linux: `source .venv/bin/activate`

```
pip install -e ".[dev]"
python web_server.py
```

Or `uvicorn watchapi.main:app --reload --port 8001`. Open http://127.0.0.1:8001/docs

Create a watch, start a scan, then open `/scans/{id}/events` or poll `/findings/`.

## Tests

```
pytest
pytest --cov=watchapi --cov-report=term-missing
```
