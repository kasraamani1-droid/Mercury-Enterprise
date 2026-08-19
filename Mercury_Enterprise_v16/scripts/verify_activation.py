#!/usr/bin/env python3
"""Repository-side activation checks. Never prints secret values.

Does not claim DNS, IdP, or certificates exist. Checks compose/docs/env *names*.
If `.env` is present, reports each required key as SET or EMPTY without values.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_ENV_NAMES = (
    "MERCURY_AUTH_PASSWORD",
    "JWT_SECRET",
    "COOKIE_SECRET",
    "DOMAIN",
    "HTTPS_ENABLED",
    "LETSENCRYPT_EMAIL",
    "MERCURY_OIDC_ISSUER",
    "MERCURY_OIDC_CLIENT_ID",
    "MERCURY_OIDC_CLIENT_SECRET",
    "MERCURY_OIDC_REDIRECT_URI",
    "MERCURY_OIDC_JWKS_URI",
    "POSTGRES_PASSWORD",
    "REDIS_URL",
    "MERCURY_CORS_ORIGINS",
)

INTERNET_MUST_BE_SET = (
    "DOMAIN",
    "HTTPS_ENABLED",
    "LETSENCRYPT_EMAIL",
    "MERCURY_OIDC_ISSUER",
    "MERCURY_OIDC_CLIENT_ID",
    "MERCURY_OIDC_CLIENT_SECRET",
    "MERCURY_OIDC_REDIRECT_URI",
    "MERCURY_OIDC_JWKS_URI",
    "POSTGRES_PASSWORD",
    "JWT_SECRET",
    "COOKIE_SECRET",
    "MERCURY_AUTH_PASSWORD",
)


class Failure(Exception):
    pass


def _read(path: Path) -> str:
    if not path.is_file():
        raise Failure(f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def check_repo_files() -> list[str]:
    notes: list[str] = []
    overlay = _read(ROOT / "docker-compose.production.yml")
    if "ports: !reset []" not in overlay:
        raise Failure("production overlay must unpublish :3000 via ports: !reset []")
    if 'REDIS_REQUIRED: "true"' not in overlay:
        raise Failure("production overlay must set REDIS_REQUIRED")
    if "noeviction" not in overlay:
        raise Failure("production overlay Redis must use maxmemory-policy noeviction")
    if "${POSTGRES_PASSWORD:?" not in overlay:
        raise Failure("production overlay must require POSTGRES_PASSWORD")
    notes.append("production overlay: :3000 unpublished, Redis required, Postgres password required")

    env_example = _read(ROOT / ".env.example")
    for name in REQUIRED_ENV_NAMES:
        if name not in env_example:
            raise Failure(f".env.example missing {name}")
    if not re.search(r"^JWT_SECRET=\s*$", env_example, re.M):
        raise Failure(".env.example must not fill JWT_SECRET")
    if not re.search(r"^MERCURY_OIDC_CLIENT_SECRET=\s*$", env_example, re.M):
        raise Failure(".env.example must not fill MERCURY_OIDC_CLIENT_SECRET")
    if not re.search(r"^MERCURY_OIDC_JWKS_URI=\s*$", env_example, re.M):
        raise Failure(".env.example must not fill MERCURY_OIDC_JWKS_URI")
    notes.append(".env.example documents required names with empty secrets")

    nginx = _read(ROOT / "deploy" / "nginx-production.conf.template")
    for needle in ("ssl_protocols TLSv1.2 TLSv1.3", "X-Forwarded-Proto", "X-Forwarded-For", "${DOMAIN}"):
        if needle not in nginx:
            raise Failure(f"nginx template missing {needle}")
    notes.append("nginx template: TLS + forwarded headers + DOMAIN substitution")

    activation = _read(ROOT / "docs" / "pilot" / "ACTIVATION.md")
    if "OWNER ACTION REQUIRED" not in activation:
        raise Failure("ACTIVATION.md must list OWNER ACTION REQUIRED")
    notes.append("activation runbook present")
    return notes


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, rest = line.partition("=")
        values[key.strip()] = rest.strip().strip("'").strip('"')
    return values


def check_dotenv(strict_internet: bool) -> list[str]:
    path = ROOT / ".env"
    if not path.is_file():
        return [".env not present (expected in CI / clean clones) — skip value presence"]
    parsed = _parse_env_file(path)
    notes: list[str] = []
    for name in REQUIRED_ENV_NAMES:
        present = bool((parsed.get(name) or "").strip())
        notes.append(f".env {name}: {'SET' if present else 'EMPTY'}")
        if strict_internet and name in INTERNET_MUST_BE_SET and not present:
            raise Failure(f".env {name} is EMPTY (required for internet-facing boot)")
    https = (parsed.get("HTTPS_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}
    domain = (parsed.get("DOMAIN") or "").strip()
    redirect = (parsed.get("MERCURY_OIDC_REDIRECT_URI") or "").strip().rstrip("/")
    if https and domain and redirect:
        expected = f"https://{domain}/api/v1/auth/oidc/callback"
        if redirect != expected:
            raise Failure("MERCURY_OIDC_REDIRECT_URI does not match https://$DOMAIN/api/v1/auth/oidc/callback")
        notes.append("OIDC redirect matches DOMAIN (value not printed)")
    return notes


def try_compose_config() -> str:
    docker = shutil.which("docker")
    if not docker:
        return "docker compose config SKIPPED (Docker not on PATH)"
    env = os.environ.copy()
    env.setdefault("POSTGRES_PASSWORD", "ci-compose-not-for-production")
    env.setdefault("DOMAIN", "ci.invalid")
    proc = subprocess.run(
        [
            docker,
            "compose",
            "-f",
            str(ROOT / "docker-compose.yml"),
            "-f",
            str(ROOT / "docker-compose.production.yml"),
            "config",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise Failure("docker compose production overlay config failed (stderr omitted if it may contain env)")
    merged = proc.stdout or ""
    if "3000:80" in merged.replace(" ", ""):
        # Published mapping would look like 3000:80
        if re.search(r"published:\s*[\"']?3000", merged) or re.search(r"- [\"']?3000:80", merged):
            raise Failure("production overlay still publishes host :3000")
    return "docker compose production overlay config: OK"


def main() -> int:
    parser = argparse.ArgumentParser(description="Mercury activation pack verify (no secret printing)")
    parser.add_argument(
        "--strict-internet-env",
        action="store_true",
        help="Fail if .env exists but internet-required keys are empty",
    )
    parser.add_argument("--skip-docker", action="store_true")
    args = parser.parse_args()
    try:
        notes = check_repo_files()
        notes.extend(check_dotenv(strict_internet=args.strict_internet_env))
        if not args.skip_docker:
            notes.append(try_compose_config())
        print("ACTIVATION VERIFY PASSED (repository-side; infrastructure is not claimed live)")
        for note in notes:
            print(f"  - {note}")
        return 0
    except Failure as exc:
        print(f"ACTIVATION VERIFY FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
