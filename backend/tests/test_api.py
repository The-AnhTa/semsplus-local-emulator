import sqlite3

from fastapi.testclient import TestClient

from app.main import create_app
from app.models import ControlAction
from app.notifier import NotificationResult
from app.store import SimulatorStore


def test_login_is_local_and_deterministic(client):
    bad = client.post("/api/auth/login", json={"email": "wrong", "password": "wrong"})
    assert bad.status_code == 401

    good = client.post(
        "/api/auth/login",
        json={"email": "researcher@example.local", "password": "test-password"},
    )
    assert good.status_code == 200
    assert good.json()["accessToken"] == "local-research-session"


def test_device_transition_and_state_dependent_telemetry(client):
    running = client.get("/api/devices/device-test-001").json()
    assert running["status"] == "RUNNING"
    assert running["activePowerKw"] > 0

    requested = client.post(
        "/api/control/requests",
        json={"deviceId": "INV-TEST-001", "action": "STOP"},
    )
    assert requested.status_code == 202
    assert requested.json()["status"] == "PENDING"
    assert requested.json()["requestId"] == "CR-000001"
    assert client.get("/api/devices/device-test-001").json()["status"] == "RUNNING"

    stopped = client.post(
        f"/api/control/requests/{requested.json()['requestId']}/approve",
        json={"decisionSource": "test-controller"},
    )
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "EXECUTED"
    assert client.get("/api/devices/device-test-001").json()["status"] == "OFFLINE"
    events = client.get("/api/admin/events").json()
    approved = next(event for event in events if event["action"] == "CONTROL_REQUEST_APPROVED")
    executed = next(event for event in events if event["action"] == "CONTROL_REQUEST_EXECUTED")
    for event in (approved, executed):
        assert event["timestamp"]
        assert event["controlRequestId"] == requested.json()["requestId"]
        assert event["deviceId"] == "INV-TEST-001"
        assert event["controlAction"] == "STOP"
        assert event["decisionSource"] == "test-controller"
        assert event["previousState"] == "RUNNING"
    assert executed["resultingState"] == "OFFLINE"
    telemetry = client.get("/api/devices/device-test-001/telemetry").json()
    assert telemetry["activePowerKw"] == 0
    assert telemetry["phaseACurrent"] == 0

    started = client.post("/api/devices/device-test-001/start")
    assert started.status_code == 200
    assert started.json()["status"] == "RUNNING"


def test_illegal_transition_is_explicit_and_audited(client):
    response = client.post("/api/devices/device-test-001/start")
    assert response.status_code == 409
    assert "Cannot start" in response.json()["detail"]

    events = client.get("/api/admin/events").json()
    assert events[0]["result"] == "REJECTED"
    assert events[0]["errorReason"]


def test_restart_and_rapid_shutdown(client):
    restart_request = client.post(
        "/api/control/requests",
        json={"deviceId": "device-test-001", "action": "RESTART"},
    ).json()
    restarted = client.post(f"/api/control/requests/{restart_request['requestId']}/approve")
    assert restarted.status_code == 200
    assert restarted.json()["status"] == "EXECUTED"
    assert client.get("/api/devices/device-test-001").json()["status"] == "RUNNING"

    shutdown_request = client.post(
        "/api/control/requests",
        json={"deviceId": "device-test-001", "action": "RAPID_SHUTDOWN"},
    ).json()
    shutdown = client.post(f"/api/control/requests/{shutdown_request['requestId']}/approve")
    assert shutdown.status_code == 200
    assert shutdown.json()["status"] == "EXECUTED"
    device = client.get("/api/devices/device-test-001").json()
    assert device["status"] == "RAPID_SHUTDOWN"
    assert device["rapidShutdown"] is True
    assert client.get("/api/devices/device-test-001/telemetry").json()["activePowerKw"] == 0


def test_denied_control_request_does_not_change_device(client):
    request = client.post(
        "/api/control/requests",
        json={"deviceId": "INV-TEST-001", "action": "STOP"},
    ).json()
    denied = client.post(
        f"/api/control/requests/{request['requestId']}/deny",
        json={"decisionSource": "human-reviewer"},
    )
    assert denied.status_code == 200
    assert denied.json()["status"] == "DENIED"
    assert denied.json()["decisionSource"] == "human-reviewer"
    assert client.get("/api/devices/device-test-001").json()["status"] == "RUNNING"


