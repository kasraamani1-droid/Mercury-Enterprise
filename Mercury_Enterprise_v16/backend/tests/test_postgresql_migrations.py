"""RC1 Blocker 05 — Alembic history, clean install, upgrade, and rollback checks.

Production schema authority is PostgreSQL + Alembic. SQLite uses ensure_schema()/create_all
for local/dev; Alembic is still verified here with SQLite batch mode so the revision
chain can be exercised without Docker on developer hosts.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = BACKEND_ROOT / "alembic" / "versions"
EXPECTED_HEAD = "20260814_0022"
REVISION_FILE_RE = re.compile(r"^202\d{5}_\d{4}_.+\.py$")


def _script_directory() -> ScriptDirectory:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    return ScriptDirectory.from_config(cfg)


def _alembic_env(database_url: str) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env.setdefault("MERCURY_ENV", "development")
    env.setdefault("MERCURY_AUTH_PASSWORD", "ci-test-password-not-for-production")
    return env


def _run_alembic(*args: str, database_url: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_ROOT),
        env=_alembic_env(database_url),
        capture_output=True,
        text=True,
        check=False,
    )


def test_alembic_single_linear_head() -> None:
    script = _script_directory()
    heads = script.get_heads()
    assert heads == [EXPECTED_HEAD], f"expected single head {EXPECTED_HEAD}, got {heads}"
    revisions = list(script.walk_revisions())
    assert len(revisions) >= 22
    # Linear: each revision (except base) has exactly one parent; no branches.
    for rev in revisions:
        if rev.revision == "20260810_0001":
            assert rev.down_revision is None
        else:
            assert isinstance(rev.down_revision, str) and rev.down_revision


def test_every_revision_file_declares_upgrade_and_downgrade() -> None:
    files = sorted(VERSIONS_DIR.glob("*.py"))
    assert files, "no alembic version files found"
    for path in files:
        assert REVISION_FILE_RE.match(path.name), f"unexpected revision filename: {path.name}"
        text = path.read_text(encoding="utf-8")
        assert "revision =" in text or "revision=" in text
        assert "down_revision" in text
        assert re.search(r"^def upgrade\(", text, re.M), path.name
        assert re.search(r"^def downgrade\(", text, re.M), path.name


def test_production_compose_defaults_postgres_database_url() -> None:
    compose = (BACKEND_ROOT.parent / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgresql+psycopg://mercury:mercury@postgres:5432/mercury" in compose
    assert "DATABASE_URL:" in compose
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY alembic ./alembic" in dockerfile
    assert "COPY alembic.ini ./alembic.ini" in dockerfile
    assert "docker-entrypoint.sh" in dockerfile
    entrypoint = (BACKEND_ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    assert "alembic upgrade head" in entrypoint


def test_env_example_points_at_postgres() -> None:
    example = (BACKEND_ROOT.parent / ".env.example").read_text(encoding="utf-8")
    assert example.splitlines()[4].startswith(
        "DATABASE_URL=postgresql+psycopg://mercury:mercury@postgres:5432/mercury"
    )


def test_clean_install_upgrade_to_head(tmp_path: Path) -> None:
    db_path = tmp_path / "clean_install.db"
    url = f"sqlite:///{db_path.as_posix()}"
    result = _run_alembic("upgrade", "head", database_url=url)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    current = _run_alembic("current", database_url=url)
    assert current.returncode == 0, current.stderr
    assert EXPECTED_HEAD in current.stdout


def test_upgrade_is_idempotent_at_head(tmp_path: Path) -> None:
    db_path = tmp_path / "idempotent.db"
    url = f"sqlite:///{db_path.as_posix()}"
    first = _run_alembic("upgrade", "head", database_url=url)
    assert first.returncode == 0, first.stderr
    second = _run_alembic("upgrade", "head", database_url=url)
    assert second.returncode == 0, second.stderr
    current = _run_alembic("current", database_url=url)
    assert EXPECTED_HEAD in current.stdout


def test_rollback_one_revision_then_reupgrade(tmp_path: Path) -> None:
    """Verify alembic downgrade -1 and re-upgrade (operator rollback procedure)."""
    db_path = tmp_path / "rollback.db"
    url = f"sqlite:///{db_path.as_posix()}"
    upgraded = _run_alembic("upgrade", "head", database_url=url)
    assert upgraded.returncode == 0, upgraded.stderr

    downgraded = _run_alembic("downgrade", "-1", database_url=url)
    assert downgraded.returncode == 0, downgraded.stdout + "\n" + downgraded.stderr
    after_down = _run_alembic("current", database_url=url)
    assert after_down.returncode == 0, after_down.stderr
    assert "20260814_0021" in after_down.stdout
    assert EXPECTED_HEAD not in after_down.stdout

    reupgraded = _run_alembic("upgrade", "head", database_url=url)
    assert reupgraded.returncode == 0, reupgraded.stderr
    after_up = _run_alembic("current", database_url=url)
    assert EXPECTED_HEAD in after_up.stdout


def test_postgres_upgrade_when_database_url_configured(tmp_path: Path) -> None:
    """Optional live PostgreSQL gate — skipped unless MERCURY_TEST_DATABASE_URL is set."""
    pg_url = os.environ.get("MERCURY_TEST_DATABASE_URL", "").strip()
    if not pg_url or not pg_url.startswith(("postgresql", "postgres")):
        pytest.skip("Set MERCURY_TEST_DATABASE_URL to a PostgreSQL URL to run live PG migration verification")

    # Use a unique schema/database URL supplied by the operator; do not mutate shared prod DBs.
    result = _run_alembic("upgrade", "head", database_url=pg_url)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    current = _run_alembic("current", database_url=pg_url)
    assert EXPECTED_HEAD in current.stdout
    # Rollback one step and re-apply — same procedure as the deploy runbook.
    down = _run_alembic("downgrade", "-1", database_url=pg_url)
    assert down.returncode == 0, down.stderr
    up = _run_alembic("upgrade", "head", database_url=pg_url)
    assert up.returncode == 0, up.stderr

    from sqlalchemy import create_engine, inspect

    engine = create_engine(pg_url)
    try:
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        assert "alembic_version" in tables
        assert "incidents" in tables
        assert "approval_requests" in tables
        assert "logistics_warehouses" in tables
        fks = insp.get_foreign_keys("timeline_events")
        assert any(fk.get("referred_table") == "incidents" for fk in fks)
        indexes = {ix["name"] for ix in insp.get_indexes("incidents")}
        assert "ix_incidents_organization_id" in indexes
        uniques = insp.get_unique_constraints("logistics_warehouses")
        assert any(u.get("name") == "uq_log_wh_org_code" for u in uniques)
    finally:
        engine.dispose()


def test_full_downgrade_to_base_then_upgrade_head(tmp_path: Path) -> None:
    """Exercise the entire downgrade path, then recreate from empty (rollback support)."""
    db_path = tmp_path / "full_cycle.db"
    url = f"sqlite:///{db_path.as_posix()}"
    upgraded = _run_alembic("upgrade", "head", database_url=url)
    assert upgraded.returncode == 0, upgraded.stderr
    to_base = _run_alembic("downgrade", "base", database_url=url)
    assert to_base.returncode == 0, to_base.stdout + "\n" + to_base.stderr
    current = _run_alembic("current", database_url=url)
    assert current.returncode == 0, current.stderr
    assert EXPECTED_HEAD not in current.stdout
    reupgraded = _run_alembic("upgrade", "head", database_url=url)
    assert reupgraded.returncode == 0, reupgraded.stderr
    after = _run_alembic("current", database_url=url)
    assert EXPECTED_HEAD in after.stdout


def test_engine_kwargs_postgres_enables_pooling() -> None:
    from app.core.config import settings
    from app.database import engine_kwargs

    kwargs = engine_kwargs("postgresql+psycopg://mercury:mercury@postgres:5432/mercury")
    assert kwargs["pool_pre_ping"] is True
    assert kwargs["pool_size"] == settings.db_pool_size
    assert kwargs["max_overflow"] == settings.db_max_overflow
    assert kwargs["pool_recycle"] == settings.db_pool_recycle
    assert kwargs["connect_args"] == {}


def test_engine_kwargs_sqlite_omits_queue_pool_size() -> None:
    from app.database import engine_kwargs

    kwargs = engine_kwargs("sqlite:///./mercury.db")
    assert kwargs["pool_pre_ping"] is True
    assert "pool_size" not in kwargs
    assert "pool_recycle" not in kwargs
    assert kwargs["connect_args"] == {"check_same_thread": False}


def test_orm_metadata_indexes_constraints_foreign_keys() -> None:
    from sqlalchemy import UniqueConstraint

    from app.database import Base, import_orm_models

    import_orm_models()
    tables = Base.metadata.tables
    for required in (
        "incidents",
        "timeline_events",
        "evidence",
        "audit_events",
        "approval_requests",
        "org_users",
        "logistics_warehouses",
        "logistics_bins",
        "maintenance_tasks",
    ):
        assert required in tables, required

    foreign_keys = [fk for table in tables.values() for fk in table.foreign_keys]
    uniques = [c for table in tables.values() for c in table.constraints if isinstance(c, UniqueConstraint)]
    assert len(foreign_keys) >= 40, f"expected substantial FK graph, got {len(foreign_keys)}"
    assert any(fk.column.table.name == "incidents" for fk in foreign_keys)
    assert any(fk.column.table.name == "logistics_warehouses" for fk in foreign_keys)
    assert any(c.name == "uq_log_wh_org_code" for c in uniques)
    assert any(c.name == "uq_maintenance_task_org_number" for c in uniques)
    incidents = tables["incidents"]
    org_indexed = incidents.c.organization_id.index or any(
        col.name == "organization_id" for ix in incidents.indexes for col in ix.columns
    )
    assert org_indexed


def test_models_use_dialect_portable_column_types() -> None:
    from app.database import Base, import_orm_models

    import_orm_models()
    for table in Base.metadata.tables.values():
        for column in table.columns:
            module = type(column.type).__module__
            assert "postgresql" not in module, f"{table.name}.{column.name} uses {type(column.type).__name__}"
            assert "sqlite" not in module, f"{table.name}.{column.name} uses {type(column.type).__name__}"


def test_alembic_revisions_avoid_postgres_only_ddl() -> None:
    forbidden = ("JSONB", "postgresql.UUID", "CITEXT", "TSVECTOR", "HSTORE", "INET", "CIDR")
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} contains {token}"


def test_ilike_and_for_update_compile_on_postgres_and_sqlite() -> None:
    from sqlalchemy import select
    from sqlalchemy.dialects import postgresql, sqlite

    from app.logistics.models import PartMaster

    stmt = select(PartMaster).where(PartMaster.description.ilike("%bolt%")).with_for_update()
    pg_sql = str(stmt.compile(dialect=postgresql.dialect()))
    sqlite_sql = str(stmt.compile(dialect=sqlite.dialect()))
    assert "ILIKE" in pg_sql.upper()
    assert "FOR UPDATE" in pg_sql.upper()
    assert "LIKE" in sqlite_sql.upper()


def test_get_db_rolls_back_uncommitted_work_on_error() -> None:
    from app.database import SessionLocal, get_db
    from app.models import Incident

    marker = "rc1-pg-rollback-sentinel"
    gen = get_db()
    db = next(gen)
    db.add(
        Incident(
            id=marker,
            title="rollback-probe",
            status="open",
            severity="low",
            summary="",
        )
    )
    db.flush()
    with pytest.raises(RuntimeError, match="forced-rollback"):
        gen.throw(RuntimeError("forced-rollback"))

    check = SessionLocal()
    try:
        assert check.get(Incident, marker) is None
    finally:
        check.close()


def test_alembic_env_registers_full_orm_metadata() -> None:
    env_py = (BACKEND_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    assert "import_orm_models" in env_py
    assert "NullPool" in env_py
    assert "render_as_batch" in env_py


def test_compose_postgres_health_gates_backend() -> None:
    compose = (BACKEND_ROOT.parent / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgres:17-alpine" in compose
    assert "pg_isready -U mercury" in compose
    assert "condition: service_healthy" in compose
    dockerfile = (BACKEND_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "ENTRYPOINT" in dockerfile
    entrypoint = (BACKEND_ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    assert "postgresql*" in entrypoint
    assert "skipping Alembic" in entrypoint


def test_ensure_schema_skips_pragma_on_non_sqlite() -> None:
    source = (BACKEND_ROOT / "app" / "database.py").read_text(encoding="utf-8")
    assert "if not is_sqlite_url():" in source
    assert "PRAGMA table_info" in source
