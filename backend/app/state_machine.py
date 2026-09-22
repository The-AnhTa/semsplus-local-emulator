from dataclasses import dataclass

from .models import DeviceState


@dataclass(frozen=True)
class TransitionPlan:
    action: str
    requested_state: DeviceState
    states: tuple[DeviceState, ...]


class IllegalTransition(ValueError):
    pass


PLANS: dict[str, dict[DeviceState, TransitionPlan]] = {
    "start": {
        DeviceState.OFFLINE: TransitionPlan("DEVICE_START", DeviceState.RUNNING, (DeviceState.STARTING, DeviceState.RUNNING)),
        DeviceState.STANDBY: TransitionPlan("DEVICE_START", DeviceState.RUNNING, (DeviceState.STARTING, DeviceState.RUNNING)),
        DeviceState.RAPID_SHUTDOWN: TransitionPlan("DEVICE_START", DeviceState.RUNNING, (DeviceState.STARTING, DeviceState.RUNNING)),
    },
    "stop": {
        DeviceState.RUNNING: TransitionPlan("DEVICE_STOP", DeviceState.OFFLINE, (DeviceState.STOPPING, DeviceState.OFFLINE)),
        DeviceState.STANDBY: TransitionPlan("DEVICE_STOP", DeviceState.OFFLINE, (DeviceState.STOPPING, DeviceState.OFFLINE)),
        DeviceState.FAULT: TransitionPlan("DEVICE_STOP", DeviceState.OFFLINE, (DeviceState.OFFLINE,)),
    },
    "restart": {
        DeviceState.RUNNING: TransitionPlan("DEVICE_RESTART", DeviceState.RUNNING, (DeviceState.STOPPING, DeviceState.OFFLINE, DeviceState.STARTING, DeviceState.RUNNING)),
        DeviceState.STANDBY: TransitionPlan("DEVICE_RESTART", DeviceState.RUNNING, (DeviceState.STOPPING, DeviceState.OFFLINE, DeviceState.STARTING, DeviceState.RUNNING)),
    },
    "rapid-shutdown": {
        DeviceState.RUNNING: TransitionPlan("DEVICE_RAPID_SHUTDOWN", DeviceState.RAPID_SHUTDOWN, (DeviceState.RAPID_SHUTDOWN,)),
        DeviceState.STANDBY: TransitionPlan("DEVICE_RAPID_SHUTDOWN", DeviceState.RAPID_SHUTDOWN, (DeviceState.RAPID_SHUTDOWN,)),
    },
}


def plan_transition(action: str, current: DeviceState) -> TransitionPlan:
    plan = PLANS.get(action, {}).get(current)
    if plan is None:
        raise IllegalTransition(f"Cannot {action} a device in {current.value} state")
    return plan

