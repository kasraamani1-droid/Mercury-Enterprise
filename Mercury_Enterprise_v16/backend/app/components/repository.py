from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from .models import (
    AlternatePart,
    AtaChapter,
    ComponentCatalogItem,
    ComponentInstallationHistory,
    SerializedComponent,
)


class ComponentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ATA
    def list_ata_chapters(self, *, active_only: bool = True) -> list[AtaChapter]:
        stmt = select(AtaChapter).order_by(AtaChapter.chapter_number, AtaChapter.subchapter)
        if active_only:
            stmt = stmt.where(AtaChapter.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_ata_chapter(self, chapter_id: str) -> AtaChapter | None:
        return self.db.get(AtaChapter, chapter_id)

    def get_ata_by_numbers(self, chapter_number: str, subchapter: str) -> AtaChapter | None:
        return self.db.scalar(
            select(AtaChapter).where(
                AtaChapter.chapter_number == chapter_number,
                AtaChapter.subchapter == subchapter,
            )
        )

    def add_ata_chapter(self, row: AtaChapter) -> AtaChapter:
        self.db.add(row)
        return row

    # Catalog
    def list_catalog(self, *, ata_chapter_id: str | None = None, component_type: str | None = None, active_only: bool = True) -> list[ComponentCatalogItem]:
        stmt = select(ComponentCatalogItem).order_by(ComponentCatalogItem.part_number)
        if ata_chapter_id:
            stmt = stmt.where(ComponentCatalogItem.ata_chapter_id == ata_chapter_id)
        if component_type:
            stmt = stmt.where(ComponentCatalogItem.component_type == component_type)
        if active_only:
            stmt = stmt.where(ComponentCatalogItem.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_catalog_item(self, item_id: str) -> ComponentCatalogItem | None:
        return self.db.get(ComponentCatalogItem, item_id)

    def get_catalog_by_part_number(self, part_number: str) -> ComponentCatalogItem | None:
        return self.db.scalar(
            select(ComponentCatalogItem).where(ComponentCatalogItem.part_number == part_number.upper())
        )

    def add_catalog_item(self, row: ComponentCatalogItem) -> ComponentCatalogItem:
        self.db.add(row)
        return row

    def list_alternates(self, catalog_item_id: str) -> list[AlternatePart]:
        return list(
            self.db.scalars(
                select(AlternatePart).where(
                    AlternatePart.catalog_item_id == catalog_item_id,
                    AlternatePart.status == "active",
                )
            ).all()
        )

    def get_alternate_pair(self, catalog_item_id: str, alternate_catalog_item_id: str) -> AlternatePart | None:
        return self.db.scalar(
            select(AlternatePart).where(
                AlternatePart.catalog_item_id == catalog_item_id,
                AlternatePart.alternate_catalog_item_id == alternate_catalog_item_id,
            )
        )

    def add_alternate(self, row: AlternatePart) -> AlternatePart:
        self.db.add(row)
        return row

    # Serialized components
    def list_components(
        self,
        *,
        organization_id: str,
        aircraft_id: str | None = None,
        component_status: str | None = None,
        catalog_item_id: str | None = None,
        active_only: bool = True,
        with_catalog: bool = False,
    ) -> list[SerializedComponent]:
        stmt = (
            select(SerializedComponent)
            .where(SerializedComponent.organization_id == organization_id)
            .order_by(SerializedComponent.serial_number)
        )
        if with_catalog:
            stmt = stmt.options(joinedload(SerializedComponent.catalog_item))
        if aircraft_id:
            stmt = stmt.where(SerializedComponent.current_aircraft_id == aircraft_id)
        if component_status:
            stmt = stmt.where(SerializedComponent.component_status == component_status)
        if catalog_item_id:
            stmt = stmt.where(SerializedComponent.catalog_item_id == catalog_item_id)
        if active_only:
            stmt = stmt.where(SerializedComponent.status == "active")
        return list(self.db.scalars(stmt).unique().all())

    def get_component(
        self,
        component_id: str,
        *,
        with_catalog: bool = False,
        with_history: bool = False,
        for_update: bool = False,
    ) -> SerializedComponent | None:
        stmt = select(SerializedComponent).where(SerializedComponent.id == component_id)
        if for_update:
            # Row lock for install/remove race safety (honored on Postgres; SQLite relies on txn + unique).
            stmt = stmt.with_for_update()
        if with_catalog:
            stmt = stmt.options(joinedload(SerializedComponent.catalog_item))
        if with_history:
            stmt = stmt.options(selectinload(SerializedComponent.history))
        return self.db.scalars(stmt).unique().first()

    def get_by_org_serial(self, organization_id: str, serial_number: str) -> SerializedComponent | None:
        return self.db.scalar(
            select(SerializedComponent).where(
                SerializedComponent.organization_id == organization_id,
                SerializedComponent.serial_number == serial_number.upper(),
            )
        )

    def get_installed_at_position(self, aircraft_id: str, position: str) -> SerializedComponent | None:
        return self.db.scalar(
            select(SerializedComponent).where(
                SerializedComponent.current_aircraft_id == aircraft_id,
                SerializedComponent.installation_position == position.upper(),
                SerializedComponent.component_status == "installed",
                SerializedComponent.status == "active",
            )
        )

    def add_component(self, row: SerializedComponent) -> SerializedComponent:
        self.db.add(row)
        return row

    def list_history(
        self,
        *,
        organization_id: str,
        component_id: str | None = None,
        aircraft_id: str | None = None,
        limit: int = 200,
    ) -> list[ComponentInstallationHistory]:
        stmt = (
            select(ComponentInstallationHistory)
            .where(ComponentInstallationHistory.organization_id == organization_id)
            .order_by(ComponentInstallationHistory.occurred_at.desc())
            .limit(max(1, min(limit, 500)))
        )
        if component_id:
            stmt = stmt.where(ComponentInstallationHistory.component_id == component_id)
        if aircraft_id:
            stmt = stmt.where(ComponentInstallationHistory.aircraft_id == aircraft_id)
        return list(self.db.scalars(stmt).all())

    def add_history(self, row: ComponentInstallationHistory) -> ComponentInstallationHistory:
        self.db.add(row)
        return row

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    def flush(self) -> None:
        self.db.flush()
