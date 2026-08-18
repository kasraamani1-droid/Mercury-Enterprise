# ADR-0006 — Hash-attested signatures now; certificate-backed PKI later, without faking it

| Field | Value |
|-------|-------|
| Status | **Accepted** |
| Date | 2026-08-14 |
| Deciders | Lead architect, security lead, compliance lead |
| Affects | [Digital Signatures](../../06_Security/Digital_Signatures.md) · [Identity](../../06_Security/Identity.md) · [Audit](../../06_Security/Audit.md) · [API Standards](../API_Standards.md) · [UI Standards](../UI_Standards.md) · [SECURITY.md](../../../SECURITY.md) |
| Supersedes | — |
| Superseded by | — |

---

## Context

A maintenance release is a legal act. When an ACA holder returns an aircraft to service, they attest — personally, and with professional consequence — that the work was performed and inspected under the applicable instructions. The record of that act is what an authority, a lessor, or a purchaser later relies on.

Mercury must therefore record signatures. The question is **what kind of signature the platform can honestly deliver today**, and how to describe it.

The full cryptographic answer — a certificate under the signer's sole control, validated to a trust anchor, with revocation checking and a trusted timestamp — is the correct long-term target. It is also not primarily a cryptography problem. The cryptography is straightforward; what it requires is:

- Key management infrastructure, and a decision about where private keys live.
- Certificate lifecycle handling: issuance, renewal, revocation, and the operational processes around each.
- A relationship with a timestamp authority.
- Long-term validation evidence retention, so a signature made in 2026 is still verifiable in 2050.
- Smart card or token distribution and support for a shop-floor workforce.

None of that can be delivered as a sprint, and none of it should be simulated. This creates the specific temptation this ADR exists to foreclose: **a platform can very easily store a hash, label the method `pki`, set a flag called `pki_ready`, and let every downstream consumer assume a cryptographic signature exists.** That would produce an impressive-looking method field and a corrupt evidence chain. An auditor, an integrator, or a future engineer would reasonably read the record as cryptographically signed, and they would be wrong.

The platform therefore needs a mechanism that is genuinely strong within its limits, and a **description of that mechanism that is exactly accurate.**

---

## Decision

**Implement signatures as hash-attested, credential-verified, authority-checked records with strong integrity and attribution. Do not claim cryptographic non-repudiation. Refuse — do not simulate — signing methods that are not production-enabled. Design the record so that certificate-backed signing is additive when the infrastructure exists.**

### 1. What a signature record is

A signature captures the organization, the signer's employee identifier and username, the method, the purpose expressed as `certification.<step>`, the target type and identifier, the signing timestamp, notes, and a **SHA-256 digest over a canonical payload** composed of organization, task, step, employee, username, method, timestamp, and notes.

It also records method attestation flags: whether a PIN was verified, whether a password was confirmed, and whether the method was PKI, smart card, or biometric-ready.

### 2. The two methods that work, and the three that are refused

| Method | Behaviour | Verification |
|--------|-----------|--------------|
| `password` | **Signs** | The presented credential is verified against the operator directory for the authenticated user |
| `pin` | **Signs** | The presented PIN is matched against the employee's active inspection stamps using a **constant-time comparison** |
| `pki` | **Refused with `400`** | Not production-enabled |
| `smart_card` | **Refused with `400`** | Not production-enabled |
| `biometric_ready` | **Refused with `400`** | Not production-enabled |

**A refused method creates nothing.** No signature record, no certification event, no flag suggesting a cryptographic act occurred. The request fails with a message stating the method is not production-enabled.

**This refusal is a feature, and it is the operative decision of this ADR.** A signature record with `pki_ready` set and no certificate behind it would be a lie in the evidence chain. Refusing is the only defensible behaviour. The flags exist to mark the **data model's readiness** for real providers, not to imply a capability.

### 3. Authority is checked independently of permissions

Signing applies a third gate, entirely separate from endpoint permission and organization access:

