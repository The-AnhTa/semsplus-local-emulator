import os
from datetime import date

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    Alarm,
    AlarmRequest,
    AuditEvent,
    Device,
    DeviceState,
    HistoryPoint,
    LoginRequest,
    LoginResponse,
    MpptPoint,
    ScenarioRequest,
    Station,
    StatusResponse,
    Telemetry,
)
from .state_machine import IllegalTransition
from .store import SimulatorStore


def create_app(database_path: str | None = None, transition_delay: float | None = None) -> FastAPI:
    app = FastAPI(
        title="CER Test Portal API",
        description="Offline-only synthetic CER/inverter simulator for security research.",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    store = SimulatorStore(database_path=database_path, transition_delay=transition_delay)
    app.state.store = store

    def actor(value: str | None) -> str:
        return value or "web-user"

    def not_found(kind: str, identifier: object) -> HTTPException:
        return HTTPException(status_code=404, detail=f"{kind} '{identifier}' was not found")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "offline-simulator"}

    @app.post("/api/auth/login", response_model=LoginResponse)
    def login(request: LoginRequest) -> LoginResponse:
        if request.email != "researcher@example.local" or request.password != "test-password":
            raise HTTPException(status_code=401, detail="Invalid local test credentials")
        return LoginResponse(
            access_token="local-research-session",
            display_name="CER Researcher",
        )

    @app.get("/api/stations", response_model=list[Station])
    def stations(
        search: str = "",
        address: str = "",
        email: str = "",
        status: str = "",
    ) -> list[Station]:
        result = store.list_stations()
        if search:
            term = search.lower()
            result = [s for s in result if term in s.name.lower() or term in s.id.lower()]
        if address:
            result = [s for s in result if address.lower() in s.address.lower()]
        if email:
            result = [s for s in result if email.lower() in s.email.lower()]
        if status and status.upper() != "ALL":
            result = [s for s in result if s.status.value == status.upper()]
        return result

    @app.get("/api/stations/{station_id}", response_model=Station)
    def station(station_id: str) -> Station:
        try:
            return store.get_station(station_id)
        except KeyError:
            raise not_found("Station", station_id)

    @app.get("/api/devices", response_model=list[Device])
    def devices(
        station: str = "",
        search: str = "",
        email: str = "",
        status: str = "",
    ) -> list[Device]:
        result = store.list_devices()
        if station:
            result = [d for d in result if station.lower() in d.station_name.lower()]
        if search:
            term = search.lower()
            result = [d for d in result if term in d.name.lower() or term in d.serial_number.lower()]
        if email and email.lower() not in "researcher@example.local":
            result = []
        if status and status.upper() != "ALL":
            result = [d for d in result if d.status.value == status.upper()]
        return result

    @app.get("/api/devices/{device_id}", response_model=Device)
    def device(device_id: str) -> Device:
        try:
            return store.get_device(device_id)
        except KeyError:
            raise not_found("Device", device_id)

    @app.get("/api/devices/{device_id}/telemetry", response_model=Telemetry)
    def telemetry(device_id: str) -> Telemetry:
        try:
            return store.telemetry(device_id)
        except KeyError:
            raise not_found("Device", device_id)

    @app.get("/api/devices/{device_id}/history", response_model=list[HistoryPoint])
    def history(device_id: str, day: date | None = Query(default=None)) -> list[HistoryPoint]:
        try:
            return store.history(device_id, day)
        except KeyError:
            raise not_found("Device", device_id)

    @app.get("/api/devices/{device_id}/mppt", response_model=list[MpptPoint])
    def mppt(device_id: str) -> list[MpptPoint]:
        try:
            return store.mppt(device_id)
        except KeyError:
            raise not_found("Device", device_id)

    def run_command(device_id: str, command: str, x_actor: str | None) -> Device:
        try:
            return store.command(device_id, command, actor(x_actor))
        except KeyError:
            raise not_found("Device", device_id)
        except IllegalTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    @app.post("/api/devices/{device_id}/start", response_model=Device)
    def start_device(device_id: str, x_actor: str | None = Header(default=None)) -> Device:
        return run_command(device_id, "start", x_actor)

    @app.post("/api/devices/{device_id}/stop", response_model=Device)
    def stop_device(device_id: str, x_actor: str | None = Header(default=None)) -> Device:
        return run_command(device_id, "stop", x_actor)

    @app.post("/api/devices/{device_id}/restart", response_model=Device)
    def restart_device(device_id: str, x_actor: str | None = Header(default=None)) -> Device:
        return run_command(device_id, "restart", x_actor)

    @app.post("/api/devices/{device_id}/rapid-shutdown", response_model=Device)
    def rapid_shutdown(device_id: str, x_actor: str | None = Header(default=None)) -> Device:
        return run_command(device_id, "rapid-shutdown", x_actor)

    @app.get("/api/alarms", response_model=list[Alarm])
    def alarms(
        status: str = "",
        search: str = "",
        start: date | None = None,
        end: date | None = None,
    ) -> list[Alarm]:
        result = store.list_alarms()
        if status and status.upper() != "ALL":
            result = [item for item in result if item.status == status.upper()]
        if search:
            term = search.lower()
            result = [item for item in result if term in item.device_name.lower() or term in item.station_name.lower() or term in item.alarm_name.lower()]
        if start:
            result = [item for item in result if item.alarm_time[:10] >= start.isoformat()]
        if end:
            result = [item for item in result if item.alarm_time[:10] <= end.isoformat()]
        return result

    @app.post("/api/alarms/{alarm_id}/recover", response_model=Alarm)
    def recover_alarm(alarm_id: int, x_actor: str | None = Header(default=None)) -> Alarm:
        try:
            return store.recover_alarm(alarm_id, actor(x_actor))
        except KeyError:
            raise not_found("Alarm", alarm_id)
        except IllegalTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    @app.post("/api/admin/scenario", response_model=StatusResponse)
    def set_scenario(request: ScenarioRequest, x_actor: str | None = Header(default=None)) -> StatusResponse:
        store.set_scenario(request.scenario, actor(x_actor) if x_actor else "researcher")
        return StatusResponse(status="ok", scenario=request.scenario, device=store.get_device("device-test-001"))

    @app.post("/api/admin/reset", response_model=StatusResponse)
    def reset(x_actor: str | None = Header(default=None)) -> StatusResponse:
        store.reset(actor(x_actor) if x_actor else "researcher")
        return StatusResponse(status="ok", scenario=store.scenario(), device=store.get_device("device-test-001"))

    @app.post("/api/admin/alarm", response_model=Alarm)
    def inject_alarm(request: AlarmRequest, x_actor: str | None = Header(default=None)) -> Alarm:
        return store.inject_alarm(request.alarm_type, actor(x_actor) if x_actor else "researcher")

    @app.get("/api/admin/events", response_model=list[AuditEvent])
    def events() -> list[AuditEvent]:
        return store.events()

    return app


app = create_app()
