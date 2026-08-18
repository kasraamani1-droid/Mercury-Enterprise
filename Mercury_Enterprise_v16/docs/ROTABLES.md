# Rotables (Program B)

Rotable support on stock units and dedicated cycles.

## Capabilities

- Repair cycle / core return / exchange / loan / rental / pool / warranty
- Repair vendor link
- Life-limited flags on part master (`is_life_limited`)
- Pool / loan / rental flags on stock units
- Warranty expiry on units

## API

- `GET/POST /api/v1/logistics/rotable-cycles`
- `POST /api/v1/logistics/rotable-cycles/{id}/close`
