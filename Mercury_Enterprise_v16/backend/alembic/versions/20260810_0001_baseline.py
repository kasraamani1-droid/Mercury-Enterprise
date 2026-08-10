"""Baseline schema matching current SQLAlchemy models (incidents, timeline, evidence, audit)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260810_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("organization_id", sa.String(length=80), nullable=True),
        sa.Column("site_id", sa.String(length=80), nullable=True),
    )
    op.create_index("ix_incidents_title", "incidents", ["title"])
    op.create_index("ix_incidents_organization_id", "incidents", ["organization_id"])
    op.create_index("ix_incidents_site_id", "incidents", ["site_id"])

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("incident_id", sa.String(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )
    op.create_index("ix_timeline_events_incident_id", "timeline_events", ["incident_id"])
    op.create_index("ix_timeline_events_occurred_at", "timeline_events", ["occurred_at"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("incident_id", sa.String(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column("evidence_type", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("provenance", sa.String(length=40), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("organization_id", sa.String(length=80), nullable=True),
        sa.Column("site_id", sa.String(length=80), nullable=True),
    )
    op.create_index("ix_evidence_incident_id", "evidence", ["incident_id"])
    op.create_index("ix_evidence_organization_id", "evidence", ["organization_id"])
    op.create_index("ix_evidence_site_id", "evidence", ["site_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("actor_role", sa.String(length=40), nullable=False),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("site_id", sa.String(length=80), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=True),
        sa.Column("target_id", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("origin", sa.String(length=40), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_site_id", "audit_events", ["site_id"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("evidence")
    op.drop_table("timeline_events")
    op.drop_table("incidents")
