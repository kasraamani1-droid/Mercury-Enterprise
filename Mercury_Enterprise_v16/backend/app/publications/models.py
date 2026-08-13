from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ..models import uid


class PublicationType(Base):
    """Shared catalog of publication codes (AMM, AIPC, SB, …)."""

    __tablename__ = "publication_types"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(40), index=True)  # maintenance_manual | other
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    publications: Mapped[list["Publication"]] = relationship(back_populates="publication_type")


class Publication(Base):
    """Organization-scoped technical publication (metadata + current revision pointer)."""

    __tablename__ = "publications"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    publication_type_id: Mapped[str] = mapped_column(ForeignKey("publication_types.id"), index=True)
    publication_code: Mapped[str] = mapped_column(String(40), index=True)  # denormalized type code
    title: Mapped[str] = mapped_column(String(300), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    manufacturer_id: Mapped[str | None] = mapped_column(ForeignKey("manufacturers.id"), nullable=True, index=True)
    aircraft_model_id: Mapped[str | None] = mapped_column(ForeignKey("aircraft_models.id"), nullable=True, index=True)
    aircraft_variant: Mapped[str] = mapped_column(String(120), default="")
    # Primary ATA association (optional); additional chapters via publication_ata_links.
    ata_chapter_id: Mapped[str | None] = mapped_column(ForeignKey("ata_chapters.id"), nullable=True, index=True)
    publication_number: Mapped[str] = mapped_column(String(120), index=True)
    authority: Mapped[str] = mapped_column(String(120), default="")  # FAA / EASA / TC / OEM / …
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)  # active | archived
    access_classification: Mapped[str] = mapped_column(String(40), default="internal", index=True)
    supersedes_publication_id: Mapped[str | None] = mapped_column(
        ForeignKey("publications.id"), nullable=True, index=True
    )
    current_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("publication_revisions.id", use_alter=True, name="fk_publications_current_revision"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    publication_type: Mapped[PublicationType] = relationship(back_populates="publications")
    revisions: Mapped[list["PublicationRevision"]] = relationship(
        back_populates="publication",
        foreign_keys="PublicationRevision.publication_id",
        cascade="all, delete-orphan",
        order_by="PublicationRevision.created_at.desc()",
    )
    ata_links: Mapped[list["PublicationAtaLink"]] = relationship(
        back_populates="publication", cascade="all, delete-orphan"
    )
    catalog_links: Mapped[list["PublicationCatalogLink"]] = relationship(
        back_populates="publication", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "publication_number", name="uq_publication_org_number"),
        Index("ix_publications_org_type", "organization_id", "publication_type_id"),
        Index("ix_publications_org_code", "organization_id", "publication_code"),
        Index("ix_publications_org_model", "organization_id", "aircraft_model_id"),
        Index("ix_publications_org_mfr", "organization_id", "manufacturer_id"),
        Index("ix_publications_org_ata", "organization_id", "ata_chapter_id"),
        Index("ix_publications_org_status", "organization_id", "status"),
        Index("ix_publications_org_title", "organization_id", "title"),
    )


class PublicationRevision(Base):
    """Immutable revision row — never overwrite; activate/supersede via status."""

    __tablename__ = "publication_revisions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    publication_id: Mapped[str] = mapped_column(ForeignKey("publications.id"), index=True)
    revision_number: Mapped[str] = mapped_column(String(80))
    revision_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)  # draft|current|superseded|archived
    supersedes_revision_id: Mapped[str | None] = mapped_column(
        ForeignKey("publication_revisions.id"), nullable=True, index=True
    )
    # License-safe storage locator only (no OEM binary payload).
    storage_kind: Mapped[str] = mapped_column(String(40), default="none")
    storage_uri: Mapped[str] = mapped_column(String(1000), default="")
    storage_object_key: Mapped[str] = mapped_column(String(500), default="")
    storage_content_type: Mapped[str] = mapped_column(String(120), default="")
    storage_notes: Mapped[str] = mapped_column(Text, default="")
    change_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    publication: Mapped[Publication] = relationship(
        back_populates="revisions",
        foreign_keys=[publication_id],
    )

    __table_args__ = (
        UniqueConstraint("publication_id", "revision_number", name="uq_publication_revision_number"),
        Index("ix_pub_revisions_org_pub", "organization_id", "publication_id"),
        Index("ix_pub_revisions_org_status", "organization_id", "status"),
        Index("ix_pub_revisions_effective", "effective_date"),
        Index("ix_pub_revisions_revision_date", "revision_date"),
    )


class PublicationAtaLink(Base):
    """Additional ATA chapter associations for a publication."""

    __tablename__ = "publication_ata_links"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    publication_id: Mapped[str] = mapped_column(ForeignKey("publications.id"), index=True)
    ata_chapter_id: Mapped[str] = mapped_column(ForeignKey("ata_chapters.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    publication: Mapped[Publication] = relationship(back_populates="ata_links")

    __table_args__ = (
        UniqueConstraint("publication_id", "ata_chapter_id", name="uq_publication_ata"),
        Index("ix_pub_ata_org_ata", "organization_id", "ata_chapter_id"),
    )


class PublicationCatalogLink(Base):
    """Link publication to a shared component catalog item (e.g. CMM for a part)."""

    __tablename__ = "publication_catalog_links"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(String(80), index=True)
    publication_id: Mapped[str] = mapped_column(ForeignKey("publications.id"), index=True)
    catalog_item_id: Mapped[str] = mapped_column(ForeignKey("component_catalog.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    publication: Mapped[Publication] = relationship(back_populates="catalog_links")

    __table_args__ = (
        UniqueConstraint("publication_id", "catalog_item_id", name="uq_publication_catalog"),
        Index("ix_pub_catalog_org_item", "organization_id", "catalog_item_id"),
    )
