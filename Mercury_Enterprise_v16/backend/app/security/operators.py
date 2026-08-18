from __future__ import annotations

import hashlib
import hmac
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Iterable

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

try:
    from argon2.exceptions import InvalidHashError
except ImportError:  # argon2-cffi < 23
    from argon2.exceptions import InvalidHash as InvalidHashError
from argon2.low_level import Type
from sqlalchemy import select

from .authorization import Role

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_OPERATOR_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,79}$")
_FORBIDDEN_PASSWORDS = frozenset({"mercury-demo", "password", "admin", "changeme"})
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
DEV_PEPPER_FALLBACK = "mercury-dev-pepper"
_DUMMY_PASSWORD = "invalid-user-dummy-not-a-real-password"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _password_hasher() -> PasswordHasher:
    from ..core.config import settings

    return PasswordHasher(
        time_cost=max(1, int(settings.argon2_time_cost)),
        memory_cost=max(8192, int(settings.argon2_memory_kib)),
        parallelism=max(1, int(settings.argon2_parallelism)),
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )


def _is_argon2_hash(password_hash: str) -> bool:
    return (password_hash or "").startswith("$argon2")


def hash_password(password: str) -> str:
    """Argon2id with a unique per-password salt. Never SHA-256."""
    return _password_hasher().hash(password or "")


def _legacy_sha256(password: str, pepper: bytes) -> str:
    return hashlib.sha256(pepper + b"\0" + (password or "").encode("utf-8")).hexdigest()


def _legacy_peppers() -> list[bytes]:
    """Peppers that may have produced historical SHA-256 hashes."""
    from ..core.config import settings

    seen: set[bytes] = set()
    out: list[bytes] = []
    for raw in (settings.cookie_secret, settings.jwt_secret, DEV_PEPPER_FALLBACK):
        pepper = (raw or "").encode("utf-8")
        if pepper and pepper not in seen:
            seen.add(pepper)
            out.append(pepper)
    return out


def _verify_legacy_sha256(password: str, password_hash: str) -> bool:
    if not _SHA256_HEX_RE.match(password_hash or ""):
        return False
    for pepper in _legacy_peppers():
        try:
            if hmac.compare_digest(password_hash, _legacy_sha256(password, pepper)):
                return True
        except Exception:
            continue
    return False


def verify_password(password: str, password_hash: str) -> bool:
    stored = password_hash or ""
    if _is_argon2_hash(stored):
        try:
            return bool(_password_hasher().verify(stored, password or ""))
        except (VerifyMismatchError, InvalidHashError, Exception):
            return False
    if _SHA256_HEX_RE.match(stored):
        return _verify_legacy_sha256(password, stored)
    return False


def password_needs_rehash(password_hash: str) -> bool:
    stored = password_hash or ""
    if not _is_argon2_hash(stored):
        return True
    try:
        return bool(_password_hasher().check_needs_rehash(stored))
    except Exception:
        return True


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


_DUMMY_HASH: str | None = None


def _dummy_verify(password: str) -> None:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(_DUMMY_PASSWORD)
    verify_password(password or "", _DUMMY_HASH)


def _normalized_role(role: str | None) -> str:
    value = (role or "").strip() or Role.VIEWER.value
    try:
        return Role(value).value
    except ValueError:
        return Role.VIEWER.value


def authenticate_credentials(db: Session, operator: str, password: str) -> str | None:
    """Verify credentials against OrgUser. Returns platform directory role or None."""
    from ..org.models import OrgUser

    name = (operator or "").strip()
    user = db.scalar(select(OrgUser).where(OrgUser.username == name)) if name else None
    if user is None or user.status != "active" or not (user.password_hash or "").strip():
        _dummy_verify(password or "")
        return None
    if not verify_password(password or "", user.password_hash):
        return None
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password or "")
        user.updated_at = _utcnow()
        db.add(user)
        try:
            db.commit()
        except Exception:
            db.rollback()
    role = _normalized_role(user.platform_role)
    operator_store.register_role(user.username, role)
    return role


