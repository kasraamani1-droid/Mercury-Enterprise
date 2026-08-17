"""Ecosystem service — stakeholder maps and tenant enrollments."""

from __future__ import annotations

import json
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..org.service import OrganizationService
from ..platform.audit_engine import AuditEngine
from ..shared import ActorContext, clamp_page
from .catalog import CAPABILITIES, ECOSYSTEMS
from .models import EcosystemCapability, EcosystemDefinition, EcosystemEnrollment
from .schemas import (
    CapabilityOut,
    EcosystemDetailOut,
    EcosystemOut,
    EcosystemOverviewOut,
    EnrollmentCreate,
    EnrollmentOut,
)


class EcosystemService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.org = OrganizationService(db)
        self.audit = AuditEngine(db)

    def resolve_org(self, actor: ActorContext, organization_id: str | None = None) -> str:
        org_id = (organization_id or actor.organization_id or "").strip()
        if not org_id:
            raise HTTPException(status_code=400, detail="Organization is required")
        self.org.assert_org_access(
            username=actor.username, session_role=actor.role, organization_id=org_id
        )
        return org_id

    def seed(self, organization_id: str = "org-aviation-east") -> dict[str, int]:
        created = {"ecosystems": 0, "capabilities": 0, "enrollments": 0}
        for code, name, category, products, desc in ECOSYSTEMS:
            existing = self.db.scalars(
                select(EcosystemDefinition).where(EcosystemDefinition.code == code)
            ).first()
            if existing is None:
                self.db.add(
                    EcosystemDefinition(
                        code=code,
                        name=name,
                        category=category,
                        description=desc,
                        products_json=json.dumps(products),
                        ai_metadata_json=json.dumps(
                            {
                                "domain": "ecosystem",
                                "ecosystem": code,
                                "searchable": True,
                                "embedding_ready": False,
                                "aeos": True,
                            }
                        ),
                    )
                )
                created["ecosystems"] += 1
            for cap_code, cap_name, domains, fabric_types, readiness in CAPABILITIES.get(code, []):
                cap = self.db.scalars(
                    select(EcosystemCapability).where(
                        EcosystemCapability.ecosystem_code == code,
                        EcosystemCapability.code == cap_code,
                    )
                ).first()
                if cap is None:
                    self.db.add(
                        EcosystemCapability(
                            ecosystem_code=code,
                            code=cap_code,
                            name=cap_name,
                            description=f"{name} — {cap_name}",
                            domain_refs_json=json.dumps(domains),
                            fabric_entity_types_json=json.dumps(fabric_types),
                            readiness=readiness,
                        )
                    )
                    created["capabilities"] += 1

        # Demo org enrolled as airline + mro + camo
        for eco, role in (
            ("airline", "Scheduled operator"),
            ("mro", "Primary MRO"),
            ("camo", "CAMO of record"),
            ("marketplace", "Marketplace participant"),
        ):
            en = self.db.scalars(
                select(EcosystemEnrollment).where(
                    EcosystemEnrollment.organization_id == organization_id,
                    EcosystemEnrollment.ecosystem_code == eco,
                    EcosystemEnrollment.deleted_at.is_(None),
                )
            ).first()
            if en is None:
                caps = [c[0] for c in CAPABILITIES.get(eco, []) if c[4] == "ready"]
                self.db.add(
                    EcosystemEnrollment(
                        organization_id=organization_id,
                        ecosystem_code=eco,
                        role_label=role,
                        capabilities_enabled_json=json.dumps(caps),
                        created_by="system",
                    )
                )
                created["enrollments"] += 1

        if any(created.values()):
            self.db.commit()
        return created

    def list_ecosystems(self) -> list[EcosystemOut]:
        rows = self.db.scalars(
            select(EcosystemDefinition)
            .where(EcosystemDefinition.status == "active")
            .order_by(EcosystemDefinition.category, EcosystemDefinition.code)
        ).all()
        return [EcosystemOut.model_validate(r) for r in rows]

    def get_ecosystem(self, code: str) -> EcosystemDetailOut:
        eco = self.db.scalars(
            select(EcosystemDefinition).where(EcosystemDefinition.code == code)
        ).first()
        if eco is None:
            raise HTTPException(status_code=404, detail="Ecosystem not found")
        caps = self.db.scalars(
            select(EcosystemCapability)
            .where(
                EcosystemCapability.ecosystem_code == code,
                EcosystemCapability.status == "active",
            )
            .order_by(EcosystemCapability.code)
        ).all()
        return EcosystemDetailOut(
            ecosystem=EcosystemOut.model_validate(eco),
            capabilities=[CapabilityOut.model_validate(c) for c in caps],
        )

    def list_capabilities(self, ecosystem_code: str | None = None) -> list[CapabilityOut]:
        stmt = select(EcosystemCapability).where(EcosystemCapability.status == "active")
        if ecosystem_code:
            stmt = stmt.where(EcosystemCapability.ecosystem_code == ecosystem_code)
        rows = self.db.scalars(stmt.order_by(EcosystemCapability.ecosystem_code, EcosystemCapability.code)).all()
        return [CapabilityOut.model_validate(r) for r in rows]

    def enroll(self, payload: EnrollmentCreate, actor: ActorContext) -> EnrollmentOut:
        org_id = self.resolve_org(actor, payload.organization_id)
        eco = self.db.scalars(
            select(EcosystemDefinition).where(EcosystemDefinition.code == payload.ecosystem_code)
        ).first()
        if eco is None:
            raise HTTPException(status_code=404, detail="Ecosystem not found")
        row = EcosystemEnrollment(
            organization_id=org_id,
            ecosystem_code=payload.ecosystem_code.strip(),
            role_label=payload.role_label.strip(),
            capabilities_enabled_json=payload.capabilities_enabled_json,
            created_by=actor.username,
        )
        self.db.add(row)
        try:
            self.db.flush()
            self.audit.require(
                actor,
                action="ecosystem.enroll",
                target_type="ecosystem_enrollment",
                target_id=row.id,
                organization_id=org_id,
                details=payload.ecosystem_code,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Already enrolled in this ecosystem") from exc
        return EnrollmentOut.model_validate(row)

    def list_enrollments(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EnrollmentOut]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        rows = self.db.scalars(
            select(EcosystemEnrollment)
            .where(
                EcosystemEnrollment.organization_id == org_id,
                EcosystemEnrollment.deleted_at.is_(None),
            )
            .order_by(EcosystemEnrollment.ecosystem_code)
            .limit(lim)
            .offset(off)
        ).all()
        return [EnrollmentOut.model_validate(r) for r in rows]

    def overview(self, actor: ActorContext, *, organization_id: str | None = None) -> EcosystemOverviewOut:
        org_id = self.resolve_org(actor, organization_id)
        ecos = self.list_ecosystems()
        caps = self.list_capabilities()
        enrollments = int(
            self.db.scalar(
                select(func.count())
                .select_from(EcosystemEnrollment)
                .where(
                    EcosystemEnrollment.organization_id == org_id,
                    EcosystemEnrollment.deleted_at.is_(None),
                )
            )
            or 0
        )
        by_cat = dict(Counter(e.category for e in ecos))
        readiness = dict(Counter(c.readiness for c in caps))
        return EcosystemOverviewOut(
            organization_id=org_id,
            ecosystems=len(ecos),
            capabilities=len(caps),
            enrollments=enrollments,
            by_category=by_cat,
            readiness=readiness,
        )
