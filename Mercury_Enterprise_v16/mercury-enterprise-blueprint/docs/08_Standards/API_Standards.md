# API Standards — Mercury Aviation Enterprise Operating System

| Field | Value |
|-------|-------|
| Document | API Standards |
| Product | Mercury Aviation Enterprise Operating System (AEOS) |
| Organization | Mercury Technologies |
| Layer | Standards (HTTP contract, versioning, pagination, filtering, errors, authentication, bulk operations) |
| Audience | Backend developers, frontend developers, integrators, reviewers, partner engineering teams |
| Status | Living baseline |
| Companion documents | [UI Standards](UI_Standards.md) · [Coding Standards](Coding_Standards.md) · [ADR register](ADR/README.md) |
| Upstream authority | [Technical Architecture](../02_Architecture/Technical_Architecture.md) · [Blueprint README](../../README.md) |

---

## 1. Scope

### 1.1 In scope

This document is the **normative contract for every HTTP surface Mercury exposes**. It governs:

- URL structure and the `/api/v1` versioning policy, including what may change inside a version and what forces a new one.
- Resource naming, verb selection, and status codes.
- Pagination, filtering, sorting, and search parameter conventions.
- The error model — shape, status mapping, and what an error is permitted to reveal.
- Authentication by session cookie, session context switching, and how permission dependencies are declared.
- **Organization scoping** — the query parameter and body field that carry tenancy, and the two-gate enforcement behind them.
- Idempotency: what the platform guarantees today, what it does not, and how a client is expected to behave in the absence of a replay key.
- OpenAPI generation, documentation surfaces, and schema obligations.
- **Bulk operation patterns**, generalized from the logistics module, which is where Mercury's bulk semantics were first established.
- The WebSocket notification contract, insofar as it is part of the API surface.

Every rule here applies to all nine domain modules — `org`, `fleet`, `components`, `publications`, `personnel`, `maintenance`, `work_orders`, `planning`, `logistics` — and to any module added later.

### 1.2 Out of scope

| Concern | Authoritative location |
|---------|------------------------|
| Layering, module pattern, transaction boundaries | [Technical Architecture](../02_Architecture/Technical_Architecture.md) |
| Bounded contexts, aggregates, ubiquitous language | [Domain Architecture](../02_Architecture/Domain_Architecture.md) |
| Actors, external systems, deployment topology | [System Context](../02_Architecture/System_Context.md) |
| Column-level schema, identifier formats, enumerations | [Data Model](../04_Data/Data_Model.md) · [Master Data](../04_Data/Master_Data.md) |
| Permission matrices and role definitions | [RBAC](../06_Security/RBAC.md) |
| Session lifecycle, credential handling, identity | [Identity](../06_Security/Identity.md) |
| Audit record content and the action catalogue | [Audit](../06_Security/Audit.md) |
| Signature semantics and certification gates | [Digital Signatures](../06_Security/Digital_Signatures.md) |
| Python, SQLAlchemy, Pydantic, and test conventions | [Coding Standards](Coding_Standards.md) |
| Frontend consumption patterns | [UI Standards](UI_Standards.md) |

### 1.3 Honesty markers

Markers are used identically across the blueprint.

| Marker | Meaning |
|--------|---------|
| **Current** | Implemented in the runtime and exercised by tests |
| **Partial** | Present for a subset of the described scope |
| **Planned** | Specified here, not built |
| **Debt** | A known deviation from the target contract, tracked deliberately |

A rule written without a marker is **normative for all new and modified endpoints**, whether or not every existing endpoint already satisfies it.

---

## 2. Design principles

| # | Principle | Consequence |
|---|-----------|-------------|
| 1 | **The API is the product.** The vanilla JavaScript frontend is one client among several — integrators, partner systems, and future mobile clients are peers, not afterthoughts. | No endpoint may exist only to serve a screen's rendering convenience. No behaviour may depend on a client-side step. |
| 2 | **Additive evolution inside a version.** `/api/v1` grows; it does not change shape underneath a caller. | Adding a field, an optional parameter, or an endpoint is routine. Removing or renaming one is a version event. |
| 3 | **The server decides everything that matters.** Permissions, tenancy, invariants, limits, and defaults are enforced server-side. | A malicious or defective client cannot obtain a result an honest one could not. |
| 4 | **Tenancy is a parameter, never a trust.** `organization_id` states an *intent*; entitlement is verified before it is honoured. | See §7. |
| 5 | **Errors are contracts.** Status codes and messages are part of the API and are chosen deliberately, including what they refuse to disclose. | See §6. |
| 6 | **Uniformity beats local optimisation.** Two endpoints that do similar things use the same parameter names, ordering, and shapes. | A developer who knows one module's list endpoint knows all of them. |
| 7 | **Reads are cheap to attempt, writes are honest about failure.** Lists are bounded and paginated; mutations either complete fully or report precisely what did not. | See §5 and §9. |
| 8 | **Every mutation is attributable.** No write path exists that does not carry an actor into the audit trail. | See [Audit](../06_Security/Audit.md). |
| 9 | **Never claim more than the mechanism delivers.** An endpoint does not advertise idempotency, cryptographic strength, or asynchrony it does not have. | See §8 and [ADR-0006](ADR/ADR-0006-hash-signatures-before-pki.md). |
| 10 | **The contract is generated, not narrated.** OpenAPI is produced from the code's response models, so documentation cannot drift from behaviour. | See §10. |

---

## 3. URL structure and versioning

### 3.1 The version prefix

Every non-probe route lives under `/api/v1`. **Current.**

```text
https://<host>/api/v1/<domain>/<resource>[/<identifier>][/<sub-resource>][/<action>]
```

| Element | Rule |
|---------|------|
| Version | `v1` today. Exactly one major version is served at a time unless a migration window is explicitly announced. |
| Domain | The owning module: `fleet`, `components`, `publications`, `library`, `personnel`, `maintenance`, `work-orders`, `planning`, `logistics`. Organizations mount directly under `/api/v1`. |
| Resource | Plural, lower case, hyphenated: `purchase-orders`, `material-requests`, `job-cards`, `work-packages`. |
| Identifier | An opaque application-generated string. Never a database sequence number, never guessable, never meaningful. |
| Sub-resource | Plural and owned: `/tools/{tool_id}/history`, `/purchase-orders/{po_id}/lines`. |
| Action | A verb only where a state transition is not expressible as a resource write: `/job-cards/{id}/release`, `/stock/issue`, `/receipts/{id}/putaway`. |

