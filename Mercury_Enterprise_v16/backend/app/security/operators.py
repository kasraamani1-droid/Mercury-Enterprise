from __future__ import annotations

import hashlib
import hmac
import re
from copy import deepcopy

from .authorization import Role

_OPERATOR_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,79}$")
_FORBIDDEN_PASSWORDS = frozenset({"mercury-demo", "password", "admin", "changeme"})


def _pepper() -> bytes:
    # Prefer dedicated secrets; fall back only for local/dev single-process use.
    from ..core.config import settings

    raw = (settings.cookie_secret or settings.jwt_secret or "mercury-dev-pepper").encode("utf-8")
    return raw


def hash_password(password: str) -> str:
    return hashlib.sha256(_pepper() + b"\0" + password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hmac.compare_digest(password_hash, hash_password(password))
    except Exception:
        return False


def validate_operator_name(operator: str) -> str:
    name = (operator or "").strip()
    if not _OPERATOR_NAME_RE.match(name):
        raise ValueError("invalid_operator_name")
    return name


def validate_password(password: str) -> str:
    secret = password or ""
    if len(secret) < 12:
        raise ValueError("weak_password")
    if secret.lower() in _FORBIDDEN_PASSWORDS:
        raise ValueError("forbidden_password")
    return secret


class OperatorStore:
    """In-memory operator directory (single-worker). Passwords stored hashed."""

    def __init__(self) -> None:
        self._operators: dict[str, dict[str, str]] = {}

    def bootstrap(self, *, auth_operator: str, auth_password: str, role_by_operator: dict[str, str]) -> None:
        hashed = hash_password(auth_password) if auth_password else hash_password("")
        for name, role in role_by_operator.items():
            self._operators[name] = {"role": role, "password_hash": hashed}

    def authenticate(self, operator: str, password: str) -> str | None:
        record = self._operators.get(operator)
        if record is None:
            # Constant-time-ish dummy compare to reduce user-enumeration timing skew.
            verify_password(password or "", hash_password("invalid-user-dummy"))
            return None
        if not verify_password(password or "", record["password_hash"]):
            return None
        return record["role"]

    def list_operators(self) -> list[dict[str, str]]:
        return [{"operator": name, "role": data["role"]} for name, data in sorted(self._operators.items())]

    def get(self, operator: str) -> dict[str, str] | None:
        record = self._operators.get(operator)
        if record is None:
            return None
        return {"operator": operator, "role": record["role"]}

    def admin_count(self) -> int:
        return sum(1 for data in self._operators.values() if data["role"] == Role.ADMINISTRATOR.value)

    def create(self, operator: str, password: str, role: str) -> dict[str, str]:
        name = validate_operator_name(operator)
        secret = validate_password(password)
        if name in self._operators:
            raise ValueError("operator_exists")
        Role(role)  # validate
        self._operators[name] = {"role": role, "password_hash": hash_password(secret)}
        return {"operator": name, "role": role}

    def set_password(self, operator: str, password: str) -> dict[str, str]:
        record = self._operators.get(operator)
        if record is None:
            raise ValueError("operator_not_found")
        secret = validate_password(password)
        record["password_hash"] = hash_password(secret)
        return {"operator": operator, "role": record["role"]}

    def set_role(self, operator: str, role: str) -> dict[str, str]:
        record = self._operators.get(operator)
        if record is None:
            raise ValueError("operator_not_found")
        Role(role)
        if (
            record["role"] == Role.ADMINISTRATOR.value
            and role != Role.ADMINISTRATOR.value
            and self.admin_count() <= 1
        ):
            raise ValueError("last_admin")
        record["role"] = role
        return {"operator": operator, "role": role}

    def snapshot(self) -> dict[str, dict[str, str]]:
        # Never include password hashes in snapshots.
        return {name: {"role": data["role"]} for name, data in deepcopy(self._operators).items()}


operator_store = OperatorStore()
