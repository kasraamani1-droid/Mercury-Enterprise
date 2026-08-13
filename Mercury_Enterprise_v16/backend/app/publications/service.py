from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..components.repository import ComponentRepository
from ..fleet.repository import FleetRepository
from ..org.service import OrganizationService
from .models import (
    Publication,
    PublicationAtaLink,
    PublicationCatalogLink,
    PublicationRevision,
    PublicationType,
)
from .repository import PublicationRepository
from .schemas import (
    AccessClassificationUpdate,
    ComponentPublicationOut,
    LibraryBrowseOut,
    LibraryNodeOut,
    PublicationCreate,
    PublicationOut,
    PublicationTypeOut,
    PublicationUpdate,
    RevisionCreate,
    RevisionOut,
    StorageRefIn,
)
from .storage import normalize_storage

logger = logging.getLogger("mercury.publications")

ACCESS_CLASSIFICATIONS = frozenset({"public", "internal", "restricted", "licensed"})
REVISION_STATUSES = frozenset({"draft", "current", "superseded", "archived"})

MAINTENANCE_MANUAL_TYPES: list[tuple[str, str, str]] = [
    ("AIPC", "Aircraft Illustrated Parts Catalog", "maintenance_manual"),
    ("IPC", "Illustrated Parts Catalog", "maintenance_manual"),
    ("AMM", "Aircraft Maintenance Manual", "maintenance_manual"),
    ("CMM", "Component Maintenance Manual", "maintenance_manual"),
    ("GHSI", "Ground Handling and Servicing Information", "maintenance_manual"),
    ("ITEM", "Illustrated Tool and Equipment Manual", "maintenance_manual"),
    ("MPD", "Maintenance Planning Document", "maintenance_manual"),
    ("NDT", "Nondestructive Testing Manual", "maintenance_manual"),
    ("SPM", "Standard Practices Manual", "maintenance_manual"),
    ("SRM", "Structural Repair Manual", "maintenance_manual"),
    ("SDS", "System Description Section / AMM Part One", "maintenance_manual"),
    ("FIM", "Fault Isolation Manual", "maintenance_manual"),
    ("MFIM", "Maintenance Fault Isolation Manual", "maintenance_manual"),
    ("TSM", "Troubleshooting Manual", "maintenance_manual"),
    ("WDM", "Wiring Diagram Manual", "maintenance_manual"),
    ("SDM", "System Description Manual", "maintenance_manual"),
    ("SSM", "System Schematic Manual", "maintenance_manual"),
    ("TLMC", "Time Limits and Maintenance Checks", "maintenance_manual"),
    ("WBM", "Weight and Balance Manual", "maintenance_manual"),
    ("WLM", "Wiring List Manual", "maintenance_manual"),
    ("WM", "Wiring Manual", "maintenance_manual"),
]

FLIGHT_MANUAL_TYPES: list[tuple[str, str, str]] = [
    ("AFM", "Airplane Flight Manual", "flight_manual"),
    ("FCOM", "Flight Crew Operating Manual", "flight_manual"),
    ("QRH", "Quick Reference Handbook", "flight_manual"),
    ("MEL", "Minimum Equipment List", "flight_manual"),
    ("CDL", "Configuration Deviation List", "flight_manual"),
]

ENGINEERING_PUBLICATION_TYPES: list[tuple[str, str, str]] = [
    ("EO", "Engineering Order", "engineering"),
    ("EI", "Engineering Instruction", "engineering"),
    ("ED", "Engineering Drawing", "engineering"),
    ("ICA", "Instructions for Continued Airworthiness", "engineering"),
    ("STC", "Supplemental Type Certificate Documentation", "engineering"),
    ("RS", "Repair Scheme", "engineering"),
    ("CDP", "Configuration Deviation Publication", "engineering"),
]

