# Named operators for an internet-facing pilot

Demo users `operator` / `viewer` / `reviewer` share `MERCURY_AUTH_PASSWORD` and exist only when `MERCURY_SEED_DEMO=true`. Production startup **refuses** demo seed. Internet OIDC **rejects** unknown identities (`MERCURY_OIDC_AUTO_PROVISION` defaults false).

Create **named** `org_users`, bind each to the IdP subject (`sub`), then grant organization memberships.

## Break-glass local password

`POST /api/v1/org/users` still requires a unique password (≥ 12 characters). Store it in your password manager. It is for directory recovery if the IdP is down **and** you have explicitly set `MERCURY_ALLOW_PASSWORD_AUTH=true` (not a paid-internet default).

## Create a named user (admin session)

```http
POST /api/v1/org/users
{
  "username": "j.smith",
  "password": "<unique-12+-char>",
  "display_name": "Jordan Smith",
  "email": "jordan.smith@your-company.example",
  "oidc_issuer": "https://<your-idp-issuer>",
  "oidc_subject": "<idp-sub-claim>"
}
```

`oidc_issuer` must be `https://`. Issuer + subject must be unique. Response includes `oidc_bound` (never a password).

If the IdP `sub` is not known yet, create the user without OIDC fields, then bind:

```http
POST /api/v1/org/users/j.smith/oidc
{
  "oidc_issuer": "https://<your-idp-issuer>",
  "oidc_subject": "<idp-sub-claim>"
}
```

First successful SSO also binds `oidc_subject` when the user matches by email or username and the subject is still empty.

## Membership

```http
POST /api/v1/memberships
{
  "username": "j.smith",
  "organization_id": "org-aviation-east",
  "role": "Operator",
  "site_id": "site-cyul"
}
```

Membership roles are Operator, Reviewer, or Viewer — never platform Administrator. Platform admin remains the seeded/admin directory role.

## IdP console

1. Create a **confidential** client.
2. Allow redirect `https://$DOMAIN/api/v1/auth/oidc/callback`.
3. Copy issuer, client id/secret, and `jwks_uri` into server `.env` only.
4. Prefer MFA at the IdP.
5. Record each operator's `sub` from the IdP (Entra: Object ID is **not** always `sub` — use the token `sub` claim).

## Verification

1. User can SSO and land in the correct org/site.
2. East operator cannot read west resource IDs (403/404).
3. Unprovisioned IdP accounts receive 403 `Identity is not provisioned for this Mercury tenant`.
4. `/api/v1/auth/public-config` shows `oidc_enabled: true` and does not include secrets.
