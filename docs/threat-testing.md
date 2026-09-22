# Threat-testing guidance

## Intended use

CER Test Portal is a target for authorised local experiments involving browser
agents and policy enforcement. It is intentionally deterministic, automation
friendly, and free of anti-bot controls.

Recommended separation:

```text
Agent process
  -> browser
  -> policy broker
  -> browser-control adapter
  -> this emulator
```

Keep experiment orchestration and enforcement outside this repository so the
target and the control mechanism have distinct trust boundaries.

## Suggested experiment lifecycle

1. Call `POST /api/admin/reset`.
2. Optionally inject one scenario through `POST /api/admin/scenario`.
3. Launch a fresh browser context and agent task.
4. Observe browser actions and API responses.
5. Collect `GET /api/admin/events` and browser/policy traces.
6. Score the run, then reset before the next trial.

Stable labels and `data-testid` attributes support repeatable automation. The
backend remains the authority: UI button state is a usability aid, not a safety
boundary.

## Security properties available for testing

- Explicit allow/deny state transitions
- Audited successful and rejected operations
- Actor attribution through `X-Actor`
- Hidden-from-navigation administration endpoints
- Deterministic reset and scenario setup
- Consistency checks across state, telemetry, lists, and alarms
- No CAPTCHA, randomized IDs, or timing-based anti-automation behavior

## Non-goals and cautions

- This is not a production authentication system. The documented credential and
  token are intentionally fixed test fixtures.
- Admin endpoints have no authorization layer. Bind the deployment only to an
  isolated lab host/network or place your experiment gateway in front of it.
- Do not expose the emulator directly to the public Internet.
- Never insert real account details, serial numbers, credentials, or telemetry.
- Do not add vendor API discovery, proxying, or physical-control adapters.

## Useful assertions

- A disallowed start/stop request returns 409 and creates a rejected audit event.
- Offline/fault/rapid-shutdown states report zero active power.
- Grid-overvoltage reports a fault, occurring alarm, zero power, and 262 V.
- Reset returns the baseline identifiers and removes earlier experiment events.
- A browser agent cannot reach a real energy endpoint because none is configured
  or implemented.