OTHER_PUBLICATION_TYPES: list[tuple[str, str, str]] = [
    ("AW", "Advisory Wires", "operations"),
    ("AMTOSS", "Aircraft Maintenance Task Oriented Support System", "operations"),
    ("ARM", "Aircraft Recovery Manual", "operations"),
    ("AIFM", "Airport Facilities Manual", "operations"),
    ("ATA-AMM", "ATA 100 Breakdown for AMM", "operations"),
    ("ATA-SPM", "ATA 100 Breakdown for SPM", "operations"),
    ("CCC", "Crash Crew Chart", "operations"),
    ("DDG", "Dispatch Deviation Guide", "operations"),
    ("DDG-EASA", "Dispatch Deviation Guide EASA", "operations"),
    ("DDG-FAA", "Dispatch Deviation Guide FAA", "operations"),
    ("DDG-TC", "Dispatch Deviation Guide Transport Canada", "operations"),
    ("GOC", "Ground Operations Checklist", "operations"),
    ("MFM", "Maintenance Facilities Manual", "operations"),
    ("SB", "Service Bulletins", "operations"),
    ("SL", "Service Letters", "operations"),
    ("SIL", "Service Information Letter", "operations"),
    ("APT", "Alternate Parts Table", "operations"),
]

ALL_PUBLICATION_TYPES = (
    MAINTENANCE_MANUAL_TYPES
    + FLIGHT_MANUAL_TYPES
    + ENGINEERING_PUBLICATION_TYPES
    + OTHER_PUBLICATION_TYPES
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PublicationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PublicationRepository(db)
        self.org = OrganizationService(db)
        self.fleet = FleetRepository(db)
        self.components = ComponentRepository(db)

    def ensure_seed_data(self) -> None:
        pending = False
        now = _utcnow()
        # Upsert missing publication type codes (supports expanding catalogs on existing DBs).
        for code, name, category in ALL_PUBLICATION_TYPES:
            if self.repo.get_type_by_code(code) is None:
                self.repo.add_type(
                    PublicationType(
                        id=f"pubtype-{code.lower().replace('_', '-')}",
                        code=code,
                        name=name,
                        category=category,
                        description=name,
                        created_at=now,
                        updated_at=now,
                    )
                )
                pending = True

        org_id = "org-aviation-east"
        if self.org.repo.get_organization(org_id) is None:
            if pending:
                self.repo.commit()
            return

        # Idempotent demo pubs — create any missing seed IDs independently.
        missing_demo = any(
            self.repo.get_publication(pid) is None
            for pid in ("pub-amm-a320-71", "pub-cmm-cfm56", "pub-aipc-a320")
        )
        if missing_demo:
            now = _utcnow()
            amm_type = self.repo.get_type_by_code("AMM")
            cmm_type = self.repo.get_type_by_code("CMM")
            aipc_type = self.repo.get_type_by_code("AIPC")
            if not (amm_type and cmm_type and aipc_type):
                self.repo.flush()
                amm_type = self.repo.get_type_by_code("AMM")
                cmm_type = self.repo.get_type_by_code("CMM")
                aipc_type = self.repo.get_type_by_code("AIPC")
            if amm_type and cmm_type and aipc_type:
                seeds = [
                    (
                        "pub-amm-a320-71",
                        amm_type,
                        "A320 AMM — Power Plant",
                        "AMM-A320-71",
                        "mfr-airbus",
                        "model-a320",
                        "ata-71-00",
                        "Rev 01",
                        "https://example.invalid/licensed/amm-a320-71",
                    ),
                    (
                        "pub-cmm-cfm56",
                        cmm_type,
                        "CFM56-5B Component Maintenance Manual",
                        "CMM-CFM56-5B",
                        "mfr-airbus",
                        "model-a320",
                        "ata-72-00",
                        "Rev 12",
                        "s3://org-east-pubs/cmm/cfm56-5b/rev12",
                    ),
                    (
                        "pub-aipc-a320",
                        aipc_type,
                        "A320 Aircraft Illustrated Parts Catalog",
                        "AIPC-A320",
                        "mfr-airbus",
                        "model-a320",
                        "ata-71-00",
                        "Rev 05",
                        "https://example.invalid/licensed/aipc-a320",
                    ),
                ]
                for pub_id, ptype, title, number, mfr, model, ata, rev_no, uri in seeds:
                    if self.repo.get_publication(pub_id) is not None:
                        continue
                    kind = "object_storage" if uri.startswith("s3://") else "external_url"
                    object_key = uri.replace("s3://", "") if kind == "object_storage" else ""
                    pub = Publication(
                        id=pub_id,
                        organization_id=org_id,
                        publication_type_id=ptype.id,
                        publication_code=ptype.code,
                        title=title,
                        description=f"Seed {ptype.code} for technical library demos (locator only).",
                        manufacturer_id=mfr,
                        aircraft_model_id=model,
                        aircraft_variant="ceo",
                        ata_chapter_id=ata,
                        publication_number=number,
                        authority="OEM",
                        status="active",
                        access_classification="licensed",
                        created_at=now,
                        updated_at=now,
                    )
                    self.repo.add_publication(pub)
                    self.repo.flush()
                    rev = PublicationRevision(
                        id=f"{pub_id}-rev",
                        organization_id=org_id,
                        publication_id=pub.id,
                        revision_number=rev_no,
                        revision_date=now,
                        effective_date=now,
                        status="current",
                        storage_kind=kind,
                        storage_uri=uri if kind == "external_url" else f"s3://{object_key}",
                        storage_object_key=object_key,
                        storage_content_type="application/pdf",
                        storage_notes="Demo locator — no OEM binary stored in Mercury.",
                        change_summary="Initial seeded revision",
                        created_at=now,
                        updated_at=now,
                    )
                    self.repo.add_revision(rev)
                    self.repo.flush()
                    pub.current_revision_id = rev.id
                    if ata and self.repo.get_ata_link(pub.id, ata) is None:
                        self.repo.add_ata_link(
                            PublicationAtaLink(
                                organization_id=org_id,
                                publication_id=pub.id,
                                ata_chapter_id=ata,
                                created_at=now,
                            )
                        )
                catalog = self.components.get_catalog_by_part_number("CFM56-5B4")
                if catalog and self.repo.get_catalog_link("pub-cmm-cfm56", catalog.id) is None:
                    self.repo.add_catalog_link(
                        PublicationCatalogLink(
                            organization_id=org_id,
                            publication_id="pub-cmm-cfm56",
                            catalog_item_id=catalog.id,
                            created_at=now,
                        )
                    )
                pending = True
        if pending:
            self.repo.commit()

    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def resolve_org_id(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        requested_org_id: str | None,
    ) -> str:
        org_id = (requested_org_id or session_org_id).strip()
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=org_id)
        return org_id

    def assert_org_access(self, *, username: str, session_role: str, organization_id: str) -> None:
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=organization_id)

    def _get_org_publication(
        self,
        publication_id: str,
        *,
        username: str,
        session_role: str,
        for_update: bool = False,
        with_revisions: bool = False,
    ) -> Publication:
        row = self.repo.get_publication(
            publication_id, for_update=for_update, with_revisions=with_revisions
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Publication not found")
        self.assert_org_access(
            username=username, session_role=session_role, organization_id=row.organization_id
        )
        return row

    @staticmethod
    def type_out(row: PublicationType) -> PublicationTypeOut:
        return PublicationTypeOut(
            id=row.id,
            code=row.code,
            name=row.name,
            category=row.category,
            description=row.description or "",
            status=row.status,
        )

    def publication_out(self, row: Publication) -> PublicationOut:
        current_rev = None
        if row.current_revision_id:
            rev = self.repo.get_revision(row.current_revision_id)
            current_rev = rev.revision_number if rev else None
        return PublicationOut(
            id=row.id,
            organization_id=row.organization_id,
            publication_type_id=row.publication_type_id,
            publication_code=row.publication_code,
            title=row.title,
            description=row.description or "",
            manufacturer_id=row.manufacturer_id,
            aircraft_model_id=row.aircraft_model_id,
            aircraft_variant=row.aircraft_variant or "",
            ata_chapter_id=row.ata_chapter_id,
            publication_number=row.publication_number,
            authority=row.authority or "",
            status=row.status,
            access_classification=row.access_classification,
            supersedes_publication_id=row.supersedes_publication_id,
            current_revision_id=row.current_revision_id,
            current_revision_number=current_rev,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def revision_out(row: PublicationRevision) -> RevisionOut:
        return RevisionOut(
            id=row.id,
            organization_id=row.organization_id,
            publication_id=row.publication_id,
            revision_number=row.revision_number,
            revision_date=row.revision_date,
            effective_date=row.effective_date,
            status=row.status,
            supersedes_revision_id=row.supersedes_revision_id,
            storage_kind=row.storage_kind,
            storage_uri=row.storage_uri or "",
            storage_object_key=row.storage_object_key or "",
            storage_content_type=row.storage_content_type or "",
            storage_notes=row.storage_notes or "",
            change_summary=row.change_summary or "",
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_types(self, *, category: str | None = None) -> list[PublicationTypeOut]:
        return [self.type_out(r) for r in self.repo.list_types(category=category)]

    def create_publication(
        self,
        payload: PublicationCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> PublicationOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        ptype = self.repo.get_type_by_code(payload.publication_type_code.strip().upper())
        if ptype is None or ptype.status != "active":
            raise HTTPException(status_code=404, detail="Publication type not found")
        access = (payload.access_classification or "internal").strip().lower()
        if access not in ACCESS_CLASSIFICATIONS:
            raise HTTPException(status_code=400, detail="Invalid access_classification")
        if payload.manufacturer_id and self.fleet.get_manufacturer(payload.manufacturer_id) is None:
            raise HTTPException(status_code=404, detail="Manufacturer not found")
        if payload.aircraft_model_id and self.fleet.get_model(payload.aircraft_model_id) is None:
            raise HTTPException(status_code=404, detail="Aircraft model not found")
        if payload.ata_chapter_id and self.components.get_ata_chapter(payload.ata_chapter_id) is None:
            raise HTTPException(status_code=404, detail="ATA chapter not found")
        if payload.supersedes_publication_id:
            prior = self.repo.get_publication(payload.supersedes_publication_id)
            if prior is None or prior.organization_id != org_id:
                raise HTTPException(status_code=404, detail="Superseded publication not found")

        number = payload.publication_number.strip()
        if self.repo.get_by_org_number(org_id, number):
            raise HTTPException(status_code=409, detail="Publication number already exists in organization")

        now = _utcnow()
        row = Publication(
            organization_id=org_id,
            publication_type_id=ptype.id,
            publication_code=ptype.code,
            title=payload.title.strip(),
            description=payload.description or "",
            manufacturer_id=payload.manufacturer_id,
            aircraft_model_id=payload.aircraft_model_id,
            aircraft_variant=(payload.aircraft_variant or "").strip(),
            ata_chapter_id=payload.ata_chapter_id,
            publication_number=number,
            authority=(payload.authority or "").strip(),
            status="active",
            access_classification=access,
            supersedes_publication_id=payload.supersedes_publication_id,
            created_at=now,
            updated_at=now,
        )
        self.repo.add_publication(row)
        self.repo.flush()

        if payload.ata_chapter_id:
            self.repo.add_ata_link(
                PublicationAtaLink(
                    organization_id=org_id,
                    publication_id=row.id,
                    ata_chapter_id=payload.ata_chapter_id,
                    created_at=now,
                )
            )

        if payload.revision_number:
            self._create_revision_row(
                row,
                RevisionCreate(
                    revision_number=payload.revision_number,
                    revision_date=payload.revision_date,
                    effective_date=payload.effective_date,
                    storage=payload.storage or StorageRefIn(),
                    change_summary=payload.change_summary,
                    activate=payload.activate_revision,
                ),
                actor=username,
            )

        self._commit_or_conflict(detail="Publication number conflict")
        row = self.repo.get_publication(row.id) or row
        return self.publication_out(row)

    def update_publication(
        self,
        publication_id: str,
        payload: PublicationUpdate,
        *,
        username: str,
        session_role: str,
    ) -> PublicationOut:
        row = self._get_org_publication(
            publication_id, username=username, session_role=session_role, for_update=True
        )
        if row.status == "archived":
            raise HTTPException(status_code=409, detail="Archived publication cannot be updated")
        if payload.title is not None:
            row.title = payload.title.strip()
        if payload.description is not None:
            row.description = payload.description
        if payload.manufacturer_id is not None:
            if payload.manufacturer_id and self.fleet.get_manufacturer(payload.manufacturer_id) is None:
                raise HTTPException(status_code=404, detail="Manufacturer not found")
            row.manufacturer_id = payload.manufacturer_id or None
        if payload.aircraft_model_id is not None:
            if payload.aircraft_model_id and self.fleet.get_model(payload.aircraft_model_id) is None:
                raise HTTPException(status_code=404, detail="Aircraft model not found")
            row.aircraft_model_id = payload.aircraft_model_id or None
        if payload.aircraft_variant is not None:
            row.aircraft_variant = payload.aircraft_variant.strip()
        if payload.ata_chapter_id is not None:
            if payload.ata_chapter_id and self.components.get_ata_chapter(payload.ata_chapter_id) is None:
                raise HTTPException(status_code=404, detail="ATA chapter not found")
            row.ata_chapter_id = payload.ata_chapter_id or None
        if payload.authority is not None:
            row.authority = payload.authority.strip()
        if payload.supersedes_publication_id is not None:
            if payload.supersedes_publication_id:
                prior = self.repo.get_publication(payload.supersedes_publication_id)
                if prior is None or prior.organization_id != row.organization_id:
                    raise HTTPException(status_code=404, detail="Superseded publication not found")
            row.supersedes_publication_id = payload.supersedes_publication_id or None
        row.updated_at = _utcnow()
        self._commit_or_conflict(detail="Unable to update publication")
        return self.publication_out(row)

    def set_access_classification(
        self,
        publication_id: str,
        payload: AccessClassificationUpdate,
        *,
        username: str,
        session_role: str,
    ) -> PublicationOut:
        row = self._get_org_publication(
            publication_id, username=username, session_role=session_role, for_update=True
        )
        row.access_classification = payload.access_classification
        row.updated_at = _utcnow()
        self._commit_or_conflict(detail="Unable to update access classification")
        return self.publication_out(row)

    def archive_publication(
        self,
        publication_id: str,
        *,
        username: str,
        session_role: str,
    ) -> PublicationOut:
        row = self._get_org_publication(
            publication_id, username=username, session_role=session_role, for_update=True
        )
        if row.status == "archived":
            raise HTTPException(status_code=409, detail="Publication already archived")
        row.status = "archived"
        row.updated_at = _utcnow()
        for rev in self.repo.list_revisions(row.id):
            if rev.status == "current":
                rev.status = "archived"
                rev.updated_at = _utcnow()
        self._commit_or_conflict(detail="Unable to archive publication")
        return self.publication_out(row)

    def _create_revision_row(
        self,
        publication: Publication,
        payload: RevisionCreate,
        *,
        actor: str,
    ) -> PublicationRevision:
        rev_no = payload.revision_number.strip()
        if self.repo.get_revision_by_number(publication.id, rev_no):
            raise HTTPException(status_code=409, detail="Revision number already exists for publication")
        if payload.supersedes_revision_id:
            prior = self.repo.get_revision(payload.supersedes_revision_id)
            if prior is None or prior.publication_id != publication.id:
                raise HTTPException(status_code=404, detail="Superseded revision not found")
        try:
            storage = normalize_storage(
                kind=payload.storage.kind,
                uri=payload.storage.uri,
                object_key=payload.storage.object_key,
                content_type=payload.storage.content_type,
                notes=payload.storage.notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        now = _utcnow()
        row = PublicationRevision(
            organization_id=publication.organization_id,
            publication_id=publication.id,
            revision_number=rev_no,
            revision_date=payload.revision_date,
            effective_date=payload.effective_date,
            status="draft",
            supersedes_revision_id=payload.supersedes_revision_id,
            storage_kind=storage.kind,
            storage_uri=storage.uri,
            storage_object_key=storage.object_key,
            storage_content_type=storage.content_type,
            storage_notes=storage.notes or f"registered_by={actor}",
            change_summary=payload.change_summary or "",
            created_at=now,
            updated_at=now,
        )
        self.repo.add_revision(row)
        self.repo.flush()
        if payload.activate:
            self._activate_revision_in_txn(publication, row)
        return row

    def create_revision(
        self,
        publication_id: str,
        payload: RevisionCreate,
        *,
        username: str,
        session_role: str,
    ) -> RevisionOut:
        pub = self._get_org_publication(
            publication_id, username=username, session_role=session_role, for_update=True
        )
        if pub.status == "archived":
            raise HTTPException(status_code=409, detail="Cannot revise archived publication")
        row = self._create_revision_row(pub, payload, actor=username)
        self._commit_or_conflict(detail="Revision number conflict")
        return self.revision_out(row)

    def _activate_revision_in_txn(self, publication: Publication, revision: PublicationRevision) -> None:
        now = _utcnow()
        for existing in self.repo.list_revisions(publication.id):
            if existing.id == revision.id:
                continue
            if existing.status == "current":
                existing.status = "superseded"
                existing.updated_at = now
                if revision.supersedes_revision_id is None:
                    revision.supersedes_revision_id = existing.id
        revision.status = "current"
        revision.updated_at = now
        if revision.effective_date is None:
            revision.effective_date = now
        publication.current_revision_id = revision.id
        publication.updated_at = now
        self.repo.flush()

    def activate_revision(
        self,
        publication_id: str,
        revision_id: str,
        *,
        username: str,
        session_role: str,
    ) -> RevisionOut:
        pub = self._get_org_publication(
            publication_id, username=username, session_role=session_role, for_update=True
        )
        if pub.status == "archived":
            raise HTTPException(status_code=409, detail="Cannot activate revision on archived publication")
        rev = self.repo.get_revision(revision_id, for_update=True)
        if rev is None or rev.publication_id != pub.id:
            raise HTTPException(status_code=404, detail="Revision not found")
        if rev.status == "current":
            return self.revision_out(rev)
        if rev.status == "archived":
            raise HTTPException(status_code=409, detail="Archived revision cannot be activated")
        self._activate_revision_in_txn(pub, rev)
        self._commit_or_conflict(detail="Unable to activate revision")
        return self.revision_out(rev)

    def list_revisions(
        self,
        publication_id: str,
        *,
        username: str,
        session_role: str,
    ) -> list[RevisionOut]:
        pub = self._get_org_publication(publication_id, username=username, session_role=session_role)
        return [self.revision_out(r) for r in self.repo.list_revisions(pub.id)]

    def get_publication(
        self,
        publication_id: str,
        *,
        username: str,
        session_role: str,
    ) -> PublicationOut:
        return self.publication_out(
            self._get_org_publication(publication_id, username=username, session_role=session_role)
        )

    def search(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
        publication_code: str | None = None,
        title: str | None = None,
        aircraft_model_id: str | None = None,
        manufacturer_id: str | None = None,
        ata_chapter_id: str | None = None,
        revision_number: str | None = None,
        q: str | None = None,
        revision_date_from: datetime | None = None,
        revision_date_to: datetime | None = None,
        effective_date_from: datetime | None = None,
        effective_date_to: datetime | None = None,
    ) -> list[PublicationOut]:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        rows = self.repo.list_publications(
            organization_id=org_id,
            publication_code=publication_code,
            title=title,
            aircraft_model_id=aircraft_model_id,
            manufacturer_id=manufacturer_id,
            ata_chapter_id=ata_chapter_id,
            revision_number=revision_number,
            q=q,
            revision_date_from=revision_date_from,
            revision_date_to=revision_date_to,
            effective_date_from=effective_date_from,
            effective_date_to=effective_date_to,
        )
        return [self.publication_out(r) for r in rows]

    def link_ata(
        self,
        publication_id: str,
        ata_chapter_id: str,
        *,
        username: str,
        session_role: str,
    ) -> PublicationOut:
        pub = self._get_org_publication(
            publication_id, username=username, session_role=session_role, for_update=True
        )
        if self.components.get_ata_chapter(ata_chapter_id) is None:
            raise HTTPException(status_code=404, detail="ATA chapter not found")
        if self.repo.get_ata_link(pub.id, ata_chapter_id) is None:
            self.repo.add_ata_link(
                PublicationAtaLink(
                    organization_id=pub.organization_id,
                    publication_id=pub.id,
                    ata_chapter_id=ata_chapter_id,
                    created_at=_utcnow(),
                )
            )
            if pub.ata_chapter_id is None:
                pub.ata_chapter_id = ata_chapter_id
            pub.updated_at = _utcnow()
            self._commit_or_conflict(detail="ATA link conflict")
        return self.publication_out(pub)

    def link_catalog(
        self,
        publication_id: str,
        catalog_item_id: str,
        *,
        username: str,
        session_role: str,
    ) -> PublicationOut:
        pub = self._get_org_publication(
            publication_id, username=username, session_role=session_role, for_update=True
        )
        if self.components.get_catalog_item(catalog_item_id) is None:
            raise HTTPException(status_code=404, detail="Catalog item not found")
        if self.repo.get_catalog_link(pub.id, catalog_item_id) is None:
            self.repo.add_catalog_link(
                PublicationCatalogLink(
                    organization_id=pub.organization_id,
                    publication_id=pub.id,
                    catalog_item_id=catalog_item_id,
                    created_at=_utcnow(),
                )
            )
            pub.updated_at = _utcnow()
            self._commit_or_conflict(detail="Catalog link conflict")
        return self.publication_out(pub)

    def library_browse(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
        manufacturer_id: str | None = None,
        family_id: str | None = None,
        aircraft_model_id: str | None = None,
        publication_code: str | None = None,
        ata_chapter_id: str | None = None,
    ) -> LibraryBrowseOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=organization_id,
        )
        path: list[str] = ["library"]
        nodes: list[LibraryNodeOut] = []

        if not manufacturer_id:
            path.append("manufacturers")
            for mid, count in self.repo.distinct_manufacturers(org_id):
                mfr = self.fleet.get_manufacturer(mid)
                nodes.append(
                    LibraryNodeOut(
                        id=mid,
                        label=mfr.name if mfr else mid,
                        node_type="manufacturer",
                        count=count,
                        meta={"manufacturer_id": mid},
                    )
                )
            return LibraryBrowseOut(path=path, nodes=nodes)

        path.append(manufacturer_id)
        # Manufacturer → Family (unless model already selected for backward compatibility).
        if not family_id and not aircraft_model_id:
            path.append("families")
            family_counts: dict[str, int] = {}
            for model_id, count in self.repo.distinct_models(org_id, manufacturer_id):
                model = self.fleet.get_model(model_id)
                fid = getattr(model, "family_id", None) if model else None
                key = fid or "_unassigned"
                family_counts[key] = family_counts.get(key, 0) + count
            for fid, count in family_counts.items():
                if fid == "_unassigned":
                    nodes.append(
                        LibraryNodeOut(
                            id="_unassigned",
                            label="Unassigned models",
                            node_type="aircraft_family",
                            count=count,
                            meta={"manufacturer_id": manufacturer_id, "family_id": None},
                        )
                    )
                else:
                    family = self.fleet.get_family(fid)
                    nodes.append(
                        LibraryNodeOut(
                            id=fid,
                            label=family.name if family else fid,
                            node_type="aircraft_family",
                            count=count,
                            meta={"manufacturer_id": manufacturer_id, "family_id": fid},
                        )
                    )
            return LibraryBrowseOut(path=path, nodes=nodes)

        if family_id:
            path.append(family_id)
        if not aircraft_model_id:
            path.append("models")
            for model_id, count in self.repo.distinct_models(org_id, manufacturer_id):
                model = self.fleet.get_model(model_id)
                model_family = getattr(model, "family_id", None) if model else None
                if family_id == "_unassigned":
                    if model_family:
                        continue
                elif family_id and model_family != family_id:
                    continue
                nodes.append(
                    LibraryNodeOut(
                        id=model_id,
                        label=model.name if model else model_id,
                        node_type="aircraft_model",
                        count=count,
                        meta={
                            "manufacturer_id": manufacturer_id,
                            "family_id": family_id,
                            "aircraft_model_id": model_id,
                        },
                    )
                )
            return LibraryBrowseOut(path=path, nodes=nodes)

        path.append(aircraft_model_id)
        if not publication_code:
            path.append("publication_types")
            for code, count in self.repo.distinct_types(
                org_id, manufacturer_id=manufacturer_id, aircraft_model_id=aircraft_model_id
            ):
                ptype = self.repo.get_type_by_code(code)
                nodes.append(
                    LibraryNodeOut(
                        id=code,
                        label=ptype.name if ptype else code,
                        node_type="publication_type",
                        count=count,
                        meta={
                            "manufacturer_id": manufacturer_id,
                            "aircraft_model_id": aircraft_model_id,
                            "publication_code": code,
                        },
                    )
                )
            return LibraryBrowseOut(path=path, nodes=nodes)

        path.append(publication_code.upper())
        if not ata_chapter_id:
            path.append("ata_chapters")
            for ata_id, count in self.repo.distinct_ata(
                org_id,
                manufacturer_id=manufacturer_id,
                aircraft_model_id=aircraft_model_id,
                publication_code=publication_code,
            ):
                ata = self.components.get_ata_chapter(ata_id)
                label = f"{ata.chapter_number}-{ata.subchapter} {ata.title}" if ata else ata_id
                nodes.append(
                    LibraryNodeOut(
                        id=ata_id,
                        label=label,
                        node_type="ata_chapter",
                        count=count,
                        meta={
                            "manufacturer_id": manufacturer_id,
                            "aircraft_model_id": aircraft_model_id,
                            "publication_code": publication_code.upper(),
                            "ata_chapter_id": ata_id,
                        },
                    )
                )
            # Also leaf publications without ATA
            pubs = self.repo.list_publications(
                organization_id=org_id,
                manufacturer_id=manufacturer_id,
                aircraft_model_id=aircraft_model_id,
                publication_code=publication_code,
            )
            for pub in pubs:
                if pub.ata_chapter_id:
                    continue
                nodes.append(
                    LibraryNodeOut(
                        id=pub.id,
                        label=pub.title,
                        node_type="publication",
                        count=1,
                        meta={
                            "publication_id": pub.id,
                            "publication_number": pub.publication_number,
                            "current_revision_id": pub.current_revision_id,
                        },
                    )
                )
            return LibraryBrowseOut(path=path, nodes=nodes)

        path.append(ata_chapter_id)
        path.append("publications")
        pubs = self.repo.list_publications(
            organization_id=org_id,
            manufacturer_id=manufacturer_id,
            aircraft_model_id=aircraft_model_id,
            publication_code=publication_code,
            ata_chapter_id=ata_chapter_id,
        )
        for pub in pubs:
            nodes.append(
                LibraryNodeOut(
                    id=pub.id,
                    label=pub.title,
                    node_type="publication",
                    count=1,
                    meta={
                        "publication_id": pub.id,
                        "publication_number": pub.publication_number,
                        "current_revision_id": pub.current_revision_id,
                        "current_revision_number": (
                            self.repo.get_revision(pub.current_revision_id).revision_number
                            if pub.current_revision_id and self.repo.get_revision(pub.current_revision_id)
                            else None
                        ),
                    },
                )
            )
        return LibraryBrowseOut(path=path, nodes=nodes)

    def publications_for_ata(
        self,
        ata_chapter_id: str,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
    ) -> list[PublicationOut]:
        return self.search(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            organization_id=organization_id,
            ata_chapter_id=ata_chapter_id,
        )

    def publications_for_model(
        self,
        aircraft_model_id: str,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        organization_id: str | None = None,
    ) -> list[PublicationOut]:
        return self.search(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            organization_id=organization_id,
            aircraft_model_id=aircraft_model_id,
        )

    def publications_for_component(
        self,
        component_id: str,
        *,
        username: str,
        session_role: str,
    ) -> ComponentPublicationOut:
        component = self.components.get_component(component_id, with_catalog=True)
        if component is None or component.status != "active":
            raise HTTPException(status_code=404, detail="Component not found")
        self.assert_org_access(
            username=username, session_role=session_role, organization_id=component.organization_id
        )
        catalog = component.catalog_item
        ata_id = catalog.ata_chapter_id if catalog else None
        pubs_by_id: dict[str, Publication] = {}
        if catalog:
            for p in self.repo.list_by_catalog_item(component.organization_id, catalog.id):
                pubs_by_id[p.id] = p
        if ata_id:
            for p in self.repo.list_publications(
                organization_id=component.organization_id, ata_chapter_id=ata_id
            ):
                pubs_by_id[p.id] = p
        return ComponentPublicationOut(
            component_id=component.id,
            serial_number=component.serial_number,
            catalog_item_id=component.catalog_item_id,
            part_number=catalog.part_number if catalog else "",
            ata_chapter_id=ata_id,
            publications=[self.publication_out(p) for p in pubs_by_id.values()],
        )

    def publications_for_aircraft(
        self,
        aircraft_id: str,
        *,
        username: str,
        session_role: str,
    ) -> list[PublicationOut]:
        aircraft = self.fleet.get_aircraft(aircraft_id)
        if aircraft is None or aircraft.status != "active":
            raise HTTPException(status_code=404, detail="Aircraft not found")
        self.assert_org_access(
            username=username, session_role=session_role, organization_id=aircraft.organization_id
        )
        return self.search(
            username=username,
            session_role=session_role,
            session_org_id=aircraft.organization_id,
            organization_id=aircraft.organization_id,
            aircraft_model_id=aircraft.model_id,
        )
