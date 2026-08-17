# Deployment Strategy

| Field | Value |
|-------|--------|
| Document | Deployment Strategy |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Deployment Strategy for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Modular monolith deployable today ([ADR-0004](ADR/ADR-0004-api-first-modular-monolith.md)); cloud-native ready; secrets never in git.

## 3. Normative requirements
- Single FastAPI app + static frontend; PostgreSQL; Alembic migrations.
- Environments: development, staging, production with distinct secrets.
- Compose profiles for local/prod-like; TLS termination at edge in production.
- Backups and restore drills for DB including audit tables.

## 4. Future
Kubernetes HA, object store, Redis sessions, message bus — without rewriting domain packages.

## 5. Security / Scalability
Zero Trust at edge; horizontal scale of API workers after shared session store; DB connection pooling.

---

## 6. Non-functional requirements

Traceability, reviewability, and operability appropriate to safety-adjacent enterprise software. Changes that alter normative rules require ADR or standards PR with CHANGELOG entry.

---

## 7. Security considerations

No standard may weaken organization isolation, RBAC, or fail-closed audit without an explicit superseding ADR.

---

## 8. Scalability considerations

Standards must remain implementable on the modular monolith and remain valid when contexts are extracted.

---

## 9. Related documents

[ADR Index](ADR/README.md) · [Coding Standards](Coding_Standards.md) · [API Standards](API_Standards.md) · [Technical Architecture](../02_Architecture/Technical_Architecture.md)
