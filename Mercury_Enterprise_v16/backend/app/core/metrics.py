from __future__ import annotations

import time
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# Process start for uptime / metrics.
STARTED_AT = time.time()

REQUESTS = Counter(
    "mercury_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "mercury_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
ERRORS = Counter(
    "mercury_http_errors_total",
    "HTTP responses with status >= 400",
    ["method", "path", "status"],
)
LOGIN_ATTEMPTS = Counter(
    "mercury_login_attempts_total",
    "Login attempts",
    ["outcome"],
)
RATE_LIMIT_BLOCKS = Counter(
    "mercury_rate_limit_blocks_total",
    "Requests blocked by application rate limiting",
    ["bucket"],
)
ACTIVE_USERS = Gauge(
    "mercury_active_users",
    "Active authenticated sessions",
)
DB_LATENCY = Histogram(
    "mercury_database_latency_seconds",
    "Database check / query latency in seconds",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)


def normalize_path(path: str) -> str:
    """Collapse high-cardinality path segments for metric labels."""
    known = {
        "api",
        "v1",
        "auth",
        "admin",
        "health",
        "ready",
        "live",
        "metrics",
        "incidents",
        "decisions",
        "connectors",
        "approvals",
        "reports",
        "alerts",
        "ops",
        "users",
        "password",
        "role",
        "config",
        "login",
        "logout",
        "session",
        "system",
        "audit",
        "status",
        "summary",
        "history",
        "evaluate",
        "review",
        "coordinate",
        "platform",
        "integrations",
        "compliance",
        "dashboard",
        "ws",
    }
    parts = path.split("/")
    normalized: list[str] = []
    for part in parts:
        if not part:
            normalized.append(part)
            continue
        lower = part.lower()
        if lower in known:
            normalized.append(lower)
        elif len(part) > 24 or any(ch.isdigit() for ch in part) or "-" in part or "_" in part:
            normalized.append(":id")
        else:
            # Unknown static-looking segment — keep bounded.
            normalized.append(lower[:32])
    return "/".join(normalized) or "/"


def observe_rate_limit_block(bucket: str) -> None:
    RATE_LIMIT_BLOCKS.labels(bucket=bucket).inc()


def observe_request(*, method: str, path: str, status_code: int, duration_seconds: float) -> None:
    label_path = normalize_path(path)
    REQUESTS.labels(method=method, path=label_path, status=str(status_code)).inc()
    REQUEST_DURATION.labels(method=method, path=label_path).observe(duration_seconds)
    if status_code >= 400:
        ERRORS.labels(method=method, path=label_path, status=str(status_code)).inc()


def observe_login(*, success: bool) -> None:
    LOGIN_ATTEMPTS.labels(outcome="success" if success else "failure").inc()


def set_active_users(count: int) -> None:
    ACTIVE_USERS.set(max(0, int(count)))


def observe_db_latency(seconds: float) -> None:
    DB_LATENCY.observe(max(0.0, float(seconds)))


def render_prometheus() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def metrics_snapshot() -> dict[str, Any]:
    """Compact JSON snapshot for admin dashboard (not full Prometheus exposition)."""
    return {
        "uptime_seconds": round(time.time() - STARTED_AT, 3),
        "active_users": _gauge_value(ACTIVE_USERS),
        "login_attempts_total": _counter_total(LOGIN_ATTEMPTS),
        "login_failures_total": _counter_labeled_total(LOGIN_ATTEMPTS, {"outcome": "failure"}),
        "http_requests_total": _counter_total(REQUESTS),
        "http_errors_total": _counter_total(ERRORS),
        "rate_limit_blocks_total": _counter_total(RATE_LIMIT_BLOCKS),
    }


def _gauge_value(gauge: Gauge) -> float:
    for metric in gauge.collect():
        for sample in metric.samples:
            if sample.name == gauge._name:  # noqa: SLF001
                return float(sample.value)
    return 0.0


def _counter_total(counter: Counter) -> float:
    total = 0.0
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                total += float(sample.value)
    return total


def _counter_labeled_total(counter: Counter, labels: dict[str, str]) -> float:
    total = 0.0
    for metric in counter.collect():
        for sample in metric.samples:
            if not sample.name.endswith("_total"):
                continue
            if all(sample.labels.get(k) == v for k, v in labels.items()):
                total += float(sample.value)
    return total
