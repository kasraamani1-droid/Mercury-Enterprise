# Mercury Digital Twin — Architecture

**Program 15** · Complete digital lifecycle of every aviation asset.

## Positioning

Mercury Digital Twin is **not a 3D model**. It is the permanent digital lifecycle registry for aircraft, engines, APUs, landing gear, components, tools, GSE, facilities, organizations, and personnel.

- Every twin has a permanent UUID
- Every twin links to a Fabric **Digital Passport** (passports never disappear)
- History is **append-only / immutable**
- Ownership may change; history never changes
- Reliability and AI Q&A surfaces are **architecture readiness only**
- Future 3D visualization is metadata-ready (`visualization_ready`)

## Package

`backend/app/twin/` → API `/api/v1/twin`  
Permissions: `twin.read` / `twin.manage`  
Alembic: `20260814_0018`

## Layers

| Layer | Responsibility |
|-------|----------------|
| Twin Object | Lifecycle registry + identity |
| Fabric Passport | Permanent identity / thread spine |
| Twin History | Typed immutable history entries |
| Twin Configuration | Current / previous / planned baselines |
| Twin Reliability | MTBUR/MTBF/… architecture snapshots |
| Twin Search | Serial / passport / type search projection |
| Fabric Relationships | Digital Thread edges (reused) |

## Digital Thread (conceptual)

Aircraft → Configuration → Component → Work Order → Inspection → Finding → Repair → Release → Flight → Reliability → Retirement

Runtime edges live in Fabric; Twin provides the lifecycle product API over them.

## Related docs

- [DIGITAL_TWIN_GUIDE.md](DIGITAL_TWIN_GUIDE.md)
- [DIGITAL_PASSPORT.md](DIGITAL_PASSPORT.md) (updated)
- [TWIN_RELATIONSHIP_DIAGRAM.md](TWIN_RELATIONSHIP_DIAGRAM.md)
- [TWIN_LIFECYCLE_DIAGRAM.md](TWIN_LIFECYCLE_DIAGRAM.md)
- [TWIN_API.md](TWIN_API.md)
- [TWIN_FUTURE_ROADMAP.md](TWIN_FUTURE_ROADMAP.md)
- [TWIN_PRODUCTION_READINESS.md](TWIN_PRODUCTION_READINESS.md)
- ADR-0015
