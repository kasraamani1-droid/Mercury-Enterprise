"""OIDC authorization-code + PKCE integration boundary.

Full IdP activation requires operator-supplied issuer, client id/secret, and
redirect URI. Missing production OIDC config fails closed. No fake credentials.

ID tokens are signature-verified via JWKS (RS256/ES256). PKCE state lives in
Redis for production OIDC (no in-memory fallback).
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import settings
from ..org.models import OrgUser
from .jwks import JwksCache, verify_id_token
from .oidc_pending import PENDING_TTL_SECONDS, MemoryPendingStore, PendingStore, build_pending_store
from .operators import validate_operator_name
from .redact import redact_text

logger = logging.getLogger("mercury.security.oidc")

HTTP_TIMEOUT_SECONDS = 10

HttpGet = Callable[[str, dict[str, str] | None], dict[str, Any]]
HttpPostForm = Callable[[str, dict[str, str], dict[str, str] | None], dict[str, Any]]


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def generate_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def public_auth_config() -> dict[str, Any]:
    """Unauthenticated runtime flags. No secrets."""
    configured = settings.oidc_is_configured
    return {
        "environment": settings.environment,
        "auth_mode": settings.auth_mode,
        "password_login_enabled": settings.password_login_enabled,
        "oidc_enabled": configured,
        "oidc_login_path": "/api/v1/auth/oidc/login" if configured else None,
        "sim_workspaces_visible": settings.sim_workspaces_visible,
        "https_enabled": settings.https_enabled,
        "lan_port_3000_is_not_production": True,
    }


def _http_get(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC provider request failed") from exc
    except Exception as exc:
        logger.warning("OIDC HTTP GET failed url=%s error=%s", url.split("?")[0], type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC provider unreachable") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC provider returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC provider returned invalid JSON")
    return payload


def _http_post_form(url: str, fields: dict[str, str], headers: dict[str, str] | None = None) -> dict[str, Any]:
    body = urllib.parse.urlencode(fields).encode("utf-8")
    merged = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
    if headers:
        merged.update(headers)
    request = urllib.request.Request(url, data=body, headers=merged, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC token exchange failed") from exc
    except Exception as exc:
        logger.warning("OIDC HTTP POST failed url=%s error=%s", url.split("?")[0], type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC provider unreachable") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC provider returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC provider returned invalid JSON")
    return payload


class OidcService:
    def __init__(
        self,
        *,
        http_get: HttpGet | None = None,
        http_post_form: HttpPostForm | None = None,
        pending_store: PendingStore | None = None,
    ) -> None:
        self._http_get = http_get or _http_get
        self._http_post_form = http_post_form or _http_post_form
        self._pending: PendingStore | None = pending_store
        self._discovery: dict[str, Any] | None = None
        ttl = int(getattr(settings, "oidc_jwks_cache_seconds", 300) or 300)
        self._jwks = JwksCache(self._http_get, ttl_seconds=ttl)

    def _store(self) -> PendingStore:
        if self._pending is not None:
            return self._pending
        self._pending = build_pending_store()
        return self._pending

    def reset_pending_for_tests(self) -> None:
        if self._pending is None:
            self._pending = MemoryPendingStore()
        self._pending.clear()

    def require_configured(self) -> None:
        if not settings.oidc_is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC is not configured",
            )

    def discover(self) -> dict[str, Any]:
        if self._discovery is not None:
            return self._discovery
        issuer = settings.oidc_issuer.rstrip("/")
        url = settings.oidc_discovery_url or f"{issuer}/.well-known/openid-configuration"
        document = self._http_get(url, {"Accept": "application/json"})
        discovered_issuer = str(document.get("issuer") or "").rstrip("/")
        if discovered_issuer and discovered_issuer != issuer:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OIDC issuer mismatch")
        for key in ("authorization_endpoint", "token_endpoint", "userinfo_endpoint", "jwks_uri"):
            if not str(document.get(key) or "").strip():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="OIDC discovery document is incomplete",
                )
        self._discovery = document
        return document

    def start_authorization(self) -> str:
        self.require_configured()
        document = self.discover()
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        verifier, challenge = generate_pkce()
        self._store().save(
            state,
            {
                "code_verifier": verifier,
                "nonce": nonce,
            },
            ttl_seconds=PENDING_TTL_SECONDS,
        )
        params = {
            "response_type": "code",
            "client_id": settings.oidc_client_id,
            "redirect_uri": settings.oidc_redirect_uri,
            "scope": settings.oidc_scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        endpoint = str(document["authorization_endpoint"])
        return f"{endpoint}?{urllib.parse.urlencode(params)}"

    def complete(self, *, code: str, state: str) -> dict[str, str]:
        self.require_configured()
        code = (code or "").strip()
        state = (state or "").strip()
        if not code or not state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OIDC callback")
        pending = self._store().consume(state)
        if pending is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OIDC state")
        verifier = str(pending.get("code_verifier") or "")
        nonce = str(pending.get("nonce") or "")
        if not verifier:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired OIDC state")
        document = self.discover()
        token_payload = self._http_post_form(
            str(document["token_endpoint"]),
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oidc_redirect_uri,
                "client_id": settings.oidc_client_id,
                "client_secret": settings.oidc_client_secret,
                "code_verifier": verifier,
            },
            None,
        )
        access_token = str(token_payload.get("access_token") or "").strip()
        id_token = str(token_payload.get("id_token") or "").strip()
        if not access_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC token exchange failed")
        if not id_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC id_token missing")
        jwks_uri = str(document.get("jwks_uri") or "").strip()
        configured_jwks = str(getattr(settings, "oidc_jwks_uri", "") or "").strip()
        if configured_jwks and configured_jwks.rstrip("/") != jwks_uri.rstrip("/"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC JWKS URI mismatch",
            )
        if not jwks_uri:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OIDC discovery document is incomplete",
            )
        jwks = self._jwks.jwks_for_token(jwks_uri, id_token)
        id_claims = verify_id_token(
            id_token,
            issuer=settings.oidc_issuer.rstrip("/"),
            audience=settings.oidc_client_id,
            jwks=jwks,
            nonce=nonce or None,
            leeway_seconds=int(getattr(settings, "oidc_clock_skew_seconds", 60) or 60),
        )
        claims = self._http_get(
            str(document["userinfo_endpoint"]),
            {"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        subject = str(claims.get("sub") or "").strip()
        id_subject = str(id_claims.get("sub") or "").strip()
        if not subject or not id_subject or subject != id_subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OIDC identity is incomplete")
        username_claim = str(
            claims.get(settings.oidc_username_claim)
            or claims.get("preferred_username")
            or claims.get("email")
            or ""
        ).strip()
        email = str(claims.get("email") or "").strip().lower()
        return {
            "subject": subject,
            "issuer": settings.oidc_issuer.rstrip("/"),
            "username_claim": username_claim,
            "email": email,
            "name": str(claims.get("name") or username_claim or subject),
        }

    def resolve_directory_user(self, db: Session, claims: dict[str, str]) -> OrgUser:
        from ..org.repository import OrgRepository

        repo = OrgRepository(db)
        issuer = claims["issuer"]
        subject = claims["subject"]
        user = repo.get_user_by_oidc(issuer, subject)
        if user is None and claims.get("email"):
            user = repo.get_user_by_email(claims["email"])
        if user is None and claims.get("username_claim"):
            try:
                candidate = validate_operator_name(claims["username_claim"].split("@", 1)[0])
            except ValueError:
                candidate = ""
            if candidate:
                user = repo.get_user_by_username(candidate)
        if user is None:
            if not settings.oidc_auto_provision:
                logger.info("OIDC login denied: identity is not provisioned")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Identity is not provisioned for this Mercury tenant",
                )
            user = self._provision(repo, claims)
        if user.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
        if not (user.oidc_subject or "").strip():
            user.oidc_issuer = issuer
            user.oidc_subject = subject
            user.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.add(user)
            db.flush()
        return user

    def _provision(self, repo: Any, claims: dict[str, str]) -> OrgUser:
        from .authorization import Role

        raw = (claims.get("username_claim") or f"oidc-{claims['subject'][:12]}").split("@", 1)[0]
        try:
            username = validate_operator_name(raw)
        except ValueError:
            username = validate_operator_name(f"oidc{secrets.token_hex(4)}")
        existing = repo.get_user_by_username(username)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        user = OrgUser(
            username=username,
            display_name=claims.get("name") or username,
            email=claims.get("email") or "",
            password_hash="",
            platform_role=Role.VIEWER.value,
            status="active",
            oidc_issuer=claims["issuer"],
            oidc_subject=claims["subject"],
            created_at=now,
            updated_at=now,
        )
        repo.add_user(user)
        repo.flush()
        logger.info("OIDC auto-provisioned directory user username=%s", username)
        return user


oidc_service = OidcService()


def reset_pending_for_tests() -> None:
    oidc_service.reset_pending_for_tests()


def log_oidc_event(message: str, **fields: str) -> None:
    extras = " ".join(f"{key}={redact_text(value)}" for key, value in fields.items())
    logger.info("%s %s", message, extras)
