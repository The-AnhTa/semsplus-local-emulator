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

    stopped = client.post("/api/devices/device-test-001/stop")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "OFFLINE"
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
    restarted = client.post("/api/devices/device-test-001/restart")
    assert restarted.status_code == 200
    assert restarted.json()["status"] == "RUNNING"

    shutdown = client.post("/api/devices/device-test-001/rapid-shutdown")
    assert shutdown.status_code == 200
    assert shutdown.json()["status"] == "RAPID_SHUTDOWN"
    assert shutdown.json()["rapidShutdown"] is True
    assert client.get("/api/devices/device-test-001/telemetry").json()["activePowerKw"] == 0


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
