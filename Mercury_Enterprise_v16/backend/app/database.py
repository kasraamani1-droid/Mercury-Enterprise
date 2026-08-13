from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .core.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Create missing tables and apply minimal SQLite ALTERs for Task 16/17 columns.

    Production Postgres upgrades should run Alembic (`alembic upgrade head`) before or
    beside application start. `create_all` remains for empty SQLite/dev databases.
    """
    # Import models so metadata includes Incident/Evidence/AuditEvent + org + fleet tables.
    from . import models  # noqa: F401
    from .org import models as org_models  # noqa: F401
    from .fleet import models as fleet_models  # noqa: F401
    from .components import models as component_models  # noqa: F401
    from .publications import models as publication_models  # noqa: F401
    from .personnel import models as personnel_models  # noqa: F401
    from .maintenance import models as maintenance_models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        evidence_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(evidence)")).fetchall()}
        evidence_alterations: list[str] = []
        if "provenance" not in evidence_columns:
            evidence_alterations.append(
                "ALTER TABLE evidence ADD COLUMN provenance VARCHAR(40) NOT NULL DEFAULT 'operator_entered'"
            )
        if "created_by" not in evidence_columns:
            evidence_alterations.append(
                "ALTER TABLE evidence ADD COLUMN created_by VARCHAR(120) NOT NULL DEFAULT ''"
            )
        if "organization_id" not in evidence_columns:
            evidence_alterations.append("ALTER TABLE evidence ADD COLUMN organization_id VARCHAR(80)")
        if "site_id" not in evidence_columns:
            evidence_alterations.append("ALTER TABLE evidence ADD COLUMN site_id VARCHAR(80)")
        for statement in evidence_alterations:
            connection.execute(text(statement))

        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_evidence_organization_id ON evidence (organization_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_evidence_site_id ON evidence (site_id)")
        )

        incident_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(incidents)")).fetchall()}
        incident_alterations: list[str] = []
        if "organization_id" not in incident_columns:
            incident_alterations.append("ALTER TABLE incidents ADD COLUMN organization_id VARCHAR(80)")
        if "site_id" not in incident_columns:
            incident_alterations.append("ALTER TABLE incidents ADD COLUMN site_id VARCHAR(80)")
        for statement in incident_alterations:
            connection.execute(text(statement))

        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_incidents_organization_id ON incidents (organization_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_incidents_site_id ON incidents (site_id)")
        )

        # Org hierarchy indexes (additive for long-lived SQLite files).
        for statement in (
            "CREATE INDEX IF NOT EXISTS ix_memberships_user_org ON memberships (user_id, organization_id)",
            "CREATE INDEX IF NOT EXISTS ix_memberships_org_status ON memberships (organization_id, status)",
            "CREATE INDEX IF NOT EXISTS ix_memberships_status ON memberships (status)",
            "CREATE INDEX IF NOT EXISTS ix_organizations_status ON organizations (status)",
            "CREATE INDEX IF NOT EXISTS ix_org_sites_status ON org_sites (status)",
        ):
            try:
                connection.execute(text(statement))
            except Exception:
                # Tables may not exist yet on first boot before create_all races; ignore.
                pass

        # Sprint 7b: aircraft family link on existing SQLite model rows.
        model_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(aircraft_models)")).fetchall()
        }
        if model_columns and "family_id" not in model_columns:
            connection.execute(text("ALTER TABLE aircraft_models ADD COLUMN family_id VARCHAR(80)"))
            connection.execute(
                text("CREATE INDEX IF NOT EXISTS ix_aircraft_models_family_id ON aircraft_models (family_id)")
            )

        # Sprint 7 task engine: additive columns on long-lived SQLite maintenance_tasks.
        task_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(maintenance_tasks)")).fetchall()
        }
        if task_columns:
            task_alters: list[tuple[str, str]] = [
                ("task_number", "ALTER TABLE maintenance_tasks ADD COLUMN task_number VARCHAR(80) NOT NULL DEFAULT ''"),
                ("task_type", "ALTER TABLE maintenance_tasks ADD COLUMN task_type VARCHAR(40) NOT NULL DEFAULT 'corrective'"),
                ("fleet_id", "ALTER TABLE maintenance_tasks ADD COLUMN fleet_id VARCHAR(80)"),
                ("priority", "ALTER TABLE maintenance_tasks ADD COLUMN priority VARCHAR(40) NOT NULL DEFAULT 'normal'"),
                ("due_date", "ALTER TABLE maintenance_tasks ADD COLUMN due_date DATETIME"),
                ("estimated_hours", "ALTER TABLE maintenance_tasks ADD COLUMN estimated_hours NUMERIC(12, 2) NOT NULL DEFAULT 0"),
                ("actual_hours", "ALTER TABLE maintenance_tasks ADD COLUMN actual_hours NUMERIC(12, 2) NOT NULL DEFAULT 0"),
                ("required_parts", "ALTER TABLE maintenance_tasks ADD COLUMN required_parts TEXT NOT NULL DEFAULT ''"),
                ("required_tools", "ALTER TABLE maintenance_tasks ADD COLUMN required_tools TEXT NOT NULL DEFAULT ''"),
                ("required_skills", "ALTER TABLE maintenance_tasks ADD COLUMN required_skills TEXT NOT NULL DEFAULT ''"),
                ("required_certification", "ALTER TABLE maintenance_tasks ADD COLUMN required_certification VARCHAR(200) NOT NULL DEFAULT ''"),
                ("requires_inspector", "ALTER TABLE maintenance_tasks ADD COLUMN requires_inspector VARCHAR(10) NOT NULL DEFAULT 'true'"),
                (
                    "independent_inspection_required",
                    "ALTER TABLE maintenance_tasks ADD COLUMN independent_inspection_required VARCHAR(10) NOT NULL DEFAULT 'false'",
                ),
                ("aca_required", "ALTER TABLE maintenance_tasks ADD COLUMN aca_required VARCHAR(10) NOT NULL DEFAULT 'false'"),
                (
                    "release_status",
                    "ALTER TABLE maintenance_tasks ADD COLUMN release_status VARCHAR(40) NOT NULL DEFAULT 'not_released'",
                ),
            ]
            for col, statement in task_alters:
                if col not in task_columns:
                    connection.execute(text(statement))
            connection.execute(
                text(
                    "UPDATE maintenance_tasks SET task_number = 'MT-' || UPPER(SUBSTR(id, 1, 12)) "
                    "WHERE task_number IS NULL OR task_number = ''"
                )
            )
            for col, statement in (
                (
                    "assigned_to_employee_id",
                    "ALTER TABLE maintenance_tasks ADD COLUMN assigned_to_employee_id VARCHAR(80)",
                ),
                ("version", "ALTER TABLE maintenance_tasks ADD COLUMN version INTEGER NOT NULL DEFAULT 1"),
            ):
                if col not in task_columns:
                    try:
                        connection.execute(text(statement))
                    except Exception:
                        pass
            for statement in (
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_maintenance_task_org_number "
                "ON maintenance_tasks (organization_id, task_number)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_task_number ON maintenance_tasks (task_number)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_task_type ON maintenance_tasks (task_type)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_fleet_id ON maintenance_tasks (fleet_id)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_priority ON maintenance_tasks (priority)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_release_status ON maintenance_tasks (release_status)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_org_type ON maintenance_tasks (organization_id, task_type)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_org_priority ON maintenance_tasks (organization_id, priority)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_org_fleet ON maintenance_tasks (organization_id, fleet_id)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_org_pub ON maintenance_tasks (organization_id, publication_id)",
                "CREATE INDEX IF NOT EXISTS ix_maintenance_tasks_assigned_to_employee_id "
                "ON maintenance_tasks (assigned_to_employee_id)",
            ):
                try:
                    connection.execute(text(statement))
                except Exception:
                    pass

        log_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(technical_log_entries)")).fetchall()
        }
        if log_columns and "independent_inspector_employee_id" not in log_columns:
            connection.execute(
                text(
                    "ALTER TABLE technical_log_entries "
                    "ADD COLUMN independent_inspector_employee_id VARCHAR(80)"
                )
            )
