"""OIDC ID-token verification via JWKS (RS256 / ES256).

Fail closed: alg=none, missing/mismatched kid, unknown algorithms, and
unavailable JWKS documents are rejected. Never uses HMAC/client-secret keys.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

import jwt
from fastapi import HTTPException, status
from jwt.algorithms import ECAlgorithm, RSAAlgorithm
from jwt.exceptions import InvalidTokenError

logger = logging.getLogger("mercury.security.jwks")

ALLOWED_ALGS = frozenset({"RS256", "ES256"})
HttpGet = Callable[[str, dict[str, str] | None], dict[str, Any]]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _unavailable(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


def parse_unverified_header(token: str) -> dict[str, Any]:
    token = (token or "").strip()
    parts = token.split(".")
    if len(parts) != 3:
        raise _unauthorized("OIDC id_token is invalid")
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise _unauthorized("OIDC id_token is invalid") from exc
    if not isinstance(header, dict):
        raise _unauthorized("OIDC id_token is invalid")
    if header.get("crit"):
        raise _unauthorized("OIDC id_token is invalid")
    alg = str(header.get("alg") or "").strip()
    if not alg or alg.lower() == "none":
        raise _unauthorized("OIDC id_token algorithm is not allowed")
    if alg not in ALLOWED_ALGS:
        raise _unauthorized("OIDC id_token algorithm is not allowed")
    kid = str(header.get("kid") or "").strip()
    if not kid:
        raise _unauthorized("OIDC id_token is missing kid")
    return header


def _jwk_expired(jwk: dict[str, Any], now_ts: int) -> bool:
    raw_exp = jwk.get("exp")
    if raw_exp is None:
        return False
    try:
        exp = int(raw_exp)
    except (TypeError, ValueError):
        return True
    return exp <= now_ts


def select_jwk(jwks: dict[str, Any], *, kid: str, alg: str, now_ts: int | None = None) -> dict[str, Any]:
    if not isinstance(jwks, dict):
        raise _unavailable("OIDC JWKS unavailable")
    keys = jwks.get("keys")
    if not isinstance(keys, list) or not keys:
        raise _unavailable("OIDC JWKS unavailable")
    now = int(time.time() if now_ts is None else now_ts)
    for item in keys:
        if not isinstance(item, dict):
            continue
        if str(item.get("kid") or "").strip() != kid:
            continue
        use = str(item.get("use") or "").strip()
        if use and use != "sig":
            continue
        jwk_alg = str(item.get("alg") or "").strip()
        if jwk_alg and jwk_alg != alg:
            continue
        if _jwk_expired(item, now):
            raise _unauthorized("OIDC signing key is expired")
        kty = str(item.get("kty") or "").strip()
        if alg.startswith("RS") and kty != "RSA":
            raise _unauthorized("OIDC signing key is invalid")
        if alg.startswith("ES") and kty != "EC":
            raise _unauthorized("OIDC signing key is invalid")
        return item
    raise _unauthorized("OIDC signing key not found")


def public_key_from_jwk(jwk: dict[str, Any], alg: str) -> Any:
    try:
        if alg.startswith("RS"):
            return RSAAlgorithm.from_jwk(jwk)
        if alg.startswith("ES"):
            return ECAlgorithm.from_jwk(jwk)
    except Exception as exc:
        raise _unauthorized("OIDC signing key is invalid") from exc
    raise _unauthorized("OIDC signing key is invalid")


def verify_id_token(
    token: str,
    *,
    issuer: str,
    audience: str,
    jwks: dict[str, Any],
    nonce: str | None = None,
    leeway_seconds: int = 60,
) -> dict[str, Any]:
    """Verify ID-token signature and standard claims. Fail closed."""
    header = parse_unverified_header(token)
    alg = str(header["alg"])
    kid = str(header["kid"])
    expected_issuer = (issuer or "").rstrip("/")
    expected_audience = (audience or "").strip()
    if not expected_issuer or not expected_audience:
        raise _unauthorized("OIDC id_token is invalid")
    jwk = select_jwk(jwks, kid=kid, alg=alg)
    key = public_key_from_jwk(jwk, alg)
    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=[alg],
            issuer=expected_issuer,
            audience=expected_audience,
            leeway=max(0, int(leeway_seconds)),
            options={
                "require": ["exp", "iat", "iss", "aud"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
            },
        )
    except InvalidTokenError as exc:
        logger.info("OIDC id_token rejected: %s", type(exc).__name__)
        raise _unauthorized("OIDC id_token is invalid") from exc
    except Exception as exc:
        logger.info("OIDC id_token rejected: %s", type(exc).__name__)
        raise _unauthorized("OIDC id_token is invalid") from exc
    if not isinstance(claims, dict):
        raise _unauthorized("OIDC id_token is invalid")
    token_iss = str(claims.get("iss") or "").rstrip("/")
    if token_iss != expected_issuer:
        raise _unauthorized("OIDC id_token is invalid")
    expected_nonce = (nonce or "").strip()
    if expected_nonce:
        token_nonce = str(claims.get("nonce") or "").strip()
        if token_nonce != expected_nonce:
            raise _unauthorized("OIDC id_token is invalid")
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise _unauthorized("OIDC identity is incomplete")
    return claims


class JwksCache:
    """In-process JWKS cache keyed by URI, with TTL and one forced refresh on kid miss."""

    def __init__(self, http_get: HttpGet, ttl_seconds: int = 300) -> None:
        self._http_get = http_get
        self._ttl = max(1, int(ttl_seconds))
        self._lock = threading.Lock()
        self._uri = ""
        self._document: dict[str, Any] | None = None
        self._expires_at = 0.0

    def fetch(self, jwks_uri: str, *, force: bool = False) -> dict[str, Any]:
        uri = (jwks_uri or "").strip()
        if not uri:
            raise _unavailable("OIDC JWKS unavailable")
        now = time.monotonic()
        with self._lock:
            if (
                not force
                and self._document is not None
                and self._uri == uri
                and now < self._expires_at
            ):
                return self._document
        try:
            document = self._http_get(uri, {"Accept": "application/json"})
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("JWKS fetch failed uri=%s error=%s", uri.split("?")[0], type(exc).__name__)
            raise _unavailable("OIDC JWKS unavailable") from exc
        if not isinstance(document, dict) or not isinstance(document.get("keys"), list):
            raise _unavailable("OIDC JWKS unavailable")
        with self._lock:
            self._uri = uri
            self._document = document
            self._expires_at = time.monotonic() + self._ttl
        return document

    def jwks_for_token(self, jwks_uri: str, token: str) -> dict[str, Any]:
        header = parse_unverified_header(token)
        kid = str(header["kid"])
        alg = str(header["alg"])
        document = self.fetch(jwks_uri)
        try:
            select_jwk(document, kid=kid, alg=alg)
            return document
        except HTTPException as exc:
            if exc.status_code != status.HTTP_401_UNAUTHORIZED:
                raise
        document = self.fetch(jwks_uri, force=True)
        select_jwk(document, kid=kid, alg=alg)
        return document
