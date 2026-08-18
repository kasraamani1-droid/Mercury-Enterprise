# Electronic Logbook Standards

| Field | Value |
|-------|--------|
| Document | Electronic Logbook Standards |
| Status | Normative |
| Layer | Standards |

---

## 1. Scope

This standard governs Electronic Logbook Standards for the Mercury AEOS blueprint and conforming runtime implementations.

## 2. Design principles
Logbook entries are airworthiness evidence: attributable, amendable only by append, tied to aircraft and certification events.

## 3. Normative requirements
- Entries reference aircraft, actors, timestamps, task/work identifiers.
- Amendments create new records; originals remain.
- Signatures hash-attested today; PKI later without faking.

## 4. Security / Future
Org isolation; export into Passport packs; authority-readable views under grant.

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
