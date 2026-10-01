import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.notifier import NotificationResult


class UnavailableNotifier:
    def notify_control_request(self, request_id: str, action: str, device_id: str) -> NotificationResult:
        return NotificationResult(delivered=False, reason="test OpenClaw CLI unavailable")


@pytest.fixture
def client(tmp_path):
    app = create_app(
        str(tmp_path / "test.db"),
        transition_delay=0,
        notifier=UnavailableNotifier(),
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def expired_client(tmp_path):
    app = create_app(
        str(tmp_path / "expired.db"),
        transition_delay=0,
        control_request_ttl_seconds=-1,
        notifier=UnavailableNotifier(),
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unavailable_openclaw_client(tmp_path):
    app = create_app(
        str(tmp_path / "unavailable.db"),
        transition_delay=0,
        notifier=UnavailableNotifier(),
    )
    with TestClient(app) as test_client:
        yield test_client
