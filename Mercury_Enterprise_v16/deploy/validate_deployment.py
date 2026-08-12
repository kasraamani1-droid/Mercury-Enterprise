#!/usr/bin/env python3
"""Validate Mercury production Compose + NGINX configuration without Docker daemon.

Checks:
  - docker-compose.yml structure (restart, healthcheck, depends_on, production profile)
  - NGINX security / HTTPS / rate-limit / proxy requirements (static + template)
  - Optional: real `nginx -t` when nginx binary or Docker is available
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
NGINX_PROD = ROOT / "deploy" / "nginx-production.conf"
NGINX_TEMPLATE = ROOT / "deploy" / "nginx-production.conf.template"
NGINX_FRONTEND = ROOT / "frontend" / "nginx.conf"

REQUIRED_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "Cross-Origin-Opener-Policy",
    "Cross-Origin-Resource-Policy",
]


class Failure(Exception):
    pass


def _load_compose() -> dict:
    data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "services" not in data:
        raise Failure("docker-compose.yml missing services")
    return data


def validate_compose(data: dict) -> list[str]:
    notes: list[str] = []
    services = data["services"]
    for name in ("postgres", "backend", "frontend", "nginx", "certbot"):
        if name not in services:
            raise Failure(f"missing service: {name}")

    for name in ("postgres", "backend", "frontend", "nginx", "certbot"):
        restart = services[name].get("restart")
        if restart != "unless-stopped":
            raise Failure(f"{name}: restart must be unless-stopped (got {restart!r})")

    for name in ("postgres", "backend", "frontend", "nginx"):
        if "healthcheck" not in services[name]:
            raise Failure(f"{name}: missing healthcheck")

    backend_dep = services["backend"].get("depends_on") or {}
    if not isinstance(backend_dep, dict) or backend_dep.get("postgres", {}).get("condition") != "service_healthy":
        raise Failure("backend must depend on postgres with condition: service_healthy")

    frontend_dep = services["frontend"].get("depends_on") or {}
    if not isinstance(frontend_dep, dict) or frontend_dep.get("backend", {}).get("condition") != "service_healthy":
        raise Failure("frontend must depend on backend with condition: service_healthy")

    nginx = services["nginx"]
    if "production" not in (nginx.get("profiles") or []):
        raise Failure("nginx must use profiles: [production]")
    if "production" not in (services["certbot"].get("profiles") or []):
        raise Failure("certbot must use profiles: [production]")

    env = nginx.get("environment") or {}
    if env.get("NGINX_ENVSUBST_FILTER") != "^DOMAIN$":
        raise Failure("nginx must set NGINX_ENVSUBST_FILTER=^DOMAIN$ to protect $host/$scheme")

    ports = {str(p) for p in (nginx.get("ports") or [])}
    if "80:80" not in ports or "443:443" not in ports:
        raise Failure("nginx must publish 80:80 and 443:443")

    backend_hc = str(services["backend"]["healthcheck"].get("test"))
    if "/ready" not in backend_hc:
        raise Failure("backend healthcheck must probe /ready")

    frontend_hc = str(services["frontend"]["healthcheck"].get("test"))
    if "/live" not in frontend_hc:
        raise Failure("frontend healthcheck must probe /live")

    notes.append("compose structure OK (restart, healthchecks, depends_on, production profile)")
    return notes


def validate_nginx_text(path: Path, *, require_https: bool) -> list[str]:
    text = path.read_text(encoding="utf-8")
    notes: list[str] = []

    # Basic brace balance
    if text.count("{") != text.count("}"):
        raise Failure(f"{path.name}: unbalanced braces")

    if "limit_req_status 429" not in text:
        raise Failure(f"{path.name}: missing limit_req_status 429")
    if "limit_req_zone" not in text or "login_limit" not in text or "api_limit" not in text:
        raise Failure(f"{path.name}: missing login/api rate limit zones")
    if "gzip on" not in text:
        raise Failure(f"{path.name}: gzip not enabled")
    if "client_max_body_size" not in text:
        raise Failure(f"{path.name}: missing upload limit")
    if "proxy_request_buffering on" not in text:
        raise Failure(f"{path.name}: missing request buffering")
    if not re.search(r"proxy_set_header\s+Upgrade", text):
        raise Failure(f"{path.name}: missing WebSocket Upgrade header")
    if "proxy_read_timeout" not in text:
        raise Failure(f"{path.name}: missing proxy read timeout")

    for header in REQUIRED_HEADERS:
        if header == "Strict-Transport-Security" and not require_https:
            continue
        if header not in text:
            raise Failure(f"{path.name}: missing security header {header}")

    if require_https:
        if "return 301 https://" not in text:
            raise Failure(f"{path.name}: missing HTTP→HTTPS redirect")
        if "ssl_protocols TLSv1.2 TLSv1.3" not in text:
            raise Failure(f"{path.name}: TLS must be 1.2 minimum with 1.3 enabled")
        if "letsencrypt" not in text:
            raise Failure(f"{path.name}: missing Let's Encrypt certificate paths")
        if "acme-challenge" not in text:
            raise Failure(f"{path.name}: missing ACME webroot location")
        for probe in ("/health", "/ready", "/live"):
            if f"location = {probe}" not in text:
                raise Failure(f"{path.name}: missing probe location {probe}")

    notes.append(f"{path.name}: structural NGINX checks OK")
    return notes


def prepare_nginx_test_conf(src: Path, work: Path, *, cert_mount: str = "/work/certs") -> Path:
    """Rewrite upstreams + cert paths so nginx -t can run offline."""
    text = src.read_text(encoding="utf-8")
    text = text.replace("server frontend:80;", "server 127.0.0.1:8080;")
    text = text.replace("server backend:8000;", "server 127.0.0.1:8000;")
    text = text.replace("${DOMAIN}", "mercury.example.com")

    cert_dir = work / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    crt = cert_dir / "fullchain.pem"
    key = cert_dir / "privkey.pem"
    if not crt.exists():
        _write_self_signed(crt, key)

    if "ssl_certificate" in text:
        text = re.sub(
            r"ssl_certificate\s+[^;]+;",
            f"ssl_certificate {cert_mount}/fullchain.pem;",
            text,
        )
        text = re.sub(
            r"ssl_certificate_key\s+[^;]+;",
            f"ssl_certificate_key {cert_mount}/privkey.pem;",
            text,
        )
        # Stapling needs a real CA chain; disable for offline -t.
        text = text.replace("ssl_stapling on;", "ssl_stapling off;")
        text = text.replace("ssl_stapling_verify on;", "ssl_stapling_verify off;")

    out = work / src.name
    out.write_text(text, encoding="utf-8")
    return out


def _write_self_signed(cert_path: Path, key_path: Path) -> None:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        import datetime
    except ImportError as exc:  # pragma: no cover
        raise Failure("cryptography package required for offline nginx -t") from exc

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "mercury.example.com")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def run_nginx_t(conf: Path, cert_dir: Path) -> str:
    docker = shutil.which("docker")
    if docker:
        cmd = [
            docker,
            "run",
            "--rm",
            "-v",
            f"{conf}:/etc/nginx/conf.d/default.conf:ro",
            "-v",
            f"{cert_dir}:/work/certs:ro",
            "nginx:1.27-alpine",
            "nginx",
            "-t",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise Failure(f"nginx -t via Docker failed for {conf.name}:\n{output}")
        return "nginx -t via Docker: OK"

    nginx = shutil.which("nginx") or shutil.which("nginx.exe")
    if nginx:
        # Rewrite cert paths to local filesystem for native nginx.
        native = conf.read_text(encoding="utf-8")
        native = native.replace("/work/certs/", cert_dir.as_posix().rstrip("/") + "/")
        native_conf = conf.parent / f"native-{conf.name}"
        native_conf.write_text(native, encoding="utf-8")
        main = conf.parent / "nginx-main.conf"
        prefix = conf.parent / "prefix"
        (prefix / "logs").mkdir(parents=True, exist_ok=True)
        main.write_text(
            f"""
