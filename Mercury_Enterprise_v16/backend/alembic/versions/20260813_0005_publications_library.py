"""Publications & technical library tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260813_0005"
down_revision = "20260812_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "publication_types",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_publication_types_code", "publication_types", ["code"], unique=True)
    op.create_index("ix_publication_types_category", "publication_types", ["category"])
    op.create_index("ix_publication_types_status", "publication_types", ["status"])

    op.create_table(
        "publications",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("publication_type_id", sa.String(length=80), sa.ForeignKey("publication_types.id"), nullable=False),
        sa.Column("publication_code", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("manufacturer_id", sa.String(length=80), sa.ForeignKey("manufacturers.id"), nullable=True),
        sa.Column("aircraft_model_id", sa.String(length=80), sa.ForeignKey("aircraft_models.id"), nullable=True),
        sa.Column("aircraft_variant", sa.String(length=120), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), sa.ForeignKey("ata_chapters.id"), nullable=True),
        sa.Column("publication_number", sa.String(length=120), nullable=False),
        sa.Column("authority", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("access_classification", sa.String(length=40), nullable=False),
        sa.Column("supersedes_publication_id", sa.String(length=80), sa.ForeignKey("publications.id"), nullable=True),
        sa.Column("current_revision_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "publication_number", name="uq_publication_org_number"),
    )
    op.create_index("ix_publications_organization_id", "publications", ["organization_id"])
    op.create_index("ix_publications_publication_type_id", "publications", ["publication_type_id"])
    op.create_index("ix_publications_publication_code", "publications", ["publication_code"])
    op.create_index("ix_publications_title", "publications", ["title"])
    op.create_index("ix_publications_manufacturer_id", "publications", ["manufacturer_id"])
    op.create_index("ix_publications_aircraft_model_id", "publications", ["aircraft_model_id"])
    op.create_index("ix_publications_ata_chapter_id", "publications", ["ata_chapter_id"])
    op.create_index("ix_publications_publication_number", "publications", ["publication_number"])
    op.create_index("ix_publications_status", "publications", ["status"])
    op.create_index("ix_publications_access_classification", "publications", ["access_classification"])
    op.create_index("ix_publications_supersedes_publication_id", "publications", ["supersedes_publication_id"])
    op.create_index("ix_publications_current_revision_id", "publications", ["current_revision_id"])
    op.create_index("ix_publications_org_type", "publications", ["organization_id", "publication_type_id"])
    op.create_index("ix_publications_org_code", "publications", ["organization_id", "publication_code"])
    op.create_index("ix_publications_org_model", "publications", ["organization_id", "aircraft_model_id"])
    op.create_index("ix_publications_org_mfr", "publications", ["organization_id", "manufacturer_id"])
    op.create_index("ix_publications_org_ata", "publications", ["organization_id", "ata_chapter_id"])
    op.create_index("ix_publications_org_status", "publications", ["organization_id", "status"])
    op.create_index("ix_publications_org_title", "publications", ["organization_id", "title"])

    op.create_table(
        "publication_revisions",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("publication_id", sa.String(length=80), sa.ForeignKey("publications.id"), nullable=False),
        sa.Column("revision_number", sa.String(length=80), nullable=False),
        sa.Column("revision_date", sa.DateTime(), nullable=True),
        sa.Column("effective_date", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("supersedes_revision_id", sa.String(length=80), sa.ForeignKey("publication_revisions.id"), nullable=True),
        sa.Column("storage_kind", sa.String(length=40), nullable=False),
        sa.Column("storage_uri", sa.String(length=1000), nullable=False),
        sa.Column("storage_object_key", sa.String(length=500), nullable=False),
        sa.Column("storage_content_type", sa.String(length=120), nullable=False),
        sa.Column("storage_notes", sa.Text(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("publication_id", "revision_number", name="uq_publication_revision_number"),
    )
    op.create_index("ix_publication_revisions_organization_id", "publication_revisions", ["organization_id"])
    op.create_index("ix_publication_revisions_publication_id", "publication_revisions", ["publication_id"])
    op.create_index("ix_publication_revisions_status", "publication_revisions", ["status"])
    op.create_index("ix_publication_revisions_supersedes_revision_id", "publication_revisions", ["supersedes_revision_id"])
    op.create_index("ix_pub_revisions_org_pub", "publication_revisions", ["organization_id", "publication_id"])
    op.create_index("ix_pub_revisions_org_status", "publication_revisions", ["organization_id", "status"])
    op.create_index("ix_pub_revisions_effective", "publication_revisions", ["effective_date"])
    op.create_index("ix_pub_revisions_revision_date", "publication_revisions", ["revision_date"])

    op.create_foreign_key(
        "fk_publications_current_revision",
        "publications",
        "publication_revisions",
        ["current_revision_id"],
        ["id"],
    )

    op.create_table(
        "publication_ata_links",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("publication_id", sa.String(length=80), sa.ForeignKey("publications.id"), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), sa.ForeignKey("ata_chapters.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("publication_id", "ata_chapter_id", name="uq_publication_ata"),
    )
    op.create_index("ix_publication_ata_links_organization_id", "publication_ata_links", ["organization_id"])
    op.create_index("ix_publication_ata_links_publication_id", "publication_ata_links", ["publication_id"])
    op.create_index("ix_publication_ata_links_ata_chapter_id", "publication_ata_links", ["ata_chapter_id"])
    op.create_index("ix_pub_ata_org_ata", "publication_ata_links", ["organization_id", "ata_chapter_id"])

    op.create_table(
        "publication_catalog_links",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("publication_id", sa.String(length=80), sa.ForeignKey("publications.id"), nullable=False),
        sa.Column("catalog_item_id", sa.String(length=80), sa.ForeignKey("component_catalog.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("publication_id", "catalog_item_id", name="uq_publication_catalog"),
    )
    op.create_index("ix_publication_catalog_links_organization_id", "publication_catalog_links", ["organization_id"])
    op.create_index("ix_publication_catalog_links_publication_id", "publication_catalog_links", ["publication_id"])
    op.create_index("ix_publication_catalog_links_catalog_item_id", "publication_catalog_links", ["catalog_item_id"])
    op.create_index("ix_pub_catalog_org_item", "publication_catalog_links", ["organization_id", "catalog_item_id"])


def downgrade() -> None:
    op.drop_table("publication_catalog_links")
    op.drop_table("publication_ata_links")
    op.drop_constraint("fk_publications_current_revision", "publications", type_="foreignkey")
    op.drop_table("publication_revisions")
    op.drop_table("publications")
    op.drop_table("publication_types")
