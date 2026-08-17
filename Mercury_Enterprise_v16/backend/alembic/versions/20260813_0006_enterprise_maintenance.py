"""Enterprise maintenance: families, alternates, personnel, certification, logbook, AI stubs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260813_0006"
down_revision = "20260813_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "aircraft_families",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("manufacturer_id", sa.String(length=80), sa.ForeignKey("manufacturers.id"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("manufacturer_id", "code", name="uq_aircraft_family_mfr_code"),
    )
    op.create_index("ix_aircraft_families_manufacturer_id", "aircraft_families", ["manufacturer_id"])
    op.create_index("ix_aircraft_families_name", "aircraft_families", ["name"])
    op.create_index("ix_aircraft_families_code", "aircraft_families", ["code"])
    op.create_index("ix_aircraft_families_status", "aircraft_families", ["status"])

    op.add_column("aircraft_models", sa.Column("family_id", sa.String(length=80), nullable=True))
    with op.batch_alter_table("aircraft_models") as batch_op:
        batch_op.create_foreign_key(
            "fk_aircraft_models_family_id",
            "aircraft_families",
            ["family_id"],
            ["id"],
        )
    op.create_index("ix_aircraft_models_family_id", "aircraft_models", ["family_id"])

    op.create_table(
        "alternate_parts",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("catalog_item_id", sa.String(length=80), sa.ForeignKey("component_catalog.id"), nullable=False),
        sa.Column("alternate_catalog_item_id", sa.String(length=80), sa.ForeignKey("component_catalog.id"), nullable=False),
        sa.Column("interchangeability", sa.String(length=40), nullable=False),
        sa.Column("conditions", sa.Text(), nullable=False),
        sa.Column("authority_reference", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("catalog_item_id", "alternate_catalog_item_id", name="uq_alternate_part_pair"),
    )
    op.create_index("ix_alternate_parts_catalog_item_id", "alternate_parts", ["catalog_item_id"])
    op.create_index("ix_alternate_parts_alternate_catalog_item_id", "alternate_parts", ["alternate_catalog_item_id"])
    op.create_index("ix_alternate_parts_interchangeability", "alternate_parts", ["interchangeability"])
    op.create_index("ix_alternate_parts_status", "alternate_parts", ["status"])

    op.create_table(
        "personnel_employees",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("employee_number", sa.String(length=80), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("department_id", sa.String(length=80), nullable=True),
        sa.Column("position_title", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("user_username", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "employee_number", name="uq_personnel_org_employee_number"),
    )
    op.create_index("ix_personnel_employees_organization_id", "personnel_employees", ["organization_id"])
    op.create_index("ix_personnel_employees_org_status", "personnel_employees", ["organization_id", "status"])

    op.create_table(
        "personnel_qualifications",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("employee_id", sa.String(length=80), sa.ForeignKey("personnel_employees.id"), nullable=False),
        sa.Column("qualification_type", sa.String(length=40), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("authority", sa.String(length=120), nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_personnel_qualifications_employee_id", "personnel_qualifications", ["employee_id"])

    op.create_table(
        "personnel_authorizations",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("employee_id", sa.String(length=80), sa.ForeignKey("personnel_employees.id"), nullable=False),
        sa.Column("auth_type", sa.String(length=40), nullable=False),
        sa.Column("scope", sa.String(length=200), nullable=False),
        sa.Column("aircraft_model_id", sa.String(length=80), nullable=True),
        sa.Column("ata_chapter_id", sa.String(length=80), nullable=True),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_personnel_authorizations_employee_id", "personnel_authorizations", ["employee_id"])

    op.create_table(
        "digital_stamp_profiles",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("employee_id", sa.String(length=80), sa.ForeignKey("personnel_employees.id"), nullable=False),
        sa.Column("stamp_code", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_digital_stamp_profiles_employee_id", "digital_stamp_profiles", ["employee_id"])

    op.create_table(
        "fault_codes",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_fault_code_org_code"),
    )
    op.create_index("ix_fault_codes_organization_id", "fault_codes", ["organization_id"])

    op.create_table(
        "critical_task_policies",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("domain", sa.String(length=40), nullable=False),
        sa.Column("requires_inspector", sa.String(length=10), nullable=False),
        sa.Column("requires_independent", sa.String(length=10), nullable=False),
        sa.Column("requires_aca", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("organization_id", "code", name="uq_critical_policy_org_code"),
    )
    op.create_index("ix_critical_task_policies_organization_id", "critical_task_policies", ["organization_id"])

    op.create_table(
        "maintenance_tasks",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("aircraft_id", sa.String(length=80), nullable=False),
        sa.Column("registration", sa.String(length=40), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("publication_id", sa.String(length=80), nullable=True),
        sa.Column("publication_revision_id", sa.String(length=80), nullable=True),
        sa.Column("component_id", sa.String(length=80), nullable=True),
        sa.Column("serial_number", sa.String(length=120), nullable=False),
        sa.Column("fault_code_id", sa.String(length=80), sa.ForeignKey("fault_codes.id"), nullable=True),
        sa.Column("critical_policy_id", sa.String(length=80), sa.ForeignKey("critical_task_policies.id"), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("performed_by_employee_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_maintenance_tasks_organization_id", "maintenance_tasks", ["organization_id"])
    op.create_index("ix_maintenance_tasks_aircraft_id", "maintenance_tasks", ["aircraft_id"])
    op.create_index("ix_maintenance_tasks_status", "maintenance_tasks", ["status"])

    op.create_table(
        "digital_signatures",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("signer_employee_id", sa.String(length=80), nullable=True),
        sa.Column("signer_username", sa.String(length=120), nullable=False),
        sa.Column("method", sa.String(length=40), nullable=False),
        sa.Column("purpose", sa.String(length=120), nullable=False),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=80), nullable=False),
        sa.Column("signature_hash", sa.String(length=128), nullable=False),
        sa.Column("pin_verified", sa.String(length=10), nullable=False),
        sa.Column("password_confirmed", sa.String(length=10), nullable=False),
        sa.Column("pki_ready", sa.String(length=10), nullable=False),
        sa.Column("smart_card_ready", sa.String(length=10), nullable=False),
        sa.Column("biometric_ready", sa.String(length=10), nullable=False),
        sa.Column("signed_at", sa.DateTime(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
    )
    op.create_index("ix_digital_signatures_organization_id", "digital_signatures", ["organization_id"])
    op.create_index("ix_digital_signatures_target", "digital_signatures", ["target_type", "target_id"])

    op.create_table(
        "certification_events",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("task_id", sa.String(length=80), sa.ForeignKey("maintenance_tasks.id"), nullable=False),
        sa.Column("step", sa.String(length=40), nullable=False),
        sa.Column("actor_employee_id", sa.String(length=80), nullable=True),
        sa.Column("actor_username", sa.String(length=120), nullable=False),
        sa.Column("signature_id", sa.String(length=80), sa.ForeignKey("digital_signatures.id"), nullable=True),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
    )
    op.create_index("ix_certification_events_task_id", "certification_events", ["task_id"])

    op.create_table(
        "technical_log_entries",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("aircraft_id", sa.String(length=80), nullable=False),
        sa.Column("registration", sa.String(length=40), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), nullable=True),
        sa.Column("task_id", sa.String(length=80), sa.ForeignKey("maintenance_tasks.id"), nullable=False),
        sa.Column("publication_id", sa.String(length=80), nullable=True),
        sa.Column("publication_revision_id", sa.String(length=80), nullable=True),
        sa.Column("component_id", sa.String(length=80), nullable=True),
        sa.Column("serial_number", sa.String(length=120), nullable=False),
        sa.Column("mechanic_employee_id", sa.String(length=80), nullable=True),
        sa.Column("inspector_employee_id", sa.String(length=80), nullable=True),
        sa.Column("aca_employee_id", sa.String(length=80), nullable=True),
        sa.Column("release_signature_id", sa.String(length=80), sa.ForeignKey("digital_signatures.id"), nullable=True),
        sa.Column("summary", sa.String(length=400), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
    )
    op.create_index("ix_technical_log_entries_organization_id", "technical_log_entries", ["organization_id"])
    op.create_index("ix_technical_log_entries_aircraft_id", "technical_log_entries", ["aircraft_id"])
    op.create_index("ix_technical_log_entries_task_id", "technical_log_entries", ["task_id"])

    op.create_table(
        "ai_document_index_stubs",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("ata_chapter_id", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_document_index_stubs_source", "ai_document_index_stubs", ["source_type", "source_id"])

    op.create_table(
        "ai_embedding_stubs",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("index_id", sa.String(length=80), sa.ForeignKey("ai_document_index_stubs.id"), nullable=False),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_embedding_stubs_index_id", "ai_embedding_stubs", ["index_id"])

    op.create_table(
        "ai_knowledge_cross_refs",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("organization_id", sa.String(length=80), nullable=False),
        sa.Column("from_type", sa.String(length=80), nullable=False),
        sa.Column("from_id", sa.String(length=80), nullable=False),
        sa.Column("to_type", sa.String(length=80), nullable=False),
        sa.Column("to_id", sa.String(length=80), nullable=False),
        sa.Column("relation", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_knowledge_cross_refs_organization_id", "ai_knowledge_cross_refs", ["organization_id"])


def downgrade() -> None:
    op.drop_table("ai_knowledge_cross_refs")
    op.drop_table("ai_embedding_stubs")
    op.drop_table("ai_document_index_stubs")
    op.drop_table("technical_log_entries")
    op.drop_table("certification_events")
    op.drop_table("digital_signatures")
    op.drop_table("maintenance_tasks")
    op.drop_table("critical_task_policies")
    op.drop_table("fault_codes")
    op.drop_table("digital_stamp_profiles")
    op.drop_table("personnel_authorizations")
    op.drop_table("personnel_qualifications")
    op.drop_table("personnel_employees")
    op.drop_table("alternate_parts")
    op.drop_index("ix_aircraft_models_family_id", table_name="aircraft_models")
    with op.batch_alter_table("aircraft_models") as batch_op:
        batch_op.drop_constraint("fk_aircraft_models_family_id", type_="foreignkey")
        batch_op.drop_column("family_id")
    op.drop_table("aircraft_families")
