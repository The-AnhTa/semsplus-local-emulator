import os
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationResult:
    delivered: bool
    reason: str | None = None


@dataclass(frozen=True)
class OpenClawCliNotifier:
    executable: str = "openclaw"
    controller_agent: str = "controller"
    session_key: str = "agent:controller:main"
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "OpenClawCliNotifier":
        return cls(
            executable=os.getenv("OPENCLAW_CLI_PATH", "openclaw"),
            controller_agent=os.getenv("OPENCLAW_CONTROLLER_AGENT", "controller"),
            session_key=os.getenv("OPENCLAW_SESSION_KEY", "agent:controller:main"),
            timeout_seconds=float(os.getenv("OPENCLAW_CLI_TIMEOUT_SECONDS", "30")),
        )

    def notify_control_request(self, request_id: str, action: str, device_id: str) -> NotificationResult:
        message = (
            f"CONTROL_REQUEST request_id={request_id} action={action} "
            f"device_id={device_id} status=PENDING"
        )
        command = [
            self.executable,
            "agent",
            "--agent",
            self.controller_agent,
            "--session-key",
            self.session_key,
            "--message",
            message,
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return NotificationResult(
                delivered=False,
                reason=f"OpenClaw CLI timed out after {self.timeout_seconds:g} seconds",
            )
        except FileNotFoundError:
            return NotificationResult(
                delivered=False,
                reason="OpenClaw CLI executable was not found",
            )
        except OSError as exc:
            return NotificationResult(
                delivered=False,
                reason=f"OpenClaw CLI could not start ({type(exc).__name__})",
            )

        if completed.returncode == 0:
            return NotificationResult(delivered=True)
        return NotificationResult(
            delivered=False,
            reason=f"OpenClaw CLI exited with code {completed.returncode}",
        )
