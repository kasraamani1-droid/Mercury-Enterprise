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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import ensure_schema
from app.main import seed_demo, seed_fleet, seed_organizations

ensure_schema()
seed_organizations()
seed_fleet()
seed_demo()