| Check | Question |
|-------|----------|
| Employee validity | Does this employee exist, in this organization, and are they active? |
| Signer binding | Is this employee bound to the authenticated user making the request? |
| Credential verification | Was a credential appropriate to the declared method presented and verified? |
| Step authority | Does this employee hold the authority the step demands, including ACA where required? |
| Distinct signer | Has this employee already signed a step that must be signed by someone else? |

**A user holding every permission in the system still cannot sign as an employee they are not bound to.** This separation is deliberate and must never be collapsed into a permission check.

### 4. What Mercury claims, stated exactly

| The mechanism **does** establish | The mechanism **does not** establish |
|----------------------------------|--------------------------------------|
| The recorded content has not been altered since it was written, verifiable by recomputing the digest | That a private key under the signer's **sole control** was used |
| Which named employee's authority was exercised, verified against active, unexpired qualifications at that moment | That the signer cannot later plausibly deny signing, to a third party, without Mercury's cooperation |
| Which authenticated account performed the act | Any assurance independent of trusting the Mercury platform and its database |
| **How** the signer was verified — password against the directory, or PIN against an active stamp | A signature verifiable by an external party using only public information |
| That the ordered chain of steps was satisfied by distinct, authorized persons | A certificate chain to a trusted authority, revocation status, or timestamp authority attestation |
| That the release cites an immutable revision, snapshotted into the record | Long-term cryptographic validity independent of the platform's continued existence |

**The honest summary, which appears in the product documentation and not only here:** Mercury's signature is trustworthy **because Mercury's controls are trustworthy**. A cryptographic signature would be trustworthy **regardless**. That is the gap.

### 5. The PKI path is additive

| Property of the plan | Detail |
|---------------------|--------|
| **Additive, not a replacement** | Existing signatures remain valid records of what they were. New signatures carry cryptographic evidence **in addition to** the digest |
| **The canonical payload is reused** | It is already deterministic and complete, so it becomes the signed content without redesign. This is why the payload is defined precisely |
| **The refusal becomes an acceptance** | `pki` and `smart_card` stop being rejected once a real provider exists, and the `_ready` flags gain meaning |
| **Historical records are never retro-signed** | A signature made under the hash mechanism is never presented as cryptographic. Retroactively signing old evidence would be a fabrication |

---

## Consequences

### Positive

| Consequence | Detail |
|-------------|--------|
| **No record in the evidence chain overstates its own strength** | The single most important property. It is what makes every other claim in the platform credible |
| **Genuine integrity and attribution today** | The digest detects alteration through the application; the gates establish who exercised what authority, verified at that moment |
| **A meaningful step-up beyond an active session** | Re-presenting a credential at the moment of signing is materially stronger than an authenticated session alone |
| **The PIN method ties the act to a physical stamp** | Matched against active inspection stamps issued by the quality organization, with constant-time comparison so a stamp code cannot be recovered by timing |
| **Authority is enforced independently of permissions** | The gate structure means a broad permission grant cannot become signing authority |
| **The upgrade path is real, not aspirational** | Because the canonical payload already exists in the form a cryptographic signature would sign |
| **Audits are survivable** | An assessor asking "is this a digital signature in the PKI sense" receives a precise answer with the mechanism documented, rather than a claim that collapses under questioning |
| **Customers can make an informed decision** | Some will accept the current mechanism; some will wait for certificates. Both are better outcomes than a customer discovering the difference after deployment |

### Negative

