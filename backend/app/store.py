import math
import os
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .models import (
    Alarm,
    AlarmType,
    AuditEvent,
    ControlAction,
    ControlRequest,
    ControlRequestStatus,
    Device,
    DeviceState,
    HistoryPoint,
    MpptPoint,
    Scenario,
    Station,
    Telemetry,
)
from .state_machine import IllegalTransition, plan_transition


DEFAULT_STATION_ID = "station-test-01"
DEFAULT_DEVICE_ID = "device-test-001"
DEFAULT_SERIAL = "INV-TEST-001"

ALARM_CATALOG: dict[AlarmType, tuple[str, str]] = {
    AlarmType.GRID_OVERVOLTAGE: ("Grid overvoltage", "CRITICAL"),
    AlarmType.GRID_UNDERVOLTAGE: ("Grid undervoltage", "CRITICAL"),
    AlarmType.GRID_FREQUENCY_HIGH: ("Grid frequency high", "CRITICAL"),
    AlarmType.GRID_FREQUENCY_LOW: ("Grid frequency low", "CRITICAL"),
    AlarmType.INVERTER_OVER_TEMPERATURE: ("Inverter over temperature", "CRITICAL"),
    AlarmType.COMMUNICATION_LOSS: ("Communication loss", "WARNING"),
    AlarmType.DEVICE_FAULT: ("Device fault", "CRITICAL"),
}

CONTROL_ACTION_COMMANDS: dict[ControlAction, str] = {
    ControlAction.RAPID_SHUTDOWN: "rapid-shutdown",
    ControlAction.STOP: "stop",
    ControlAction.RESTART: "restart",
}


