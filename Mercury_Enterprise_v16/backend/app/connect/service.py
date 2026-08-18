"""Mercury Connect service."""

from __future__ import annotations

import json
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ecosystem.catalog import CONNECTORS
from ..org.service import OrganizationService
from ..platform.audit_engine import AuditEngine
from ..shared import ActorContext, clamp_page
from .models import ConnectBinding, ConnectConnector
from .schemas import BindingCreate, BindingOut, ConnectOverviewOut, ConnectorOut


class ConnectService:
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
        created = {"connectors": 0, "bindings": 0}
        for code, name, category, caps, readiness in CONNECTORS:
            if self.db.scalars(select(ConnectConnector).where(ConnectConnector.code == code)).first():
                continue
            self.db.add(
                ConnectConnector(
                    code=code,
                    name=name,
                    category=category,
                    description=f"Mercury Connect — {name}",
                    capabilities_json=json.dumps(caps),
                    readiness=readiness,
                    ai_metadata_json=json.dumps(
                        {
                            "domain": "connect",
                            "connector": code,
                            "searchable": True,
                            "embedding_ready": False,
                        }
                    ),
                )
            )
            created["connectors"] += 1

        # Demo bindings (metadata only — secrets via config_ref)
        for code, label in (
            ("identity.oidc", "Primary IdP"),
            ("email.smtp", "Notification SMTP"),
            ("storage.object", "Tech Pubs Object Store"),
        ):
            exists = self.db.scalars(
                select(ConnectBinding).where(
                    ConnectBinding.organization_id == organization_id,
                    ConnectBinding.connector_code == code,
                    ConnectBinding.deleted_at.is_(None),
                )
            ).first()
            if exists:
                continue
            self.db.add(
                ConnectBinding(
                    organization_id=organization_id,
                    connector_code=code,
                    display_name=label,
                    binding_status="configured",
                    config_ref=f"vault://connect/{organization_id}/{code}",
                    created_by="system",
                )
            )
            created["bindings"] += 1

        if any(created.values()):
            self.db.commit()
        return created

    def list_connectors(self, *, category: str | None = None) -> list[ConnectorOut]:
        stmt = select(ConnectConnector).where(ConnectConnector.status == "active")
        if category:
            stmt = stmt.where(ConnectConnector.category == category)
        rows = self.db.scalars(stmt.order_by(ConnectConnector.category, ConnectConnector.code)).all()
        return [ConnectorOut.model_validate(r) for r in rows]

    def get_connector(self, code: str) -> ConnectorOut:
        row = self.db.scalars(select(ConnectConnector).where(ConnectConnector.code == code)).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Connector not found")
        return ConnectorOut.model_validate(row)

    def create_binding(self, payload: BindingCreate, actor: ActorContext) -> BindingOut:
        org_id = self.resolve_org(actor, payload.organization_id)
        if self.db.scalars(
            select(ConnectConnector).where(ConnectConnector.code == payload.connector_code)
        ).first() is None:
            raise HTTPException(status_code=404, detail="Connector not found")
        row = ConnectBinding(
            organization_id=org_id,
            connector_code=payload.connector_code.strip(),
            display_name=payload.display_name.strip() or payload.connector_code,
            config_ref=payload.config_ref.strip(),
            endpoint_hint=payload.endpoint_hint.strip(),
            metadata_json=payload.metadata_json,
            created_by=actor.username,
        )
        self.db.add(row)
        try:
            self.db.flush()
            self.audit.require(
                actor,
                action="connect.binding.create",
                target_type="connect_binding",
                target_id=row.id,
                organization_id=org_id,
                details=payload.connector_code,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Binding already exists") from exc
        return BindingOut.model_validate(row)

    def list_bindings(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[BindingOut]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        rows = self.db.scalars(
            select(ConnectBinding)
            .where(
                ConnectBinding.organization_id == org_id,
                ConnectBinding.deleted_at.is_(None),
            )
            .order_by(ConnectBinding.connector_code)
            .limit(lim)
            .offset(off)
        ).all()
        return [BindingOut.model_validate(r) for r in rows]

    def overview(self, actor: ActorContext, *, organization_id: str | None = None) -> ConnectOverviewOut:
        org_id = self.resolve_org(actor, organization_id)
        connectors = self.list_connectors()
        bindings = int(
            self.db.scalar(
                select(func.count())
                .select_from(ConnectBinding)
                .where(
                    ConnectBinding.organization_id == org_id,
                    ConnectBinding.deleted_at.is_(None),
                )
            )
            or 0
        )
        return ConnectOverviewOut(
            organization_id=org_id,
            connectors=len(connectors),
            bindings=bindings,
            by_category=dict(Counter(c.category for c in connectors)),
            readiness=dict(Counter(c.readiness for c in connectors)),
        )
