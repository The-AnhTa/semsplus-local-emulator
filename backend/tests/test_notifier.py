import json

from app.notifier import OpenClawNotifier


class FakeResponse:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_openclaw_notification_uses_backend_bearer_token(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    notifier = OpenClawNotifier(
        hook_url="http://127.0.0.1:18789/hooks/wake",
        hook_token="dedicated-secret",
        controller_agent="controller",
        timeout_seconds=1.5,
    )
    result = notifier.notify_control_request("CR-000001", "STOP", "INV-TEST-001")

    assert result.delivered is True
    assert captured["timeout"] == 1.5
    assert captured["request"].get_header("Authorization") == "Bearer dedicated-secret"
    payload = json.loads(captured["request"].data)
    assert payload == {
        "text": "CONTROL_REQUEST request_id=CR-000001 action=STOP device=INV-TEST-001 status=PENDING",
        "mode": "now",
        "agentId": "controller",
    }