def test_expired_control_request_cannot_execute(expired_client):
    request = expired_client.post(
        "/api/control/requests",
        json={"deviceId": "INV-TEST-001", "action": "STOP"},
    ).json()
    approval = expired_client.post(f"/api/control/requests/{request['requestId']}/approve")
    assert approval.status_code == 409
    assert "expired" in approval.json()["detail"]
    stored = expired_client.get(f"/api/control/requests/{request['requestId']}").json()
    assert stored["status"] == "EXPIRED"
    assert expired_client.get("/api/devices/device-test-001").json()["status"] == "RUNNING"
    events = expired_client.get("/api/admin/events").json()
    expired = next(event for event in events if event["action"] == "CONTROL_REQUEST_EXPIRED")
    assert expired["controlRequestId"] == request["requestId"]
    assert expired["resultingState"] == "RUNNING"
    assert expired["decisionSource"] == "system-expiry"


def test_openclaw_unavailable_leaves_request_pending(unavailable_openclaw_client):
    response = unavailable_openclaw_client.post(
        "/api/control/requests",
        json={"deviceId": "INV-TEST-001", "action": "STOP"},
    )
    assert response.status_code == 202
    assert response.json()["status"] == "PENDING"
    assert unavailable_openclaw_client.get("/api/devices/device-test-001").json()["status"] == "RUNNING"
    events = unavailable_openclaw_client.get("/api/admin/events").json()
    notification = next(
        event for event in events
        if event["action"] == "CONTROL_REQUEST_NOTIFICATION_FAILED"
    )
    assert notification["controlRequestId"] == response.json()["requestId"]
    assert notification["deviceId"] == "INV-TEST-001"
    assert notification["controlAction"] == "STOP"
    assert notification["previousState"] == "RUNNING"
    assert notification["resultingState"] == "RUNNING"
    assert notification["result"] == "FAILED"
    assert notification["errorReason"] == "test OpenClaw CLI unavailable"


def test_control_request_is_committed_pending_before_openclaw_cli_runs(tmp_path):
    database_path = str(tmp_path / "commit-order.db")

    class CommitInspectingNotifier:
        observed_request = None
        observed_device_state = None

        def notify_control_request(self, request_id: str, action: str, device_id: str) -> NotificationResult:
            with sqlite3.connect(database_path) as db:
                self.observed_request = db.execute(
                    "SELECT request_id, action, device_id, status FROM control_requests WHERE request_id=?",
                    (request_id,),
                ).fetchone()
                self.observed_device_state = db.execute(
                    "SELECT status FROM devices WHERE serial_number=?",
                    (device_id,),
                ).fetchone()[0]
            return NotificationResult(delivered=True)

    notifier = CommitInspectingNotifier()
    app = create_app(database_path, transition_delay=0, notifier=notifier)
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/control/requests",
            json={"deviceId": "INV-TEST-001", "action": "RESTART"},
        )
        events = test_client.get("/api/admin/events").json()

    assert response.status_code == 202
    assert notifier.observed_request == (
        "CR-000001", "RESTART", "INV-TEST-001", "PENDING"
    )
    assert notifier.observed_device_state == "RUNNING"
    notification = next(
        event for event in events
        if event["action"] == "CONTROL_REQUEST_NOTIFICATION_SUCCEEDED"
    )
    assert notification["controlRequestId"] == "CR-000001"
    assert notification["controlAction"] == "RESTART"
    assert notification["requestedState"] == "PENDING"
    assert notification["result"] == "SUCCESS"


def test_direct_protected_endpoints_cannot_bypass_approval(client):
    for endpoint in ("stop", "restart", "rapid-shutdown"):
        response = client.post(f"/api/devices/device-test-001/{endpoint}")
        assert response.status_code == 409
        assert "Approval required" in response.json()["detail"]
        assert client.get("/api/devices/device-test-001").json()["status"] == "RUNNING"


def test_execution_failure_is_persisted_and_audited(client):
    stop_request = client.post(
        "/api/control/requests",
        json={"deviceId": "INV-TEST-001", "action": "STOP"},
    ).json()
    restart_request = client.post(
        "/api/control/requests",
        json={"deviceId": "INV-TEST-001", "action": "RESTART"},
    ).json()
    assert client.post(f"/api/control/requests/{stop_request['requestId']}/approve").json()["status"] == "EXECUTED"
    failed = client.post(f"/api/control/requests/{restart_request['requestId']}/approve").json()
    assert failed["status"] == "FAILED"
    assert failed["failureReason"]
    assert client.get("/api/devices/device-test-001").json()["status"] == "OFFLINE"
    events = client.get("/api/admin/events").json()
    assert any(event["action"] == "CONTROL_REQUEST_FAILED" for event in events)


