import subprocess
from pathlib import Path

from app.notifier import OpenClawCliNotifier


def test_openclaw_notification_invokes_cli_without_shell(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("app.notifier.sys.platform", "linux")
    notifier = OpenClawCliNotifier(
        executable="openclaw",
        controller_agent="controller",
        session_key="agent:controller:main",
        timeout_seconds=4,
    )
    result = notifier.notify_control_request("CR-000001", "STOP", "INV-TEST-001")

    assert result.delivered is True
    assert captured["command"] == [
        "openclaw",
        "agent",
        "--agent",
        "controller",
        "--session-key",
        "agent:controller:main",
        "--message",
        "CONTROL_REQUEST request_id=CR-000001 action=STOP device_id=INV-TEST-001 status=PENDING",
    ]
    assert captured["kwargs"] == {
        "capture_output": True,
        "text": True,
        "timeout": 4,
        "check": False,
        "shell": False,
    }


def test_windows_notification_uses_portable_node_entrypoint(monkeypatch):
    captured = {}
    fake_home = Path("C:/Users/test-researcher")

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("app.notifier.sys.platform", "win32")
    monkeypatch.setattr("app.notifier.Path.home", lambda: fake_home)

    result = OpenClawCliNotifier().notify_control_request(
        "CR-000006", "RAPID_SHUTDOWN", "INV-TEST-001"
    )

    portable_node = (
        fake_home
        / "AppData"
        / "Local"
        / "OpenClaw"
        / "deps"
        / "portable-node"
    )
    assert result.delivered is True
    assert captured["command"] == [
        str(portable_node / "node.exe"),
        str(portable_node / "node_modules" / "openclaw" / "openclaw.mjs"),
        "agent",
        "--agent",
        "controller",
        "--session-key",
        "agent:controller:main",
        "--message",
        "CONTROL_REQUEST request_id=CR-000006 action=RAPID_SHUTDOWN device_id=INV-TEST-001 status=PENDING",
    ]
    assert captured["kwargs"]["timeout"] == 60
    assert captured["kwargs"]["shell"] is False


def test_openclaw_notification_reports_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, returncode=7),
    )
    result = OpenClawCliNotifier().notify_control_request(
        "CR-000002", "RESTART", "INV-TEST-001"
    )

    assert result.delivered is False
    assert result.reason == "OpenClaw CLI exited with code 7"


def test_openclaw_notification_timeout_is_best_effort_failure(monkeypatch):
    def time_out(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr("subprocess.run", time_out)
    result = OpenClawCliNotifier(timeout_seconds=2).notify_control_request(
        "CR-000003", "RAPID_SHUTDOWN", "INV-TEST-001"
    )

    assert result.delivered is False
    assert result.reason == "OpenClaw CLI timed out after 2 seconds"
