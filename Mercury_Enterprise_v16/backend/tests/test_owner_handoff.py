"""Owner activation handoff — repo-side checklist only (no live IdP/DNS/certs)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def test_owner_handoff_is_the_start_document():
    handoff = (PACKAGE_ROOT / "docs" / "pilot" / "OWNER_HANDOFF.md").read_text(encoding="utf-8")
    assert "2 vCPU" in handoff
    assert "4 GiB" in handoff
    assert "token_urlsafe" in handoff
    assert "openssl rand -base64 48" in handoff
    assert "ufw" in handoff
    assert "https://$DOMAIN/api/v1/auth/oidc/callback" in handoff
    assert "docker compose --profile production -f docker-compose.yml -f docker-compose.production.yml" in handoff
    assert "/live" in handoff and "/ready" in handoff
    assert "down -v" in handoff
    assert "OWNER ACTION REQUIRED" in handoff
    assert "**A.**" in handoff and "**B.**" in handoff and "**C.**" in handoff
    assert "kasra" not in handoff.lower()
    assert "okta.com" not in handoff
    assert "amazonaws.com" not in handoff
    activation = (PACKAGE_ROOT / "docs" / "pilot" / "ACTIVATION.md").read_text(encoding="utf-8")
    assert "OWNER_HANDOFF.md" in activation
    index = (PACKAGE_ROOT / "docs" / "pilot" / "README.md").read_text(encoding="utf-8")
    assert "OWNER_HANDOFF.md" in index


def test_init_letsencrypt_uses_production_overlay():
    script = (PACKAGE_ROOT / "deploy" / "init-letsencrypt.sh").read_text(encoding="utf-8")
    assert "docker-compose.production.yml" in script
    assert "COMPOSE=" in script


def test_env_example_points_at_handoff_and_secret_commands():
    env_example = (PACKAGE_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OWNER_HANDOFF.md" in env_example
    assert "token_urlsafe" in env_example
    assert re.search(r"^JWT_SECRET=\s*$", env_example, re.M)
    assert re.search(r"^COOKIE_SECRET=\s*$", env_example, re.M)
    assert re.search(r"^MERCURY_OIDC_CLIENT_SECRET=\s*$", env_example, re.M)
    for name in (
        "MERCURY_AUTH_MODE",
        "MERCURY_REQUIRE_OIDC",
        "MERCURY_SEED_DEMO",
        "MERCURY_ALLOW_PASSWORD_AUTH",
        "POSTGRES_PASSWORD",
    ):
        assert name in env_example


def test_verify_activation_passes_without_printing_secrets():
    from conftest import TEST_AUTH_PASSWORD

    result = subprocess.run(
        [sys.executable, str(PACKAGE_ROOT / "scripts" / "verify_activation.py"), "--skip-docker"],
        cwd=str(PACKAGE_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    blob = (result.stdout + result.stderr).lower()
    assert "activation verify passed" in blob
    assert "owner handoff checklist present" in blob
    assert "init-letsencrypt uses production overlay" in blob
    assert TEST_AUTH_PASSWORD.lower() not in blob
