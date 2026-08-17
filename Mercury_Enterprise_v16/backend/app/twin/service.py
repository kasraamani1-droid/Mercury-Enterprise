"""Program 15 — Mercury Digital Twin service.

Complete digital lifecycle registry. Not a 3D model.
Passports never disappear; history is append-only and immutable.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..fabric.models import FabricPassport, FabricRelationship
from ..fabric.schemas import PassportCreate
from ..fabric.service import FabricService
from ..org.service import OrganizationService
from ..platform.audit_engine import AuditEngine
from ..platform.event_framework import event_framework
from ..shared import ActorContext, clamp_page
from .catalog import (
    CONFIG_BASELINES,
    HISTORY_KINDS,
    LIFECYCLE_STATES,
    PASSPORT_KIND_MAP,
    RELIABILITY_METRICS,
    TWIN_TYPES,
)
from .models import (
    TwinConfiguration,
    TwinHistoryEntry,
    TwinObject,
    TwinReliabilitySnapshot,
    TwinSearchEntry,
)
from .schemas import (
    RelationshipOut,
    TwinDetailOut,
    TwinOut,
    TwinOverviewOut,
    TwinSearchHit,
    TwinSearchResponse,
)

DISCLAIMER = (
    "Mercury Digital Twin is the complete digital lifecycle of aviation assets — "
    "not a 3D model. Passports never disappear; history is immutable. "
    "Reliability metrics are architecture readiness only. AI answers are future advisory."
)


def _ai_meta(**kwargs) -> str:
    base = {
        "domain": "twin",
        "digital_twin": True,
        "searchable": True,
        "embedding_ready": False,
        "ai_questions_ready": True,
        "questions": [
            "What failed?",
            "Why?",
            "History?",
            "Applicable SB?",
            "Applicable AD?",
            "Previous Repairs?",
            "Reliability Trend?",
        ],
    }
    base.update(kwargs)
    return json.dumps(base)


class TwinService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.org = OrganizationService(db)
        self.audit = AuditEngine(db)
        self.fabric = FabricService(db)

    def resolve_org(self, actor: ActorContext, organization_id: str | None = None) -> str:
        org_id = (organization_id or actor.organization_id or "").strip()
        if not org_id:
            raise HTTPException(status_code=400, detail="Organization is required")
        self.org.assert_org_access(
            username=actor.username, session_role=actor.role, organization_id=org_id
        )
        return org_id

    def seed(self, organization_id: str = "org-aviation-east") -> dict[str, int]:
        created = {"twins": 0, "history": 0, "configurations": 0, "reliability": 0}
        samples = [
            ("aircraft", "C-FYXZ Digital Twin", "FYXZ", "B737-800", "aircraft", "ac-demo-east-1"),
            ("engine", "CFM56 Twin LH", "ENG-LH-001", "CFM56-7B", "serialized_component", "sc-eng-lh-1"),
            ("apu", "APU Twin", "APU-001", "GTCP131", "serialized_component", "sc-apu-1"),
            ("landing_gear", "NLG Twin", "NLG-001", "NLG-B737", "serialized_component", "sc-nlg-1"),
            ("tool", "Torque Wrench Twin", "TQ-250", "TQ-1/4", "tool", "tool-tq-250"),
            ("test_equipment", "Pitot Static Tester Twin", "PST-01", "PST-2000", "tool", "tool-pst-1"),
            ("gse", "GPU Cart Twin", "GPU-01", "GPU-90KVA", "gse", "gse-gpu-1"),
            ("personnel", "AME Professional Twin", "OP-AME", "", "personnel", "pers-ame-1"),
            ("organization", "East Ops Twin", "ORG-EAST", "", "organization", organization_id),
            ("facility", "East Hangar Twin", "HANGAR-1", "", "facility", "fac-hangar-1"),
        ]
        actor = ActorContext(
            username="system",
            role="Administrator",
            organization_id=organization_id,
            site_id="",
        )
        for twin_type, name, serial, pn, fet, fid in samples:
            exists = self.db.scalars(
                select(TwinObject).where(
                    TwinObject.organization_id == organization_id,
                    TwinObject.twin_type == twin_type,
                    TwinObject.serial_number == serial,
                    TwinObject.part_number == pn,
                )
            ).first()
            if exists:
                continue
            twin = self.create_twin(
                actor,
                twin_type=twin_type,
                display_name=name,
                serial_number=serial,
                part_number=pn,
                fabric_entity_type=fet,
                fabric_entity_id=fid,
                lifecycle_state="operated" if twin_type == "aircraft" else "delivered",
                ownership_json=json.dumps({"operator": organization_id}),
                organization_id=organization_id,
                ensure_passport=True,
                _seeding=True,
            )
            created["twins"] += 1
            self.append_history(
                actor,
                twin.id,
                history_kind="lifecycle",
                title="Twin created",
                summary=f"Digital Twin registered ({twin_type})",
                organization_id=organization_id,
                _seeding=True,
            )
            created["history"] += 1
            if twin_type == "aircraft":
                cfg = self.create_configuration(
                    actor,
                    twin.id,
                    baseline="current",
                    version_label="CFG-1",
                    configuration_json=json.dumps(
                        {"engines": ["ENG-LH-001"], "apu": "APU-001", "nlg": "NLG-001"}
                    ),
                    engineering_changes_json=json.dumps([]),
                    approved_modifications_json=json.dumps([]),
                    optional_equipment_json=json.dumps(["WiFi"]),
                    weight_balance_json=json.dumps({"ready": True}),
                    set_as_current=True,
                    organization_id=organization_id,
                    _seeding=True,
                )
                created["configurations"] += 1
                for metric, value, unit in (
                    ("mtbur", "2400", "hours"),
                    ("mtbf", "4800", "hours"),
                    ("dispatch_reliability", "99.2", "percent"),
                    ("failure_rate", "0.004", "per_fh"),
                    ("repeat_defects", "2", "count"),
                    ("deferred_defects", "1", "count"),
                    ("trend_analysis", "stable", "label"),
                ):
                    self.create_reliability(
                        actor,
                        twin.id,
                        metric_code=metric,
                        metric_value=value,
                        unit=unit,
                        window_label="rolling_12m",
                        organization_id=organization_id,
                        _seeding=True,
                    )
                    created["reliability"] += 1
                _ = cfg
            if twin_type in {"engine", "tool"}:
                self.append_history(
                    actor,
                    twin.id,
                    history_kind="installation" if twin_type == "engine" else "inspection",
                    title="Baseline history",
                    summary="Seed history entry",
                    organization_id=organization_id,
                    _seeding=True,
                )
                created["history"] += 1

        if any(created.values()):
            self.db.commit()
        return created

    def overview(self, actor: ActorContext, organization_id: str | None = None) -> TwinOverviewOut:
        org_id = self.resolve_org(actor, organization_id)
        rows = list(
            self.db.scalars(
                select(TwinObject).where(TwinObject.organization_id == org_id)
            ).all()
        )
        by_type = dict(Counter(r.twin_type for r in rows))
        return TwinOverviewOut(
            organization_id=org_id,
            twins=len(rows),
            by_type=by_type,
            history_entries=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(TwinHistoryEntry)
                    .where(TwinHistoryEntry.organization_id == org_id)
                )
                or 0
            ),
            configurations=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(TwinConfiguration)
                    .where(TwinConfiguration.organization_id == org_id)
                )
                or 0
            ),
            reliability_snapshots=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(TwinReliabilitySnapshot)
                    .where(TwinReliabilitySnapshot.organization_id == org_id)
                )
                or 0
            ),
            disclaimer=DISCLAIMER,
        )

    def _index_twin(self, twin: TwinObject) -> None:
        entry = self.db.scalars(
            select(TwinSearchEntry).where(
                TwinSearchEntry.organization_id == twin.organization_id,
                TwinSearchEntry.twin_id == twin.id,
            )
        ).first()
        tags = [twin.twin_type, twin.lifecycle_state, twin.serial_number, twin.part_number]
        payload = {
            "twin_uuid": twin.twin_uuid,
            "twin_type": twin.twin_type,
            "passport_id": twin.passport_id,
            "serial_number": twin.serial_number,
            "title": twin.display_name,
            "summary": f"{twin.twin_type} · {twin.lifecycle_state}",
            "tags_json": json.dumps([t for t in tags if t]),
            "status": twin.status,
            "updated_at": datetime.utcnow(),
        }
        if entry is None:
            self.db.add(
                TwinSearchEntry(
                    organization_id=twin.organization_id,
                    twin_id=twin.id,
                    **payload,
                )
            )
        else:
            for k, v in payload.items():
                setattr(entry, k, v)

    def create_twin(
        self,
        actor: ActorContext,
        *,
        twin_type: str,
        display_name: str,
        serial_number: str = "",
        part_number: str = "",
        fabric_entity_type: str = "",
        fabric_entity_id: str = "",
        lifecycle_state: str = "manufactured",
        ownership_json: str = "{}",
        organization_id: str | None = None,
        ensure_passport: bool = True,
        _seeding: bool = False,
    ) -> TwinObject:
        if twin_type not in TWIN_TYPES:
            raise HTTPException(status_code=400, detail="Invalid twin_type")
        if lifecycle_state not in LIFECYCLE_STATES:
            raise HTTPException(status_code=400, detail="Invalid lifecycle_state")
        org_id = self.resolve_org(actor, organization_id)
        fet = fabric_entity_type or PASSPORT_KIND_MAP.get(twin_type, twin_type)
        fid = fabric_entity_id or f"twin-{uuid.uuid4().hex[:12]}"
        passport_id = ""
        if ensure_passport:
            try:
                passport = self.fabric.ensure_passport(
                    PassportCreate(
                        organization_id=org_id,
                        entity_type=fet,
                        entity_id=fid,
                        display_name=display_name,
                        ownership_json=ownership_json,
                    ),
                    actor,
                )
                passport_id = passport.id
            except Exception:
                # Passport ensure may fail if fabric not seeded in unusual contexts
                passport_id = ""

        twin = TwinObject(
            organization_id=org_id,
            twin_uuid=str(uuid.uuid4()),
            twin_type=twin_type,
            display_name=display_name.strip(),
            serial_number=serial_number.strip(),
            part_number=part_number.strip(),
            passport_id=passport_id,
            fabric_entity_type=fet,
            fabric_entity_id=fid,
            lifecycle_state=lifecycle_state,
            ownership_json=ownership_json,
            status="active",
            visualization_ready="false",
            weight_balance_ready="true" if twin_type == "aircraft" else "false",
            ai_metadata_json=_ai_meta(twin_type=twin_type, passport_kind=PASSPORT_KIND_MAP.get(twin_type)),
            created_by=actor.username,
        )
        self.db.add(twin)
        try:
            self.db.flush()
            self._index_twin(twin)
            self.audit.require(
                actor,
                action="twin.create",
                target_type="twin_object",
                target_id=twin.id,
                organization_id=org_id,
                details=twin.twin_uuid,
            )
            if not _seeding:
                self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Twin already exists") from exc
        if not _seeding:
            event_framework.publish_sync(
                "twin.created",
                {"id": twin.id, "twin_uuid": twin.twin_uuid, "twin_type": twin_type},
                organization_id=org_id,
                source="twin",
            )
        return twin

    def list_twins(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        twin_type: str | None = None,
        lifecycle_state: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TwinObject]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(TwinObject).where(TwinObject.organization_id == org_id)
        if twin_type:
            stmt = stmt.where(TwinObject.twin_type == twin_type)
        if lifecycle_state:
            stmt = stmt.where(TwinObject.lifecycle_state == lifecycle_state)
        return list(
            self.db.scalars(
                stmt.order_by(TwinObject.twin_type, TwinObject.display_name).limit(lim).offset(off)
            ).all()
        )

    def get_twin(
        self, actor: ActorContext, twin_id: str, organization_id: str | None = None
    ) -> TwinDetailOut:
        org_id = self.resolve_org(actor, organization_id)
        twin = self.db.get(TwinObject, twin_id)
        if twin is None or twin.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Twin not found")
        base = TwinOut.model_validate(twin)
        return TwinDetailOut(
            **base.model_dump(),
            history_count=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(TwinHistoryEntry)
                    .where(TwinHistoryEntry.twin_id == twin.id)
                )
                or 0
            ),
            configuration_count=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(TwinConfiguration)
                    .where(TwinConfiguration.twin_id == twin.id)
                )
                or 0
            ),
            reliability_count=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(TwinReliabilitySnapshot)
                    .where(TwinReliabilitySnapshot.twin_id == twin.id)
                )
                or 0
            ),
            disclaimer=DISCLAIMER,
        )

    def get_by_uuid(
        self, actor: ActorContext, twin_uuid: str, organization_id: str | None = None
    ) -> TwinDetailOut:
        org_id = self.resolve_org(actor, organization_id)
        twin = self.db.scalars(
            select(TwinObject).where(
                TwinObject.organization_id == org_id,
                TwinObject.twin_uuid == twin_uuid,
            )
        ).first()
        if twin is None:
            raise HTTPException(status_code=404, detail="Twin not found")
        return self.get_twin(actor, twin.id, org_id)

    def _require_twin(self, org_id: str, twin_id: str) -> TwinObject:
        twin = self.db.get(TwinObject, twin_id)
        if twin is None or twin.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Twin not found")
        return twin

    def transition_lifecycle(
        self,
        actor: ActorContext,
        twin_id: str,
        *,
        to_state: str,
        summary: str = "",
        related_ref: str = "",
        organization_id: str | None = None,
    ) -> TwinObject:
        if to_state not in LIFECYCLE_STATES:
            raise HTTPException(status_code=400, detail="Invalid lifecycle_state")
        org_id = self.resolve_org(actor, organization_id)
        twin = self._require_twin(org_id, twin_id)
        prev = twin.lifecycle_state
        twin.lifecycle_state = to_state
        twin.updated_at = datetime.utcnow()
        if to_state in {"retired", "archived", "scrapped"}:
            twin.archived_at = datetime.utcnow()
            twin.status = "archived"
        self.append_history(
            actor,
            twin.id,
            history_kind="lifecycle",
            title=f"{prev} → {to_state}",
            summary=summary or f"Lifecycle transition to {to_state}",
            payload_json=json.dumps({"from": prev, "to": to_state}),
            related_ref=related_ref,
            organization_id=org_id,
            _seeding=True,
        )
        self._index_twin(twin)
        self.audit.require(
            actor,
            action="twin.lifecycle",
            target_type="twin_object",
            target_id=twin.id,
            organization_id=org_id,
            details=to_state,
        )
        self.db.commit()
        return twin

    def append_history(
        self,
        actor: ActorContext,
        twin_id: str,
        *,
        history_kind: str,
        title: str = "",
        summary: str = "",
        payload_json: str = "{}",
        related_ref: str = "",
        occurred_at: datetime | None = None,
        organization_id: str | None = None,
        _seeding: bool = False,
    ) -> TwinHistoryEntry:
        if history_kind not in HISTORY_KINDS:
            raise HTTPException(status_code=400, detail="Invalid history_kind")
        org_id = self.resolve_org(actor, organization_id)
        twin = self._require_twin(org_id, twin_id)
        row = TwinHistoryEntry(
            organization_id=org_id,
            twin_id=twin.id,
            history_kind=history_kind,
            title=title.strip() or history_kind,
            summary=summary.strip(),
            payload_json=payload_json,
            related_ref=related_ref,
            actor=actor.username,
            occurred_at=occurred_at or datetime.utcnow(),
        )
        self.db.add(row)
        self.db.flush()
        if not _seeding:
            self.audit.require(
                actor,
                action="twin.history.append",
                target_type="twin_history",
                target_id=row.id,
                organization_id=org_id,
                details=history_kind,
            )
            self.db.commit()
        return row

    def list_history(
        self,
        actor: ActorContext,
        twin_id: str,
        *,
        organization_id: str | None = None,
        history_kind: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[TwinHistoryEntry]:
        org_id = self.resolve_org(actor, organization_id)
        self._require_twin(org_id, twin_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(TwinHistoryEntry).where(TwinHistoryEntry.twin_id == twin_id)
        if history_kind:
            stmt = stmt.where(TwinHistoryEntry.history_kind == history_kind)
        return list(
            self.db.scalars(
                stmt.order_by(TwinHistoryEntry.occurred_at.desc()).limit(lim).offset(off)
            ).all()
        )

    def create_configuration(
        self,
        actor: ActorContext,
        twin_id: str,
        *,
        baseline: str = "current",
        version_label: str = "",
        configuration_json: str = "{}",
        engineering_changes_json: str = "[]",
        approved_modifications_json: str = "[]",
        optional_equipment_json: str = "[]",
        weight_balance_json: str = "{}",
        visualization_meta_json: str = "{}",
        set_as_current: bool = True,
        organization_id: str | None = None,
        _seeding: bool = False,
    ) -> TwinConfiguration:
        if baseline not in CONFIG_BASELINES:
            raise HTTPException(status_code=400, detail="Invalid baseline")
        org_id = self.resolve_org(actor, organization_id)
        twin = self._require_twin(org_id, twin_id)
        row = TwinConfiguration(
            organization_id=org_id,
            twin_id=twin.id,
            baseline=baseline,
            version_label=version_label.strip(),
            configuration_json=configuration_json,
            engineering_changes_json=engineering_changes_json,
            approved_modifications_json=approved_modifications_json,
            optional_equipment_json=optional_equipment_json,
            weight_balance_json=weight_balance_json,
            visualization_meta_json=visualization_meta_json
            or json.dumps({"visualization_ready": False, "format": "future_gltf"}),
            status="active",
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        if set_as_current and baseline == "current":
            twin.current_configuration_id = row.id
            twin.weight_balance_ready = "true"
            twin.updated_at = datetime.utcnow()
        self.append_history(
            actor,
            twin.id,
            history_kind="configuration",
            title=f"Configuration {baseline}",
            summary=version_label or baseline,
            payload_json=json.dumps({"configuration_id": row.id, "baseline": baseline}),
            organization_id=org_id,
            _seeding=True,
        )
        if not _seeding:
            self.audit.require(
                actor,
                action="twin.configuration.create",
                target_type="twin_configuration",
                target_id=row.id,
                organization_id=org_id,
                details=baseline,
            )
            self.db.commit()
        return row

    def list_configurations(
        self,
        actor: ActorContext,
        twin_id: str,
        *,
        organization_id: str | None = None,
        baseline: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TwinConfiguration]:
        org_id = self.resolve_org(actor, organization_id)
        self._require_twin(org_id, twin_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(TwinConfiguration).where(TwinConfiguration.twin_id == twin_id)
        if baseline:
            stmt = stmt.where(TwinConfiguration.baseline == baseline)
        return list(
            self.db.scalars(stmt.order_by(TwinConfiguration.created_at.desc()).limit(lim).offset(off)).all()
        )

    def create_reliability(
        self,
        actor: ActorContext,
        twin_id: str,
        *,
        metric_code: str,
        metric_value: str = "",
        unit: str = "",
        window_label: str = "",
        details_json: str = "{}",
        organization_id: str | None = None,
        _seeding: bool = False,
    ) -> TwinReliabilitySnapshot:
        if metric_code not in RELIABILITY_METRICS:
            raise HTTPException(status_code=400, detail="Invalid metric_code")
        org_id = self.resolve_org(actor, organization_id)
        twin = self._require_twin(org_id, twin_id)
        row = TwinReliabilitySnapshot(
            organization_id=org_id,
            twin_id=twin.id,
            metric_code=metric_code,
            metric_value=metric_value,
            unit=unit,
            window_label=window_label,
            details_json=details_json,
            architecture_only="true",
        )
        self.db.add(row)
        self.db.flush()
        if not _seeding:
            self.audit.require(
                actor,
                action="twin.reliability.create",
                target_type="twin_reliability",
                target_id=row.id,
                organization_id=org_id,
                details=metric_code,
            )
            self.db.commit()
        return row

    def list_reliability(
        self,
        actor: ActorContext,
        twin_id: str,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TwinReliabilitySnapshot]:
        org_id = self.resolve_org(actor, organization_id)
        self._require_twin(org_id, twin_id)
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(TwinReliabilitySnapshot)
                .where(TwinReliabilitySnapshot.twin_id == twin_id)
                .order_by(TwinReliabilitySnapshot.metric_code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def relationships(
        self, actor: ActorContext, twin_id: str, organization_id: str | None = None
    ) -> RelationshipOut:
        org_id = self.resolve_org(actor, organization_id)
        twin = self._require_twin(org_id, twin_id)
        edges: list[dict] = []
        if twin.passport_id:
            rows = list(
                self.db.scalars(
                    select(FabricRelationship).where(
                        FabricRelationship.organization_id == org_id,
                        FabricRelationship.deleted_at.is_(None),
                        or_(
                            FabricRelationship.from_passport_id == twin.passport_id,
                            FabricRelationship.to_passport_id == twin.passport_id,
                        ),
                    )
                ).all()
            )
            edges = [
                {
                    "id": r.id,
                    "relationship_type": r.relationship_type,
                    "from_passport_id": r.from_passport_id,
                    "to_passport_id": r.to_passport_id,
                    "cardinality": r.cardinality,
                }
                for r in rows
            ]
        return RelationshipOut(
            twin_id=twin.id,
            passport_id=twin.passport_id,
            fabric_relationships=edges,
            digital_thread_hint=(
                f"/api/v1/fabric/passports/{twin.passport_id}/thread"
                if twin.passport_id
                else ""
            ),
        )

    def passport_view(
        self, actor: ActorContext, twin_id: str, organization_id: str | None = None
    ) -> dict:
        org_id = self.resolve_org(actor, organization_id)
        twin = self._require_twin(org_id, twin_id)
        passport = self.db.get(FabricPassport, twin.passport_id) if twin.passport_id else None
        return {
            "twin_id": twin.id,
            "twin_uuid": twin.twin_uuid,
            "passport_id": twin.passport_id,
            "passport_number": passport.passport_number if passport else "",
            "passport_lifecycle": passport.lifecycle if passport else "",
            "entity_type": twin.fabric_entity_type,
            "entity_id": twin.fabric_entity_id,
            "never_disappears": True,
            "history_immutable": True,
            "disclaimer": DISCLAIMER,
        }

    def search(
        self,
        actor: ActorContext,
        *,
        q: str = "",
        twin_type: str | None = None,
        organization_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> TwinSearchResponse:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(TwinSearchEntry).where(
            TwinSearchEntry.organization_id == org_id,
            TwinSearchEntry.status == "active",
        )
        if twin_type:
            stmt = stmt.where(TwinSearchEntry.twin_type == twin_type)
        query = (q or "").strip()
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    TwinSearchEntry.title.ilike(like),
                    TwinSearchEntry.summary.ilike(like),
                    TwinSearchEntry.serial_number.ilike(like),
                    TwinSearchEntry.twin_uuid.ilike(like),
                    TwinSearchEntry.passport_id.ilike(like),
                    TwinSearchEntry.tags_json.ilike(like),
                )
            )
        rows = list(
            self.db.scalars(stmt.order_by(TwinSearchEntry.title).limit(lim).offset(off)).all()
        )
        return TwinSearchResponse(
            query=query,
            total=len(rows),
            items=[TwinSearchHit.model_validate(r) for r in rows],
        )
