import sys
from pathlib import Path

_VENV_PY = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"

try:
    import sqlalchemy  # noqa: F401
except ModuleNotFoundError:
    sys.exit(
        "sqlalchemy is not installed for this interpreter:\n"
        f"  {sys.executable}\n\n"
        "Use the project venv (Python 3.12):\n"
        f"  {_VENV_PY} web_server.py\n"
        "In PyCharm: Settings → Project → Python Interpreter → "
        r".venv\Scripts\python.exe"
    )

from watchapi.config import settings
from watchapi.main import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "watchapi.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