class OperatorStore:
    """Process-local role directory. Passwords live on OrgUser only."""

    def __init__(self) -> None:
        self._operators: dict[str, dict[str, str]] = {}

    def bootstrap(self, *, auth_operator: str, auth_password: str, role_by_operator: dict[str, str]) -> None:
        _ = auth_operator, auth_password
        for name, role in role_by_operator.items():
            self._operators[name] = {"role": _normalized_role(role)}

    def hydrate_from_db(self, db: Session) -> None:
        from ..org.models import OrgUser

        rows = list(db.scalars(select(OrgUser)).all())
        self.hydrate(((row.username, row.platform_role) for row in rows))

    def hydrate(self, records: Iterable[tuple[str, str]]) -> None:
        for name, role in records:
            username = (name or "").strip()
            if not username:
                continue
            self._operators[username] = {"role": _normalized_role(role)}

    def register_role(self, operator: str, role: str) -> dict[str, str]:
        name = (operator or "").strip()
        self._operators[name] = {"role": _normalized_role(role)}
        return {"operator": name, "role": self._operators[name]["role"]}

    def authenticate(self, operator: str, password: str, db: Session | None = None) -> str | None:
        if db is not None:
            return authenticate_credentials(db, operator, password)
        from ..database import SessionLocal

        session = SessionLocal()
        try:
            return authenticate_credentials(session, operator, password)
        finally:
            session.close()

    def list_operators(self) -> list[dict[str, str]]:
        return [{"operator": name, "role": data["role"]} for name, data in sorted(self._operators.items())]

    def get(self, operator: str) -> dict[str, str] | None:
        record = self._operators.get(operator)
        if record is None:
            return None
        return {"operator": operator, "role": record["role"]}

    def admin_count(self) -> int:
        return sum(1 for data in self._operators.values() if data["role"] == Role.ADMINISTRATOR.value)

    def create(self, operator: str, password: str, role: str, *, db: Session | None = None) -> dict[str, str]:
        from ..org.models import OrgUser

        name = validate_operator_name(operator)
        secret = validate_password(password)
        Role(role)
        if db is not None:
            existing = db.scalar(select(OrgUser).where(OrgUser.username == name))
            if existing is not None:
                raise ValueError("operator_exists")
            now = _utcnow()
            db.add(
                OrgUser(
                    username=name,
                    display_name=name,
                    password_hash=hash_password(secret),
                    platform_role=role,
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.flush()
        elif name in self._operators:
            raise ValueError("operator_exists")
        self._operators[name] = {"role": role}
        return {"operator": name, "role": role}

    def set_password(self, operator: str, password: str, *, db: Session | None = None) -> dict[str, str]:
        from ..org.models import OrgUser
        from .sessions import session_store

        record = self._operators.get(operator)
        secret = validate_password(password)
        hashed = hash_password(secret)
        if db is not None:
            user = db.scalar(select(OrgUser).where(OrgUser.username == operator))
            if user is None:
                raise ValueError("operator_not_found")
            user.password_hash = hashed
            user.updated_at = _utcnow()
            db.add(user)
            db.flush()
            role = _normalized_role(user.platform_role or (record["role"] if record else Role.VIEWER.value))
            self._operators[operator] = {"role": role}
            session_store.delete_for_operator(operator)
            return {"operator": operator, "role": role}
        if record is None:
            raise ValueError("operator_not_found")
        session_store.delete_for_operator(operator)
        return {"operator": operator, "role": record["role"]}

    def set_role(self, operator: str, role: str, *, db: Session | None = None) -> dict[str, str]:
        from ..org.models import OrgUser

        Role(role)
        record = self._operators.get(operator)
        if db is not None:
            user = db.scalar(select(OrgUser).where(OrgUser.username == operator))
            if user is None:
                raise ValueError("operator_not_found")
            current = _normalized_role(user.platform_role or (record["role"] if record else Role.VIEWER.value))
            if current == Role.ADMINISTRATOR.value and role != Role.ADMINISTRATOR.value and self.admin_count() <= 1:
                raise ValueError("last_admin")
            user.platform_role = role
            user.updated_at = _utcnow()
            db.add(user)
            db.flush()
            self._operators[operator] = {"role": role}
            return {"operator": operator, "role": role}
        if record is None:
            raise ValueError("operator_not_found")
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
