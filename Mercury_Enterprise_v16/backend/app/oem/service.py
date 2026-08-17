"""OEM manufacturer registry service."""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..platform.audit_engine import AuditEngine
from ..shared import ActorContext, clamp_page
from .models import OemManufacturer

SEED_OEMS = [
    ("bombardier", "Bombardier", "airframe", "CA"),
    ("airbus", "Airbus", "airframe", "EU"),
    ("boeing", "Boeing", "airframe", "US"),
    ("embraer", "Embraer", "airframe", "BR"),
    ("atr", "ATR", "airframe", "FR"),
    ("textron", "Textron Aviation", "airframe", "US"),
    ("pratt_whitney", "Pratt & Whitney", "engine", "US"),
    ("ge_aerospace", "GE Aerospace", "engine", "US"),
    ("rolls_royce", "Rolls-Royce", "engine", "UK"),
    ("honeywell", "Honeywell", "avionics", "US"),
    ("safran", "Safran", "systems", "FR"),
    ("collins", "Collins Aerospace", "avionics", "US"),
    ("thales", "Thales", "avionics", "FR"),
    ("garmin", "Garmin", "avionics", "US"),
]


class OemService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditEngine(db)

    def seed(self) -> int:
        created = 0
        for code, name, category, country in SEED_OEMS:
            if self.db.scalars(select(OemManufacturer).where(OemManufacturer.code == code)).first():
                continue
            self.db.add(
                OemManufacturer(
                    code=code,
                    name=name,
                    category=category,
                    country_code=country,
                    portal_status="ready",
                    capabilities_json=json.dumps(
                        ["products", "publications", "service_bulletins", "training", "marketplace", "support"]
                    ),
                    ai_metadata_json=json.dumps(
                        {"domain": "oem", "manufacturer": code, "searchable": True, "embedding_ready": False}
                    ),
                )
            )
            created += 1
        if created:
            self.db.commit()
        return created

    def list(self, *, category: str | None = None, limit: int = 100, offset: int = 0) -> list[OemManufacturer]:
        lim, off = clamp_page(limit, offset)
        stmt = select(OemManufacturer).where(
            OemManufacturer.deleted_at.is_(None), OemManufacturer.status == "active"
        )
        if category:
            stmt = stmt.where(OemManufacturer.category == category)
        return list(self.db.scalars(stmt.order_by(OemManufacturer.name).limit(lim).offset(off)).all())

    def get(self, code: str) -> OemManufacturer:
        row = self.db.scalars(
            select(OemManufacturer).where(
                OemManufacturer.code == code, OemManufacturer.deleted_at.is_(None)
            )
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Manufacturer not found")
        return row