Current module prefixes are enumerated in [Technical Architecture §3.3](../02_Architecture/Technical_Architecture.md#33-router-conventions). Prefixes do not overlap, so router registration order is irrelevant.

### 3.2 Routes outside the version prefix

| Route | Purpose | Authentication |
|-------|---------|----------------|
| `GET /health` | Liveness plus dependency detail | Public |
| `GET /ready` | Readiness for traffic | Public |
| `GET /live` | Process liveness | Public |
| `GET /metrics` | Prometheus exposition, disableable by configuration | Restricted at the edge |
| `GET /openapi.json` | Generated specification | Follows deployment policy |
| `GET /docs`, `GET /redoc` | Interactive documentation | Follows deployment policy |

Probes are deliberately unversioned: they are operational infrastructure, not a business contract, and an orchestrator must not have to track an API version to know whether a container is alive.

### 3.3 Action naming

Actions are **imperative and unambiguous**. `POST /api/v1/logistics/stock/issue`, not `POST /api/v1/logistics/stock/issuance`. Where an action is a certification step it is named for the step, matching the vocabulary in [Digital Signatures](../06_Security/Digital_Signatures.md): `complete-work`, `inspect`, `release`.

An action endpoint is justified when **any** of the following is true:

1. The transition has preconditions that a generic field update cannot express (job card release requires an ATA chapter, a publication revision, and a complete signature chain).
2. The transition writes records in other aggregates (release writes a signature, a certification event, a logbook entry, and component history).
3. The transition consumes a credential (any signing step).
4. The transition is not idempotent and must be explicitly requested (stock issue draws physical units).

Where none of those hold, use `PATCH` on the resource.

### 3.4 What may change inside `v1`

| Change | Permitted in `v1` | Notes |
|--------|-------------------|-------|
| Add an endpoint | **Yes** | The normal way Mercury grows |
| Add an optional query parameter with a safe default | **Yes** | Default must preserve prior behaviour exactly |
| Add a field to a response model | **Yes** | Clients must tolerate unknown fields — see §3.6 |
| Add an optional field to a request model | **Yes** | Required fields may not be added |
| Widen a validation rule | **Yes** | Previously valid input stays valid |
| Add an enumerated value | **Yes, with care** | Clients must not crash on an unrecognised value. Announce in [CHANGELOG.md](../../CHANGELOG.md) |
| Narrow a validation rule | **No** | Breaks callers that were valid yesterday |
| Rename or remove a field or parameter | **No** | Add the replacement, deprecate the original, remove in the next major version |
| Change a status code for an existing condition | **No** | Status codes are branch conditions in client code |
| Change a default page size downward | **No** | Silently truncates results for existing callers |
| Change the meaning of an existing value | **No** | The most damaging possible change, because nothing fails loudly |

### 3.5 Deprecation

A field or endpoint being retired is:

1. Marked deprecated in its OpenAPI description, stating the replacement and the earliest removal version.
2. Recorded in [CHANGELOG.md](../../CHANGELOG.md).
3. Kept functional for the whole life of the major version.
4. Removed only in `/api/v2`, alongside an [ADR](ADR/README.md) recording the removal.

Mercury does not use a `Sunset` header today. **Planned.**

### 3.6 Client obligations

A conforming client:

- Ignores response fields it does not recognise.
- Treats enumerated values as open sets, degrading to displaying the raw value rather than failing.
- Never constructs an identifier; it uses identifiers the API returned.
- Never depends on collection ordering that the endpoint did not document.
- Sends `Content-Type: application/json` on requests with a body.

---

## 4. Methods, status codes, and payload shapes

### 4.1 Method semantics

| Method | Use | Idempotent | Position |
|--------|-----|-----------|----------|
| `GET` | Read a resource or a collection. Never mutates, never audits as a mutation | Yes | **Current** |
| `POST` | Create a resource, or invoke an action | No, unless documented | **Current** |
| `PATCH` | Partial update; only supplied fields are applied | Yes in effect | **Current** — aircraft status, component life limits and time-cycles, publications, employees |
| `PUT` | **Not used for new endpoints.** Mercury has no full-replacement semantics, because replacing an aviation record wholesale is rarely the intent | Yes in effect | **Debt** — four existing routes use `PUT` with partial-update semantics: logistics part master, tool, and vendor updates, and the planning utilization write. They accept only the fields supplied and are therefore `PATCH` in behaviour and `PUT` in name |
| `DELETE` | Reserved for soft delete where a record must remain referenceable; never used on evidence | Yes in effect | **Planned** — no `DELETE` endpoint exists today. See §5.5 |

Two honest notes on this table:

**`PUT` is discouraged, not banned retroactively.** A full replacement invites a client to send a stale copy of an aggregate and silently revert a concurrent change; `PATCH` plus optimistic version checking makes that impossible. The four existing `PUT` routes already behave as partial updates — they apply only the fields the caller supplied — so their names are wrong rather than their semantics. Renaming them is a breaking change and therefore a `v2` item; **new update endpoints use `PATCH`.**

**There is no delete.** No endpoint deletes or soft-deletes a record. Records are retired by **status transition** — `cancelled`, `closed`, `scrapped`, `returned`, `archived` — which is the correct model for a domain in which a purchase order that was cancelled is a fact worth keeping. See §5.5 and [ADR-0005](ADR/ADR-0005-immutable-audit-and-history.md).

### 4.2 Status codes

| Code | Condition | Body |
|------|-----------|------|
| `200 OK` | Successful read, successful action, successful patch | The resource or result model |
| `201 Created` | Resource created. **Current** — creates declare `status_code=201` explicitly | The created resource, including its identifier |
| `204 No Content` | Soft delete with nothing meaningful to return | Empty |
| `400 Bad Request` | The request is well-formed but semantically impossible: a missing organization, a signing method that is not production-enabled, a step the task does not require | `{"detail": "..."}` |
| `401 Unauthorized` | No session cookie, or an expired session | `{"detail": "..."}` |
| `403 Forbidden` | Authenticated but not entitled: missing permission, or an organization the caller may not act in | `{"detail": "..."}` |
| `404 Not Found` | The record does not exist **or** belongs to another organization — deliberately indistinguishable | `{"detail": "..."}` |
| `409 Conflict` | An invariant or state-machine violation, a uniqueness collision, or an optimistic version mismatch | `{"detail": "..."}` |
| `422 Unprocessable Entity` | Schema validation failure, produced by Pydantic before the service is reached | FastAPI validation detail array |
| `429 Too Many Requests` | Rate limit exceeded. **Current** — accompanied by `Retry-After: 60` | `{"detail": "..."}` |
| `500 Internal Server Error` | Unhandled fault, logged with the request identifier that is also returned in the response headers | `{"detail": "..."}` |

`501`, `502`, and `503` are not produced by application code. `503` may be produced by the edge when the application is unavailable.

### 4.3 The 409 versus 422 boundary

This distinction is the most commonly confused one and is therefore normative:

| Situation | Code | Reason |
|-----------|------|--------|
| `qty` is the string `"abc"` | `422` | The request could not be parsed into the contract |
| `qty` is `-5` where the schema requires a positive value | `422` | The schema expresses the rule |
| `qty` is `500` and only `12` are available | `409` | The request is valid; the world does not permit it |
| A certification step is signed out of order | `409` | State machine violation |
| A warehouse code already exists in this organization | `409` | Uniqueness collision, surfaced from an integrity error |
| A version counter does not match the caller's expectation | `409` | Concurrent modification |

**Rule:** if the answer depends on data in the database, it is `409`. If it depends only on the request, it is `422`.

### 4.4 Payload conventions

| Concern | Rule |
|---------|------|
| Field naming | `snake_case` throughout, in requests and responses. The frontend does not camel-case Mercury payloads |
| Booleans | `true` / `false` JSON literals in the API. Where legacy tables persist flags as the strings `"true"` / `"false"`, the schema layer converts — the wire contract is never polluted by a storage compromise. See [Coding Standards §6.4](Coding_Standards.md#64-boolean-flags-and-the-string-flag-legacy) |
| Quantities and money | JSON numbers backed by fixed-precision decimals server-side. Never floating point in persistence or arithmetic. See [Coding Standards §6.3](Coding_Standards.md#63-decimals-quantities-and-money) |
| Timestamps | ISO 8601 in UTC. Stored naive-UTC by platform convention; serialized unambiguously |
| Dates | `YYYY-MM-DD` where a date has no meaningful time — certificate expiry, calibration due |
| Enumerations | Short lower-case strings, validated by pattern in the schema layer |
| Absent versus null | Omit a field to mean "do not change" in a `PATCH`; send `null` to mean "clear it". These are different requests |
| Empty collections | `[]`, never `null` |
| Identifiers | Opaque strings. A client treats them as tokens |
| Nesting depth | Two levels maximum in a response. Deeper relationships are separate endpoints, so a caller is not forced to fetch a subtree it does not need |

### 4.5 Detail models versus summary models

A module that has both exposes them explicitly, following logistics: `PurchaseOrderOut` for collection entries, `PurchaseOrderDetailOut` for a single record with its lines. A collection endpoint never returns the detail model — that is how an innocuous list call becomes a hundred-query page load.

---

## 5. Collections — pagination, filtering, sorting, search

### 5.1 Pagination

| Parameter | Type | Rule |
|-----------|------|------|
| `limit` | integer | Maximum records returned. Per-endpoint default, typically `100`, and `200` for high-cardinality ledger and balance reads. **Clamped server-side in the repository** — logistics clamps to a module ceiling of `500` and a floor of `1`, so a client cannot request an unbounded page or a zero-length one |
| `offset` | integer | Records skipped. Default `0`, clamped to a floor of `0` |

Clamping belongs in the repository, not the router, so that no caller — including another service — can bypass it:

```python
MAX_PAGE = 500

def _page(limit: int, offset: int) -> tuple[int, int]:
    return min(max(int(limit), 1), MAX_PAGE), max(int(offset), 0)
```

**Current shape:** list endpoints return a **bare JSON array** typed as `list[<Model>Out]`, with `limit` and `offset` as plain query parameters. This is the established contract across all nine modules and is not being changed inside `v1`.

```http
GET /api/v1/logistics/stock/balances?part_master_id=pm-77c1&limit=50&offset=100
```

```json
[
  {
    "id": "sb-4f2a",
    "part_master_id": "pm-77c1",
    "location_id": "loc-a12",
    "condition": "serviceable",
    "qty_on_hand": 42.000,
    "qty_reserved": 6.000
  }
]
```

**Planned — the pagination envelope.** A `total`, `limit`, `offset`, and `items` envelope is genuinely useful for pagers and for progress reporting, and its absence is a real gap: a client cannot currently distinguish "the last page" from "exactly a full page". Because introducing it would change the shape of every list response, it is **additive by new endpoint or by opt-in parameter**, never by mutating an existing response. The chosen mechanism is an opt-in `Prefer: envelope` style parameter under `/api/v1`, or bare arrays retiring in `/api/v2` — decided in an ADR before implementation, not here.

Interim client guidance: request `limit + 1` records; if you receive more than `limit`, there is at least one more page.

**Planned — cursor pagination** for the append-only ledgers (stock movements, audit records, certification events). Offset pagination over a table that is being appended to can skip or repeat rows between pages. For time-ordered ledgers a cursor over `(created_at, id)` is the correct mechanism, and it is required before any customer-facing export of movement history at volume.

### 5.2 Filtering

Filters are **optional, orthogonal, and combinable with AND**. A filter that is absent does not constrain.

| Parameter | Meaning | Example endpoints |
|-----------|---------|-------------------|
| `organization_id` | Tenancy scope — see §7 | Every tenant-scoped collection |
| `status_filter` | Filter by lifecycle status | Transfers, tools, material requests, purchase requests, RFQs, purchase orders, receipts, shipments, vendors, lost tool reports |
| `q` | Free-text search — see §5.4 | Parts, tools, vendors |
| `<relation>_id` | Filter by a related record | `warehouse_id`, `part_master_id`, `location_id`, `vendor_id`, `purchase_order_id`, `work_package_id`, `reference_id`, `source_id` |
| `<attribute>` | Filter by a classifying attribute | `location_type`, `part_class`, `movement_type`, `condition`, `serial_number`, `calibration_status`, `direction`, `source_type`, `vendor_type` |

**`status_filter`, not `status`.** This is a deliberate, platform-wide convention. In a FastAPI router, `status` is the imported `fastapi.status` module; a parameter of that name shadows it and produces a subtle class of bug in exactly the code that raises HTTP errors. The name is therefore `status_filter` everywhere, including in modules where the shadowing would not occur, because consistency across the platform is worth more than the marginally nicer name. **Current.**

Filter value rules:

- An empty string is treated as absent, not as a match on empty.
- An unknown filter parameter is ignored by FastAPI rather than rejected; clients must not rely on typos failing loudly.
- A filter naming a record in another organization yields an empty result, not an error — the organization scope is applied first.
- Multi-value filtering (`status_filter=open,closed`) is **Planned**. Today, issue one request per value.

### 5.3 Sorting

**Current:** each collection endpoint has a documented, stable default order — ledgers and evidence newest-first, catalogues by business code, plans by scheduled date. There is no `sort` parameter.

**Planned:** an explicit `sort` parameter of the form `sort=-created_at,code`, restricted to an allow-list of indexed columns per endpoint. The allow-list is not optional: permitting arbitrary sort columns is how a list endpoint becomes a full table scan on a table with fifty million rows.

### 5.4 Search

`q` is a **case-insensitive substring match over a documented set of business identifier and description fields** — for a part master, the OEM part number and description; for a tool, the tool number and description; for a vendor, the code and name. It is deliberately narrow and predictable.

`q` is not a query language. It does not support operators, wildcards, or field prefixes, and it will not be extended to do so; if Mercury needs real search, it will gain a search index and a distinct endpoint, recorded in an ADR. See [Knowledge Graph](../04_Data/Knowledge_Graph.md) for the graph-traversal reads that some search-shaped questions actually want.

### 5.5 Soft-deleted records

The soft-delete model is **half built, and the built half is the read side.**

| Aspect | Position |
|--------|----------|
| A `deleted_at` column on records that may be retired — warehouses, part masters, tools, maintenance programmes, MPD tasks, maintenance checks | **Current** |
| Every list and lookup query filtering `deleted_at IS NULL` | **Current** — the filter is in the repository, so no caller can forget it |
| An endpoint that sets `deleted_at` | **Planned** — none exists. Nothing in the runtime soft-deletes anything today |
| Retirement in practice | **Current** — by status transition: `cancelled`, `closed`, `scrapped`, `returned` |
| Evidence tables carrying a soft-delete concept at all | **Never.** Signatures, certification events, logbook entries, stock movements, component history, and audit records have no delete path, conventional or otherwise |

When a delete endpoint is added it will be a `DELETE` that sets `deleted_at`, is permission-gated, is audited, refuses to touch evidence, and refuses to retire a record that other live records depend on. Exposing soft-deleted records to a caller will require an explicit, permission-gated parameter and a marked deleted state in the response. Building the read filter first was the right order: it means adding the write side cannot accidentally resurrect deleted rows into existing screens. See [ADR-0005](ADR/ADR-0005-immutable-audit-and-history.md).

---

## 6. Errors

### 6.1 The error body

Mercury uses **FastAPI's native error shape**. **Current.**

```json
{ "detail": "Insufficient stock to reserve: requested 12.000, available 4.000" }
```

Validation errors carry FastAPI's structured array, which names the failing field path:

```json
{
  "detail": [
    {
      "type": "string_pattern_mismatch",
      "loc": ["body", "condition"],
      "msg": "String should match pattern '^(serviceable|unserviceable|quarantine|scrap)$'",
      "input": "broken"
    }
  ]
}
```

Every client reads `detail` first and falls back to a status-derived message — the pattern the frontend API module already implements. See [UI Standards §5](UI_Standards.md#5-the-api-module-is-the-only-door).

**Planned — a structured error envelope** carrying a stable machine-readable `code`, the human `message`, and the `request_id`. The gap is real: today a client that must branch on *which* conflict occurred has to match on message text, which is not a contract. The upgrade is additive — `detail` remains, with the envelope alongside — and is a named item in §14.

### 6.2 Writing a good `detail`

| Requirement | Example |
|-------------|---------|
| State what failed and why | `"Reserve per location: no single location can satisfy 40.000"` |
| Include the numbers that make it actionable | `"requested 12.000, available 4.000"` |
| Name the operation on a conflict | `"Stock adjust conflict"`, `"Certification conflict"`, `"Package generation conflict"` |
| Stay under roughly 200 characters | Messages are surfaced in operator toasts |
| Never include a credential, token, hash, stack trace, SQL fragment, or file path | — |
| Never reveal another organization's data, including its existence | See §6.3 |
| Never blame the user | Describe the state, not the person |

### 6.3 What an error must not disclose

**A record in another organization returns `404`, identical to a record that does not exist.** **Current.** Returning `403` would confirm that the identifier exists somewhere in the platform, which is an enumeration channel across tenants. The distinction between the two `403`/`404` cases is precise:

| Caller action | Result | Why |
|---------------|--------|-----|
| `GET /logistics/parts?organization_id=<org the caller may not act in>` | `403` | The caller asserted an entitlement it does not hold. Refusing the assertion discloses nothing about that organization's contents |
| `GET /logistics/parts/{id}` where the part belongs to another organization | `404` | The query was scoped to the caller's organization, so the record simply is not there. Indistinguishable from a bad identifier |

Both behaviours are correct and both are tested. Do not "improve" the second into a `403`.

### 6.4 Error mapping is centralised

Services raise `HTTPException` with the status codes above; integrity errors are translated to `409` by a single commit helper per service (`_commit_or_conflict`). Routers do not translate errors, and do not catch and re-raise them with different codes. A router that maps a service error is hiding a decision from the layer that should own it. See [Coding Standards §5.4](Coding_Standards.md#54-error-raising-and-the-commit-helper).

---

## 7. Authentication, authorization, and organization scoping

### 7.1 Session cookie authentication

**Current.** Authentication is a server-side session referenced by an opaque cookie.

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/auth/login` | Exchange operator credentials for a session cookie |
| `POST /api/v1/auth/logout` | Invalidate the session and clear the cookie |
| `GET /api/v1/auth/session` | Report whether the caller is authenticated, and the session's expiry |
| `GET /api/v1/auth/context` | Report the active organization, site, role, and the options available |
| `POST /api/v1/auth/context` | Switch the active organization or site, re-deriving the effective role |

Cookie attributes:

| Attribute | Value | Rationale |
|-----------|-------|-----------|
| Name | Configurable; `mercury_session` by default | Deployments behind shared hostnames can differentiate |
| `HttpOnly` | Always | Script cannot read the session, so a cross-site scripting defect cannot exfiltrate it |
| `Secure` | **Forced true** when the environment is production or HTTPS is enabled; startup validation refuses to boot a production configuration that would emit an insecure cookie | The platform cannot be misconfigured into sending sessions in clear text |
| `SameSite` | Configurable `lax` (default), `strict`, or `none`; anything else is coerced to `lax` | Cross-site request forgery mitigation with same-origin deployment |
| `Path` | `/` | One session for the application and its WebSocket |
| `Max-Age` | The configured session lifetime, one hour by default | Bounded exposure of a stolen cookie |

Why cookies rather than bearer tokens: the primary client is a same-origin browser application, and `HttpOnly` is a stronger guarantee than any discipline about where a token is stored in a page. See [Identity](../06_Security/Identity.md).

**Client rules.** Browser clients send `credentials: "include"` and never attempt to read the cookie. Server-to-server integrators authenticate through the same login endpoint and maintain a cookie jar. **Planned:** first-class machine credentials — service accounts with scoped, revocable API keys — so integrations stop borrowing a human operator's session. This is the most requested integration gap and it is named in §14.

**Debt:** sessions live in the application process's memory. A restart ends every session, and the application cannot run as more than one instance. This is the platform's binding scalability constraint, described in [Technical Architecture §15.1](../02_Architecture/Technical_Architecture.md#151-the-binding-constraint).

### 7.2 CSRF posture

Same-origin deployment (the web tier proxies `/api` and the WebSocket path), `SameSite` cookies, and JSON-only request bodies are the current mitigations. Mercury does not implement CSRF tokens. **Planned**, and required before any deployment that legitimately needs `SameSite=none`.

### 7.3 Gate 1 — endpoint permission

Every router endpoint declares a permission dependency. **Current.**

```python
@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(
    payload: WarehouseCreate,
    db: Session = Depends(get_db),
    session: Session_ = Depends(require_logistics_manage),
) -> WarehouseOut:
    return _svc(db).create_warehouse(payload, _actor(session))
```

| Rule | Detail |
|------|--------|
| Permission naming | `<domain>.<capability>` — `logistics.read`, `logistics.manage`, `logistics.stores`, `logistics.purchase`, `logistics.tools`, `fleet.manage`, `maintenance.read`, `work_order.manage` |
| Dependency naming | `require_<domain>_<capability>`, defined once per module and reused |
| Alternative permissions | A dependency may accept any of several permissions where a capability is legitimately shared — logistics reads are granted to planning, maintenance, and work-order readers, because a planner who cannot see stock cannot plan |
| Failure | `403` with a short message naming the requirement — `"Stores permission required"` |
| No endpoint without a dependency | An endpoint with no permission dependency is a defect, caught in review |

Permission definitions and role mappings are authoritative in [RBAC](../06_Security/RBAC.md).

### 7.4 Gate 2 — organization scoping

**This is the tenancy control, and it is enforced in the service layer, never in the router.**

| Surface | Mechanism |
|---------|-----------|
| `GET` collections and reads | Optional `organization_id` **query parameter** |
| `POST` and `PATCH` bodies | Optional `organization_id` **body field** |
| Absent | The caller's active session organization is used |
| Present | Honoured **only after** `assert_org_access` confirms entitlement; otherwise `403` |
| Empty or whitespace | `400 Bad Request` — `"Organization is required"` |

```python
def resolve_org_id(self, actor: ActorContext, requested_org_id: str | None = None) -> str:
    org_id = (requested_org_id or actor.organization_id or "").strip()
    if not org_id:
        raise HTTPException(status_code=400, detail="Organization is required")
    self.org.assert_org_access(username=actor.username, session_role=actor.role, organization_id=org_id)
    return org_id
```

Every tenant-aware service method begins by resolving the organization, and every repository query filters on it. A service method whose first statement is not a resolution — or which uses `actor.organization_id` directly instead of the resolved value — is a tenancy defect regardless of whether a test currently catches it. See [ADR-0003](ADR/ADR-0003-org-isolation-multitenancy.md).

**Cross-organization access** is available only to the administrator role, and every crossing is audited. A cross-organization read is not a side effect of a broad permission; it is an explicit, recorded act.

### 7.5 Gate 3 — certification authority

Signing endpoints apply a third, entirely separate set of checks — employee validity, signer binding to the authenticated user, credential verification, step authority, and distinct-signer enforcement. **A caller holding every permission in the system still cannot sign as an employee they are not bound to.** These gates are specified in [Digital Signatures §4.2](../06_Security/Digital_Signatures.md#42-the-enforcement-gate-at-every-signature) and must never be collapsed into a permission check.

### 7.6 Rate limiting

**Current.** Two independent per-minute budgets — one for authentication, one for general API traffic — keyed by client address with forwarded-header awareness, and disableable by configuration for test environments. Exceeding a budget yields `429` with `Retry-After: 60`.

**Debt:** counters are per process, so limits are per replica rather than per platform. Distributed rate limiting follows the shared session store in the dependency order in [Technical Architecture §15.2](../02_Architecture/Technical_Architecture.md#152-scaling-levers-in-dependency-order).

### 7.7 Request correlation headers

**Current.** Every response carries:

| Header | Meaning |
|--------|---------|
| `x-request-id` | Unique per request; echoed from the caller's `x-request-id` when supplied, otherwise generated |
| `x-correlation-id` | Echoed from the caller's `x-correlation-id`, otherwise equal to the request identifier; propagates across a multi-call workflow |
| `x-response-time-ms` | Server-side processing duration |

These identifiers are bound into every structured log line for the request. When reporting a fault, quote the `x-request-id`: it is the join key between a user's complaint and the platform's logs. Integrators should generate a stable `x-correlation-id` per business workflow.

---

## 8. Idempotency and safe retries

### 8.1 The honest position

**Mercury does not implement an `Idempotency-Key` header. Retrying a `POST` is not, in general, safe.** Stated plainly, because the alternative — implying replay protection that does not exist — would cause exactly the double-issue and double-receipt errors that inventory correctness depends on avoiding. **Planned**, and the highest-value item in §14 for integrators.

### 8.2 What is safe today, and why

| Category | Safety | Mechanism |
|----------|--------|-----------|
| `GET` on any endpoint | **Safe** | No mutation, no mutation audit |
| `PATCH` with the same body | **Safe in effect** | Applying identical values converges; the version counter increments and audit records each attempt |
| A status transition that is already in the target state | **Safe by rejection** | The state machine refuses the transition with `409`, naming the current status — `"Reservation is 'consumed'"` |
| Create with a unique business key — warehouse code, part number, task number, package number | **Safe by rejection** | A retry violates `UniqueConstraint(organization_id, code)`; the integrity error is translated to `409`. The duplicate is refused, not created |
| `POST /logistics/seed-demo` | **Idempotent by design** | Checks for existing demonstration data and reports `created: false` on a repeat |
| Certification signing | **Safe by rejection** | A step may be signed only once per task; a replay is `409` |
| Job card release | **Safe by rejection** | An already-released task cannot be released again; `409` |
| Reservation against a plan line | **Partially safe** | The reservation is keyed to its demand source, so re-planning updates rather than duplicating |
| **Stock receive, issue, adjust, transfer, scrap** | **NOT safe** | Each writes a new append-only movement. A retried issue draws stock twice. There is no natural key to collide with, because two genuine issues of the same part on the same day are legitimate |
| Purchase request, RFQ, purchase order, receipt creation | **NOT safe** | Each creates a new document with a generated number |

The pattern is worth naming: **Mercury's evidence and ledger design makes replays visible rather than silent.** A duplicated movement is a real, findable row in a ledger, not a corrupted balance of unknown provenance. That is a much better failure mode than the alternative, but it is not idempotency.

### 8.3 Client guidance until replay keys exist

1. **Use optimistic version checks on updates.** Send the `version` you read; a `409` tells you to re-read rather than overwrite.
2. **Never blind-retry an unsafe `POST`.** On a timeout or a `5xx`, **read back** — query the movement ledger by `reference_id`, the material request by work package, the purchase order by number — and only re-issue if the record is genuinely absent.
3. **Send `x-correlation-id`.** It is what makes the read-back audit-traceable, and what lets support determine whether the first attempt committed.
4. **Prefer bulk endpoints over loops.** One `bulk-adjust` with forty lines has one failure mode; forty sequential adjusts have forty. See §9.
5. **Treat `409` as information, not failure.** On a create with a business key, `409` frequently means your earlier attempt succeeded.

### 8.4 The planned mechanism

When implemented, replay protection will be:

| Property | Design |
|----------|--------|
| Header | `Idempotency-Key`, a client-generated opaque string |
| Scope | Per organization, per endpoint, per key |
| Storage | A persisted record of key, request digest, response status, and response body |
| Replay with an identical body | The stored response is returned, with the original status code |
| Replay with a different body under the same key | `409` — the key was reused for a different request, which is a client defect worth surfacing |
| Retention | A bounded window, long enough to cover realistic client retry behaviour |
| Applicability | Every non-`GET` endpoint; mandatory on stock movements, procurement documents, and signing |
| Prerequisite | Durable shared storage, which is the same prerequisite as the shared session store |

Until then, this document tells integrators the truth and gives them §8.3.

---

## 9. Bulk operation patterns

The logistics module established Mercury's bulk semantics, and they are normative for every module that adds bulk capability.

### 9.1 The three shapes

| Shape | Semantics | Example | When to use |
|-------|-----------|---------|-------------|
| **Atomic bulk** | All lines succeed or none do; one transaction, one rollback | Warehouse tree creation, transfer completion, receipt putaway | When the lines are one logical act and a partial result would be incoherent |
| **Per-line result bulk** | Each line is evaluated independently; the response reports per-line outcome; valid lines commit | `POST /logistics/stock/bulk-adjust` | When lines are independent and rejecting forty good corrections because of one bad one would be operationally hostile |
| **Orchestrated planning** | One call fans out across modules and returns a per-line resolution | `POST /logistics/material-planning`, `POST /logistics/tool-planning`, planning's package generation | When the platform, not the caller, should decide how demand is met |

### 9.2 The per-line result contract

The canonical example, **Current**:

```http
POST /api/v1/logistics/stock/bulk-adjust
Content-Type: application/json

{
  "reason": "Cycle count variance, aisle A, 2026-08-14",
  "lines": [
    { "part_master_id": "pm-77c1", "location_id": "loc-a12", "condition": "serviceable", "qty_delta": 3 },
    { "part_master_id": "pm-88d2", "location_id": "loc-a12", "condition": "serviceable", "qty_delta": -2 },
    { "part_master_id": "pm-99e3", "location_id": "loc-zz9", "condition": "serviceable", "qty_delta": 5 }
  ]
}
```

```json
{
  "applied": 2,
  "rejected": 1,
  "lines": [
    { "part_master_id": "pm-77c1", "location_id": "loc-a12", "condition": "serviceable", "qty_delta": 3.000, "applied": true, "message": "" },
    { "part_master_id": "pm-88d2", "location_id": "loc-a12", "condition": "serviceable", "qty_delta": -2.000, "applied": true, "message": "" },
    { "part_master_id": "pm-99e3", "location_id": "loc-zz9", "condition": "serviceable", "qty_delta": 5.000, "applied": false, "message": "Location not found" }
  ]
}
```

Normative rules for this shape:

| # | Rule | Rationale |
|---|------|-----------|
| 1 | **HTTP status is `200`, not `207`.** The request was processed exactly as specified | The per-line result *is* the answer. `207 Multi-Status` implies WebDAV semantics Mercury does not use, and clients handle it inconsistently |
| 2 | **`applied` and `rejected` counts are in the response root** | A caller can decide whether to alert a human without walking the array |
| 3 | **Every submitted line appears in the result, in submission order** | The caller can zip results back to its own input without matching on keys |
| 4 | **Each line carries `applied` and a `message`** — empty on success, specific on rejection | An operator reading the result must know exactly which line failed and why |
| 5 | **A rejected line changes nothing** | No partial application within a line |
| 6 | **A mandatory `reason`, minimum length one, maximum four hundred characters** | A bulk stock correction without a stated reason is an unexplained inventory change, which is unacceptable in an audited system |
| 7 | **One audit record for the operation**, carrying `applied`, `rejected`, and the truncated reason; per-line movement rows carry the detail | Forty audit records for one cycle count would bury the signal. The ledger holds the granularity |
| 8 | **`lines` has a minimum length of one** | An empty bulk request is a client defect, rejected at `422` |
| 9 | **`lines` has a documented maximum** | An unbounded bulk request is an unbounded transaction. Where a caller has more, it pages |
| 10 | **Validation that can be done per line is done per line** — a bad line does not `422` the whole request | Otherwise the shape provides nothing over a loop |

### 9.3 Choosing between atomic and per-line

Ask what a partial result means to the person receiving it.

- **Cycle count corrections:** independent facts about independent bins. Rejecting all forty because one bin code was mistyped wastes a stores keeper's afternoon. **Per-line.**
- **Warehouse hierarchy creation:** a building with no zones is not a partially created warehouse, it is a broken one. **Atomic.**
- **Work package generation:** a package whose material was not reserved would cause a planner to schedule work that cannot be performed. **Atomic**, and deliberately so — the reasoning is in [Technical Architecture §7.2](../02_Architecture/Technical_Architecture.md#72-why-this-is-one-transaction).

The test is not "which is easier to implement". It is **"which failure mode does the operator prefer".**

### 9.4 Orchestrated planning results

Material and tool planning accept a set of plan lines and return per-line resolution: available quantity, reserved quantity, resulting status, expected delivery where a purchase request was raised, and calibration status for tools. The caller does not tell the platform which location to draw from; the platform applies the part's issue policy — first expired, first out by default — and reports what it did.

Two properties are normative:

1. **Pessimistic initial state.** A parts plan line is created as a shortage with zero reserved, and is promoted only when stock is actually held. A line that failed to process therefore remains visibly short rather than defaulting to a comfortable lie.
2. **No silent splitting.** A reservation that no single location can satisfy is refused with a `409` instructing the caller to reserve per location, rather than being spread across two bins. A silent split produces a reservation that looks satisfiable but sends a picker to two places — a small operational lie that compounds.

### 9.5 Bulk read

Where a screen needs several collections, it issues concurrent requests rather than asking for a compound endpoint. The logistics workspace loads ten collections with one `Promise.all`, which is faster than any single aggregate endpoint would be and keeps each endpoint independently cacheable, testable, and permission-gated. A compound "workspace" endpoint is justified only when the server can compute something the client cannot — which is what the purpose-built dashboard endpoints (`/logistics/dashboard`, `/logistics/shortages`) exist for.

---

## 10. OpenAPI and documentation

### 10.1 Generation

**Current.** The specification is generated by FastAPI from the router signatures and Pydantic models. Title and version come from central configuration. Surfaces: `/openapi.json`, `/docs` (Swagger UI), `/redoc`.

A generated specification cannot drift from behaviour, which is the entire reason Mercury does not hand-maintain one. RC1 enrichment (`backend/app/openapi_docs.py`) adds tag catalog entries, auth/permission/validation descriptions, and documented error responses without changing handlers.

### 10.2 Obligations that make generation sufficient

| Obligation | Detail |
|------------|--------|
| **Every endpoint declares `response_model`** | Without it the schema is untyped and the response is unfiltered — the mechanism that stops internal columns leaking into a contract |
| **Every endpoint declares its `status_code`** where it is not `200` | So `201` appears in the specification |
| **Every module declares a `tags` value** | Tags are how the documentation is navigable: `organizations`, `fleet`, `components`, `publications`, `technical-library`, `personnel`, `maintenance`, `work-orders`, `planning`, `logistics` |
| **Request and response models are separate** | `PartMasterCreate`, `PartMasterUpdate`, `PartMasterOut` — never one model doing all three jobs |
| **Validation lives in the schema** | `Field(min_length=…, max_length=…)`, `pattern=…`, and constrained numerics all appear in the specification, so a caller learns the rule from the document rather than from a `422` |
| **Docstrings and `description` are written for an integrator** | The first line of a route docstring becomes its summary. Write it for someone who does not have the code |
| **Non-obvious semantics are stated in the description** | Idempotency status, bulk partial-success behaviour, audit consequences, required permission |

### 10.3 Exposure policy

| Environment | `/docs`, `/redoc`, `/openapi.json` |
|-------------|-----------------------------------|
| Development | Exposed |
| Internal staging | Exposed |
| Production | Restricted at the edge to trusted networks, or served to authenticated integrators only |

The specification enumerates every endpoint and every permission requirement. That is not secret, and Mercury's security does not depend on it being secret — but it is a map, and maps are given to partners rather than published.

### 10.4 Generated client artefacts

**Planned.** A published specification per release, plus generated client stubs for partner integration and contract tests generated from the specification. The prerequisite is the structured error envelope in §6.1, without which a generated client cannot branch on failure reliably.

---

## 11. Real-time notifications

**Current.** A WebSocket endpoint at `/api/v1/ws` delivers notifications. The connection is authenticated from the same session cookie **before acceptance**; an unauthenticated connection is refused, not accepted-then-closed. A five-second heartbeat keeps intermediaries from idling the connection out.

| Rule | Detail |
|------|--------|
| **Real-time is additive** | Every screen and every integration must remain correct and usable if the socket never connects. The socket informs; the API is the source of truth |
| **Messages are notifications, not state** | A message says something changed; the client re-reads through the API. A client that reconstructs state from a message stream will drift |
| **No authorization decision is delegated to the socket** | A notification never carries data the recipient could not have fetched |
| **Reconnection is the client's responsibility** | With backoff, and a full refresh on reconnect |

**Debt:** the connection registry is in process memory, so fan-out reaches only clients attached to that instance. Broker-backed fan-out follows the message bus in the dependency order in [Technical Architecture §15.2](../02_Architecture/Technical_Architecture.md#152-scaling-levers-in-dependency-order).

---

## 12. Non-functional requirements

### 12.1 Reading the targets

**Current baseline** is what the runtime demonstrably does. **Aspirational enterprise target** is a directional target for sizing and planning, not a service-level agreement. Figures align with [Technical Architecture §13](../02_Architecture/Technical_Architecture.md#13-non-functional-requirements).

### 12.2 Contract stability

| Requirement | Position |
|-------------|----------|
| Additive change only within `/api/v1` | **Current** |
| Every endpoint typed by a `response_model` | **Current** |
| Every endpoint gated by a permission dependency | **Current** |
| Every tenant-scoped endpoint resolves the organization in the service layer | **Current** |
| Generated OpenAPI matches runtime behaviour | **Current** — a consequence of generation, not of discipline |
| Machine-readable error codes | **Planned** — §6.1 |
| Contract tests per module boundary | **Planned** — prerequisite for any service extraction, see [ADR-0009](ADR/ADR-0009-modular-monolith-before-services.md) |

### 12.3 Performance

| Concern | Current baseline | Aspirational enterprise target |
|---------|------------------|-------------------------------|
| Request timing | Measured per request, returned as `x-response-time-ms`, exposed as Prometheus histograms | Unchanged |
| Read latency | Measured, not committed | 95th percentile under 300 ms |
| Write latency | Measured, not committed | 95th percentile under 800 ms |
| Certification signing | One short transaction with a row lock | 95th percentile under 500 ms |
| Aircraft release | Adds logbook and component history to the same transaction | 95th percentile under 1 second |
| List endpoints | Server-clamped limits, indexed organization filter | Unchanged, plus cursor pagination on ledgers |
| Bulk adjust | Bounded line count, one transaction | Under 2 seconds for 200 lines |
| Package generation | Bounded by a caller-supplied job card ceiling | Under 5 seconds for 200 job cards |
| Dashboard endpoints | Aggregate across modules on demand | Under 1 second from purpose-built read models |
| Concurrency | Single worker | 500 concurrent authenticated sessions per tenant |

### 12.4 Reliability and availability

| Concern | Current baseline | Aspirational enterprise target |
|---------|------------------|-------------------------------|
| Availability | Single process; no published figure | 99.9 percent monthly for the API |
| Session survival across restart | Sessions are lost; callers re-authenticate | Sessions survive rolling deployment |
| Retry safety on unsafe writes | Read-back guidance only — §8.3 | `Idempotency-Key` replay protection |
| Rate limit accuracy | Per process | Per platform |
| Graceful degradation | Not differentiated | Read-only continuation while the write path is degraded |

### 12.5 Observability

| Capability | Position |
|------------|----------|
| Request and correlation identifiers on every response, bound into logs | **Current** |
| Structured JSON logging with user binding | **Current** |
| Prometheus request rate, latency, login outcome, rate-limit blocks, active sessions | **Current** |
| Audit of authenticated mutating API calls | **Current** |
| Distributed tracing across containers | **Planned** |

### 12.6 Compatibility

| Requirement | Position |
|-------------|----------|
| Clients tolerate unknown response fields | **Normative client obligation** — §3.6 |
| Enumerations treated as open sets | **Normative client obligation** |
| No client depends on undocumented ordering | **Normative client obligation** |
| Deprecations announced before removal | **Current** — via OpenAPI description and [CHANGELOG.md](../../CHANGELOG.md) |

---

## 13. Security considerations

**Two gates always; three when signing.** Endpoint permission and organization access are independent and both mandatory on every tenant-scoped call. Signing adds employee validity, signer binding, credential verification, step authority, and distinct-signer checks. No gate substitutes for another, and no internal call path bypasses them: cross-module calls carry the caller's username and session role, and the peer service re-asserts.

**Cross-tenant identifiers are not probeable.** `404` for another organization's record is a security control, not an inconvenience. The `403`-versus-`404` split in §6.3 is deliberate and tested.

**Validation happens before the domain sees the request.** Pydantic validates at the router boundary, so services operate on well-formed data. This also means every validation rule is in the OpenAPI specification, which is why "the schema is the documentation" is a security property as well as a convenience.

**Errors do not leak.** No `detail` carries a credential, token, hash, stack trace, SQL fragment, internal path, or another organization's data. Unhandled faults return a generic message plus the request identifier; the diagnostic detail is in the log, which is where it belongs.

**Cookies are hardened by configuration validation, not by hope.** `HttpOnly` always; `Secure` forced under production or HTTPS, with startup refusing to boot an unsafe combination; `SameSite` coerced to a valid value. A misconfiguration that would emit sessions in clear text is a startup failure rather than a silent risk.

**Rate limiting protects the login path separately.** Authentication has its own budget, because credential stuffing has a different shape from ordinary API traffic.

**Bulk endpoints are audited as one operation with a mandatory reason.** A bulk stock correction cannot be performed anonymously or without explanation, and the per-line ledger rows preserve the granularity an investigator needs.

**Permission-gated documentation, not security by obscurity.** Restricting `/docs` in production reduces reconnaissance; it is not a control. Every endpoint is safe when its specification is known.

**Known API-layer security debt**, tracked openly: no `Idempotency-Key` replay protection, no CSRF tokens, no machine credentials distinct from operator sessions, message-text-only error discrimination, per-process rate limiting, in-memory sessions, and no automated dependency-vulnerability gate in the build. Full posture: [SECURITY.md](../../SECURITY.md), [Identity](../06_Security/Identity.md), [RBAC](../06_Security/RBAC.md), [Audit](../06_Security/Audit.md), [Digital Signatures](../06_Security/Digital_Signatures.md).

---

## 14. Scalability considerations

### 14.1 What the API contract must not prevent

The contract is designed so that the platform can scale without a breaking change:

| Property | How the contract preserves it |
|----------|------------------------------|
| Stateless request handling | No endpoint depends on server-side per-request state beyond the session, which is externalizable |
| Horizontal replicas | Nothing in the contract identifies which instance served a request |
| Read replicas | Read endpoints are separable from writes by method and path |
| Asynchronous side effects | Actions return the resource plus the resolution the caller needs, not a promise that side effects already fanned out |
| Cursor pagination | `limit` and `offset` are optional parameters; a cursor parameter can be added additively |
| Partitioned ledgers | Ledger reads are already time-ordered and filterable, which is what partition pruning needs |

### 14.2 Query-level scaling

| Pattern | Status |
|---------|--------|
| List endpoints capped, with limits clamped server-side rather than trusted | **Current** |
| Organization filter on every tenant query, backed by an index | **Current** |
| Composite indexes matching real filter combinations | **Current** |
| Summary models on collections, detail models on single reads | **Current** |
| Bounded bulk and generation loops | **Current** |
| Cursor pagination on ledgers | **Planned** |
| Sort allow-lists on indexed columns | **Planned** |
| Purpose-built read models for dashboards and the aircraft passport | **Planned** |

### 14.3 The known constraint

The application runs as a single process because sessions, approvals, rate-limit counters, and WebSocket connections live in its memory. Every other API-level scaling improvement — distributed rate limiting, replica-safe real-time fan-out, replay-key storage, zero-downtime deployment — is downstream of externalizing that state. This is stated identically in [Technical Architecture §15.1](../02_Architecture/Technical_Architecture.md#151-the-binding-constraint) because it is the same constraint, not a separate one.

### 14.4 What must survive any scaling change

- Organization isolation on every call, on every replica.
- Two-gate authorization, and the third gate on signing.
- `404` rather than `403` for another organization's records.
- Ordered certification enforcement and distinct-signer rules.
- Atomic release plus logbook creation.
- Stock reservation correctness under concurrency.
- A complete audit trail, with no gap introduced by asynchrony.

---

## 15. Future enhancements

| # | Enhancement | Value | Depends on |
|---|-------------|-------|------------|
| 1 | `Idempotency-Key` replay protection | Safe retries for stock movements, procurement documents, and signing — the largest integration gap | Durable shared storage |
| 2 | Structured error envelope with stable machine-readable codes | Clients branch on codes rather than message text | Error taxonomy definition |
| 3 | Machine credentials — scoped, revocable service accounts | Integrations stop borrowing operator sessions | Identity extension, see [Identity](../06_Security/Identity.md) |
| 4 | Pagination envelope with total count | Real pagers, and progress reporting on long lists | ADR on introduction path — opt-in or `v2` |
| 5 | Cursor pagination on append-only ledgers | Correct, stable paging over growing history | Item 4 |
| 6 | Explicit `sort` parameter with per-endpoint allow-lists | Client-controlled ordering without unbounded scans | Index review |
| 7 | Multi-value and range filters | Fewer round trips for real operational queries | Query builder extension |
| 8 | CSRF tokens | Enables deployments that need `SameSite=none` | Session extension |
| 9 | Distributed rate limiting | Accurate limits at any replica count | Shared session store |
| 10 | Published specification per release, plus generated client stubs | Partner integration without hand-written clients | Item 2 |
| 11 | Contract tests generated from the specification | Boundaries verified mechanically; prerequisite for extraction | Items 2 and 10 |
| 12 | Webhooks for domain events | Push integration instead of polling | Transactional outbox and message bus |
| 13 | Bulk endpoints for high-volume receiving and putaway | Warehouse-scale operations in one call | §9.2 shape, already established |
| 14 | Field selection and expansion on read | Smaller payloads for constrained clients | Response model introspection |
| 15 | Long-running operation endpoints with status polling | Package generation and large exports without long-held connections | Job scheduling |
| 16 | Read-only replica routing for dashboard and reporting endpoints | Analytical load off the primary | Database topology |
| 17 | `Sunset` and `Deprecation` headers | Machine-visible deprecation signalling | Item 2 |
| 18 | OpenAPI-driven request example library per endpoint | Faster integrator onboarding | Documentation effort |

Sequencing is tracked in [ROADMAP.md](../../ROADMAP.md). Any item that changes an existing contract requires an ADR before implementation.

---

## 16. Endpoint review checklist

Before merging any new or modified endpoint, confirm every line:

- [ ] Mounted under `/api/v1/<domain>`, plural hyphenated resource, action name imperative if an action.
- [ ] Method matches semantics; `PUT` not used.
- [ ] `response_model` declared; `status_code=201` on create.
- [ ] Separate `Create`, `Update`, and `Out` schemas; validation expressed with `Field` constraints and patterns.
- [ ] Permission dependency attached, named `require_<domain>_<capability>`.
- [ ] `organization_id` accepted as an optional query parameter (reads) or body field (writes).
- [ ] The service method's first act is `resolve_org_id`; every repository query filters on the resolved organization.
- [ ] Collections accept `limit` and `offset`, with the limit clamped server-side and a documented default order.
- [ ] Filters follow the naming convention, including `status_filter` rather than `status`.
- [ ] Status codes match §4.2; the `409`-versus-`422` boundary in §4.3 is respected.
- [ ] Another organization's record returns `404`, not `403`.
- [ ] `detail` messages are actionable and disclose nothing per §6.2 and §6.3.
- [ ] Mutations write an audit record with actor, action, target, and business detail; bulk operations audit once with counts and a mandatory reason.
- [ ] Idempotency status is documented in the endpoint description, honestly.
- [ ] Bulk endpoints follow §9.2 exactly: `200`, root counts, every line in order, per-line `applied` and `message`, bounded line count.
- [ ] Tests cover the happy path, the tenancy boundary, the permission boundary, and every invariant. See [Coding Standards §9](Coding_Standards.md#9-testing).
- [ ] Nothing in the change contradicts [ADR-0001](ADR/ADR-0001-vanilla-js-fastapi-aeos.md), [ADR-0003](ADR/ADR-0003-org-isolation-multitenancy.md), [ADR-0004](ADR/ADR-0004-repository-service-router.md), or [ADR-0005](ADR/ADR-0005-immutable-audit-and-history.md).

---

## 17. Related documents

**Standards set**
[UI Standards](UI_Standards.md) · [Coding Standards](Coding_Standards.md) · [ADR register](ADR/README.md)

**Architecture**
[Technical Architecture](../02_Architecture/Technical_Architecture.md) · [Enterprise Architecture](../02_Architecture/Enterprise_Architecture.md) · [Domain Architecture](../02_Architecture/Domain_Architecture.md) · [System Context](../02_Architecture/System_Context.md)

**Data and digital thread**
[Data Model](../04_Data/Data_Model.md) · [Master Data](../04_Data/Master_Data.md) · [Digital Thread](../04_Data/Digital_Thread.md) · [Knowledge Graph](../04_Data/Knowledge_Graph.md)

**Security**
[Identity](../06_Security/Identity.md) · [RBAC](../06_Security/RBAC.md) · [Audit](../06_Security/Audit.md) · [Digital Signatures](../06_Security/Digital_Signatures.md) · [SECURITY.md](../../SECURITY.md)

**Governing decisions**
[ADR-0001 — Vanilla JS and FastAPI](ADR/ADR-0001-vanilla-js-fastapi-aeos.md) · [ADR-0003 — Organization isolation](ADR/ADR-0003-org-isolation-multitenancy.md) · [ADR-0004 — Repository, service, router](ADR/ADR-0004-repository-service-router.md) · [ADR-0005 — Immutable audit and history](ADR/ADR-0005-immutable-audit-and-history.md) · [ADR-0007 — Logistics as an integrated program](ADR/ADR-0007-logistics-as-integrated-program.md)

**Repository root**
[README](../../README.md) · [VISION](../../VISION.md) · [ROADMAP](../../ROADMAP.md) · [CONTRIBUTING](../../CONTRIBUTING.md) · [CHANGELOG](../../CHANGELOG.md)

---

*Mercury Technologies — One Digital Thread. One Digital Aircraft Passport. One Aviation Enterprise Operating System.*