def test_control_request_lists_and_audit_lifecycle(client):
    first = client.post(
        "/api/control/requests",
        json={"deviceId": "INV-TEST-001", "action": "STOP"},
    ).json()
    second = client.post(
        "/api/control/requests",
        json={"deviceId": "INV-TEST-001", "action": "RESTART"},
    ).json()
    assert first["requestId"] == "CR-000001"
    assert second["requestId"] == "CR-000002"
    assert len(client.get("/api/control/requests/pending").json()) == 2
    client.post(
        f"/api/control/requests/{first['requestId']}/deny",
        json={"decisionSource": "controller-agent"},
    )
    assert len(client.get("/api/control/requests/pending").json()) == 1
    assert len(client.get("/api/control/requests").json()) == 2
    events = client.get("/api/admin/events").json()
    actions = {event["action"] for event in events}
    assert {"CONTROL_REQUEST_CREATED", "CONTROL_REQUEST_DENIED"}.issubset(actions)
    denied_event = next(event for event in events if event["action"] == "CONTROL_REQUEST_DENIED")
    assert denied_event["controlRequestId"] == first["requestId"]
    assert denied_event["deviceId"] == "INV-TEST-001"
    assert denied_event["controlAction"] == "STOP"
    assert denied_event["decisionSource"] == "controller-agent"


def test_control_request_persists_across_store_recreation(tmp_path):
    database = str(tmp_path / "persistent.db")
    first_store = SimulatorStore(database, transition_delay=0)
    created = first_store.create_control_request("INV-TEST-001", ControlAction.STOP)

    reopened_store = SimulatorStore(database, transition_delay=0)
    persisted = reopened_store.get_control_request(created.request_id)

    assert persisted.request_id == "CR-000001"
    assert persisted.status == "PENDING"
    assert persisted.device_id == "INV-TEST-001"
    assert reopened_store.get_device("INV-TEST-001").status == "RUNNING"


def test_scenario_creates_and_recovers_alarm(client):
    injected = client.post("/api/admin/scenario", json={"scenario": "GRID_OVERVOLTAGE"})
    assert injected.status_code == 200
    assert injected.json()["device"]["status"] == "FAULT"

    alarms = client.get("/api/alarms?status=OCCURRING").json()
    assert len(alarms) == 1
    assert alarms[0]["alarmType"] == "GRID_OVERVOLTAGE"
    telemetry = client.get("/api/devices/device-test-001/telemetry").json()
    assert telemetry["phaseAVoltage"] == 262.0
    assert telemetry["activePowerKw"] == 0

    recovered = client.post(f"/api/alarms/{alarms[0]['id']}/recover")
    assert recovered.json()["status"] == "RECOVERED"
    assert len(client.get("/api/alarms?status=RECOVERED").json()) == 1


def test_reset_is_deterministic_and_clears_old_events(client):
    client.post("/api/admin/scenario", json={"scenario": "COMMUNICATION_LOSS"})
    client.post("/api/devices/device-test-001/start")
    assert len(client.get("/api/admin/events").json()) >= 2

    reset = client.post("/api/admin/reset")
    assert reset.status_code == 200
    assert reset.json()["scenario"] == "NORMAL"
    assert reset.json()["device"]["status"] == "RUNNING"
    assert client.get("/api/alarms").json() == []
    events = client.get("/api/admin/events").json()
    assert len(events) == 1
    assert events[0]["action"] == "SIMULATOR_RESET"


def test_all_required_scenarios_load(client):
    scenarios = [
        "NORMAL", "SUNNY_HIGH_GENERATION", "LOW_GENERATION", "DEVICE_OFFLINE",
        "GRID_OVERVOLTAGE", "GRID_UNDERVOLTAGE", "GRID_FAULT",
        "INVERTER_FAULT", "COMMUNICATION_LOSS", "OVER_TEMPERATURE",
    ]
    for scenario in scenarios:
        response = client.post("/api/admin/scenario", json={"scenario": scenario})
        assert response.status_code == 200, scenario


def test_all_required_alarm_types_can_be_injected(client):
    alarm_types = [
        "GRID_OVERVOLTAGE", "GRID_UNDERVOLTAGE", "GRID_FREQUENCY_HIGH",
        "GRID_FREQUENCY_LOW", "INVERTER_OVER_TEMPERATURE",
        "COMMUNICATION_LOSS", "DEVICE_FAULT",
    ]
    for alarm_type in alarm_types:
        response = client.post("/api/admin/alarm", json={"alarmType": alarm_type})
        assert response.status_code == 200, alarm_type
        assert response.json()["alarmType"] == alarm_type
        assert response.json()["status"] == "OCCURRING"


def test_compiled_frontend_and_spa_routes_are_served(client):
    root = client.get("/")
    assert root.status_code == 200
    assert "CER Test Portal" in root.text

    spa_route = client.get("/devices/device-test-001")
    assert spa_route.status_code == 200
    assert "CER Test Portal" in spa_route.text

    missing_api = client.get("/api/not-a-real-route")
    assert missing_api.status_code == 404
    assert missing_api.headers["content-type"].startswith("application/json")
