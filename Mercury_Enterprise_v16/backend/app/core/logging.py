from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler

request_id_var: ContextVar[str] = ContextVar("request_id", default="")
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")


from ..security.redact import redact_text


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        request_id = getattr(record, "request_id", None) or request_id_var.get()
        correlation_id = getattr(record, "correlation_id", None) or correlation_id_var.get()
        user_id = getattr(record, "user_id", None) or user_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if user_id:
            payload["user_id"] = user_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_text(super().format(record))


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = request_id_var.get()
        if not getattr(record, "correlation_id", None):
            record.correlation_id = correlation_id_var.get()
        if not getattr(record, "user_id", None):
            record.user_id = user_id_var.get()
        return True


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_json = os.getenv("MERCURY_LOG_JSON", "false").lower() in {"1", "true", "yes", "on"}
    log_file = (os.getenv("LOG_FILE") or "").strip()
    max_bytes = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    root = logging.getLogger()
    root.handlers.clear()
    context_filter = _ContextFilter()

    stream = logging.StreamHandler()
    if log_json:
        stream.setFormatter(_JsonFormatter())
    else:
        stream.setFormatter(
            _RedactingFormatter(
                "%(asctime)s %(levelname)s %(name)s "
                "[request_id=%(request_id)s correlation_id=%(correlation_id)s user_id=%(user_id)s] %(message)s"
            )
        )
    stream.addFilter(context_filter)
    root.addHandler(stream)

    if log_file:
        rotating = RotatingFileHandler(
            log_file,
            maxBytes=max(1024, max_bytes),
            backupCount=max(1, backup_count),
            encoding="utf-8",
        )
        if log_json:
            rotating.setFormatter(_JsonFormatter())
        else:
            rotating.setFormatter(_RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        rotating.addFilter(context_filter)
        root.addHandler(rotating)

    root.setLevel(getattr(logging, level, logging.INFO))


def bind_request_context(*, request_id: str, correlation_id: str, user_id: str = "") -> None:
    request_id_var.set(request_id)
    correlation_id_var.set(correlation_id)
    user_id_var.set(user_id or "")
