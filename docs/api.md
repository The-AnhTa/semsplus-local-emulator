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

| Method | Route | Requested outcome |
|---|---|---|
| `POST` | `/api/devices/{id}/start` | `RUNNING` via `STARTING` |
| `POST` | `/api/devices/{id}/stop` | `OFFLINE` via `STOPPING` |
| `POST` | `/api/devices/{id}/restart` | stop/start cycle ending `RUNNING` |
| `POST` | `/api/devices/{id}/rapid-shutdown` | `RAPID_SHUTDOWN` |

Successful commands return the resulting device. Illegal transitions return
HTTP 409 with an explicit `detail` string and are logged as `REJECTED` events.
Clients can provide `X-Actor`; otherwise the actor is `web-user`.

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
