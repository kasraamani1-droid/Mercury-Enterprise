"""Universal Data Fabric repository."""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from ..shared import clamp_page
from .models import (
    FabricAttachmentRef,
    FabricEntityType,
    FabricEvent,
    FabricLegalHold,
    FabricPassport,
    FabricPassportHistory,
    FabricRelationship,
    FabricRetentionPolicy,
    FabricTag,
)


class FabricRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: object) -> object:
        self.db.add(row)
        return row

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    # --- entity types ---
    def get_entity_type(self, code: str) -> FabricEntityType | None:
        return self.db.scalars(select(FabricEntityType).where(FabricEntityType.code == code)).first()

    def list_entity_types(self) -> list[FabricEntityType]:
        return list(
            self.db.scalars(
                select(FabricEntityType)
                .where(FabricEntityType.status == "active")
                .order_by(FabricEntityType.domain, FabricEntityType.code)
            ).all()
        )

    def count_entity_types(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(FabricEntityType)) or 0)

    # --- passports ---
    def get_passport(self, organization_id: str, passport_id: str) -> FabricPassport | None:
        return self.db.scalars(
            select(FabricPassport).where(
                FabricPassport.id == passport_id,
                FabricPassport.organization_id == organization_id,
                FabricPassport.deleted_at.is_(None),
            )
        ).first()

    def get_passport_by_entity(
        self, organization_id: str, entity_type: str, entity_id: str
    ) -> FabricPassport | None:
        return self.db.scalars(
            select(FabricPassport).where(
                FabricPassport.organization_id == organization_id,
                FabricPassport.entity_type == entity_type,
                FabricPassport.entity_id == entity_id,
                FabricPassport.deleted_at.is_(None),
            )
        ).first()

    def list_passports(
        self,
        *,
        organization_id: str,
        entity_type: str | None = None,
        lifecycle: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FabricPassport]:
        lim, off = clamp_page(limit, offset)
        stmt = select(FabricPassport).where(
            FabricPassport.organization_id == organization_id,
            FabricPassport.deleted_at.is_(None),
        )
        if entity_type:
            stmt = stmt.where(FabricPassport.entity_type == entity_type)
        if lifecycle:
            stmt = stmt.where(FabricPassport.lifecycle == lifecycle)
        return list(
            self.db.scalars(stmt.order_by(FabricPassport.modified_at.desc()).limit(lim).offset(off)).all()
        )

    def count_passports(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(FabricPassport)
                .where(
                    FabricPassport.organization_id == organization_id,
                    FabricPassport.deleted_at.is_(None),
                )
            )
            or 0
        )

    def search_passports(
        self, *, organization_id: str, query: str, limit: int = 50, offset: int = 0
    ) -> list[FabricPassport]:
        lim, off = clamp_page(limit, offset)
        q = f"%{query.strip()}%"
        return list(
            self.db.scalars(
                select(FabricPassport)
                .where(
                    FabricPassport.organization_id == organization_id,
                    FabricPassport.deleted_at.is_(None),
                    or_(
                        FabricPassport.display_name.ilike(q),
                        FabricPassport.passport_number.ilike(q),
                        FabricPassport.entity_id.ilike(q),
                        FabricPassport.tags_json.ilike(q),
                        FabricPassport.entity_type.ilike(q),
                    ),
                )
                .order_by(FabricPassport.modified_at.desc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    def list_passport_history(self, passport_id: str, limit: int = 100) -> list[FabricPassportHistory]:
        lim, _ = clamp_page(limit, 0)
        return list(
            self.db.scalars(
                select(FabricPassportHistory)
                .where(FabricPassportHistory.passport_id == passport_id)
                .order_by(FabricPassportHistory.version.desc())
                .limit(lim)
            ).all()
        )

    # --- relationships ---
    def list_relationships(
        self,
        *,
        organization_id: str,
        passport_id: str | None = None,
        relationship_type: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[FabricRelationship]:
        lim, off = clamp_page(limit, offset)
        stmt: Select[tuple[FabricRelationship]] = select(FabricRelationship).where(
            FabricRelationship.organization_id == organization_id,
            FabricRelationship.deleted_at.is_(None),
            FabricRelationship.status == "active",
        )
        if passport_id:
            stmt = stmt.where(
                or_(
                    FabricRelationship.from_passport_id == passport_id,
                    FabricRelationship.to_passport_id == passport_id,
                )
            )
        if relationship_type:
            stmt = stmt.where(FabricRelationship.relationship_type == relationship_type)
        return list(
            self.db.scalars(stmt.order_by(FabricRelationship.created_at.desc()).limit(lim).offset(off)).all()
        )

    def count_relationships(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(FabricRelationship)
                .where(
                    FabricRelationship.organization_id == organization_id,
                    FabricRelationship.deleted_at.is_(None),
                )
            )
            or 0
        )

    # --- events ---
    def list_events(
        self,
        *,
        organization_id: str,
        passport_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FabricEvent]:
        lim, off = clamp_page(limit, offset)
        stmt = select(FabricEvent).where(FabricEvent.organization_id == organization_id)
        if passport_id:
            stmt = stmt.where(FabricEvent.passport_id == passport_id)
        if event_type:
            stmt = stmt.where(FabricEvent.event_type == event_type)
        return list(
            self.db.scalars(stmt.order_by(FabricEvent.occurred_at.desc()).limit(lim).offset(off)).all()
        )

    def count_events(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(FabricEvent)
                .where(FabricEvent.organization_id == organization_id)
            )
            or 0
        )

    # --- tags / attachments ---
    def list_tags(self, organization_id: str, passport_id: str) -> list[FabricTag]:
        return list(
            self.db.scalars(
                select(FabricTag).where(
                    FabricTag.organization_id == organization_id,
                    FabricTag.passport_id == passport_id,
                )
            ).all()
        )

    def count_tags(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(FabricTag)
                .where(FabricTag.organization_id == organization_id)
            )
            or 0
        )

    def list_attachments(self, organization_id: str, passport_id: str) -> list[FabricAttachmentRef]:
        return list(
            self.db.scalars(
                select(FabricAttachmentRef).where(
                    FabricAttachmentRef.organization_id == organization_id,
                    FabricAttachmentRef.passport_id == passport_id,
                    FabricAttachmentRef.deleted_at.is_(None),
                )
            ).all()
        )

    # --- governance ---
    def list_retention_policies(self, organization_id: str) -> list[FabricRetentionPolicy]:
        return list(
            self.db.scalars(
                select(FabricRetentionPolicy).where(
                    or_(
                        FabricRetentionPolicy.organization_id == organization_id,
                        FabricRetentionPolicy.organization_id == "*",
                    ),
                    FabricRetentionPolicy.status == "active",
                )
            ).all()
        )

    def count_retention_policies(self, organization_id: str) -> int:
        return len(self.list_retention_policies(organization_id))

    def list_legal_holds(
        self, organization_id: str, *, active_only: bool = True
    ) -> list[FabricLegalHold]:
        stmt = select(FabricLegalHold).where(FabricLegalHold.organization_id == organization_id)
        if active_only:
            stmt = stmt.where(FabricLegalHold.status == "active")
        return list(self.db.scalars(stmt.order_by(FabricLegalHold.placed_at.desc())).all())

    def count_legal_holds(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(FabricLegalHold)
                .where(
                    FabricLegalHold.organization_id == organization_id,
                    FabricLegalHold.status == "active",
                )
            )
            or 0
        )

    def get_legal_hold(self, organization_id: str, hold_id: str) -> FabricLegalHold | None:
        return self.db.scalars(
            select(FabricLegalHold).where(
                FabricLegalHold.id == hold_id,
                FabricLegalHold.organization_id == organization_id,
            )
        ).first()
