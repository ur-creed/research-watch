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
