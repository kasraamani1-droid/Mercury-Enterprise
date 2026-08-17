"""Program 16 — Mercury Plugin Platform service."""

from __future__ import annotations

import json
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..org.service import OrganizationService
from ..platform.audit_engine import AuditEngine
from ..platform.event_framework import event_framework
from ..shared import ActorContext, clamp_page
from .catalog import INSTALL_STATUSES, PLUGINS
from .models import PluginDashboardLayout, PluginDefinition, PluginInstallation
from .schemas import PluginsOverviewOut

DISCLAIMER = (
    "Mercury Plugin Platform is architecture readiness for OEM and operational integrations. "
    "Live Garmin/Honeywell/drone/ERP adapters are future Connect bindings (vault secrets only). "
    "SMS means Safety Management System — not cellular text messaging."
)


class PluginService:
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
        created = {"plugins": 0, "installations": 0, "dashboards": 0}
        for code, name, category, connector, caps, readiness, desc in PLUGINS:
            row = self.db.scalars(
                select(PluginDefinition).where(PluginDefinition.code == code)
            ).first()
            if row is None:
                self.db.add(
                    PluginDefinition(
                        code=code,
                        name=name,
                        category=category,
                        connect_connector=connector,
                        description=desc,
                        capabilities_json=json.dumps(caps),
                        readiness=readiness,
                        disclaimer=(
                            "Architecture readiness only. Not a live vendor certification. "
                            + (
                                "SMS = Safety Management System (not text messaging)."
                                if code == "sms"
                                else "Live adapters via Mercury Connect."
                            )
                        ),
                        ai_metadata_json=json.dumps(
                            {
                                "domain": "plugins",
                                "plugin": code,
                                "searchable": True,
                                "embedding_ready": False,
                                "connect_connector": connector,
                            }
                        ),
                        status="active",
                    )
                )
                created["plugins"] += 1

        # Demo installs: ready/partial plugins that are commonly demoed
        for code in ("accounting", "erp", "custom_dashboards", "weather", "ndt", "garmin"):
            exists = self.db.scalars(
                select(PluginInstallation).where(
                    PluginInstallation.organization_id == organization_id,
                    PluginInstallation.plugin_code == code,
                    PluginInstallation.deleted_at.is_(None),
                )
            ).first()
            if exists:
                continue
            self.db.add(
                PluginInstallation(
                    organization_id=organization_id,
                    plugin_code=code,
                    install_status="configured" if code in {"accounting", "erp", "custom_dashboards"} else "installed",
                    config_ref=f"vault://plugins/{organization_id}/{code}",
                    config_json=json.dumps({"seed": True}),
                    notes="Demo installation — secrets via config_ref only",
                    created_by="system",
                )
            )
            created["installations"] += 1

        dash = self.db.scalars(
            select(PluginDashboardLayout).where(
                PluginDashboardLayout.organization_id == organization_id,
                PluginDashboardLayout.name == "Ops Overview",
                PluginDashboardLayout.deleted_at.is_(None),
            )
        ).first()
        if dash is None:
            self.db.add(
                PluginDashboardLayout(
                    organization_id=organization_id,
                    name="Ops Overview",
                    widgets_json=json.dumps(
                        [
                            {"id": "w1", "type": "fleet_status", "title": "Fleet"},
                            {"id": "w2", "type": "weather", "title": "Weather"},
                            {"id": "w3", "type": "work_orders", "title": "Open WOs"},
                            {"id": "w4", "type": "marketplace", "title": "Open Quotes"},
                        ]
                    ),
                    is_default="true",
                    status="active",
                    created_by="system",
                )
            )
            created["dashboards"] += 1

        if any(created.values()):
            self.db.commit()
        return created

    def overview(self, actor: ActorContext, organization_id: str | None = None) -> PluginsOverviewOut:
        org_id = self.resolve_org(actor, organization_id)
        defs = list(
            self.db.scalars(
                select(PluginDefinition).where(PluginDefinition.status == "active")
            ).all()
        )
        installs = int(
            self.db.scalar(
                select(func.count())
                .select_from(PluginInstallation)
                .where(
                    PluginInstallation.organization_id == org_id,
                    PluginInstallation.deleted_at.is_(None),
                )
            )
            or 0
        )
        dashboards = int(
            self.db.scalar(
                select(func.count())
                .select_from(PluginDashboardLayout)
                .where(
                    PluginDashboardLayout.organization_id == org_id,
                    PluginDashboardLayout.deleted_at.is_(None),
                )
            )
            or 0
        )
        return PluginsOverviewOut(
            organization_id=org_id,
            plugins=len(defs),
            installations=installs,
            dashboards=dashboards,
            by_category=dict(Counter(d.category for d in defs)),
            by_readiness=dict(Counter(d.readiness for d in defs)),
            disclaimer=DISCLAIMER,
        )

    def list_plugins(self, *, category: str | None = None) -> list[PluginDefinition]:
        stmt = select(PluginDefinition).where(PluginDefinition.status == "active")
        if category:
            stmt = stmt.where(PluginDefinition.category == category)
        return list(self.db.scalars(stmt.order_by(PluginDefinition.category, PluginDefinition.code)).all())

    def get_plugin(self, code: str) -> PluginDefinition:
        row = self.db.scalars(select(PluginDefinition).where(PluginDefinition.code == code)).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Plugin not found")
        return row

    def install(self, actor: ActorContext, **kwargs) -> PluginInstallation:
        code = kwargs["plugin_code"].strip()
        plugin = self.get_plugin(code)
        status = kwargs.get("install_status") or "installed"
        if status not in INSTALL_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid install_status")
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        config_ref = (kwargs.get("config_ref") or "").strip()
        if config_ref and not config_ref.startswith("vault://"):
            raise HTTPException(status_code=400, detail="config_ref must be a vault:// reference")
        row = PluginInstallation(
            organization_id=org_id,
            plugin_code=plugin.code,
            install_status=status,
            config_json=kwargs.get("config_json") or "{}",
            config_ref=config_ref or f"vault://plugins/{org_id}/{plugin.code}",
            notes=(kwargs.get("notes") or "").strip(),
            created_by=actor.username,
        )
        self.db.add(row)
        try:
            self.db.flush()
            self.audit.require(
                actor,
                action="plugins.install",
                target_type="plugin_installation",
                target_id=row.id,
                organization_id=org_id,
                details=plugin.code,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Plugin already installed") from exc
        event_framework.publish_sync(
            "plugins.installed",
            {"id": row.id, "plugin_code": plugin.code, "connect": plugin.connect_connector},
            organization_id=org_id,
            source="plugins",
        )
        return row

    def list_installations(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PluginInstallation]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(PluginInstallation)
                .where(
                    PluginInstallation.organization_id == org_id,
                    PluginInstallation.deleted_at.is_(None),
                )
                .order_by(PluginInstallation.plugin_code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def create_dashboard(self, actor: ActorContext, **kwargs) -> PluginDashboardLayout:
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        # Require custom_dashboards plugin installed
        inst = self.db.scalars(
            select(PluginInstallation).where(
                PluginInstallation.organization_id == org_id,
                PluginInstallation.plugin_code == "custom_dashboards",
                PluginInstallation.deleted_at.is_(None),
            )
        ).first()
        if inst is None:
            raise HTTPException(
                status_code=400,
                detail="Install custom_dashboards plugin before creating layouts",
            )
        row = PluginDashboardLayout(
            organization_id=org_id,
            name=kwargs["name"].strip(),
            widgets_json=kwargs.get("widgets_json") or "[]",
            is_default="true" if kwargs.get("is_default") else "false",
            status="active",
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="plugins.dashboard.create",
            target_type="plugin_dashboard",
            target_id=row.id,
            organization_id=org_id,
            details=row.name,
        )
        self.db.commit()
        return row

    def list_dashboards(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PluginDashboardLayout]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(PluginDashboardLayout)
                .where(
                    PluginDashboardLayout.organization_id == org_id,
                    PluginDashboardLayout.deleted_at.is_(None),
                )
                .order_by(PluginDashboardLayout.name)
                .limit(lim)
                .offset(off)
            ).all()
        )
