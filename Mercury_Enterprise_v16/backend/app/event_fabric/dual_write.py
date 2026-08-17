"""Best-effort domain Event Framework → Enterprise Event Fabric dual-write.

Selected dotted bus events (see BUS_TO_CATALOG) are mirrored into the durable
enterprise event store. Failures are logged and never break the domain mutation.
"""

from __future__ import annotations

import logging
from typing import Any

from .catalog import BUS_TO_CATALOG

logger = logging.getLogger("mercury.event_fabric.dual_write")


def maybe_dual_write_to_fabric(
    *,
    bus_event_type: str,
    payload: dict[str, Any],
    organization_id: str,
    source: str = "mercury",
) -> None:
    """Ingest a mapped bus event into Event Fabric when org + catalog mapping exist."""
    if not organization_id or bus_event_type not in BUS_TO_CATALOG:
        return
    try:
        from ..database import SessionLocal
        from .service import EventFabricService

        db = SessionLocal()
        try:
            EventFabricService(db).ingest_bus_event(
                organization_id=organization_id,
                bus_event_type=bus_event_type,
                payload=payload,
                source=source,
            )
        finally:
            db.close()
    except Exception:
        logger.exception(
            "event fabric dual-write failed bus_event_type=%s org=%s",
            bus_event_type,
            organization_id,
        )
