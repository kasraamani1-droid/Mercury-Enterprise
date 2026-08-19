"""Ephemeral RSA/EC keys for OIDC tests. Never used as production secrets."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

ISSUER = "https://idp.example.test"
AUDIENCE = "mercury-client"
SUBJECT = "oidc-operator-1"
KID = "test-rsa-kid-1"
EC_KID = "test-ec-kid-1"


def _as_jwk_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    return json.loads(raw)


def generate_rsa_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


def generate_ec_pair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


def rsa_jwk(public_key, kid: str = KID) -> dict[str, Any]:
    jwk = _as_jwk_dict(RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "RS256"
    return jwk


def ec_jwk(public_key, kid: str = EC_KID) -> dict[str, Any]:
    jwk = _as_jwk_dict(ECAlgorithm.to_jwk(public_key))
    jwk["kid"] = kid
    jwk["use"] = "sig"
    jwk["alg"] = "ES256"
    return jwk


def default_claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": SUBJECT,
        "exp": now + 3600,
        "iat": now,
        "nbf": now,
        "nonce": "test-nonce",
    }
    claims.update(overrides)
    return claims


def sign_id_token(private_key, *, kid: str, alg: str = "RS256", claims: dict[str, Any] | None = None) -> str:
    payload = claims or default_claims()
    return jwt.encode(payload, private_key, algorithm=alg, headers={"kid": kid, "typ": "JWT"})


def unsigned_alg_none_token(claims: dict[str, Any] | None = None) -> str:
    payload = claims or default_claims()
    header = {"alg": "none", "typ": "JWT", "kid": KID}

    def b64(obj: dict[str, Any]) -> str:
        raw = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{b64(header)}.{b64(payload)}."


def jwks_document(*keys: dict[str, Any]) -> dict[str, Any]:
    return {"keys": list(keys)}
