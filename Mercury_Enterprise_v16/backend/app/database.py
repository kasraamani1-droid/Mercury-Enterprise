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
    """Create missing tables and apply minimal SQLite ALTERs for evidence provenance columns."""
    # Import models so metadata includes Incident/Evidence/AuditEvent tables.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(evidence)")).fetchall()}
        alterations: list[str] = []
        if "provenance" not in columns:
            alterations.append(
                "ALTER TABLE evidence ADD COLUMN provenance VARCHAR(40) NOT NULL DEFAULT 'operator_entered'"
            )
        if "created_by" not in columns:
            alterations.append(
                "ALTER TABLE evidence ADD COLUMN created_by VARCHAR(120) NOT NULL DEFAULT ''"
            )
        if "organization_id" not in columns:
            alterations.append("ALTER TABLE evidence ADD COLUMN organization_id VARCHAR(80)")
        if "site_id" not in columns:
            alterations.append("ALTER TABLE evidence ADD COLUMN site_id VARCHAR(80)")
        for statement in alterations:
            connection.execute(text(statement))

        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_evidence_organization_id ON evidence (organization_id)")
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_evidence_site_id ON evidence (site_id)")
        )
