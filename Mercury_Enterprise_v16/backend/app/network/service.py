"""Program 14 — Mercury Aviation Network service.

Isolation by default. Cross-org collaboration requires an active partnership.
"""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..org.service import OrganizationService
from ..platform.audit_engine import AuditEngine
from ..platform.event_framework import event_framework
from ..shared import ActorContext, clamp_page
from .catalog import (
    COLLABORATION_TYPES,
    EVENT_TYPES,
    MESSAGE_SCOPES,
    ORG_TYPES,
    PARTNERSHIP_TYPES,
    PROFESSIONAL_ROLES,
    SHARE_MODES,
)
from .models import (
    NetworkCollaboration,
    NetworkDirectoryEntry,
    NetworkDocumentShare,
    NetworkEvent,
    NetworkMessage,
    NetworkMessageThread,
    NetworkOrgProfile,
    NetworkPartnership,
    NetworkProfessionalProfile,
)
from .schemas import DirectoryHitOut, DirectorySearchResponse, NetworkOverviewOut

DISCLAIMER = (
    "Mercury Aviation Network is a secure professional collaboration platform. "
    "Organizations remain isolated by default. Cross-organization access requires "
    "explicit partnership authorization. Not social media. Not regulatory verification."
)


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _ai_meta(**kwargs) -> str:
    base = {
        "domain": "network",
        "searchable": True,
        "embedding_ready": False,
        "zero_trust_ready": True,
    }
    base.update(kwargs)
    return json.dumps(base)


