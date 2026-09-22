# Implementation Plan

This plan is a living checklist. A phase is complete only after its relevant
verification passes.

## Phase 1 — Project skeleton and backend simulator

- [x] Scaffold FastAPI backend, React/TypeScript frontend, tests, docs, and
      deployment files.
- [x] Define typed station, device, telemetry, alarm, scenario, authentication,
      and audit-event models.
- [x] Implement SQLite persistence with deterministic seed/reset behavior.
- [x] Implement device state machine and explicit illegal-transition errors.
- [x] Implement synthetic, state-dependent telemetry and history.
- [x] Implement REST endpoints and local-only authentication.
- [x] Add backend tests for transitions, alarms, scenarios, reset, and audit.

Acceptance: backend test suite passes and OpenAPI exposes all required routes.

## Phase 2 — Frontend pages

- [x] Implement generic CER Test Portal login.
- [x] Implement dark application shell and stable left navigation.
- [x] Implement Station List, Device List, Device Detail, and Alarm Center.
- [x] Add synthetic monitoring and MPPT charts without proprietary assets.
- [x] Add semantic labels and stable `data-testid` hooks.

Acceptance: frontend builds and component tests pass.

## Phase 3 — Controls and state machine integration

- [x] Implement Start, Stop, Restart, and Rapid Shutdown controls.
- [x] Surface transitional states and explicit API errors in the UI.
- [x] Keep telemetry, lists, and details consistent with simulator state.

Acceptance: browser workflow can stop an online device and start it again.

## Phase 4 — Alarms, scenarios, and audit logs

- [x] Implement alarm occurrence/recovery and filtering.
- [x] Implement admin scenario injection and deterministic reset endpoints.
- [x] Record successful and rejected mutations in the audit log.
- [x] Verify scenario-driven state, telemetry, and alarm consistency.

Acceptance: API and browser tests cover grid overvoltage and reset behavior.

## Phase 5 — Docker, tests, and documentation

- [x] Add production containers and Docker Compose on port 8080.
- [x] Add Playwright end-to-end workflows.
- [x] Complete README and architecture/API/simulator/threat-testing docs.
- [x] Run backend tests, frontend tests/build, and Playwright tests.
- [ ] Run Docker Compose build (blocked: no Docker/container runtime installed on
      the current machine).

Acceptance: a fresh clone can run with `docker compose up --build` and no host
Node or Python installation.

## Phase 6 — UI cleanup against screenshots

- [x] Inspect every supplied screenshot for hierarchy and interaction cues.
- [x] Compare the rendered local UI at desktop viewport sizes.
- [x] Fix obvious spacing, contrast, responsiveness, and usability issues.
- [x] Re-run browser tests after visual cleanup.

Acceptance: the UI approximately reproduces the reference interaction model
with generic branding, synthetic data, and no copied proprietary assets.

## Completion gates

- [x] No code connects to a real energy service or physical device.
- [x] All required functionality is implemented and documented.
- [x] Backend tests pass.
- [x] Frontend tests and production build pass.
- [x] Playwright tests pass.
- [ ] Docker Compose build passes.
