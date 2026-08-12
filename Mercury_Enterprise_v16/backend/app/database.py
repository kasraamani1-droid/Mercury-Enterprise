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
