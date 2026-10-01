import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationResult:
    delivered: bool
    reason: str | None = None


@dataclass(frozen=True)
class OpenClawNotifier:
    hook_url: str | None
    hook_token: str | None
    controller_agent: str
    timeout_seconds: float = 3.0

    @classmethod
    def from_env(cls) -> "OpenClawNotifier":
        return cls(
            hook_url=os.getenv("OPENCLAW_HOOK_URL"),
            hook_token=os.getenv("OPENCLAW_HOOK_TOKEN"),
            controller_agent=os.getenv("OPENCLAW_CONTROLLER_AGENT", "controller"),
            timeout_seconds=float(os.getenv("OPENCLAW_HOOK_TIMEOUT_SECONDS", "3")),
        )

    def notify_control_request(self, request_id: str, action: str, device_id: str) -> NotificationResult:
        if not self.hook_url and not self.hook_token:
            return NotificationResult(delivered=False)
        if not self.hook_url or not self.hook_token:
            return NotificationResult(delivered=False, reason="OpenClaw hook configuration is incomplete")

        payload = {
            "text": f"CONTROL_REQUEST request_id={request_id} action={action} device={device_id} status=PENDING",
            "mode": "now",
            "agentId": self.controller_agent,
        }
        request = urllib.request.Request(
            self.hook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.hook_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                if 200 <= response.status < 300:
                    return NotificationResult(delivered=True)
                return NotificationResult(delivered=False, reason=f"OpenClaw returned HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            return NotificationResult(delivered=False, reason=f"OpenClaw returned HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return NotificationResult(delivered=False, reason=f"OpenClaw unavailable ({type(exc).__name__})")
