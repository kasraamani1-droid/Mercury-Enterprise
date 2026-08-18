from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from ..shared import clamp_page
from .models import (
    Publication,
    PublicationAtaLink,
    PublicationCatalogLink,
    PublicationRevision,
    PublicationType,
)


class PublicationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- types ---
    def list_types(self, *, category: str | None = None, active_only: bool = True) -> list[PublicationType]:
        stmt = select(PublicationType).order_by(PublicationType.category, PublicationType.code)
        if category:
            stmt = stmt.where(PublicationType.category == category)
        if active_only:
            stmt = stmt.where(PublicationType.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_type(self, type_id: str) -> PublicationType | None:
        return self.db.get(PublicationType, type_id)

    def get_type_by_code(self, code: str) -> PublicationType | None:
        return self.db.scalar(select(PublicationType).where(PublicationType.code == code.upper()))

    def add_type(self, row: PublicationType) -> PublicationType:
        self.db.add(row)
        return row

    # --- publications ---
    def _pub_stmt(self, *, with_revisions: bool = False) -> Select[tuple[Publication]]:
        stmt = select(Publication)
        if with_revisions:
            stmt = stmt.options(selectinload(Publication.revisions))
        return stmt

    def list_publications(
        self,
        *,
        organization_id: str | None = None,
        publication_code: str | None = None,
        title: str | None = None,
        aircraft_model_id: str | None = None,
        manufacturer_id: str | None = None,
        ata_chapter_id: str | None = None,
        revision_number: str | None = None,
        status: str | None = None,
        q: str | None = None,
        revision_date_from: datetime | None = None,
        revision_date_to: datetime | None = None,
        effective_date_from: datetime | None = None,
        effective_date_to: datetime | None = None,
        active_only: bool = True,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Publication]:
        lim, off = clamp_page(limit, offset)
        stmt = self._pub_stmt().order_by(Publication.title)
        if organization_id:
            stmt = stmt.where(Publication.organization_id == organization_id)
        if publication_code:
            stmt = stmt.where(Publication.publication_code == publication_code.upper())
        if title:
            stmt = stmt.where(Publication.title.ilike(f"%{title.strip()}%"))
        if aircraft_model_id:
            stmt = stmt.where(Publication.aircraft_model_id == aircraft_model_id)
        if manufacturer_id:
            stmt = stmt.where(Publication.manufacturer_id == manufacturer_id)
        if ata_chapter_id:
            ata_ids = select(PublicationAtaLink.publication_id).where(
                PublicationAtaLink.ata_chapter_id == ata_chapter_id
            )
            stmt = stmt.where(
                or_(Publication.ata_chapter_id == ata_chapter_id, Publication.id.in_(ata_ids))
            )
        if status:
            stmt = stmt.where(Publication.status == status)
        elif active_only:
            stmt = stmt.where(Publication.status == "active")
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Publication.title.ilike(like),
                    Publication.publication_number.ilike(like),
                    Publication.publication_code.ilike(like),
                    Publication.description.ilike(like),
                )
            )
        if revision_number or revision_date_from or revision_date_to or effective_date_from or effective_date_to:
            rev = select(PublicationRevision.publication_id)
            if organization_id:
                rev = rev.where(PublicationRevision.organization_id == organization_id)
            if revision_number:
                rev = rev.where(PublicationRevision.revision_number == revision_number.strip())
            if revision_date_from:
                rev = rev.where(PublicationRevision.revision_date >= revision_date_from)
            if revision_date_to:
                rev = rev.where(PublicationRevision.revision_date <= revision_date_to)
            if effective_date_from:
                rev = rev.where(PublicationRevision.effective_date >= effective_date_from)
            if effective_date_to:
                rev = rev.where(PublicationRevision.effective_date <= effective_date_to)
            stmt = stmt.where(Publication.id.in_(rev))
        return list(self.db.scalars(stmt.limit(lim).offset(off)).unique().all())

    def get_publication(
        self,
        publication_id: str,
        *,
        for_update: bool = False,
        with_revisions: bool = False,
    ) -> Publication | None:
        stmt = self._pub_stmt(with_revisions=with_revisions).where(Publication.id == publication_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).unique().first()

    def get_by_org_number(self, organization_id: str, publication_number: str) -> Publication | None:
        return self.db.scalar(
            select(Publication).where(
                Publication.organization_id == organization_id,
                Publication.publication_number == publication_number.strip(),
            )
        )

    def add_publication(self, row: Publication) -> Publication:
        self.db.add(row)
        return row

    # --- revisions ---
    def list_revisions(self, publication_id: str) -> list[PublicationRevision]:
        stmt = (
            select(PublicationRevision)
            .where(PublicationRevision.publication_id == publication_id)
            .order_by(PublicationRevision.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_revision(self, revision_id: str, *, for_update: bool = False) -> PublicationRevision | None:
        stmt = select(PublicationRevision).where(PublicationRevision.id == revision_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_revision_by_number(self, publication_id: str, revision_number: str) -> PublicationRevision | None:
        return self.db.scalar(
            select(PublicationRevision).where(
                PublicationRevision.publication_id == publication_id,
                PublicationRevision.revision_number == revision_number.strip(),
            )
        )

    def add_revision(self, row: PublicationRevision) -> PublicationRevision:
        self.db.add(row)
        return row

    def current_revision(self, publication: Publication) -> PublicationRevision | None:
        if publication.current_revision_id:
            return self.get_revision(publication.current_revision_id)
        return self.db.scalar(
            select(PublicationRevision).where(
                PublicationRevision.publication_id == publication.id,
                PublicationRevision.status == "current",
            )
        )

    # --- links ---
    def add_ata_link(self, row: PublicationAtaLink) -> PublicationAtaLink:
        self.db.add(row)
        return row

    def list_ata_links(self, publication_id: str) -> list[PublicationAtaLink]:
        return list(
            self.db.scalars(
                select(PublicationAtaLink).where(PublicationAtaLink.publication_id == publication_id)
            ).all()
        )

    def get_ata_link(self, publication_id: str, ata_chapter_id: str) -> PublicationAtaLink | None:
        return self.db.scalar(
            select(PublicationAtaLink).where(
                PublicationAtaLink.publication_id == publication_id,
                PublicationAtaLink.ata_chapter_id == ata_chapter_id,
            )
        )

    def add_catalog_link(self, row: PublicationCatalogLink) -> PublicationCatalogLink:
        self.db.add(row)
        return row

    def list_catalog_links(self, publication_id: str) -> list[PublicationCatalogLink]:
        return list(
            self.db.scalars(
                select(PublicationCatalogLink).where(PublicationCatalogLink.publication_id == publication_id)
            ).all()
        )

    def get_catalog_link(self, publication_id: str, catalog_item_id: str) -> PublicationCatalogLink | None:
        return self.db.scalar(
            select(PublicationCatalogLink).where(
                PublicationCatalogLink.publication_id == publication_id,
                PublicationCatalogLink.catalog_item_id == catalog_item_id,
            )
        )

    def list_by_catalog_item(self, organization_id: str, catalog_item_id: str) -> list[Publication]:
        ids = select(PublicationCatalogLink.publication_id).where(
            PublicationCatalogLink.organization_id == organization_id,
            PublicationCatalogLink.catalog_item_id == catalog_item_id,
        )
        stmt = (
            select(Publication)
            .where(Publication.organization_id == organization_id, Publication.id.in_(ids))
            .where(Publication.status == "active")
            .order_by(Publication.publication_code, Publication.title)
        )
        return list(self.db.scalars(stmt).all())

    # --- library navigation aggregates ---
    def distinct_manufacturers(self, organization_id: str) -> list[tuple[str, int]]:
        stmt = (
            select(Publication.manufacturer_id, func.count())
            .where(
                Publication.organization_id == organization_id,
                Publication.status == "active",
                Publication.manufacturer_id.is_not(None),
            )
            .group_by(Publication.manufacturer_id)
        )
        return [(str(m), int(c)) for m, c in self.db.execute(stmt).all() if m]

    def distinct_models(self, organization_id: str, manufacturer_id: str | None = None) -> list[tuple[str, int]]:
        stmt = (
            select(Publication.aircraft_model_id, func.count())
            .where(
                Publication.organization_id == organization_id,
                Publication.status == "active",
                Publication.aircraft_model_id.is_not(None),
            )
            .group_by(Publication.aircraft_model_id)
        )
        if manufacturer_id:
            stmt = stmt.where(Publication.manufacturer_id == manufacturer_id)
        return [(str(m), int(c)) for m, c in self.db.execute(stmt).all() if m]

    def distinct_types(
        self,
        organization_id: str,
        *,
        manufacturer_id: str | None = None,
        aircraft_model_id: str | None = None,
    ) -> list[tuple[str, int]]:
        stmt = (
            select(Publication.publication_code, func.count())
            .where(Publication.organization_id == organization_id, Publication.status == "active")
            .group_by(Publication.publication_code)
            .order_by(Publication.publication_code)
        )
        if manufacturer_id:
            stmt = stmt.where(Publication.manufacturer_id == manufacturer_id)
        if aircraft_model_id:
            stmt = stmt.where(Publication.aircraft_model_id == aircraft_model_id)
        return [(str(c), int(n)) for c, n in self.db.execute(stmt).all()]

    def distinct_ata(
        self,
        organization_id: str,
        *,
        manufacturer_id: str | None = None,
        aircraft_model_id: str | None = None,
        publication_code: str | None = None,
    ) -> list[tuple[str, int]]:
        stmt = (
            select(Publication.ata_chapter_id, func.count())
            .where(
                Publication.organization_id == organization_id,
                Publication.status == "active",
                Publication.ata_chapter_id.is_not(None),
            )
            .group_by(Publication.ata_chapter_id)
        )
        if manufacturer_id:
            stmt = stmt.where(Publication.manufacturer_id == manufacturer_id)
        if aircraft_model_id:
            stmt = stmt.where(Publication.aircraft_model_id == aircraft_model_id)
        if publication_code:
            stmt = stmt.where(Publication.publication_code == publication_code.upper())
        return [(str(a), int(c)) for a, c in self.db.execute(stmt).all() if a]

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    def flush(self) -> None:
        self.db.flush()
