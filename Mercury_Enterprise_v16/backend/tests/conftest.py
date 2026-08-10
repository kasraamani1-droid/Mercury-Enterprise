import os
import sys
from pathlib import Path

# Must run before importing app (Settings reads env at import time).
TEST_AUTH_PASSWORD = os.environ.setdefault(
    "MERCURY_AUTH_PASSWORD",
    "ci-test-password-not-for-production",
)
os.environ.setdefault("MERCURY_ENV", "development")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import ensure_schema
from app.main import seed_demo

ensure_schema()
seed_demo()