| Consequence | Mitigation |
|-------------|-----------|
| **Both working methods are shared secrets** | Whoever knows the secret can produce the signature — precisely the limit public-key cryptography removes. Stated openly; PKI is the answer, not a mitigation |
| **No third-party verifiability** | A signature cannot be validated by an external party using public information. This is the substantive commercial gap and it is named in the roadmap |
| **Immutability is conventional, not structural** | A sufficiently privileged database credential could alter a signature row and recompute its digest, because the digest is over content the same actor controls. See [ADR-0005](ADR-0005-immutable-audit-and-history.md) |
| **No hash chaining across signatures** | Each digest protects one record. Deleting an entire signature and its certification event leaves a gap detectable by workflow reasoning but not by cryptography |
| **No multi-factor authentication at signing** | A stolen password suffices for a `password`-method signature. **Planned** |
| **Credential hashing for login passwords is Argon2id** | Delivered for directory credentials; MFA at signing remains **Planned**, documented in [Identity](../../06_Security/Identity.md) |
| **No trusted timestamp** | The timestamp is the platform's clock, not an authority's attestation |
| **The administrator signing override weakens attribution** | **Debt**, documented in [Identity](../../06_Security/Identity.md). The acting username is captured in the hashed payload, which limits but does not remove the concern |
| **Refusing `pki` will occasionally lose a deal** | Accepted. A customer who buys on a false claim is a worse outcome than a customer who buys a competitor's product |
| **ACA independence from inspector and performer is not enforced** | **Debt**, documented in [Digital Signatures](../../06_Security/Digital_Signatures.md) |

### Operational

- Stamp PIN issuance and revocation are quality-organization processes that the platform depends on; a stamp that should have been withdrawn and was not is an authority-management failure the platform cannot detect.
- Signature verification today is a platform operation: recomputing a digest requires the canonical payload, which requires the platform. An external auditor cannot verify independently, which is a limitation to state in advance of an audit rather than during one.
- When PKI arrives, both mechanisms coexist. Records must remain distinguishable by mechanism forever, so that a hash-attested signature is never later presented as a certificate-backed one.

---

## Alternatives considered

### 1. Implement full PKI signing before releasing the certification chain

**Rejected on sequencing, not on merit.** It is the correct end state. Rejected as a precondition because the dependencies — key management, certificate lifecycle, revocation, a timestamp authority relationship, long-term validation evidence, and token distribution to a shop-floor workforce — would have delayed the entire maintenance execution and certification capability by a long margin. The mechanism delivered is genuinely useful, honestly described, and designed so the upgrade is additive. Delivering nothing while waiting for perfect cryptography would have served no operator.

### 2. Accept `pki` and `smart_card` as method values, store a hash, and set the readiness flags

**Rejected, emphatically. This is the alternative this ADR exists to refuse.** It costs nothing to implement and it would make the method field look complete. It was rejected because a downstream consumer — an auditor, an integrator, a future engineer, a customer's compliance officer — would reasonably read `method: pki` with `pki_ready: true` as a cryptographic signature. The record would be a lie in the evidence chain, and a platform that lies about one record's strength has no credible claim about any record. **Refusing is the only defensible behaviour**, and the refusal is implemented and tested.

### 3. Use a platform-held key pair to produce real cryptographic signatures on the signer's behalf

**Rejected.** Superficially attractive: real cryptography, no token distribution, verifiable digests. Rejected because a key the platform controls does not establish anything about the signer — it establishes that **Mercury** signed. That is a *weaker* claim dressed as a stronger one, because it invites the reader to assume sole control that does not exist. The current mechanism at least makes the trust dependency on Mercury explicit rather than concealing it behind a signature value.

### 4. Simple username-and-password confirmation with no digest

**Rejected.** Less work, and the credential step-up would still be present. Rejected because the digest provides genuine, cheap value: it detects alteration of the recorded content through the application, and it establishes the canonical payload that a future cryptographic signature will sign. Omitting it would have made the PKI upgrade a redesign instead of an addition.

### 5. Biometric signing

**Rejected for now, and the method value is refused rather than simulated.** Biometrics on shared shop-floor devices raise enrolment, spoofing, hygiene, and data-protection questions that are not resolved by adding a flag. The `biometric_ready` value marks model readiness only, and attempting to sign with it fails.

### 6. Blockchain or distributed-ledger anchoring of signatures

**Rejected as a mechanism; the useful subset is retained as a roadmap item.** A public ledger would provide third-party-verifiable existence and ordering, and it is frequently proposed for exactly this problem. Rejected because it does not solve the actual gap — sole control of a signing key — and because it introduces external dependency, cost, latency, and data-protection exposure for records that must persist for decades. **External anchoring of periodic hash-chain checkpoints** is the valuable subset and is planned under [ADR-0005](ADR-0005-immutable-audit-and-history.md): it gives third-party-verifiable integrity without putting aviation records on a public ledger.

