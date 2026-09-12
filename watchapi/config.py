from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WATCH_", extra="ignore")

    database_url: str = f"sqlite+aiosqlite:///{(DATA_DIR / 'watch.db').as_posix()}"
    host: str = "127.0.0.1"
    port: int = 8001
    reload: bool = True


settings = Settings()
