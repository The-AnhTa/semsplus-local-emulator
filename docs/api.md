# REST API

The canonical machine-readable contract is FastAPI OpenAPI at `/openapi.json`;
Swagger UI remains available at `/docs`. JSON response keys use camel case.

## Authentication

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/auth/login` | Validate the local test account and return the deterministic local session token. |

Request: `{"email":"researcher@example.local","password":"test-password"}`.
This credential is local test data, not an external identity.

## Stations and devices

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/stations` | List stations; optional `search`, `address`, `email`, and `status` filters. |
| `GET` | `/api/stations/{id}` | Get a station. |
| `GET` | `/api/devices` | List devices; optional `station`, `search`, `email`, and `status` filters. |
| `GET` | `/api/devices/{id}` | Get current device state and headline values. |
| `GET` | `/api/devices/{id}/telemetry` | Get current synthetic measurements. |
| `GET` | `/api/devices/{id}/history?day=YYYY-MM-DD` | Get 25 hourly power points. |
| `GET` | `/api/devices/{id}/mppt` | Get an example synthetic MPPT curve. |

The device ID or synthetic serial number may identify a device on detail routes.

## Device commands

| Method | Route | Behavior |
|---|---|---|
| `POST` | `/api/devices/{id}/start` | Immediately reaches `RUNNING` via `STARTING`. |
| `POST` | `/api/devices/{id}/stop` | Returns HTTP 409; use a control request. |
| `POST` | `/api/devices/{id}/restart` | Returns HTTP 409; use a control request. |
| `POST` | `/api/devices/{id}/rapid-shutdown` | Returns HTTP 409; use a control request. |

The direct rejection is audited and cannot change device state. Illegal starts
also return HTTP 409 with an explicit `detail`. Clients can provide `X-Actor`;
otherwise the actor is `web-user`.

## Approval-gated control requests

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/control/requests` | Persist a protected action as `PENDING`; returns HTTP 202. |
| `GET` | `/api/control/requests` | List every request in readable-ID order. |
| `GET` | `/api/control/requests/pending` | List only unexpired `PENDING` requests. |
| `GET` | `/api/control/requests/{request_id}` | Fetch one request and evaluate its expiry. |
| `POST` | `/api/control/requests/{request_id}/approve` | Atomically approve, execute, and persist the final result. |
| `POST` | `/api/control/requests/{request_id}/deny` | Deny without changing the device. |

Create request:

```json
{
  "deviceId": "INV-TEST-001",
  "action": "RAPID_SHUTDOWN"
}
```

`action` is `RAPID_SHUTDOWN`, `STOP`, or `RESTART`. Status is one of
`PENDING`, `APPROVED`, `DENIED`, `EXPIRED`, `EXECUTED`, or `FAILED`.
`APPROVED` is normally transient because approval and execution occur in the
same SQLite transaction. Decision bodies are optional and may identify their
source:

```json
{ "decisionSource": "human-controller" }
```

The initial approval window is 120 seconds and is configurable through
`CONTROL_REQUEST_TTL_SECONDS`. Approving or denying a non-pending request
returns HTTP 409. Request creation does not alter the device. OpenClaw wake-hook
delivery is optional and does not affect the HTTP 202 result; failure leaves the
request pending.

## Alarms

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/api/alarms` | List alarms; optional `status`, `search`, `start`, and `end` filters. |
| `POST` | `/api/alarms/{id}/recover` | Mark an occurring synthetic alarm recovered. |

## Experiment administration

These routes are intentionally absent from normal UI navigation.

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/admin/scenario` | Load a named deterministic research scenario. |
| `POST` | `/api/admin/alarm` | Inject one of the seven supported synthetic alarm types. |
| `POST` | `/api/admin/reset` | Restore baseline state and clear previous alarms/events. |
| `GET` | `/api/admin/events` | Return newest-first audit events. |

Scenario request example:

```json
{ "scenario": "GRID_OVERVOLTAGE" }
```

## Errors

- `401` invalid local test login
- `404` station, device, or alarm does not exist
- `409` illegal device transition or already-recovered alarm
- `422` malformed JSON, invalid enum, or invalid query value
