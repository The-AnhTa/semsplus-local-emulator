import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"), transition_delay=0)
    with TestClient(app) as test_client:
        yield test_client

