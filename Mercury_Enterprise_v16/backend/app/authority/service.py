"""Authority registry service — readiness only; no regulatory claims."""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..platform.audit_engine import AuditEngine
from ..shared import clamp_page
from .models import AuthorityBody

SEED_AUTHORITIES = [
    ("tc", "Transport Canada", "Canada"),
    ("faa", "Federal Aviation Administration", "United States"),
    ("easa", "European Union Aviation Safety Agency", "European Union"),
    ("caa_uk", "Civil Aviation Authority (UK)", "United Kingdom"),
    ("anac", "ANAC", "Brazil"),
    ("casa", "CASA", "Australia"),
    ("icao", "International Civil Aviation Organization", "International"),
]


class AuthorityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit = AuditEngine(db)

    def seed(self) -> int:
        created = 0
        for code, name, region in SEED_AUTHORITIES:
            if self.db.scalars(select(AuthorityBody).where(AuthorityBody.code == code)).first():
                continue
            self.db.add(
                AuthorityBody(
                    code=code,
                    name=name,
                    region=region,
                    portal_status="ready",
                    ai_metadata_json=json.dumps(
                        {
                            "domain": "authority",
                            "authority": code,
                            "searchable": True,
                            "embedding_ready": False,
                            "regulatory_claim": False,
                        }
                    ),
                )
            )
            created += 1
        if created:
            self.db.commit()
        return created

    def list(self, *, limit: int = 100, offset: int = 0) -> list[AuthorityBody]:
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(AuthorityBody)
                .where(AuthorityBody.deleted_at.is_(None), AuthorityBody.status == "active")
                .order_by(AuthorityBody.name)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def get(self, code: str) -> AuthorityBody:
        row = self.db.scalars(
            select(AuthorityBody).where(AuthorityBody.code == code, AuthorityBody.deleted_at.is_(None))
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Authority not found")
        return row