worker_processes 1;
error_log {(prefix / 'logs' / 'error.log').as_posix()};
pid {(prefix / 'nginx.pid').as_posix()};
events {{ worker_connections 64; }}
http {{
  include {native_conf.as_posix()};
}}
""",
            encoding="utf-8",
        )
        proc = subprocess.run([nginx, "-t", "-c", str(main)], capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise Failure(f"nginx -t failed for {conf.name}:\n{output}")
        return "nginx -t via local binary: OK"

    return "nginx -t SKIPPED (Docker/nginx binary not available on this host)"


def try_compose_config() -> str:
    import os

    docker = shutil.which("docker")
    if not docker:
        return "docker compose config SKIPPED (Docker not available on this host)"
    env = os.environ.copy()
    env.setdefault("DOMAIN", "mercury.example.com")
    proc = subprocess.run(
        [docker, "compose", "-f", str(COMPOSE), "config"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        raise Failure(f"docker compose config failed:\n{proc.stderr or proc.stdout}")
    return "docker compose config: OK"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-nginx-t", action="store_true")
    args = parser.parse_args()
    try:
        notes: list[str] = []
        data = _load_compose()
        notes.extend(validate_compose(data))
        notes.extend(validate_nginx_text(NGINX_PROD, require_https=True))
        notes.extend(validate_nginx_text(NGINX_TEMPLATE, require_https=True))
        notes.extend(validate_nginx_text(NGINX_FRONTEND, require_https=False))
        notes.append(try_compose_config())

        if not args.skip_nginx_t:
            with tempfile.TemporaryDirectory(prefix="mercury-nginx-") as tmp:
                work = Path(tmp)
                cert_dir = work / "certs"
                for src in (NGINX_PROD, NGINX_TEMPLATE, NGINX_FRONTEND):
                    conf = prepare_nginx_test_conf(src, work)
                    notes.append(f"{src.name}: {run_nginx_t(conf, cert_dir)}")

        print("VALIDATION PASSED")
        for note in notes:
            print(f"  - {note}")
        return 0
    except Failure as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
