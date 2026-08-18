# Serialized Parts (Program B)

Serialized / lot-tracked units live in `logistics_stock_units`.

## Tracked fields

Serial, batch, lot, TSN/TSO/CSN/CSO, current warehouse/bin (`location_id`), optional `current_aircraft_id`, condition (`serviceable|unserviceable|repair|scrap|quarantine|installed|loaned|pooled`).

## Integration with Sprint 7

Install / remove / transfer history for aircraft configuration remains on `serialized_components` / installation history. Logistics may store `serialized_component_id` when bridging a stores unit to the configuration asset.

Repair history for vendor cycles is recorded in `logistics_rotable_cycles` (see ROTABLES.md).
