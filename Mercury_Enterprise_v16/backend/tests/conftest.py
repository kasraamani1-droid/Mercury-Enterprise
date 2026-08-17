import os
import sys
from pathlib import Path

# Must run before importing app (Settings reads env at import time).
TEST_AUTH_PASSWORD = os.environ.setdefault(
    "MERCURY_AUTH_PASSWORD",
    "ci-test-password-not-for-production",
)
os.environ.setdefault("MERCURY_ENV", "development")
# Disable app-layer rate limits for the test suite (individual tests re-enable as needed).
os.environ.setdefault("MERCURY_RATE_LIMIT_LOGIN_PER_MINUTE", "0")
os.environ.setdefault("MERCURY_RATE_LIMIT_API_PER_MINUTE", "0")
os.environ.setdefault("MERCURY_METRICS_ENABLED", "true")
os.environ.setdefault("MERCURY_AUDIT_API_ACCESS", "false")
# Fast Argon2id parameters for the test suite (production defaults remain OWASP).
os.environ.setdefault("MERCURY_ARGON2_TIME_COST", "1")
os.environ.setdefault("MERCURY_ARGON2_MEMORY_KIB", "8192")
os.environ.setdefault("MERCURY_ARGON2_PARALLELISM", "1")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import ensure_schema
from app.main import (
    seed_components,
    seed_demo,
    seed_fleet,
    seed_logistics,
    seed_maintenance,
    seed_organizations,
    seed_personnel,
    seed_planning,
    seed_platform,
    seed_aeos_domains,
    seed_fabric,
    seed_ecosystem,
    seed_network,
    seed_twin,
    seed_plugins,
    seed_event_fabric,
    seed_publications,
    seed_work_orders,
)

ensure_schema()
seed_organizations()
seed_fleet()
seed_components()
seed_publications()
seed_personnel()
seed_maintenance()
seed_work_orders()
seed_planning()
seed_logistics()
seed_platform()
seed_aeos_domains()
seed_fabric()
seed_ecosystem()
seed_network()
seed_twin()
seed_plugins()
seed_event_fabric()
seed_demo()


def expire_active_temporary_access() -> None:
    """Revoke active temp grants so PermissionService overlays do not leak across tests."""
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.platform.models import PlatformTemporaryAccess

    db = SessionLocal()
    try:
        rows = list(
            db.scalars(
                select(PlatformTemporaryAccess).where(PlatformTemporaryAccess.status == "active")
            ).all()
        )
        if not rows:
            return
        for row in rows:
            row.status = "revoked"
        db.commit()
    finally:
        db.close()


import pytest


@pytest.fixture(autouse=True)
def _revoke_temp_access_after_test():
    yield
    expire_active_temporary_access()