class NetworkService:
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

    def _ensure_directory(
        self,
        organization_id: str,
        entity_type: str,
        entity_ref: str,
        title: str,
        summary: str,
        tags: list[str],
    ) -> int:
        exists = self.db.scalars(
            select(NetworkDirectoryEntry).where(
                NetworkDirectoryEntry.organization_id == organization_id,
                NetworkDirectoryEntry.entity_type == entity_type,
                NetworkDirectoryEntry.entity_ref == entity_ref,
            )
        ).first()
        if exists:
            return 0
        self.db.add(
            NetworkDirectoryEntry(
                organization_id=organization_id,
                entity_type=entity_type,
                entity_ref=entity_ref,
                title=title,
                summary=summary,
                tags_json=json.dumps(tags),
                visibility="network",
                status="active",
            )
        )
        return 1

    def overview(self, actor: ActorContext, organization_id: str | None = None) -> NetworkOverviewOut:
        org_id = self.resolve_org(actor, organization_id)

        def cnt(model) -> int:
            stmt = select(func.count()).select_from(model).where(model.organization_id == org_id)
            if hasattr(model, "deleted_at"):
                stmt = stmt.where(model.deleted_at.is_(None))
            return int(self.db.scalar(stmt) or 0)

        return NetworkOverviewOut(
            organization_id=org_id,
            org_profiles=cnt(NetworkOrgProfile),
            professionals=cnt(NetworkProfessionalProfile),
            partnerships=cnt(NetworkPartnership),
            collaborations=cnt(NetworkCollaboration),
            document_shares=cnt(NetworkDocumentShare),
            threads=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(NetworkMessageThread)
                    .where(NetworkMessageThread.organization_id == org_id)
                )
                or 0
            ),
            events=cnt(NetworkEvent),
            directory_entries=int(
                self.db.scalar(
                    select(func.count())
                    .select_from(NetworkDirectoryEntry)
                    .where(NetworkDirectoryEntry.organization_id == org_id)
                )
                or 0
            ),
            disclaimer=DISCLAIMER,
        )

    def seed(self, organization_id: str = "org-aviation-east") -> dict[str, int]:
        created = {
            "org_profiles": 0,
            "professionals": 0,
            "partnerships": 0,
            "collaborations": 0,
            "events": 0,
            "directory": 0,
        }
        partner_west = "org-aviation-west"
        profiles = [
            ("airline", "Aviation East Airlines", ["line_maintenance", "heavy_check"], ["B737", "A320"], ["CFM56", "V2500"]),
            ("mro", "Aviation East MRO", ["component_repair", "avionics"], ["B737", "CRJ"], ["CF34"]),
            ("repair_station", "East Avionics Repair", ["avionics_repair", "ndt"], ["B737"], []),
            ("training_organization", "Mercury Academy East", ["type_training", "ewis"], ["B737"], []),
            ("supplier", "Aero Fasteners Network", ["hardware", "consumables"], [], []),
        ]
        for org_type, name, caps, ac, eng in profiles:
            row = self.db.scalars(
                select(NetworkOrgProfile).where(
                    NetworkOrgProfile.organization_id == organization_id,
                    NetworkOrgProfile.org_type == org_type,
                    NetworkOrgProfile.deleted_at.is_(None),
                )
            ).first()
            if row is None:
                row = NetworkOrgProfile(
                    organization_id=organization_id,
                    org_type=org_type,
                    display_name=name,
                    summary=f"Network profile — {org_type}",
                    capabilities_json=json.dumps(caps),
                    facilities_json=json.dumps([{"name": "East Base", "city": "Toronto"}]),
                    locations_json=json.dumps([{"country": "CA"}]),
                    aircraft_supported_json=json.dumps(ac),
                    engines_supported_json=json.dumps(eng),
                    directory_visible="true",
                    status="active",
                    ai_metadata_json=_ai_meta(entity="org_profile", org_type=org_type),
                    created_by="system",
                )
                self.db.add(row)
                self.db.flush()
                created["org_profiles"] += 1
            created["directory"] += self._ensure_directory(
                organization_id,
                "repair_station" if org_type == "repair_station" else "organization",
                row.id,
                name,
                f"{org_type} capabilities",
                caps,
            )

        for role, display, headline in (
            ("ame", "Demo AME", "Licensed AME — East Base"),
            ("engineer", "Demo Engineer", "Structures & systems"),
            ("planner", "Demo Planner", "Maintenance planning"),
            ("inspector", "Demo Inspector", "QA / inspection"),
        ):
            exists = self.db.scalars(
                select(NetworkProfessionalProfile).where(
                    NetworkProfessionalProfile.organization_id == organization_id,
                    NetworkProfessionalProfile.username == "operator",
                    NetworkProfessionalProfile.professional_role == role,
                    NetworkProfessionalProfile.deleted_at.is_(None),
                )
            ).first()
            if exists:
                continue
            prof = NetworkProfessionalProfile(
                organization_id=organization_id,
                username="operator",
                professional_role=role,
                display_name=display,
                headline=headline,
                experience_json=json.dumps([{"years": 8, "domain": role}]),
                licenses_json=json.dumps(["AME-M1"] if role == "ame" else []),
                skills_json=json.dumps([role, "aviation"]),
                directory_visible="true",
                status="active",
                ai_metadata_json=_ai_meta(entity="professional", role=role),
                created_by="system",
            )
            self.db.add(prof)
            self.db.flush()
            created["professionals"] += 1
            created["directory"] += self._ensure_directory(
                organization_id, "person", prof.id, display, headline, [role]
            )

        partnership = self.db.scalars(
            select(NetworkPartnership).where(
                NetworkPartnership.organization_id == organization_id,
                NetworkPartnership.partner_organization_id == partner_west,
                NetworkPartnership.partnership_type == "partner",
                NetworkPartnership.deleted_at.is_(None),
            )
        ).first()
        if partnership is None:
            partnership = NetworkPartnership(
                organization_id=organization_id,
                partner_organization_id=partner_west,
                partnership_type="partner",
                status="active",
                permissions_json=json.dumps(
                    ["messaging", "document_share", "collaboration", "directory"]
                ),
                contracts_json=json.dumps([{"ref": "NET-MOU-001", "status": "architecture"}]),
                notes="Demo cross-org partnership — explicit authorization only",
                created_by="system",
                approved_by="system",
            )
            self.db.add(partnership)
            self.db.flush()
            created["partnerships"] += 1

        collab = self.db.scalars(
            select(NetworkCollaboration).where(
                NetworkCollaboration.organization_id == organization_id,
                NetworkCollaboration.title == "Engineering support — demo",
                NetworkCollaboration.deleted_at.is_(None),
            )
        ).first()
        if collab is None:
            self.db.add(
                NetworkCollaboration(
                    organization_id=organization_id,
                    partner_organization_id=partner_west,
                    partnership_id=partnership.id,
                    collaboration_type="engineering_support",
                    title="Engineering support — demo",
                    summary="Request structural engineering assistance",
                    status="accepted",
                    created_by="system",
                )
            )
            created["collaborations"] += 1

        for etype, title in (
            ("training", "EWIS Recurrent — East"),
            ("webinar", "Marketplace Seller Onboarding"),
            ("maintenance_event", "C-Check Hangar Window"),
        ):
            exists = self.db.scalars(
                select(NetworkEvent).where(
                    NetworkEvent.organization_id == organization_id,
                    NetworkEvent.event_type == etype,
                    NetworkEvent.title == title,
                    NetworkEvent.deleted_at.is_(None),
                )
            ).first()
            if exists:
                continue
            ev = NetworkEvent(
                organization_id=organization_id,
                event_type=etype,
                title=title,
                summary=f"Network event ({etype})",
                location="East Campus",
                directory_visible="true",
                status="published",
                created_by="system",
            )
            self.db.add(ev)
            self.db.flush()
            created["events"] += 1
            created["directory"] += self._ensure_directory(
                organization_id,
                "training" if etype == "training" else "capability",
                ev.id,
                title,
                etype,
                [etype],
            )

        if any(created.values()):
            self.db.commit()
        return created

    def _require_active_partnership(
        self, org_id: str, partner_org_id: str, permission: str | None = None
    ) -> NetworkPartnership:
        if org_id == partner_org_id:
            raise HTTPException(status_code=400, detail="Partner organization must differ")
        row = self.db.scalars(
            select(NetworkPartnership).where(
                NetworkPartnership.organization_id == org_id,
                NetworkPartnership.partner_organization_id == partner_org_id,
                NetworkPartnership.status == "active",
                NetworkPartnership.deleted_at.is_(None),
            )
        ).first()
        if row is None:
            raise HTTPException(
                status_code=403,
                detail="Active partnership required for cross-organization collaboration",
            )
        if row.expires_at and row.expires_at < datetime.utcnow():
            row.status = "expired"
            self.db.commit()
            raise HTTPException(status_code=403, detail="Partnership expired")
        if permission:
            try:
                perms = json.loads(row.permissions_json or "[]")
            except json.JSONDecodeError:
                perms = []
            if permission not in perms and "*" not in perms:
                raise HTTPException(
                    status_code=403, detail=f"Partnership lacks permission: {permission}"
                )
        return row

    def create_partnership(self, actor: ActorContext, **kwargs) -> NetworkPartnership:
        ptype = kwargs["partnership_type"]
        if ptype not in PARTNERSHIP_TYPES:
            raise HTTPException(status_code=400, detail="Invalid partnership_type")
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        partner = kwargs["partner_organization_id"].strip()
        if partner == org_id:
            raise HTTPException(status_code=400, detail="Cannot partner with self")
        row = NetworkPartnership(
            organization_id=org_id,
            partner_organization_id=partner,
            partnership_type=ptype,
            status="proposed",
            permissions_json=kwargs.get("permissions_json")
            or '["messaging","document_share","collaboration"]',
            contracts_json=kwargs.get("contracts_json") or "[]",
            expires_at=kwargs.get("expires_at"),
            notes=(kwargs.get("notes") or "").strip(),
            created_by=actor.username,
        )
        self.db.add(row)
        try:
            self.db.flush()
            self.audit.require(
                actor,
                action="network.partnership.create",
                target_type="network_partnership",
                target_id=row.id,
                organization_id=org_id,
                details=ptype,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Partnership already exists") from exc
        event_framework.publish_sync(
            "network.partnership.created",
            {"id": row.id, "partner": partner, "type": ptype},
            organization_id=org_id,
            source="network",
        )
        return row

    def approve_partnership(
        self, actor: ActorContext, partnership_id: str, organization_id: str | None = None
    ) -> NetworkPartnership:
        org_id = self.resolve_org(actor, organization_id)
        row = self.db.get(NetworkPartnership, partnership_id)
        if row is None or row.deleted_at is not None or row.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Partnership not found")
        row.status = "active"
        row.approved_by = actor.username
        row.updated_at = datetime.utcnow()
        self.audit.require(
            actor,
            action="network.partnership.approve",
            target_type="network_partnership",
            target_id=row.id,
            organization_id=org_id,
            details=row.partner_organization_id,
        )
        self.db.commit()
        return row

    def list_partnerships(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkPartnership]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(NetworkPartnership).where(
            NetworkPartnership.organization_id == org_id,
            NetworkPartnership.deleted_at.is_(None),
        )
        if status:
            stmt = stmt.where(NetworkPartnership.status == status)
        return list(
            self.db.scalars(
                stmt.order_by(NetworkPartnership.created_at.desc()).limit(lim).offset(off)
            ).all()
        )

    def create_org_profile(self, actor: ActorContext, **kwargs) -> NetworkOrgProfile:
        if kwargs["org_type"] not in ORG_TYPES:
            raise HTTPException(status_code=400, detail="Invalid org_type")
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        row = NetworkOrgProfile(
            organization_id=org_id,
            org_type=kwargs["org_type"],
            display_name=kwargs["display_name"].strip(),
            summary=(kwargs.get("summary") or "").strip(),
            capabilities_json=kwargs.get("capabilities_json") or "[]",
            certificates_json=kwargs.get("certificates_json") or "[]",
            approvals_json=kwargs.get("approvals_json") or "[]",
            facilities_json=kwargs.get("facilities_json") or "[]",
            locations_json=kwargs.get("locations_json") or "[]",
            aircraft_supported_json=kwargs.get("aircraft_supported_json") or "[]",
            engines_supported_json=kwargs.get("engines_supported_json") or "[]",
            ratings_json=kwargs.get("ratings_json") or "[]",
            marketplace_profile_ref=kwargs.get("marketplace_profile_ref") or "",
            careers_json=kwargs.get("careers_json") or "{}",
            training_json=kwargs.get("training_json") or "{}",
            library_access_json=kwargs.get("library_access_json") or "{}",
            directory_visible=_bool_str(bool(kwargs.get("directory_visible", True))),
            status="active",
            ai_metadata_json=_ai_meta(entity="org_profile"),
            created_by=actor.username,
        )
        self.db.add(row)
        try:
            self.db.flush()
            if row.directory_visible == "true":
                self._ensure_directory(
                    org_id, "organization", row.id, row.display_name, row.summary, [row.org_type]
                )
            self.audit.require(
                actor,
                action="network.org_profile.create",
                target_type="network_org_profile",
                target_id=row.id,
                organization_id=org_id,
                details=row.org_type,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Org profile already exists") from exc
        return row

    def list_org_profiles(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        org_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkOrgProfile]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(NetworkOrgProfile).where(
            NetworkOrgProfile.organization_id == org_id,
            NetworkOrgProfile.deleted_at.is_(None),
        )
        if org_type:
            stmt = stmt.where(NetworkOrgProfile.org_type == org_type)
        return list(
            self.db.scalars(stmt.order_by(NetworkOrgProfile.org_type).limit(lim).offset(off)).all()
        )

    def create_professional(self, actor: ActorContext, **kwargs) -> NetworkProfessionalProfile:
        role = kwargs["professional_role"]
        if role not in PROFESSIONAL_ROLES:
            raise HTTPException(status_code=400, detail="Invalid professional_role")
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        row = NetworkProfessionalProfile(
            organization_id=org_id,
            username=actor.username,
            professional_role=role,
            display_name=kwargs["display_name"].strip(),
            headline=(kwargs.get("headline") or "").strip(),
            experience_json=kwargs.get("experience_json") or "[]",
            licenses_json=kwargs.get("licenses_json") or "[]",
            ratings_json=kwargs.get("ratings_json") or "[]",
            training_json=kwargs.get("training_json") or "[]",
            certificates_json=kwargs.get("certificates_json") or "[]",
            skills_json=kwargs.get("skills_json") or "[]",
            employment_history_json=kwargs.get("employment_history_json") or "[]",
            portfolio_json=kwargs.get("portfolio_json") or "[]",
            credential_links_json=kwargs.get("credential_links_json") or "[]",
            personnel_ref=kwargs.get("personnel_ref") or "",
            directory_visible=_bool_str(bool(kwargs.get("directory_visible", False))),
            status="active",
            ai_metadata_json=_ai_meta(entity="professional", role=role),
            created_by=actor.username,
        )
        self.db.add(row)
        try:
            self.db.flush()
            if row.directory_visible == "true":
                self._ensure_directory(
                    org_id, "person", row.id, row.display_name, row.headline, [role]
                )
            self.audit.require(
                actor,
                action="network.professional.create",
                target_type="network_professional",
                target_id=row.id,
                organization_id=org_id,
                details=role,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Professional profile already exists") from exc
        return row

    def list_professionals(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        professional_role: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkProfessionalProfile]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(NetworkProfessionalProfile).where(
            NetworkProfessionalProfile.organization_id == org_id,
            NetworkProfessionalProfile.deleted_at.is_(None),
        )
        if professional_role:
            stmt = stmt.where(NetworkProfessionalProfile.professional_role == professional_role)
        return list(
            self.db.scalars(
                stmt.order_by(NetworkProfessionalProfile.professional_role).limit(lim).offset(off)
            ).all()
        )

    def create_collaboration(self, actor: ActorContext, **kwargs) -> NetworkCollaboration:
        ctype = kwargs["collaboration_type"]
        if ctype not in COLLABORATION_TYPES:
            raise HTTPException(status_code=400, detail="Invalid collaboration_type")
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        partner = kwargs["partner_organization_id"].strip()
        partnership = self._require_active_partnership(org_id, partner, "collaboration")
        row = NetworkCollaboration(
            organization_id=org_id,
            partner_organization_id=partner,
            partnership_id=kwargs.get("partnership_id") or partnership.id,
            collaboration_type=ctype,
            title=kwargs["title"].strip(),
            summary=(kwargs.get("summary") or "").strip(),
            status="requested",
            work_package_ref=kwargs.get("work_package_ref") or "",
            project_ref=kwargs.get("project_ref") or "",
            metadata_json=kwargs.get("metadata_json") or "{}",
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="network.collaboration.create",
            target_type="network_collaboration",
            target_id=row.id,
            organization_id=org_id,
            details=ctype,
        )
        self.db.commit()
        event_framework.publish_sync(
            "network.collaboration.created",
            {"id": row.id, "type": ctype, "partner": partner},
            organization_id=org_id,
            source="network",
        )
        return row

    def list_collaborations(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkCollaboration]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(NetworkCollaboration)
                .where(
                    NetworkCollaboration.organization_id == org_id,
                    NetworkCollaboration.deleted_at.is_(None),
                )
                .order_by(NetworkCollaboration.created_at.desc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    def create_document_share(self, actor: ActorContext, **kwargs) -> NetworkDocumentShare:
        mode = kwargs.get("share_mode") or "read_only"
        if mode not in SHARE_MODES:
            raise HTTPException(status_code=400, detail="Invalid share_mode")
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        partner = kwargs["partner_organization_id"].strip()
        partnership = self._require_active_partnership(org_id, partner, "document_share")
        approval_required = bool(kwargs.get("approval_required", False))
        row = NetworkDocumentShare(
            organization_id=org_id,
            partner_organization_id=partner,
            partnership_id=kwargs.get("partnership_id") or partnership.id,
            document_ref=kwargs["document_ref"].strip(),
            title=(kwargs.get("title") or "").strip(),
            share_mode=mode,
            watermark=_bool_str(bool(kwargs.get("watermark", True))),
            download_allowed=_bool_str(bool(kwargs.get("download_allowed", False))),
            approval_required=_bool_str(approval_required),
            approval_status="pending" if approval_required else "not_required",
            expires_at=kwargs.get("expires_at"),
            status="active",
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="network.document_share.create",
            target_type="network_document_share",
            target_id=row.id,
            organization_id=org_id,
            details=row.document_ref,
        )
        self.db.commit()
        return row

    def list_document_shares(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkDocumentShare]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(NetworkDocumentShare)
                .where(
                    NetworkDocumentShare.organization_id == org_id,
                    NetworkDocumentShare.deleted_at.is_(None),
                )
                .order_by(NetworkDocumentShare.created_at.desc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    def create_thread(self, actor: ActorContext, **kwargs) -> NetworkMessageThread:
        scope = kwargs.get("scope") or "org_to_org"
        if scope not in MESSAGE_SCOPES:
            raise HTTPException(status_code=400, detail="Invalid scope")
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        partner = (kwargs.get("partner_organization_id") or "").strip()
        partnership_id = kwargs.get("partnership_id") or ""
        if scope in {"org_to_org", "project", "work_package", "marketplace"} and partner:
            p = self._require_active_partnership(org_id, partner, "messaging")
            partnership_id = partnership_id or p.id
        row = NetworkMessageThread(
            organization_id=org_id,
            partner_organization_id=partner,
            scope=scope,
            subject=kwargs["subject"].strip(),
            project_ref=kwargs.get("project_ref") or "",
            work_package_ref=kwargs.get("work_package_ref") or "",
            marketplace_ref=kwargs.get("marketplace_ref") or "",
            partnership_id=partnership_id,
            status="open",
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="network.thread.create",
            target_type="network_message_thread",
            target_id=row.id,
            organization_id=org_id,
            details=scope,
        )
        self.db.commit()
        return row

    def list_threads(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkMessageThread]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(NetworkMessageThread)
                .where(NetworkMessageThread.organization_id == org_id)
                .order_by(NetworkMessageThread.created_at.desc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    def post_message(self, actor: ActorContext, **kwargs) -> NetworkMessage:
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        thread = self.db.get(NetworkMessageThread, kwargs["thread_id"])
        if thread is None or thread.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Thread not found")
        row = NetworkMessage(
            organization_id=org_id,
            thread_id=thread.id,
            sender_username=actor.username,
            body=kwargs["body"].strip(),
        )
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="network.message.create",
            target_type="network_message",
            target_id=row.id,
            organization_id=org_id,
            details=thread.id,
        )
        self.db.commit()
        return row

    def list_messages(
        self,
        actor: ActorContext,
        thread_id: str,
        *,
        organization_id: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[NetworkMessage]:
        org_id = self.resolve_org(actor, organization_id)
        thread = self.db.get(NetworkMessageThread, thread_id)
        if thread is None or thread.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Thread not found")
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(NetworkMessage)
                .where(NetworkMessage.thread_id == thread_id)
                .order_by(NetworkMessage.created_at.asc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    def create_event(self, actor: ActorContext, **kwargs) -> NetworkEvent:
        etype = kwargs["event_type"]
        if etype not in EVENT_TYPES:
            raise HTTPException(status_code=400, detail="Invalid event_type")
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        row = NetworkEvent(
            organization_id=org_id,
            event_type=etype,
            title=kwargs["title"].strip(),
            summary=(kwargs.get("summary") or "").strip(),
            location=(kwargs.get("location") or "").strip(),
            starts_at=kwargs.get("starts_at"),
            ends_at=kwargs.get("ends_at"),
            directory_visible=_bool_str(bool(kwargs.get("directory_visible", True))),
            status="published",
            metadata_json=kwargs.get("metadata_json") or "{}",
            created_by=actor.username,
        )
        self.db.add(row)
        self.db.flush()
        if row.directory_visible == "true":
            self._ensure_directory(
                org_id,
                "training" if etype == "training" else "capability",
                row.id,
                row.title,
                row.summary,
                [etype],
            )
        self.audit.require(
            actor,
            action="network.event.create",
            target_type="network_event",
            target_id=row.id,
            organization_id=org_id,
            details=etype,
        )
        self.db.commit()
        return row

    def list_events(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkEvent]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(NetworkEvent).where(
            NetworkEvent.organization_id == org_id,
            NetworkEvent.deleted_at.is_(None),
        )
        if event_type:
            stmt = stmt.where(NetworkEvent.event_type == event_type)
        return list(
            self.db.scalars(stmt.order_by(NetworkEvent.created_at.desc()).limit(lim).offset(off)).all()
        )

    def search_directory(
        self,
        actor: ActorContext,
        *,
        q: str = "",
        entity_type: str | None = None,
        organization_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> DirectorySearchResponse:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(NetworkDirectoryEntry).where(
            NetworkDirectoryEntry.organization_id == org_id,
            NetworkDirectoryEntry.status == "active",
        )
        if entity_type:
            stmt = stmt.where(NetworkDirectoryEntry.entity_type == entity_type)
        query = (q or "").strip()
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    NetworkDirectoryEntry.title.ilike(like),
                    NetworkDirectoryEntry.summary.ilike(like),
                    NetworkDirectoryEntry.tags_json.ilike(like),
                )
            )
        rows = list(
            self.db.scalars(stmt.order_by(NetworkDirectoryEntry.title).limit(lim).offset(off)).all()
        )
        return DirectorySearchResponse(
            query=query,
            total=len(rows),
            items=[DirectoryHitOut.model_validate(r) for r in rows],
        )
