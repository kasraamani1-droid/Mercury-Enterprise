# Security Baseline

Included:
- explicit CORS origins
- optional API key for write endpoints
- request IDs and generic 500 responses
- security headers in NGINX
- non-root external exposure through NGINX
- environment-based secrets/configuration

Required before real deployment:
- OIDC/SSO with MFA
- role/attribute-based authorization enforced server-side
- managed secrets and certificate rotation
- encrypted evidence/object storage
- immutable and signed audit logs
- rate limiting, WAF, IDS/IPS, segmentation, and egress controls
- SAST/DAST/dependency/container scanning
- privacy impact assessment and retention rules
- incident-response and disaster-recovery exercises
- aviation/security regulatory review
