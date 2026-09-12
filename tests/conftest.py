import pytest
from fastapi.testclient import TestClient

from watchapi.finders import DummyFinder
from watchapi.main import create_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    db_path = tmp_path / "watch.db"
    app = create_app(database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}", finder=DummyFinder())
    with TestClient(app) as test_client:
        yield test_client