class ControlRequestConflict(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_datetime() -> datetime:
    return datetime.now(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


class SimulatorStore:
    def __init__(
        self,
        database_path: str | None = None,
        transition_delay: float | None = None,
        control_request_ttl_seconds: int | None = None,
    ):
        self.database_path = database_path or os.getenv("CER_DATABASE_PATH", "./cer-emulator.db")
        self.transition_delay = transition_delay if transition_delay is not None else float(
            os.getenv("CER_TRANSITION_DELAY_SECONDS", "0.15")
        )
        self.control_request_ttl_seconds = (
            control_request_ttl_seconds
            if control_request_ttl_seconds is not None
            else int(os.getenv("CONTROL_REQUEST_TTL_SECONDS", "120"))
        )
        self._lock = threading.RLock()
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: sqlite3.Connection | None = None
        if self.database_path == ":memory:":
            self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False)
            self._memory_connection.row_factory = sqlite3.Row
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self._memory_connection is not None:
            return self._memory_connection
        connection = sqlite3.connect(self.database_path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _close(self, connection: sqlite3.Connection) -> None:
        if self._memory_connection is None:
            connection.close()

    def _initialize(self) -> None:
        with self._lock:
            db = self._connect()
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS stations (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, capacity_kw REAL NOT NULL,
                    address TEXT NOT NULL, email TEXT NOT NULL, note TEXT NOT NULL,
                    cumulative_generation_kwh REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, serial_number TEXT UNIQUE NOT NULL,
                    station_id TEXT NOT NULL, status TEXT NOT NULL, device_type TEXT NOT NULL,
                    rapid_shutdown INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(station_id) REFERENCES stations(id)
                );
                CREATE TABLE IF NOT EXISTS alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, alarm_type TEXT NOT NULL,
                    alarm_name TEXT NOT NULL, device_id TEXT NOT NULL, status TEXT NOT NULL,
                    level TEXT NOT NULL, alarm_time TEXT NOT NULL, recovered_time TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
                    actor TEXT NOT NULL, action TEXT NOT NULL, target TEXT NOT NULL,
                    http_request TEXT NOT NULL, previous_state TEXT, requested_state TEXT,
                    resulting_state TEXT, result TEXT NOT NULL, error_reason TEXT,
                    control_request_id TEXT, device_id TEXT, control_action TEXT,
                    decision_source TEXT
                );
                CREATE TABLE IF NOT EXISTS control_requests (
                    request_id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    decided_at TEXT,
                    executed_at TEXT,
                    decision_source TEXT,
                    failure_reason TEXT,
                    previous_state TEXT,
                    resulting_state TEXT
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                """
            )
            station_count = db.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
            if station_count == 0:
                self._seed(db)
            db.execute("INSERT OR IGNORE INTO settings VALUES ('control_request_sequence', '0')")
            self._ensure_event_columns(db)
            db.commit()
            self._close(db)

    def _ensure_event_columns(self, db: sqlite3.Connection) -> None:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(events)").fetchall()}
        for column in ("control_request_id", "device_id", "control_action", "decision_source"):
            if column not in columns:
                db.execute(f"ALTER TABLE events ADD COLUMN {column} TEXT")

    def _seed(self, db: sqlite3.Connection) -> None:
        db.execute(
            "INSERT INTO stations VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                DEFAULT_STATION_ID,
                "Test Station 01",
                10.0,
                "Melbourne Test Site",
                "researcher@example.local",
                "Synthetic research station",
                22524.8,
            ),
        )
        db.execute(
            "INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                DEFAULT_DEVICE_ID,
                "Research Inverter 01",
                DEFAULT_SERIAL,
                DEFAULT_STATION_ID,
                DeviceState.RUNNING.value,
                "On-Grid Inverter",
                0,
            ),
        )
        db.execute("INSERT OR REPLACE INTO settings VALUES ('scenario', ?)", (Scenario.NORMAL.value,))
        db.execute("INSERT OR REPLACE INTO settings VALUES ('control_request_sequence', '0')")

    def reset(self, actor: str = "researcher") -> None:
        with self._lock:
            db = self._connect()
            db.execute("DELETE FROM events")
            db.execute("DELETE FROM alarms")
            db.execute("DELETE FROM control_requests")
            db.execute("DELETE FROM devices")
            db.execute("DELETE FROM stations")
            db.execute("DELETE FROM settings")
            self._seed(db)
            db.commit()
            self._close(db)
            self.log_event(
                actor=actor,
                action="SIMULATOR_RESET",
                target="simulator",
                http_request="POST /api/admin/reset",
                previous_state=None,
                requested_state=Scenario.NORMAL.value,
                resulting_state=Scenario.NORMAL.value,
                result="SUCCESS",
            )

    def scenario(self) -> Scenario:
        db = self._connect()
        row = db.execute("SELECT value FROM settings WHERE key='scenario'").fetchone()
        self._close(db)
        return Scenario(row["value"])

    def _device_row(self, device_id: str) -> sqlite3.Row | None:
        db = self._connect()
        row = self._device_row_db(db, device_id)
        self._close(db)
        return row

    def _device_row_db(self, db: sqlite3.Connection, device_id: str) -> sqlite3.Row | None:
        return db.execute(
            """SELECT d.*, s.name AS station_name
               FROM devices d JOIN stations s ON s.id=d.station_id
               WHERE d.id=? OR d.serial_number=?""",
            (device_id, device_id),
        ).fetchone()

    def telemetry(self, device_id: str) -> Telemetry:
        row = self._device_row(device_id)
        if row is None:
            raise KeyError(device_id)
        state = DeviceState(row["status"])
        scenario = self.scenario()
        factor = {
            Scenario.SUNNY_HIGH_GENERATION: 1.35,
            Scenario.LOW_GENERATION: 0.28,
        }.get(scenario, 1.0)
        active = round(6.42 * factor, 2) if state == DeviceState.RUNNING else (0.05 if state == DeviceState.STANDBY else 0.0)
        voltage = 230.4
        frequency = 50.01
        temperature = 42.6 if active else 27.0
        if scenario == Scenario.GRID_OVERVOLTAGE:
            voltage = 262.0
        elif scenario == Scenario.GRID_UNDERVOLTAGE:
            voltage = 190.0
        elif scenario == Scenario.GRID_FAULT:
            frequency = 54.2
        elif scenario == Scenario.OVER_TEMPERATURE:
            temperature = 91.5
        elif scenario == Scenario.COMMUNICATION_LOSS:
            voltage = 0.0
            frequency = 0.0
        current = round(active * 1000 / (3 * voltage), 2) if voltage and active else 0.0
        daily = round(31.8 * factor, 2) if state == DeviceState.RUNNING else 0.0
        return Telemetry(
            timestamp=utc_now(),
            active_power_kw=active,
            reactive_power_kvar=round(active * 0.08, 2),
            power_factor=0.99 if active else 0.0,
            ac_frequency_hz=frequency,
            daily_energy_kwh=daily,
            cumulative_energy_kwh=22524.8 + daily,
            pv_power_kw=round(active * 1.04, 2),
            phase_a_voltage=voltage,
            phase_b_voltage=round(voltage - 0.6, 1) if voltage else 0.0,
            phase_c_voltage=round(voltage + 0.3, 1) if voltage else 0.0,
            phase_a_current=current,
            phase_b_current=round(current * 0.98, 2),
            phase_c_current=round(current * 1.01, 2),
            temperature_c=temperature,
        )

    def get_device(self, device_id: str) -> Device:
        row = self._device_row(device_id)
        if row is None:
            raise KeyError(device_id)
        telemetry = self.telemetry(row["id"])
        return Device(
            id=row["id"],
            name=row["name"],
            serial_number=row["serial_number"],
            station_id=row["station_id"],
            station_name=row["station_name"],
            status=DeviceState(row["status"]),
            device_type=row["device_type"],
            active_power_kw=telemetry.active_power_kw,
            daily_generation_kwh=telemetry.daily_energy_kwh,
            rapid_shutdown=bool(row["rapid_shutdown"]),
        )

    def list_devices(self) -> list[Device]:
        db = self._connect()
        ids = [row["id"] for row in db.execute("SELECT id FROM devices ORDER BY name").fetchall()]
        self._close(db)
        return [self.get_device(device_id) for device_id in ids]

    def list_stations(self) -> list[Station]:
        db = self._connect()
        rows = db.execute("SELECT * FROM stations ORDER BY name").fetchall()
        self._close(db)
        devices = self.list_devices()
        result: list[Station] = []
        for row in rows:
            station_device = next(device for device in devices if device.station_id == row["id"])
            telemetry = self.telemetry(station_device.id)
            result.append(
                Station(
                    id=row["id"],
                    name=row["name"],
                    capacity_kw=row["capacity_kw"],
                    address=row["address"],
                    email=row["email"],
                    status=station_device.status,
                    today_generation_kwh=telemetry.daily_energy_kwh,
                    cumulative_generation_kwh=telemetry.cumulative_energy_kwh,
                    specific_yield_kwh_kwp=round(telemetry.daily_energy_kwh / row["capacity_kw"], 2),
                    pv_power_kw=telemetry.pv_power_kw,
                    note=row["note"],
                )
            )
        return result

    def get_station(self, station_id: str) -> Station:
        station = next((item for item in self.list_stations() if item.id == station_id), None)
        if station is None:
            raise KeyError(station_id)
        return station

    def history(self, device_id: str, requested_date: date | None = None) -> list[HistoryPoint]:
        device = self.get_device(device_id)
        scenario = self.scenario()
        factor = {Scenario.SUNNY_HIGH_GENERATION: 1.35, Scenario.LOW_GENERATION: 0.28}.get(scenario, 1.0)
        enabled = device.status == DeviceState.RUNNING
        day = requested_date or date.today()
        points = []
        for hour in range(25):
            solar = max(0.0, math.sin(math.pi * (hour - 6) / 12))
            active = round(8.1 * factor * solar, 2) if enabled else 0.0
            points.append(
                HistoryPoint(
                    timestamp=f"{day.isoformat()}T{hour % 24:02d}:00:00",
                    active_power_kw=active,
                    pv_power_kw=round(active * 1.04, 2),
                )
            )
        return points

    def mppt(self, device_id: str) -> list[MpptPoint]:
        self.get_device(device_id)
        result = []
        for voltage in range(100, 651, 50):
            current = max(0.0, 12.0 - ((voltage - 360) / 130) ** 2)
            result.append(MpptPoint(voltage=voltage, current=round(current, 2), power_kw=round(voltage * current / 1000, 2)))
        return result

    def _set_device_state_db(self, db: sqlite3.Connection, device_id: str, state: DeviceState) -> None:
        rapid = 1 if state == DeviceState.RAPID_SHUTDOWN else 0
        db.execute("UPDATE devices SET status=?, rapid_shutdown=? WHERE id=?", (state.value, rapid, device_id))

    def _execute_transition_db(
        self,
        db: sqlite3.Connection,
        device_row: sqlite3.Row,
        command: str,
    ) -> tuple[DeviceState, DeviceState, str]:
        previous = DeviceState(device_row["status"])
        plan = plan_transition(command, previous)
        for state in plan.states:
            self._set_device_state_db(db, device_row["id"], state)
            if self.transition_delay and state != plan.states[-1]:
                time.sleep(self.transition_delay)
        return previous, plan.states[-1], plan.action

    def start_device(self, device_id: str, actor: str = "web-user") -> Device:
        with self._lock:
            db = self._connect()
            db.execute("BEGIN IMMEDIATE")
            row = self._device_row_db(db, device_id)
            if row is None:
                db.rollback()
                self._close(db)
                raise KeyError(device_id)
            current = DeviceState(row["status"])
            try:
                previous, resulting, event_action = self._execute_transition_db(db, row, "start")
            except IllegalTransition as exc:
                self._insert_event(
                    db, actor, "DEVICE_START", row["serial_number"], f"POST /api/devices/{row['id']}/start",
                    current.value, None, current.value, "REJECTED", str(exc),
                )
                db.commit()
                self._close(db)
                raise
            self._insert_event(
                db, actor, event_action, row["serial_number"], f"POST /api/devices/{row['id']}/start",
                previous.value, DeviceState.RUNNING.value, resulting.value, "SUCCESS",
            )
            db.commit()
            self._close(db)
            return self.get_device(row["id"])

    def reject_direct_protected_command(self, device_id: str, action: ControlAction, actor: str) -> None:
        row = self._device_row(device_id)
        if row is None:
            raise KeyError(device_id)
        current = DeviceState(row["status"])
        self.log_event(
            actor,
            "DIRECT_CONTROL_REJECTED",
            row["serial_number"],
            f"POST /api/devices/{row['id']}/{CONTROL_ACTION_COMMANDS[action]}",
            current.value,
            action.value,
            current.value,
            "REJECTED",
            "Approval gating is enabled; create a control request",
            device_id=row["serial_number"],
            control_action=action.value,
        )

    def _control_request_from_row(self, row: sqlite3.Row) -> ControlRequest:
        return ControlRequest(**dict(row))

    def create_control_request(
        self,
        device_id: str,
        action: ControlAction,
        actor: str = "web-user",
    ) -> ControlRequest:
        with self._lock:
            db = self._connect()
            db.execute("BEGIN IMMEDIATE")
            device = self._device_row_db(db, device_id)
            if device is None:
                db.rollback()
                self._close(db)
                raise KeyError(device_id)

            current = DeviceState(device["status"])
            command = CONTROL_ACTION_COMMANDS[action]
            try:
                plan_transition(command, current)
            except IllegalTransition:
                db.rollback()
                self._close(db)
                raise

            sequence = int(db.execute(
                "SELECT value FROM settings WHERE key='control_request_sequence'"
            ).fetchone()["value"]) + 1
            request_id = f"CR-{sequence:06d}"
            created = utc_datetime()
            created_at = format_utc(created)
            expires_at = format_utc(created + timedelta(seconds=self.control_request_ttl_seconds))
            db.execute(
                "UPDATE settings SET value=? WHERE key='control_request_sequence'",
                (str(sequence),),
            )
            db.execute(
                """INSERT INTO control_requests
                   (request_id, device_id, action, status, created_at, expires_at,
                    previous_state, resulting_state)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    request_id,
                    device["serial_number"],
                    action.value,
                    ControlRequestStatus.PENDING.value,
                    created_at,
                    expires_at,
                    current.value,
                    current.value,
                ),
            )
            self._insert_event(
                db,
                actor,
                "CONTROL_REQUEST_CREATED",
                request_id,
                "POST /api/control/requests",
                current.value,
                action.value,
                current.value,
                "SUCCESS",
                control_request_id=request_id,
                device_id=device["serial_number"],
                control_action=action.value,
            )
            row = db.execute("SELECT * FROM control_requests WHERE request_id=?", (request_id,)).fetchone()
            db.commit()
            self._close(db)
            return self._control_request_from_row(row)

    def _expire_pending_db(self, db: sqlite3.Connection, request_id: str | None = None) -> int:
        query = "SELECT * FROM control_requests WHERE status=?"
        params: list[str] = [ControlRequestStatus.PENDING.value]
        if request_id is not None:
            query += " AND request_id=?"
            params.append(request_id)
        rows = db.execute(query, params).fetchall()
        now = utc_datetime()
        now_text = format_utc(now)
        expired = 0
        for row in rows:
            expires_at = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
            if expires_at > now:
                continue
            device = self._device_row_db(db, row["device_id"])
            current = DeviceState(device["status"]) if device else None
            db.execute(
                """UPDATE control_requests
                   SET status=?, decided_at=?, decision_source=?, failure_reason=?, resulting_state=?
                   WHERE request_id=? AND status=?""",
                (
                    ControlRequestStatus.EXPIRED.value,
                    now_text,
                    "system-expiry",
                    "Approval window expired",
                    current.value if current else row["resulting_state"],
                    row["request_id"],
                    ControlRequestStatus.PENDING.value,
                ),
            )
            self._insert_event(
                db,
                "system",
                "CONTROL_REQUEST_EXPIRED",
                row["request_id"],
                f"POST /api/control/requests/{row['request_id']}/approve",
                current.value if current else row["previous_state"],
                row["action"],
                current.value if current else row["resulting_state"],
                "EXPIRED",
                "Approval window expired",
                control_request_id=row["request_id"],
                device_id=row["device_id"],
                control_action=row["action"],
                decision_source="system-expiry",
            )
            expired += 1
        return expired

    def list_control_requests(self, pending_only: bool = False) -> list[ControlRequest]:
        with self._lock:
            db = self._connect()
            db.execute("BEGIN IMMEDIATE")
            self._expire_pending_db(db)
            if pending_only:
                rows = db.execute(
                    "SELECT * FROM control_requests WHERE status=? ORDER BY request_id",
                    (ControlRequestStatus.PENDING.value,),
                ).fetchall()
            else:
                rows = db.execute("SELECT * FROM control_requests ORDER BY request_id").fetchall()
            db.commit()
            self._close(db)
            return [self._control_request_from_row(row) for row in rows]

    def get_control_request(self, request_id: str) -> ControlRequest:
        with self._lock:
            db = self._connect()
            db.execute("BEGIN IMMEDIATE")
            self._expire_pending_db(db, request_id)
            row = db.execute("SELECT * FROM control_requests WHERE request_id=?", (request_id,)).fetchone()
            if row is None:
                db.rollback()
                self._close(db)
                raise KeyError(request_id)
            db.commit()
            self._close(db)
            return self._control_request_from_row(row)

    def approve_control_request(self, request_id: str, decision_source: str) -> ControlRequest:
        with self._lock:
            db = self._connect()
            db.execute("BEGIN IMMEDIATE")
            self._expire_pending_db(db, request_id)
            request_row = db.execute(
                "SELECT * FROM control_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if request_row is None:
                db.rollback()
                self._close(db)
                raise KeyError(request_id)
            if request_row["status"] == ControlRequestStatus.EXPIRED.value:
                db.commit()
                self._close(db)
                raise ControlRequestConflict(f"Control request {request_id} has expired")
            if request_row["status"] != ControlRequestStatus.PENDING.value:
                db.rollback()
                self._close(db)
                raise ControlRequestConflict(
                    f"Control request {request_id} is {request_row['status']}, not PENDING"
                )

            device = self._device_row_db(db, request_row["device_id"])
            if device is None:
                db.rollback()
                self._close(db)
                raise KeyError(request_row["device_id"])
            previous = DeviceState(device["status"])
            decided_at = utc_now()
            db.execute(
                """UPDATE control_requests
                   SET status=?, decided_at=?, decision_source=?
                   WHERE request_id=?""",
                (ControlRequestStatus.APPROVED.value, decided_at, decision_source, request_id),
            )
            self._insert_event(
                db,
                decision_source,
                "CONTROL_REQUEST_APPROVED",
                request_id,
                f"POST /api/control/requests/{request_id}/approve",
                previous.value,
                request_row["action"],
                previous.value,
                "SUCCESS",
                control_request_id=request_id,
                device_id=request_row["device_id"],
                control_action=request_row["action"],
                decision_source=decision_source,
            )

            db.execute("SAVEPOINT control_execution")
            try:
                _, resulting, _ = self._execute_transition_db(
                    db,
                    device,
                    CONTROL_ACTION_COMMANDS[ControlAction(request_row["action"])],
                )
                db.execute("RELEASE SAVEPOINT control_execution")
            except Exception as exc:
                db.execute("ROLLBACK TO SAVEPOINT control_execution")
                db.execute("RELEASE SAVEPOINT control_execution")
                db.execute(
                    """UPDATE control_requests
                       SET status=?, failure_reason=?, resulting_state=?
                       WHERE request_id=?""",
                    (ControlRequestStatus.FAILED.value, str(exc), previous.value, request_id),
                )
                self._insert_event(
                    db,
                    decision_source,
                    "CONTROL_REQUEST_FAILED",
                    request_id,
                    f"POST /api/control/requests/{request_id}/approve",
                    previous.value,
                    request_row["action"],
                    previous.value,
                    "FAILED",
                    str(exc),
                    control_request_id=request_id,
                    device_id=request_row["device_id"],
                    control_action=request_row["action"],
                    decision_source=decision_source,
                )
            else:
                executed_at = utc_now()
                db.execute(
                    """UPDATE control_requests
                       SET status=?, executed_at=?, resulting_state=?, failure_reason=NULL
                       WHERE request_id=?""",
                    (ControlRequestStatus.EXECUTED.value, executed_at, resulting.value, request_id),
                )
                self._insert_event(
                    db,
                    decision_source,
                    "CONTROL_REQUEST_EXECUTED",
                    request_id,
                    f"POST /api/control/requests/{request_id}/approve",
                    previous.value,
                    request_row["action"],
                    resulting.value,
                    "SUCCESS",
                    control_request_id=request_id,
                    device_id=request_row["device_id"],
                    control_action=request_row["action"],
                    decision_source=decision_source,
                )

            updated = db.execute(
                "SELECT * FROM control_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            db.commit()
            self._close(db)
            return self._control_request_from_row(updated)

    def deny_control_request(self, request_id: str, decision_source: str) -> ControlRequest:
        with self._lock:
            db = self._connect()
            db.execute("BEGIN IMMEDIATE")
            self._expire_pending_db(db, request_id)
            request_row = db.execute(
                "SELECT * FROM control_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if request_row is None:
                db.rollback()
                self._close(db)
                raise KeyError(request_id)
            if request_row["status"] == ControlRequestStatus.EXPIRED.value:
                db.commit()
                self._close(db)
                raise ControlRequestConflict(f"Control request {request_id} has expired")
            if request_row["status"] != ControlRequestStatus.PENDING.value:
                db.rollback()
                self._close(db)
                raise ControlRequestConflict(
                    f"Control request {request_id} is {request_row['status']}, not PENDING"
                )

            device = self._device_row_db(db, request_row["device_id"])
            current = DeviceState(device["status"]) if device else None
            decided_at = utc_now()
            db.execute(
                """UPDATE control_requests
                   SET status=?, decided_at=?, decision_source=?, resulting_state=?
                   WHERE request_id=?""",
                (
                    ControlRequestStatus.DENIED.value,
                    decided_at,
                    decision_source,
                    current.value if current else request_row["resulting_state"],
                    request_id,
                ),
            )
            self._insert_event(
                db,
                decision_source,
                "CONTROL_REQUEST_DENIED",
                request_id,
                f"POST /api/control/requests/{request_id}/deny",
                current.value if current else request_row["previous_state"],
                request_row["action"],
                current.value if current else request_row["resulting_state"],
                "SUCCESS",
                control_request_id=request_id,
                device_id=request_row["device_id"],
                control_action=request_row["action"],
                decision_source=decision_source,
            )
            updated = db.execute(
                "SELECT * FROM control_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            db.commit()
            self._close(db)
            return self._control_request_from_row(updated)

    def _recover_open_alarms(self, db: sqlite3.Connection) -> int:
        timestamp = utc_now()
        cursor = db.execute(
            "UPDATE alarms SET status='RECOVERED', recovered_time=? WHERE status='OCCURRING'",
            (timestamp,),
        )
        return cursor.rowcount

    def set_scenario(self, scenario: Scenario, actor: str = "researcher") -> None:
        mapping: dict[Scenario, tuple[DeviceState, tuple[str, str, str] | None]] = {
            Scenario.NORMAL: (DeviceState.RUNNING, None),
            Scenario.SUNNY_HIGH_GENERATION: (DeviceState.RUNNING, None),
            Scenario.LOW_GENERATION: (DeviceState.RUNNING, None),
            Scenario.DEVICE_OFFLINE: (DeviceState.OFFLINE, None),
            Scenario.GRID_OVERVOLTAGE: (DeviceState.FAULT, ("GRID_OVERVOLTAGE", "Grid overvoltage", "CRITICAL")),
            Scenario.GRID_UNDERVOLTAGE: (DeviceState.FAULT, ("GRID_UNDERVOLTAGE", "Grid undervoltage", "CRITICAL")),
            Scenario.GRID_FAULT: (DeviceState.FAULT, ("GRID_FREQUENCY_HIGH", "Grid frequency high", "CRITICAL")),
            Scenario.INVERTER_FAULT: (DeviceState.FAULT, ("DEVICE_FAULT", "Device fault", "CRITICAL")),
            Scenario.COMMUNICATION_LOSS: (DeviceState.OFFLINE, ("COMMUNICATION_LOSS", "Communication loss", "WARNING")),
            Scenario.OVER_TEMPERATURE: (DeviceState.FAULT, ("INVERTER_OVER_TEMPERATURE", "Inverter over temperature", "CRITICAL")),
        }
        with self._lock:
            previous_scenario = self.scenario()
            previous_state = self.get_device(DEFAULT_DEVICE_ID).status
            state, alarm = mapping[scenario]
            db = self._connect()
            self._recover_open_alarms(db)
            db.execute("INSERT OR REPLACE INTO settings VALUES ('scenario', ?)", (scenario.value,))
            db.execute("UPDATE devices SET status=?, rapid_shutdown=0 WHERE id=?", (state.value, DEFAULT_DEVICE_ID))
            if alarm:
                db.execute(
                    """INSERT INTO alarms
                       (alarm_type, alarm_name, device_id, status, level, alarm_time)
                       VALUES (?, ?, ?, 'OCCURRING', ?, ?)""",
                    (alarm[0], alarm[1], DEFAULT_DEVICE_ID, alarm[2], utc_now()),
                )
            db.commit()
            self._close(db)
            self.log_event(
                actor, "SCENARIO_SET", "simulator", "POST /api/admin/scenario",
                f"{previous_scenario.value}:{previous_state.value}", scenario.value,
                f"{scenario.value}:{state.value}", "SUCCESS",
            )

    def list_alarms(self) -> list[Alarm]:
        db = self._connect()
        rows = db.execute(
            """SELECT a.*, d.name AS device_name, s.name AS station_name
               FROM alarms a JOIN devices d ON d.id=a.device_id
               JOIN stations s ON s.id=d.station_id ORDER BY a.id DESC"""
        ).fetchall()
        self._close(db)
        return [
            Alarm(
                id=row["id"], alarm_type=row["alarm_type"], alarm_name=row["alarm_name"],
                device_id=row["device_id"], device_name=row["device_name"], station_name=row["station_name"],
                status=row["status"], level=row["level"], alarm_time=row["alarm_time"], recovered_time=row["recovered_time"],
            )
            for row in rows
        ]

    def inject_alarm(self, alarm_type: AlarmType, actor: str = "researcher") -> Alarm:
        name, level = ALARM_CATALOG[alarm_type]
        with self._lock:
            db = self._connect()
            cursor = db.execute(
                """INSERT INTO alarms
                   (alarm_type, alarm_name, device_id, status, level, alarm_time)
                   VALUES (?, ?, ?, 'OCCURRING', ?, ?)""",
                (alarm_type.value, name, DEFAULT_DEVICE_ID, level, utc_now()),
            )
            alarm_id = cursor.lastrowid
            db.commit()
            self._close(db)
            self.log_event(
                actor, "ALARM_INJECT", DEFAULT_SERIAL, "POST /api/admin/alarm",
                None, alarm_type.value, "OCCURRING", "SUCCESS",
            )
            return next(alarm for alarm in self.list_alarms() if alarm.id == alarm_id)

    def recover_alarm(self, alarm_id: int, actor: str = "web-user") -> Alarm:
        with self._lock:
            db = self._connect()
            row = db.execute("SELECT * FROM alarms WHERE id=?", (alarm_id,)).fetchone()
            if row is None:
                self._close(db)
                raise KeyError(alarm_id)
            if row["status"] == "RECOVERED":
                self._close(db)
                raise IllegalTransition("Alarm is already recovered")
            db.execute("UPDATE alarms SET status='RECOVERED', recovered_time=? WHERE id=?", (utc_now(), alarm_id))
            db.commit()
            self._close(db)
            self.log_event(
                actor, "ALARM_RECOVER", str(alarm_id), f"POST /api/alarms/{alarm_id}/recover",
                "OCCURRING", "RECOVERED", "RECOVERED", "SUCCESS",
            )
            return next(alarm for alarm in self.list_alarms() if alarm.id == alarm_id)

    def log_event(
        self,
        actor: str,
        action: str,
        target: str,
        http_request: str,
        previous_state: str | None,
        requested_state: str | None,
        resulting_state: str | None,
        result: str,
        error_reason: str | None = None,
        control_request_id: str | None = None,
        device_id: str | None = None,
        control_action: str | None = None,
        decision_source: str | None = None,
    ) -> None:
        db = self._connect()
        self._insert_event(
            db,
            actor,
            action,
            target,
            http_request,
            previous_state,
            requested_state,
            resulting_state,
            result,
            error_reason,
            control_request_id,
            device_id,
            control_action,
            decision_source,
        )
        db.commit()
        self._close(db)

    def _insert_event(
        self,
        db: sqlite3.Connection,
        actor: str,
        action: str,
        target: str,
        http_request: str,
        previous_state: str | None,
        requested_state: str | None,
        resulting_state: str | None,
        result: str,
        error_reason: str | None = None,
        control_request_id: str | None = None,
        device_id: str | None = None,
        control_action: str | None = None,
        decision_source: str | None = None,
    ) -> None:
        db.execute(
            """INSERT INTO events
               (timestamp, actor, action, target, http_request, previous_state,
                requested_state, resulting_state, result, error_reason,
                control_request_id, device_id, control_action, decision_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                utc_now(), actor, action, target, http_request, previous_state,
                requested_state, resulting_state, result, error_reason,
                control_request_id, device_id, control_action, decision_source,
            ),
        )

    def events(self) -> list[AuditEvent]:
        db = self._connect()
        rows = db.execute("SELECT * FROM events ORDER BY id DESC").fetchall()
        self._close(db)
        return [AuditEvent(**dict(row)) for row in rows]
