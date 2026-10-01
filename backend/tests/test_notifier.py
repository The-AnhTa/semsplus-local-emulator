import subprocess

from app.notifier import OpenClawCliNotifier


def test_openclaw_notification_invokes_cli_without_shell(monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
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
