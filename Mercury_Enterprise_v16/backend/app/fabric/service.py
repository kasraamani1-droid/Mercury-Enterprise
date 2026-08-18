"""Universal Data Fabric service — Digital Passports, relationships, events, governance."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..org.service import OrganizationService
from ..platform.audit_engine import AuditEngine
from ..platform.event_framework import event_framework
from ..platform.models import PlatformSearchDocument
from ..platform.repository import PlatformRepository
from ..shared import ActorContext
from .catalog import ENTITY_TYPE_CATALOG, EVENT_TYPES, RELATIONSHIP_TYPES
from .models import (
    FabricAttachmentRef,
    FabricEntityType,
    FabricEvent,
    FabricLegalHold,
    FabricPassport,
    FabricPassportHistory,
    FabricRelationship,
    FabricRetentionPolicy,
    FabricTag,
)
from .repository import FabricRepository
from .schemas import (
    AttachmentRefCreate,
    AttachmentRefOut,
    DigitalThreadOut,
    EntityTypeOut,
    EventCreate,
    EventOut,
    FabricOverviewOut,
    FabricSearchHit,
    LegalHoldCreate,
    LegalHoldOut,
    PassportCreate,
    PassportHistoryOut,
    PassportOut,
    RelationshipCreate,
    RelationshipOut,
    RetentionPolicyOut,
    TagCreate,
    TagOut,
    ThreadNodeOut,
)

logger = logging.getLogger("mercury.fabric")


class FabricService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FabricRepository(db)
        self.org = OrganizationService(db)
        self.audit = AuditEngine(db)
        self.search_repo = PlatformRepository(db)

    def resolve_org(self, actor: ActorContext, organization_id: str | None = None) -> str:
        org_id = (organization_id or actor.organization_id or "").strip()
        if not org_id:
            raise HTTPException(status_code=400, detail="Organization is required")
        self.org.assert_org_access(
            username=actor.username, session_role=actor.role, organization_id=org_id
        )
        return org_id

    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def _passport_number(self, entity_type: str) -> str:
        prefix = "".join(c for c in entity_type.upper() if c.isalnum())[:6] or "ENT"
        return f"PP-{prefix}-{uuid.uuid4().hex[:10].upper()}"

    def _history_snapshot(self, passport: FabricPassport, change_type: str, actor: str) -> None:
        self.repo.add(
            FabricPassportHistory(
                organization_id=passport.organization_id,
                passport_id=passport.id,
                version=passport.version,
                change_type=change_type,
                snapshot_json=json.dumps(
                    {
                        "passport_number": passport.passport_number,
                        "display_name": passport.display_name,
                        "lifecycle": passport.lifecycle,
                        "ownership_json": passport.ownership_json,
                        "tags_json": passport.tags_json,
                        "entity_type": passport.entity_type,
                        "entity_id": passport.entity_id,
                    }
                ),
                actor=actor,
            )
        )

    def _index_search(self, passport: FabricPassport) -> None:
        """Mirror passport into platform search for universal search."""
        existing = self.search_repo.upsert_search_document(
            passport.organization_id, "fabric_passport", passport.id
        )
        body = f"{passport.entity_type} {passport.entity_id} {passport.passport_number}"
        meta = passport.ai_metadata_json or json.dumps(
            {
                "domain": "fabric",
                "entity_type": passport.entity_type,
                "searchable": True,
                "embedding_ready": False,
                "semantic_ready": True,
            }
        )
        if existing is None:
            self.repo.add(
                PlatformSearchDocument(
                    organization_id=passport.organization_id,
                    doc_type="fabric_passport",
                    entity_id=passport.id,
                    title=passport.display_name or passport.passport_number,
                    body=body,
                    keywords=passport.tags_json,
                    ai_metadata_json=meta,
                )
            )
        else:
            existing.title = passport.display_name or passport.passport_number
            existing.body = body
            existing.keywords = passport.tags_json
            existing.ai_metadata_json = meta
            existing.status = "active"
            existing.updated_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------
    def seed_fabric(self, organization_id: str = "org-aviation-east") -> dict[str, int]:
        created = {"types": 0, "passports": 0, "relationships": 0, "events": 0, "policies": 0}

        for code, name, domain, kind, desc in ENTITY_TYPE_CATALOG:
            if self.repo.get_entity_type(code) is None:
                self.repo.add(
                    FabricEntityType(
                        code=code,
                        name=name,
                        domain=domain,
                        passport_kind=kind,
                        description=desc,
                    )
                )
                created["types"] += 1

        policies = [
            ("aviation.airworthiness", "Airworthiness records", "aircraft", 3650, "true", "10-year retention"),
            ("aviation.component", "Component traceability", "component", 3650, "true", "Serialized component history"),
            ("platform.default", "Default platform retention", "*", 2555, "false", "~7 year default"),
            ("logistics.calibration", "Calibration certificates", "calibration", 1825, "true", "5-year cal records"),
        ]
        for code, name, etype, days, immutable, desc in policies:
            existing = next(
                (
                    p
                    for p in self.repo.list_retention_policies(organization_id)
                    if p.code == code and p.organization_id in {organization_id, "*"}
                ),
                None,
            )
            if existing is None:
                # check by scanning db via list for org
                from sqlalchemy import select

                row = self.db.scalars(
                    select(FabricRetentionPolicy).where(
                        FabricRetentionPolicy.organization_id == organization_id,
                        FabricRetentionPolicy.code == code,
                    )
                ).first()
                if row is None:
                    self.repo.add(
                        FabricRetentionPolicy(
                            organization_id=organization_id,
                            code=code,
                            name=name,
                            entity_type=etype,
                            retention_days=days,
                            immutable=immutable,
                            archive_after_days=max(days - 365, 0),
                            description=desc,
                        )
                    )
                    created["policies"] += 1

        # Bootstrap digital thread sample: org → aircraft → component → work_order chain if present
        org_pp = self._ensure_seed_passport(
            organization_id,
            "organization",
            organization_id,
            "Aviation East Organization",
            created,
        )
        ac_id = "ac-c-gmea"
        ac_pp = self._ensure_seed_passport(
            organization_id, "aircraft", ac_id, "Aircraft C-GMEA", created
        )
        # Demo component / work package if known from seeds
        for etype, eid, name in (
            ("component", "comp-demo-engine", "Demo Engine Position"),
            ("work_order", "wo-demo-link", "Demo Work Order Link"),
            ("personnel", "E-1001", "Planner E-1001"),
            ("publication", "pub-demo", "Demo Publication"),
            ("tool", "tool-demo", "Demo Torque Wrench"),
        ):
            self._ensure_seed_passport(organization_id, etype, eid, name, created)

        # Relationships forming a mini digital thread
        if org_pp and ac_pp:
            self._ensure_seed_rel(
                organization_id, ac_pp, org_pp, "owned_by", "many_to_many", created
            )

        # Link aircraft → component → personnel sample edges when passports exist
        ac = self.repo.get_passport_by_entity(organization_id, "aircraft", "ac-c-gmea")
        comp = self.repo.get_passport_by_entity(organization_id, "component", "comp-demo-engine")
        person = self.repo.get_passport_by_entity(organization_id, "personnel", "E-1001")
        if ac and comp:
            self._ensure_seed_rel(organization_id, comp, ac, "installed_on", "many_to_many", created)
        if ac and person:
            self._ensure_seed_rel(organization_id, person, ac, "assigned_to", "many_to_many", created)

        self.repo.commit()
        return created

    def _ensure_seed_passport(
        self,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        display_name: str,
        created: dict[str, int],
    ) -> FabricPassport | None:
        existing = self.repo.get_passport_by_entity(organization_id, entity_type, entity_id)
        if existing:
            return existing
        row = FabricPassport(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            passport_number=self._passport_number(entity_type),
            display_name=display_name,
            lifecycle="active",
            digital_identity=f"did:mercury:{organization_id}:{entity_type}:{entity_id}",
            ai_metadata_json=json.dumps(
                {
                    "domain": "fabric",
                    "entity_type": entity_type,
                    "searchable": True,
                    "embedding_ready": False,
                    "semantic_ready": True,
                    "digital_twin_ready": entity_type in {"aircraft", "component", "tool"},
                }
            ),
            tags_json=json.dumps(["seed", entity_type]),
            created_by="system",
        )
        self.repo.add(row)
        self.repo.flush()
        self._history_snapshot(row, "create", "system")
        self._index_search(row)
        self.repo.add(
            FabricEvent(
                organization_id=organization_id,
                passport_id=row.id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type="created",
                title=f"Passport issued for {display_name}",
                actor="system",
                ai_metadata_json=json.dumps({"timeline": True}),
            )
        )
        created["passports"] += 1
        created["events"] += 1
        return row

    def _ensure_seed_rel(
        self,
        organization_id: str,
        frm: FabricPassport,
        to: FabricPassport,
        rel_type: str,
        cardinality: str,
        created: dict[str, int],
    ) -> None:
        card = cardinality if cardinality in {"one_to_one", "one_to_many", "many_to_many"} else "many_to_many"
        existing = [
            r
            for r in self.repo.list_relationships(
                organization_id=organization_id, passport_id=frm.id, relationship_type=rel_type, limit=50
            )
            if r.to_passport_id == to.id
        ]
        if existing:
            return
        self.repo.add(
            FabricRelationship(
                organization_id=organization_id,
                from_passport_id=frm.id,
                to_passport_id=to.id,
                from_entity_type=frm.entity_type,
                from_entity_id=frm.entity_id,
                to_entity_type=to.entity_type,
                to_entity_id=to.entity_id,
                cardinality=card,
                relationship_type=rel_type,
                created_by="system",
            )
        )
        created["relationships"] += 1

    # ------------------------------------------------------------------
    # Entity types
    # ------------------------------------------------------------------
    def list_entity_types(self) -> list[EntityTypeOut]:
        return [EntityTypeOut.model_validate(r) for r in self.repo.list_entity_types()]

    # ------------------------------------------------------------------
    # Passports
    # ------------------------------------------------------------------
    def ensure_passport(self, payload: PassportCreate, actor: ActorContext) -> PassportOut:
        org_id = self.resolve_org(actor, payload.organization_id)
        if self.repo.get_entity_type(payload.entity_type) is None:
            # Allow unknown types but prefer catalog — auto-register soft
            self.repo.add(
                FabricEntityType(
                    code=payload.entity_type,
                    name=payload.entity_type.replace("_", " ").title(),
                    domain="custom",
                    passport_kind="organization",
                    description="Auto-registered entity type",
                )
            )
            self.repo.flush()
        existing = self.repo.get_passport_by_entity(org_id, payload.entity_type, payload.entity_id)
        if existing:
            return PassportOut.model_validate(existing)

        row = FabricPassport(
            organization_id=org_id,
            entity_type=payload.entity_type.strip(),
            entity_id=payload.entity_id.strip(),
            passport_number=self._passport_number(payload.entity_type),
            display_name=payload.display_name.strip() or payload.entity_id,
            lifecycle=payload.lifecycle,
            ownership_json=payload.ownership_json,
            digital_identity=f"did:mercury:{org_id}:{payload.entity_type}:{payload.entity_id}",
            permissions_hint=payload.permissions_hint,
            ai_metadata_json=payload.ai_metadata_json
            or json.dumps(
                {
                    "domain": "fabric",
                    "entity_type": payload.entity_type,
                    "searchable": True,
                    "embedding_ready": False,
                    "semantic_ready": True,
                }
            ),
            tags_json=payload.tags_json,
            created_by=actor.username,
        )
        self.repo.add(row)
        self.repo.flush()
        self._history_snapshot(row, "create", actor.username)
        self._index_search(row)
        self.audit.require(
            actor,
            action="fabric.passport.create",
            target_type="fabric_passport",
            target_id=row.id,
            organization_id=org_id,
            details=row.passport_number,
        )
        self._commit_or_conflict(detail="Passport already exists")
        event_framework.publish_sync(
            "fabric.passport.created",
            {"passport_id": row.id, "entity_type": row.entity_type, "entity_id": row.entity_id},
            organization_id=org_id,
            source="fabric",
        )
        return PassportOut.model_validate(row)

    def get_passport(self, passport_id: str, actor: ActorContext) -> PassportOut:
        org_id = self.resolve_org(actor)
        row = self.repo.get_passport(org_id, passport_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Passport not found")
        return PassportOut.model_validate(row)

    def list_passports(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        entity_type: str | None = None,
        lifecycle: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PassportOut]:
        org_id = self.resolve_org(actor, organization_id)
        return [
            PassportOut.model_validate(r)
            for r in self.repo.list_passports(
                organization_id=org_id,
                entity_type=entity_type,
                lifecycle=lifecycle,
                limit=limit,
                offset=offset,
            )
        ]

    def update_lifecycle(
        self, passport_id: str, lifecycle: str, actor: ActorContext
    ) -> PassportOut:
        org_id = self.resolve_org(actor)
        row = self.repo.get_passport(org_id, passport_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Passport not found")
        # Legal hold blocks archive/delete lifecycle moves
        holds = [
            h
            for h in self.repo.list_legal_holds(org_id)
            if h.passport_id == passport_id and h.status == "active"
        ]
        if holds and lifecycle in {"archived", "retired"}:
            raise HTTPException(status_code=409, detail="Passport under legal hold")
        row.lifecycle = lifecycle
        row.version = int(row.version or 1) + 1
        row.modified_at = datetime.utcnow()
        self._history_snapshot(row, "lifecycle", actor.username)
        self.audit.require(
            actor,
            action="fabric.passport.lifecycle",
            target_type="fabric_passport",
            target_id=row.id,
            organization_id=org_id,
            details=lifecycle,
        )
        self.repo.commit()
        return PassportOut.model_validate(row)

    def list_history(self, passport_id: str, actor: ActorContext) -> list[PassportHistoryOut]:
        org_id = self.resolve_org(actor)
        if self.repo.get_passport(org_id, passport_id) is None:
            raise HTTPException(status_code=404, detail="Passport not found")
        return [PassportHistoryOut.model_validate(r) for r in self.repo.list_passport_history(passport_id)]

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    def link(self, payload: RelationshipCreate, actor: ActorContext) -> RelationshipOut:
        org_id = self.resolve_org(actor, payload.organization_id)
        if payload.relationship_type not in RELATIONSHIP_TYPES:
            # allow extension but warn via storing as-is
            pass
        frm = self.repo.get_passport(org_id, payload.from_passport_id)
        to = self.repo.get_passport(org_id, payload.to_passport_id)
        if frm is None or to is None:
            # cross-org: allow to_passport from other org if flagged
            if payload.cross_organization and to is None:
                raise HTTPException(status_code=404, detail="Target passport not found in tenant scope")
            raise HTTPException(status_code=404, detail="Passport not found")
        row = FabricRelationship(
            organization_id=org_id,
            from_passport_id=frm.id,
            to_passport_id=to.id,
            from_entity_type=frm.entity_type,
            from_entity_id=frm.entity_id,
            to_entity_type=to.entity_type,
            to_entity_id=to.entity_id,
            cardinality=payload.cardinality,
            relationship_type=payload.relationship_type.strip(),
            cross_organization="true" if payload.cross_organization else "false",
            target_organization_id=payload.target_organization_id,
            metadata_json=payload.metadata_json,
            created_by=actor.username,
        )
        self.repo.add(row)
        self.repo.flush()
        self.audit.require(
            actor,
            action="fabric.relationship.create",
            target_type="fabric_relationship",
            target_id=row.id,
            organization_id=org_id,
            details=payload.relationship_type,
        )
        self.repo.commit()
        event_framework.publish_sync(
            "fabric.relationship.created",
            {
                "id": row.id,
                "from": frm.id,
                "to": to.id,
                "type": row.relationship_type,
            },
            organization_id=org_id,
            source="fabric",
        )
        return RelationshipOut.model_validate(row)

    def list_relationships(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        passport_id: str | None = None,
        relationship_type: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[RelationshipOut]:
        org_id = self.resolve_org(actor, organization_id)
        return [
            RelationshipOut.model_validate(r)
            for r in self.repo.list_relationships(
                organization_id=org_id,
                passport_id=passport_id,
                relationship_type=relationship_type,
                limit=limit,
                offset=offset,
            )
        ]

    def unlink(self, relationship_id: str, actor: ActorContext) -> RelationshipOut:
        org_id = self.resolve_org(actor)
        rows = self.repo.list_relationships(organization_id=org_id, limit=500)
        row = next((r for r in rows if r.id == relationship_id), None)
        if row is None:
            raise HTTPException(status_code=404, detail="Relationship not found")
        row.status = "deleted"
        row.deleted_at = datetime.utcnow()
        self.audit.require(
            actor,
            action="fabric.relationship.delete",
            target_type="fabric_relationship",
            target_id=row.id,
            organization_id=org_id,
        )
        self.repo.commit()
        return RelationshipOut.model_validate(row)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    def emit_event(self, payload: EventCreate, actor: ActorContext) -> EventOut:
        org_id = self.resolve_org(actor, payload.organization_id)
        if payload.event_type not in EVENT_TYPES and not payload.event_type:
            raise HTTPException(status_code=400, detail="Invalid event_type")
        passport_id = payload.passport_id
        if not passport_id:
            pp = self.repo.get_passport_by_entity(org_id, payload.entity_type, payload.entity_id)
            passport_id = pp.id if pp else ""
        row = FabricEvent(
            organization_id=org_id,
            passport_id=passport_id,
            entity_type=payload.entity_type.strip(),
            entity_id=payload.entity_id.strip(),
            event_type=payload.event_type.strip(),
            title=payload.title.strip(),
            details=payload.details.strip(),
            actor=actor.username,
            correlation_id=payload.correlation_id,
            payload_json=payload.payload_json,
            ai_metadata_json=payload.ai_metadata_json
            or json.dumps({"timeline": True, "ai_ready": True}),
            occurred_at=payload.occurred_at or datetime.utcnow(),
        )
        self.repo.add(row)
        self.repo.flush()
        self.audit.require(
            actor,
            action=f"fabric.event.{row.event_type}",
            target_type="fabric_event",
            target_id=row.id,
            organization_id=org_id,
            details=row.title,
        )
        self.repo.commit()
        event_framework.publish_sync(
            f"fabric.event.{row.event_type}",
            {"id": row.id, "entity_type": row.entity_type, "entity_id": row.entity_id},
            organization_id=org_id,
            source="fabric",
        )
        return EventOut.model_validate(row)

    def list_events(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        passport_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EventOut]:
        org_id = self.resolve_org(actor, organization_id)
        return [
            EventOut.model_validate(r)
            for r in self.repo.list_events(
                organization_id=org_id,
                passport_id=passport_id,
                event_type=event_type,
                limit=limit,
                offset=offset,
            )
        ]

    # ------------------------------------------------------------------
    # Tags / attachments
    # ------------------------------------------------------------------
    def add_tag(self, payload: TagCreate, actor: ActorContext) -> TagOut:
        org_id = self.resolve_org(actor, payload.organization_id)
        if self.repo.get_passport(org_id, payload.passport_id) is None:
            raise HTTPException(status_code=404, detail="Passport not found")
        row = FabricTag(
            organization_id=org_id,
            passport_id=payload.passport_id,
            tag=payload.tag.strip().lower(),
            category=payload.category.strip() or "general",
            created_by=actor.username,
        )
        self.repo.add(row)
        self._commit_or_conflict(detail="Tag already exists")
        return TagOut.model_validate(row)

    def list_tags(self, passport_id: str, actor: ActorContext) -> list[TagOut]:
        org_id = self.resolve_org(actor)
        return [TagOut.model_validate(r) for r in self.repo.list_tags(org_id, passport_id)]

    def add_attachment(self, payload: AttachmentRefCreate, actor: ActorContext) -> AttachmentRefOut:
        org_id = self.resolve_org(actor, payload.organization_id)
        if self.repo.get_passport(org_id, payload.passport_id) is None:
            raise HTTPException(status_code=404, detail="Passport not found")
        row = FabricAttachmentRef(
            organization_id=org_id,
            passport_id=payload.passport_id,
            file_object_id=payload.file_object_id,
            role=payload.role,
            created_by=actor.username,
        )
        self.repo.add(row)
        self.audit.require(
            actor,
            action="fabric.attachment.create",
            target_type="fabric_attachment",
            target_id=row.id,
            organization_id=org_id,
        )
        self.repo.commit()
        return AttachmentRefOut.model_validate(row)

    def list_attachments(self, passport_id: str, actor: ActorContext) -> list[AttachmentRefOut]:
        org_id = self.resolve_org(actor)
        return [AttachmentRefOut.model_validate(r) for r in self.repo.list_attachments(org_id, passport_id)]

    # ------------------------------------------------------------------
    # Digital Thread walk
    # ------------------------------------------------------------------
    def digital_thread(
        self, passport_id: str, actor: ActorContext, *, max_depth: int = 4
    ) -> DigitalThreadOut:
        org_id = self.resolve_org(actor)
        root = self.repo.get_passport(org_id, passport_id)
        if root is None:
            raise HTTPException(status_code=404, detail="Passport not found")
        visited: set[str] = set()
        nodes: list[ThreadNodeOut] = []
        edges: list[RelationshipOut] = []
        queue: list[tuple[str, int, str]] = [(passport_id, 0, "")]

        while queue:
            current_id, depth, via = queue.pop(0)
            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)
            pp = self.repo.get_passport(org_id, current_id)
            if pp is None:
                continue
            nodes.append(
                ThreadNodeOut(passport=PassportOut.model_validate(pp), depth=depth, via_relationship=via)
            )
            if depth == max_depth:
                continue
            for rel in self.repo.list_relationships(
                organization_id=org_id, passport_id=current_id, limit=200
            ):
                edges.append(RelationshipOut.model_validate(rel))
                nxt = rel.to_passport_id if rel.from_passport_id == current_id else rel.from_passport_id
                if nxt not in visited:
                    queue.append((nxt, depth + 1, rel.relationship_type))

        # de-dupe edges by id
        seen_e: set[str] = set()
        uniq_edges: list[RelationshipOut] = []
        for e in edges:
            if e.id not in seen_e:
                seen_e.add(e.id)
                uniq_edges.append(e)

        return DigitalThreadOut(root_passport_id=passport_id, nodes=nodes, edges=uniq_edges)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(
        self, actor: ActorContext, *, query: str, organization_id: str | None = None, limit: int = 50
    ) -> list[FabricSearchHit]:
        org_id = self.resolve_org(actor, organization_id)
        if not query.strip():
            raise HTTPException(status_code=400, detail="query is required")
        rows = self.repo.search_passports(organization_id=org_id, query=query, limit=limit)
        return [FabricSearchHit(passport=PassportOut.model_validate(r), score=1.0) for r in rows]

    # ------------------------------------------------------------------
    # Governance
    # ------------------------------------------------------------------
    def list_retention_policies(self, actor: ActorContext) -> list[RetentionPolicyOut]:
        org_id = self.resolve_org(actor)
        return [RetentionPolicyOut.model_validate(r) for r in self.repo.list_retention_policies(org_id)]

    def place_legal_hold(self, payload: LegalHoldCreate, actor: ActorContext) -> LegalHoldOut:
        org_id = self.resolve_org(actor, payload.organization_id)
        if self.repo.get_passport(org_id, payload.passport_id) is None:
            raise HTTPException(status_code=404, detail="Passport not found")
        row = FabricLegalHold(
            organization_id=org_id,
            passport_id=payload.passport_id,
            reason=payload.reason.strip(),
            placed_by=actor.username,
        )
        self.repo.add(row)
        self.repo.flush()
        self.audit.require(
            actor,
            action="fabric.legal_hold.place",
            target_type="fabric_legal_hold",
            target_id=row.id,
            organization_id=org_id,
        )
        self.repo.commit()
        return LegalHoldOut.model_validate(row)

    def release_legal_hold(self, hold_id: str, actor: ActorContext) -> LegalHoldOut:
        org_id = self.resolve_org(actor)
        row = self.repo.get_legal_hold(org_id, hold_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Legal hold not found")
        row.status = "released"
        row.released_at = datetime.utcnow()
        self.audit.require(
            actor,
            action="fabric.legal_hold.release",
            target_type="fabric_legal_hold",
            target_id=row.id,
            organization_id=org_id,
        )
        self.repo.commit()
        return LegalHoldOut.model_validate(row)

    def list_legal_holds(self, actor: ActorContext) -> list[LegalHoldOut]:
        org_id = self.resolve_org(actor)
        return [LegalHoldOut.model_validate(r) for r in self.repo.list_legal_holds(org_id)]

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------
    def overview(self, actor: ActorContext, *, organization_id: str | None = None) -> FabricOverviewOut:
        org_id = self.resolve_org(actor, organization_id)
        return FabricOverviewOut(
            organization_id=org_id,
            entity_types=self.repo.count_entity_types(),
            passports=self.repo.count_passports(org_id),
            relationships=self.repo.count_relationships(org_id),
            events=self.repo.count_events(org_id),
            tags=self.repo.count_tags(org_id),
            legal_holds=self.repo.count_legal_holds(org_id),
            retention_policies=self.repo.count_retention_policies(org_id),
        )
