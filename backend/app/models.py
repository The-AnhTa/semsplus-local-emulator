from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DeviceState(StrEnum):
    RUNNING = "RUNNING"
    STANDBY = "STANDBY"
    STOPPING = "STOPPING"
    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    FAULT = "FAULT"
    RAPID_SHUTDOWN = "RAPID_SHUTDOWN"


class Scenario(StrEnum):
    NORMAL = "NORMAL"
    SUNNY_HIGH_GENERATION = "SUNNY_HIGH_GENERATION"
    LOW_GENERATION = "LOW_GENERATION"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    GRID_OVERVOLTAGE = "GRID_OVERVOLTAGE"
    GRID_UNDERVOLTAGE = "GRID_UNDERVOLTAGE"
    GRID_FAULT = "GRID_FAULT"
    INVERTER_FAULT = "INVERTER_FAULT"
    COMMUNICATION_LOSS = "COMMUNICATION_LOSS"
    OVER_TEMPERATURE = "OVER_TEMPERATURE"


class AlarmType(StrEnum):
    GRID_OVERVOLTAGE = "GRID_OVERVOLTAGE"
    GRID_UNDERVOLTAGE = "GRID_UNDERVOLTAGE"
    GRID_FREQUENCY_HIGH = "GRID_FREQUENCY_HIGH"
    GRID_FREQUENCY_LOW = "GRID_FREQUENCY_LOW"
    INVERTER_OVER_TEMPERATURE = "INVERTER_OVER_TEMPERATURE"
    COMMUNICATION_LOSS = "COMMUNICATION_LOSS"
    DEVICE_FAULT = "DEVICE_FAULT"


class ControlAction(StrEnum):
    RAPID_SHUTDOWN = "RAPID_SHUTDOWN"
    STOP = "STOP"
    RESTART = "RESTART"


class ControlRequestStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class LoginRequest(ApiModel):
    email: str
    password: str


class LoginResponse(ApiModel):
    access_token: str
    token_type: str = "bearer"
    display_name: str


class ScenarioRequest(ApiModel):
    scenario: Scenario


class AlarmRequest(ApiModel):
    alarm_type: AlarmType


class ControlRequestCreate(ApiModel):
    device_id: str = Field(min_length=1)
    action: ControlAction


class ControlDecisionRequest(ApiModel):
    decision_source: str = Field(default="controller", min_length=1, max_length=100)


class ControlRequest(ApiModel):
    request_id: str
    device_id: str
    action: ControlAction
    status: ControlRequestStatus
    created_at: str
    expires_at: str
    decided_at: str | None = None
    executed_at: str | None = None
    decision_source: str | None = None
    failure_reason: str | None = None
    previous_state: DeviceState | None = None
    resulting_state: DeviceState | None = None


class Station(ApiModel):
    id: str
    name: str
    capacity_kw: float
    address: str
    email: str
    status: DeviceState
    today_generation_kwh: float
    cumulative_generation_kwh: float
    specific_yield_kwh_kwp: float
    pv_power_kw: float
    note: str


class Device(ApiModel):
    id: str
    name: str
    serial_number: str
    station_id: str
    station_name: str
    status: DeviceState
    device_type: str
    active_power_kw: float
    daily_generation_kwh: float
    rapid_shutdown: bool


class Telemetry(ApiModel):
    timestamp: str
    active_power_kw: float
    reactive_power_kvar: float
    power_factor: float
    ac_frequency_hz: float
    daily_energy_kwh: float
    cumulative_energy_kwh: float
    pv_power_kw: float
    phase_a_voltage: float
    phase_b_voltage: float
    phase_c_voltage: float
    phase_a_current: float
    phase_b_current: float
    phase_c_current: float
    temperature_c: float


class HistoryPoint(ApiModel):
    timestamp: str
    active_power_kw: float
    pv_power_kw: float


class MpptPoint(ApiModel):
    voltage: float
    current: float
    power_kw: float


class Alarm(ApiModel):
    id: int
    alarm_type: str
    alarm_name: str
    device_id: str
    device_name: str
    station_name: str
    status: str
    level: str
    alarm_time: str
    recovered_time: str | None = None


class AuditEvent(ApiModel):
    id: int
    timestamp: str
    actor: str
    action: str
    target: str
    http_request: str
    previous_state: str | None = None
    requested_state: str | None = None
    resulting_state: str | None = None
    result: str
    error_reason: str | None = None
    control_request_id: str | None = None
    device_id: str | None = None
    control_action: str | None = None
    decision_source: str | None = None


class StatusResponse(ApiModel):
    status: str
    device: Device | None = None
    scenario: Scenario | None = None
