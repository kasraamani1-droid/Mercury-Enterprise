# Operator Runbook — Mercury Enterprise V2.0

Advisory platform only. Recommendations never authorize autonomous execution, targeting, interception, or weapon control.

## Normal operations

1. Start the stack (`START_ALL.bat` locally, or `docker compose up --build`).
2. Open `http://localhost:3000`.
3. Confirm header status shows API version and Backend online.
4. Confirm org/site selectors match the operating context.
5. Use Command workspace for live incidents, alerts, connector health, and advisory decisions.
6. Use Executive/History for scoped KPIs and historical exports.
7. Use Admin audit log for attribution review.

## Decision support review

1. In Command, open **Decision Timeline**.
2. Click **Evaluate advisory decision** (or select an existing timeline entry).
3. Inspect alternatives, factors, warnings, assumptions, uncertainty, and connector trust notes.
4. Submit **Acknowledge**, **Comment**, or **Reject advisory**.
5. Confirm Admin audit shows `decision.evaluate` / `decision.review`.
6. Never treat review as authorization to execute an operational action automatically.

## Alert triage

1. Review Alert Summary and Critical banner.
2. Acknowledge alerts via existing alert controls when authorized (`alerts.ack`).
3. Correlate with incident detail, evidence provenance, and connector health.
4. Escalate via human procedures only — Mercury does not auto-dispatch.

## Degraded mode

| Signal | Operator action |
|--------|-----------------|
| Backend offline / ready fail | Stop relying on live writes; notify administrator |
| Health `status=degraded` or DB error | Treat data as unavailable; do not force actions |
| Connectors degraded/error | Lower trust in recommendations; check Integrations lifecycle |
| Decision store empty after restart | Re-evaluate advisory decisions; durable audit remains in Admin |

## Human-control reminder

- All AI/decision outputs are advisory.
- Site scope and RBAC still apply when the API is available.
- Connector recover/start/stop are explicit human actions (Operator/Admin).
