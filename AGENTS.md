# CER Local Emulator — Repository Instructions

## Purpose

This repository implements a fully local simulated CER/inverter web portal for
cybersecurity and AI-agent safety research. It is a simulator, not a real CER
controller.

## Critical safety constraints

- Never connect to GoodWe, SEMS+, or any third-party energy service.
- Never communicate with a physical inverter.
- Never add production credentials, cookies, tokens, API keys, proprietary
  assets, or private implementation details.
- Never implement transparent forwarding or proxying to a production portal.
- Keep all accounts, device identities, stations, alarms, and telemetry
  synthetic.
- Log every meaningful state-changing operation, including rejected requests.
- Keep simulator reset deterministic.
- Use the files in `docs/reference-ui/` only as visual and workflow references.
  Use generic branding and original code/assets.

## Engineering expectations

- Keep frontend and backend interfaces explicit and documented.
- Prefer simple implementations over unnecessary abstraction.
- Use typed API models and validate state transitions server-side.
- Do not rely on frontend validation for simulator safety.
- Give important controls stable semantic labels and `data-testid` attributes.
- Avoid random or dynamic DOM IDs on important controls.
- Keep REST endpoints deterministic and errors explicit.
- Do not add anti-automation mechanisms.
- Keep the agent, policy broker, and browser-control layer outside this repo.

## Required verification

After backend changes, run backend pytest tests. After frontend changes, run
frontend tests and a production build. Run relevant Playwright end-to-end tests
before completing a workflow. Before declaring the repository complete, run all
tests and `docker compose build`.

## Research boundary

The simulator must remain suitable as an isolated target in this future chain:

```text
AI Agent -> Browser -> Policy Broker -> Browser-control layer -> CER Emulator
```

Do not tightly couple browser automation, policy enforcement, or an AI agent
into the emulator itself.
