import pytest

from app.models import DeviceState
from app.state_machine import IllegalTransition, plan_transition


def test_stop_plan_uses_explicit_transitional_state():
    plan = plan_transition("stop", DeviceState.RUNNING)
    assert plan.states == (DeviceState.STOPPING, DeviceState.OFFLINE)


def test_start_plan_uses_explicit_transitional_state():
    plan = plan_transition("start", DeviceState.OFFLINE)
    assert plan.states == (DeviceState.STARTING, DeviceState.RUNNING)


def test_illegal_transition_raises():
    with pytest.raises(IllegalTransition, match="Cannot stop"):
        plan_transition("stop", DeviceState.OFFLINE)

