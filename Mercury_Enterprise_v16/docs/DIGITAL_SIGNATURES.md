# Digital Signatures

Immutable electronic signatures for maintenance certification events.

## Methods

`password` · `pin` · `pki` · `smart_card` · `biometric_ready`

- **password:** `credential` verified against the session operator password store
- **pin:** `credential` matched to an active digital stamp code for the signing employee
- **pki / smart_card / biometric_ready:** ready flags + SHA-256 canonical payload hash — IdP/HSM/card reader providers are Sprint 8+

Signer must be the employee linked to the session user (Administrator break-glass only).

## Immutability

`digital_signatures` rows have no update/delete service paths. Certification events reference signature IDs append-only.

## Permissions

`signature.create` · `certification.sign` · `certification.release` (for aircraft release)