### 7. Describe the current mechanism as a "digital signature" without qualification

**Rejected.** It is the industry's common usage and it would simplify marketing materials. Rejected because the term carries a specific meaning to security assessors and regulators, and using it loosely for a shared-secret hash attestation would be a misrepresentation. Mercury uses the term and **immediately qualifies it** — in the product, in the blueprint, and in customer conversations.

---

## Compliance and security impact

| Concern | Impact |
|---------|--------|
| **Isolation** | The signing employee must exist in the task's organization and be active; a signer from another organization is refused. Tenancy is part of the certification gate, not merely of data access. See [ADR-0003](ADR-0003-org-isolation-multitenancy.md) |
| **RBAC** | Signing authority is **not** a permission. Permissions gate whether an endpoint may be called; certification authority gates whether this employee may sign this step. A wildcard permission does not confer signing authority |
| **Audit** | Every signature, every refused signing attempt, and every gate failure is audited inside the business transaction. A signature that could not be audited does not exist |
| **Signatures** | This ADR defines the signature model and its limits |
| **Regulatory evidence** | Supports the expectations that maintenance actions are attributable to named, qualified individuals, that records establish what authorised the action through immutable revision binding, and that independence of inspection is demonstrable. It does **not** satisfy any requirement that specifies certificate-based electronic signatures — where a customer or authority requires that, Mercury's current mechanism does not meet it, and saying so early is the only acceptable conduct |
| **Non-repudiation** | **Not provided.** Attribution and integrity are provided. The distinction is stated wherever the mechanism is described |
| **Data protection** | Signature records permanently bind named individuals to acts, which is an airworthiness requirement. Credentials and PINs are verified and discarded, never stored in a signature, never logged, never audited |
| **Cryptographic hygiene** | SHA-256 over a deterministic canonical payload; constant-time comparison for PIN verification; no credential material in any record. Login passwords use Argon2id (see [Identity](../../06_Security/Identity.md)) |
| **Known debt, restated** | Shared-secret methods; no third-party verifiability; conventional rather than structural immutability; no hash chaining; no multi-factor at signing; no trusted timestamp; the administrator override; ACA independence not enforced; attachments not in integrity-checked storage. Every one appears in [SECURITY.md](../../../SECURITY.md) |

---

## Related documents

**Security**
[Digital Signatures](../../06_Security/Digital_Signatures.md) · [Identity](../../06_Security/Identity.md) · [Audit](../../06_Security/Audit.md) · [RBAC](../../06_Security/RBAC.md) · [SECURITY.md](../../../SECURITY.md)

**Architecture**
[Technical Architecture §5](../../02_Architecture/Technical_Architecture.md#5-data-flow--job-card-certification-to-technical-logbook) · [Domain Architecture](../../02_Architecture/Domain_Architecture.md)

**Standards**
[API Standards §7.5](../API_Standards.md#75-gate-3--certification-authority) · [UI Standards §8.3](../UI_Standards.md#83-confirmation-patterns) · [Coding Standards](../Coding_Standards.md)

**Business context**
[Authority](../../03_Business/Authority.md) · [MRO](../../03_Business/MRO.md) · [CAMO](../../03_Business/CAMO.md) · [Leasing](../../03_Business/Leasing.md)

**Related decisions**
[ADR-0005 — Immutable audit and history](ADR-0005-immutable-audit-and-history.md) · [ADR-0002 — Digital Thread as the spine](ADR-0002-digital-thread-as-spine.md) · [ADR-0008 — Advisory AI](ADR-0008-advisory-ai-never-auto-release.md) · [ADR-0010 — Blueprint as SSOT](ADR-0010-blueprint-as-ssot.md)

---

*Mercury Technologies — One Digital Thread. One Digital Aircraft Passport. One Aviation Enterprise Operating System.*
