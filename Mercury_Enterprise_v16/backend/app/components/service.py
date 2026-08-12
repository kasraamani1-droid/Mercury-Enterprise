from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..fleet.repository import FleetRepository
from ..org.service import OrganizationService
from .models import (
    AtaChapter,
    ComponentCatalogItem,
    ComponentInstallationHistory,
    SerializedComponent,
)
from .repository import ComponentRepository
from .schemas import (
    AircraftConfigurationItem,
    AircraftConfigurationOut,
    AtaChapterCreate,
    AtaChapterOut,
    CatalogItemCreate,
    CatalogItemOut,
    HistoryOut,
    InstallRequest,
    LifeLimitUpdate,
    RemoveRequest,
    SerializedComponentCreate,
    SerializedComponentOut,
    TimeCycleUpdate,
    TransferRequest,
)

logger = logging.getLogger("mercury.components")

MAJOR_ASSEMBLY_TYPES = frozenset({"engine", "apu", "landing_gear", "propeller", "general", "avionics", "structure"})
COMPONENT_STATUSES = frozenset({"installed", "stores", "maintenance", "retired", "quarantine"})
DESTINATION_STATUSES = frozenset({"stores", "maintenance", "retired", "quarantine"})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hours(value: Decimal | float | int | str | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _truthy(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}


def _recompute_remaining(component: SerializedComponent) -> None:
    if component.hour_limit is not None:
        component.remaining_hours = _hours(component.hour_limit) - _hours(component.tsn_hours)
    if component.cycle_limit is not None:
        component.remaining_cycles = int(component.cycle_limit) - int(component.csn_cycles)


class ComponentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = ComponentRepository(db)
        self.org = OrganizationService(db)
        self.fleet = FleetRepository(db)

    def ensure_seed_data(self) -> None:
        pending = False
        if not self.repo.list_ata_chapters(active_only=False):
            for chapter, sub, title, desc in (
                ("32", "00", "Landing Gear", "Landing gear general"),
                ("49", "00", "Airborne Auxiliary Power", "APU general"),
                ("71", "00", "Power Plant", "Engine / power plant general"),
                ("72", "00", "Engine", "Engine internals"),
            ):
                self.repo.add_ata_chapter(
                    AtaChapter(
                        id=f"ata-{chapter}-{sub}",
                        chapter_number=chapter,
                        subchapter=sub,
                        title=title,
                        description=desc,
                        created_at=_utcnow(),
                        updated_at=_utcnow(),
                    )
                )
            pending = True

        if not self.repo.list_catalog(active_only=False):
            mfr_cfm = self.fleet.get_manufacturer_by_code("BOEING")  # OEM placeholder optional
            # Prefer Airbus/Boeing already seeded; OEM name free-text is enough.
            items = [
                ("CFM56-5B4", "CFM International", "ata-71-00", "engine", True, True, Decimal("30000.00"), 20000),
                ("APS3200", "Honeywell", "ata-49-00", "apu", True, True, Decimal("10000.00"), 15000),
                ("LG-NLG-320", "Safran", "ata-32-00", "landing_gear", True, True, Decimal("20000.00"), 25000),
                ("FILTER-OIL-01", "Generic OEM", "ata-71-00", "general", False, False, None, None),
            ]
            for pn, oem, ata_id, ctype, serialized, llp, hours, cycles in items:
                self.repo.add_catalog_item(
                    ComponentCatalogItem(
                        id=f"cat-{pn.lower().replace('/', '-')[:40]}",
                        part_number=pn,
                        manufacturer_id=mfr_cfm.id if mfr_cfm and pn.startswith("CFM") else None,
                        oem_name=oem,
                        description=f"{ctype} catalog item {pn}",
                        ata_chapter_id=ata_id,
                        component_type=ctype,
                        is_serialized="true" if serialized else "false",
                        is_life_limited="true" if llp else "false",
                        hour_limit=hours,
                        cycle_limit=cycles,
                        created_at=_utcnow(),
                        updated_at=_utcnow(),
                    )
                )
            pending = True

        if pending:
            self.repo.commit()

        org_id = "org-aviation-east"
        if self.org.repo.get_organization(org_id) is None:
            return
        if self.repo.list_components(organization_id=org_id, active_only=False):
            return

        engine = self.repo.get_catalog_by_part_number("CFM56-5B4")
        apu = self.repo.get_catalog_by_part_number("APS3200")
        gear = self.repo.get_catalog_by_part_number("LG-NLG-320")
        if not engine or not apu or not gear:
            return

        aircraft = self.fleet.get_aircraft("ac-c-gmea")
        aircraft_id = aircraft.id if aircraft else None

        samples = [
            ("ENG-SN-1001", engine, "installed" if aircraft_id else "stores", aircraft_id, "ENG1"),
            ("APU-SN-2001", apu, "stores", None, None),
            ("NLG-SN-3001", gear, "maintenance", None, None),
        ]
        for serial, catalog, cstatus, ac_id, position in samples:
            row = SerializedComponent(
                organization_id=org_id,
                catalog_item_id=catalog.id,
                serial_number=serial,
                manufacturer_name=catalog.oem_name,
                component_status=cstatus,
                current_aircraft_id=ac_id,
                installation_position=position,
                date_installed=_utcnow() if cstatus == "installed" else None,
                aircraft_hours_at_install=Decimal("1250.50") if cstatus == "installed" else None,
                aircraft_cycles_at_install=840 if cstatus == "installed" else None,
                tsn_hours=Decimal("1250.50") if cstatus == "installed" else Decimal("100.00"),
                csn_cycles=840 if cstatus == "installed" else 50,
                tso_hours=Decimal("100.00"),
                cso_cycles=40,
                hour_limit=catalog.hour_limit,
                cycle_limit=catalog.cycle_limit,
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            _recompute_remaining(row)
            self.repo.add_component(row)
            self.repo.flush()
            if cstatus == "installed" and ac_id:
                self.repo.add_history(
                    ComponentInstallationHistory(
                        organization_id=org_id,
                        component_id=row.id,
                        event_type="install",
                        aircraft_id=ac_id,
                        to_aircraft_id=ac_id,
                        position=position,
                        from_status="stores",
                        to_status="installed",
                        occurred_at=_utcnow(),
                        aircraft_hours=Decimal("1250.50"),
                        aircraft_cycles=840,
                        actor="seed",
                        reason="seed_install",
                        reference="SEED",
                        created_at=_utcnow(),
                    )
                )
        self.repo.commit()

    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def resolve_org_id(
        self,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
        requested_org_id: str | None,
    ) -> str:
        org_id = (requested_org_id or session_org_id).strip()
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=org_id)
        return org_id

    def assert_org_access(self, *, username: str, session_role: str, organization_id: str) -> None:
        self.org.assert_org_access(username=username, session_role=session_role, organization_id=organization_id)

    # --- serializers ---
    @staticmethod
    def ata_out(row: AtaChapter) -> AtaChapterOut:
        return AtaChapterOut(
            id=row.id,
            chapter_number=row.chapter_number,
            subchapter=row.subchapter,
            title=row.title,
            description=row.description,
            status=row.status,
        )

    @staticmethod
    def catalog_out(row: ComponentCatalogItem) -> CatalogItemOut:
        return CatalogItemOut(
            id=row.id,
            part_number=row.part_number,
            manufacturer_id=row.manufacturer_id,
            oem_name=row.oem_name,
            description=row.description,
            ata_chapter_id=row.ata_chapter_id,
            component_type=row.component_type,
            is_serialized=_truthy(row.is_serialized),
            is_life_limited=_truthy(row.is_life_limited),
            hour_limit=row.hour_limit,
            cycle_limit=row.cycle_limit,
            calendar_limit_days=row.calendar_limit_days,
            status=row.status,
        )

    @staticmethod
    def component_out(row: SerializedComponent) -> SerializedComponentOut:
        catalog = row.catalog_item
        return SerializedComponentOut(
            id=row.id,
            organization_id=row.organization_id,
            catalog_item_id=row.catalog_item_id,
            part_number=catalog.part_number if catalog else None,
            component_type=catalog.component_type if catalog else None,
            serial_number=row.serial_number,
            manufacturer_name=row.manufacturer_name,
            component_status=row.component_status,
            current_aircraft_id=row.current_aircraft_id,
            installation_position=row.installation_position,
            date_installed=row.date_installed,
            date_removed=row.date_removed,
            tsn_hours=_hours(row.tsn_hours),
            csn_cycles=int(row.csn_cycles or 0),
            tso_hours=_hours(row.tso_hours),
            cso_cycles=int(row.cso_cycles or 0),
            aircraft_hours_at_install=row.aircraft_hours_at_install,
            aircraft_cycles_at_install=row.aircraft_cycles_at_install,
            hour_limit=row.hour_limit,
            cycle_limit=row.cycle_limit,
            calendar_limit_days=row.calendar_limit_days,
            remaining_hours=row.remaining_hours,
            remaining_cycles=row.remaining_cycles,
            due_date=row.due_date,
            notes=row.notes,
            status=row.status,
        )

    @staticmethod
    def history_out(row: ComponentInstallationHistory) -> HistoryOut:
        return HistoryOut(
            id=row.id,
            organization_id=row.organization_id,
            component_id=row.component_id,
            event_type=row.event_type,
            aircraft_id=row.aircraft_id,
            from_aircraft_id=row.from_aircraft_id,
            to_aircraft_id=row.to_aircraft_id,
            position=row.position,
            from_status=row.from_status,
            to_status=row.to_status,
            occurred_at=row.occurred_at,
            aircraft_hours=row.aircraft_hours,
            aircraft_cycles=row.aircraft_cycles,
            actor=row.actor,
            reason=row.reason,
            reference=row.reference,
            details=row.details,
        )

    def _get_org_component(
        self,
        component_id: str,
        *,
        username: str,
        session_role: str,
        for_update: bool = False,
    ) -> SerializedComponent:
        row = self.repo.get_component(component_id, with_catalog=True, for_update=for_update)
        if row is None or row.status != "active":
            raise HTTPException(status_code=404, detail="Component not found")
        self.assert_org_access(username=username, session_role=session_role, organization_id=row.organization_id)
        return row

    def _assert_aircraft_in_org(self, *, organization_id: str, aircraft_id: str) -> None:
        aircraft = self.fleet.get_aircraft(aircraft_id)
        if aircraft is None or aircraft.organization_id != organization_id or aircraft.status != "active":
            raise HTTPException(status_code=404, detail="Aircraft not found")

    def _append_history(
        self,
        *,
        component: SerializedComponent,
        event_type: str,
        actor: str,
        from_status: str,
        to_status: str,
        aircraft_id: str | None,
        from_aircraft_id: str | None,
        to_aircraft_id: str | None,
        position: str | None,
        aircraft_hours: Decimal | None,
        aircraft_cycles: int | None,
        occurred_at: datetime,
        reason: str,
        reference: str,
        details: str = "",
    ) -> ComponentInstallationHistory:
        row = ComponentInstallationHistory(
            organization_id=component.organization_id,
            component_id=component.id,
            event_type=event_type,
            aircraft_id=aircraft_id,
            from_aircraft_id=from_aircraft_id,
            to_aircraft_id=to_aircraft_id,
            position=position,
            from_status=from_status,
            to_status=to_status,
            occurred_at=occurred_at,
            aircraft_hours=aircraft_hours,
            aircraft_cycles=aircraft_cycles,
            actor=actor,
            reason=reason or "",
            reference=reference or "",
            details=details,
            created_at=_utcnow(),
        )
        self.repo.add_history(row)
        return row

    # --- catalog mutations ---
    def create_ata_chapter(self, payload: AtaChapterCreate) -> AtaChapterOut:
        chapter = payload.chapter_number.strip()
        sub = (payload.subchapter or "00").strip()
        if self.repo.get_ata_by_numbers(chapter, sub):
            raise HTTPException(status_code=409, detail="ATA chapter already exists")
        row = AtaChapter(
            chapter_number=chapter,
            subchapter=sub,
            title=payload.title.strip(),
            description=payload.description or "",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_ata_chapter(row)
        self._commit_or_conflict(detail="ATA chapter already exists")
        self.repo.refresh(row)
        return self.ata_out(row)

    def create_catalog_item(self, payload: CatalogItemCreate) -> CatalogItemOut:
        pn = payload.part_number.strip().upper()
        if self.repo.get_catalog_by_part_number(pn):
            raise HTTPException(status_code=409, detail="Part number already exists")
        ctype = (payload.component_type or "general").strip().lower()
        if ctype not in MAJOR_ASSEMBLY_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid component_type; allowed={sorted(MAJOR_ASSEMBLY_TYPES)}")
        if payload.ata_chapter_id and self.repo.get_ata_chapter(payload.ata_chapter_id) is None:
            raise HTTPException(status_code=404, detail="ATA chapter not found")
        if payload.manufacturer_id and self.fleet.get_manufacturer(payload.manufacturer_id) is None:
            raise HTTPException(status_code=404, detail="Manufacturer not found")
        row = ComponentCatalogItem(
            part_number=pn,
            manufacturer_id=payload.manufacturer_id,
            oem_name=(payload.oem_name or "").strip(),
            description=(payload.description or "").strip(),
            ata_chapter_id=payload.ata_chapter_id,
            component_type=ctype,
            is_serialized="true" if payload.is_serialized else "false",
            is_life_limited="true" if payload.is_life_limited else "false",
            hour_limit=payload.hour_limit,
            cycle_limit=payload.cycle_limit,
            calendar_limit_days=payload.calendar_limit_days,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        self.repo.add_catalog_item(row)
        self._commit_or_conflict(detail="Part number already exists")
        self.repo.refresh(row)
        return self.catalog_out(row)

    def create_component(
        self,
        payload: SerializedComponentCreate,
        *,
        username: str,
        session_role: str,
        session_org_id: str,
    ) -> SerializedComponentOut:
        org_id = self.resolve_org_id(
            username=username,
            session_role=session_role,
            session_org_id=session_org_id,
            requested_org_id=payload.organization_id,
        )
        catalog = self.repo.get_catalog_item(payload.catalog_item_id)
        if catalog is None or catalog.status != "active":
            raise HTTPException(status_code=404, detail="Catalog item not found")
        if not _truthy(catalog.is_serialized):
            raise HTTPException(status_code=400, detail="Catalog item is not serialized")
        serial = payload.serial_number.strip().upper()
        if self.repo.get_by_org_serial(org_id, serial):
            raise HTTPException(status_code=409, detail="Serial number already exists in organization")
        cstatus = (payload.component_status or "stores").strip().lower()
        if cstatus not in DESTINATION_STATUSES:
            raise HTTPException(status_code=400, detail="New components must start in stores/maintenance/retired/quarantine")

        hour_limit = payload.hour_limit if payload.hour_limit is not None else catalog.hour_limit
        cycle_limit = payload.cycle_limit if payload.cycle_limit is not None else catalog.cycle_limit
        calendar_limit = (
            payload.calendar_limit_days if payload.calendar_limit_days is not None else catalog.calendar_limit_days
        )
        row = SerializedComponent(
            organization_id=org_id,
            catalog_item_id=catalog.id,
            serial_number=serial,
            manufacturer_name=(payload.manufacturer_name or catalog.oem_name).strip(),
            component_status=cstatus,
            tsn_hours=_hours(payload.tsn_hours),
            csn_cycles=payload.csn_cycles,
            tso_hours=_hours(payload.tso_hours),
            cso_cycles=payload.cso_cycles,
            hour_limit=hour_limit,
            cycle_limit=cycle_limit,
            calendar_limit_days=calendar_limit,
            due_date=payload.due_date,
            notes=payload.notes or "",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        _recompute_remaining(row)
        self.repo.add_component(row)
        self._commit_or_conflict(detail="Serial number already exists in organization")
        self.repo.refresh(row)
        row = self.repo.get_component(row.id, with_catalog=True) or row
        return self.component_out(row)

    def update_life_limits(
        self,
        component_id: str,
        payload: LifeLimitUpdate,
        *,
        username: str,
        session_role: str,
    ) -> SerializedComponentOut:
        row = self._get_org_component(component_id, username=username, session_role=session_role)
        if payload.hour_limit is not None:
            row.hour_limit = _hours(payload.hour_limit)
        if payload.cycle_limit is not None:
            row.cycle_limit = payload.cycle_limit
        if payload.calendar_limit_days is not None:
            row.calendar_limit_days = payload.calendar_limit_days
        if payload.due_date is not None:
            row.due_date = payload.due_date
        _recompute_remaining(row)
        row.updated_at = _utcnow()
        self._commit_or_conflict(detail="Unable to update life limits")
        row = self.repo.get_component(row.id, with_catalog=True) or row
        return self.component_out(row)

    def update_time_cycles(
        self,
        component_id: str,
        payload: TimeCycleUpdate,
        *,
        username: str,
        session_role: str,
    ) -> SerializedComponentOut:
        row = self._get_org_component(component_id, username=username, session_role=session_role)
        if payload.tsn_hours is not None:
            row.tsn_hours = _hours(payload.tsn_hours)
        if payload.csn_cycles is not None:
            row.csn_cycles = payload.csn_cycles
        if payload.tso_hours is not None:
            row.tso_hours = _hours(payload.tso_hours)
        if payload.cso_cycles is not None:
            row.cso_cycles = payload.cso_cycles
        _recompute_remaining(row)
        row.updated_at = _utcnow()
        self._commit_or_conflict(detail="Unable to update time/cycles")
        row = self.repo.get_component(row.id, with_catalog=True) or row
        return self.component_out(row)

    def _apply_install(
        self,
        row: SerializedComponent,
        payload: InstallRequest,
        *,
        actor: str,
    ) -> SerializedComponent:
        """Mutate component + history for install. Caller owns the transaction commit."""
        if row.component_status == "installed":
            raise HTTPException(status_code=409, detail="Component already installed")
        if row.component_status == "retired":
            raise HTTPException(status_code=409, detail="Retired component cannot be installed")
        self._assert_aircraft_in_org(organization_id=row.organization_id, aircraft_id=payload.aircraft_id)
        position = payload.position.strip().upper()
        occupant = self.repo.get_installed_at_position(payload.aircraft_id, position)
        if occupant is not None and occupant.id != row.id:
            raise HTTPException(status_code=409, detail="Position already occupied on aircraft")

        occurred = payload.occurred_at or _utcnow()
        from_status = row.component_status
        row.component_status = "installed"
        row.current_aircraft_id = payload.aircraft_id
        row.installation_position = position
        row.date_installed = occurred
        row.date_removed = None
        row.aircraft_hours_at_install = _hours(payload.aircraft_hours)
        row.aircraft_cycles_at_install = payload.aircraft_cycles
        row.updated_at = _utcnow()
        self._append_history(
            component=row,
            event_type="install",
            actor=actor,
            from_status=from_status,
            to_status="installed",
            aircraft_id=payload.aircraft_id,
            from_aircraft_id=None,
            to_aircraft_id=payload.aircraft_id,
            position=position,
            aircraft_hours=_hours(payload.aircraft_hours),
            aircraft_cycles=payload.aircraft_cycles,
            occurred_at=occurred,
            reason=payload.reason,
            reference=payload.reference,
        )
        self.repo.flush()
        return row

    def _apply_remove(
        self,
        row: SerializedComponent,
        payload: RemoveRequest,
        *,
        actor: str,
    ) -> SerializedComponent:
        """Mutate component + history for remove. Caller owns the transaction commit."""
        if row.component_status != "installed" or not row.current_aircraft_id:
            raise HTTPException(status_code=409, detail="Component is not installed")
        dest = payload.destination_status.strip().lower()
        if dest not in DESTINATION_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid destination_status")

        occurred = payload.occurred_at or _utcnow()
        remove_hours = _hours(payload.aircraft_hours)
        remove_cycles = int(payload.aircraft_cycles)
        install_hours = _hours(row.aircraft_hours_at_install or 0)
        install_cycles = int(row.aircraft_cycles_at_install or 0)
        if remove_hours < install_hours or remove_cycles < install_cycles:
            raise HTTPException(status_code=400, detail="Removal hours/cycles cannot be less than installation values")

        delta_hours = remove_hours - install_hours
        delta_cycles = remove_cycles - install_cycles
        row.tsn_hours = _hours(row.tsn_hours) + delta_hours
        row.csn_cycles = int(row.csn_cycles or 0) + delta_cycles
        row.tso_hours = _hours(row.tso_hours) + delta_hours
        row.cso_cycles = int(row.cso_cycles or 0) + delta_cycles
        _recompute_remaining(row)

        from_aircraft = row.current_aircraft_id
        from_position = row.installation_position
        from_status = row.component_status
        row.component_status = dest
        row.current_aircraft_id = None
        row.installation_position = None
        row.date_removed = occurred
        row.aircraft_hours_at_install = None
        row.aircraft_cycles_at_install = None
        row.updated_at = _utcnow()
        self._append_history(
            component=row,
            event_type="remove",
            actor=actor,
            from_status=from_status,
            to_status=dest,
            aircraft_id=from_aircraft,
            from_aircraft_id=from_aircraft,
            to_aircraft_id=None,
            position=from_position,
            aircraft_hours=remove_hours,
            aircraft_cycles=remove_cycles,
            occurred_at=occurred,
            reason=payload.reason,
            reference=payload.reference,
            details=f"delta_hours={delta_hours};delta_cycles={delta_cycles}",
        )
        self.repo.flush()
        return row

    def install(
        self,
        component_id: str,
        payload: InstallRequest,
        *,
        username: str,
        session_role: str,
    ) -> SerializedComponentOut:
        # Single DB transaction: lock row → mutate → history → commit.
        row = self._get_org_component(
            component_id, username=username, session_role=session_role, for_update=True
        )
        self._apply_install(row, payload, actor=username)
        self._commit_or_conflict(detail="Install conflict (position occupied or concurrent install)")
        row = self.repo.get_component(row.id, with_catalog=True) or row
        return self.component_out(row)

    def remove(
        self,
        component_id: str,
        payload: RemoveRequest,
        *,
        username: str,
        session_role: str,
    ) -> SerializedComponentOut:
        # Single DB transaction: lock row → mutate → history → commit.
        row = self._get_org_component(
            component_id, username=username, session_role=session_role, for_update=True
        )
        self._apply_remove(row, payload, actor=username)
        self._commit_or_conflict(detail="Unable to remove component")
        row = self.repo.get_component(row.id, with_catalog=True) or row
        return self.component_out(row)

    def transfer(
        self,
        component_id: str,
        payload: TransferRequest,
        *,
        username: str,
        session_role: str,
    ) -> SerializedComponentOut:
        to_status = payload.to_status.strip().lower()
        # Lock once; remove+install (or status move) commit together — no multi-commit race window.
        row = self._get_org_component(
            component_id, username=username, session_role=session_role, for_update=True
        )

        if to_status == "installed":
            if not payload.to_aircraft_id or not payload.position:
                raise HTTPException(status_code=400, detail="to_aircraft_id and position required for install transfer")
            if row.component_status == "installed":
                self._apply_remove(
                    row,
                    RemoveRequest(
                        destination_status="stores",
                        aircraft_hours=payload.aircraft_hours,
                        aircraft_cycles=payload.aircraft_cycles,
                        occurred_at=payload.occurred_at,
                        reason=payload.reason or "transfer_remove",
                        reference=payload.reference,
                    ),
                    actor=username,
                )
            self._apply_install(
                row,
                InstallRequest(
                    aircraft_id=payload.to_aircraft_id,
                    position=payload.position,
                    aircraft_hours=payload.aircraft_hours,
                    aircraft_cycles=payload.aircraft_cycles,
                    occurred_at=payload.occurred_at,
                    reason=payload.reason or "transfer_install",
                    reference=payload.reference,
                ),
                actor=username,
            )
            self._commit_or_conflict(detail="Transfer install conflict")
            row = self.repo.get_component(row.id, with_catalog=True) or row
            return self.component_out(row)

        if to_status not in DESTINATION_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid to_status")
        if row.component_status == "installed":
            self._apply_remove(
                row,
                RemoveRequest(
                    destination_status=to_status,
                    aircraft_hours=payload.aircraft_hours,
                    aircraft_cycles=payload.aircraft_cycles,
                    occurred_at=payload.occurred_at,
                    reason=payload.reason or "transfer",
                    reference=payload.reference,
                ),
                actor=username,
            )
            self._commit_or_conflict(detail="Unable to transfer component")
            row = self.repo.get_component(row.id, with_catalog=True) or row
            return self.component_out(row)

        occurred = payload.occurred_at or _utcnow()
        from_status = row.component_status
        row.component_status = to_status
        row.updated_at = _utcnow()
        self._append_history(
            component=row,
            event_type="transfer",
            actor=username,
            from_status=from_status,
            to_status=to_status,
            aircraft_id=None,
            from_aircraft_id=None,
            to_aircraft_id=None,
            position=None,
            aircraft_hours=_hours(payload.aircraft_hours),
            aircraft_cycles=payload.aircraft_cycles,
            occurred_at=occurred,
            reason=payload.reason,
            reference=payload.reference,
        )
        self._commit_or_conflict(detail="Unable to transfer component")
        row = self.repo.get_component(row.id, with_catalog=True) or row
        return self.component_out(row)

    def aircraft_configuration(
        self,
        aircraft_id: str,
        *,
        username: str,
        session_role: str,
    ) -> AircraftConfigurationOut:
        aircraft = self.fleet.get_aircraft(aircraft_id)
        if aircraft is None or aircraft.status != "active":
            raise HTTPException(status_code=404, detail="Aircraft not found")
        self.assert_org_access(
            username=username,
            session_role=session_role,
            organization_id=aircraft.organization_id,
        )
        rows = self.repo.list_components(
            organization_id=aircraft.organization_id,
            aircraft_id=aircraft_id,
            component_status="installed",
            with_catalog=True,
        )
        installed = [
            AircraftConfigurationItem(
                component_id=r.id,
                serial_number=r.serial_number,
                part_number=r.catalog_item.part_number if r.catalog_item else "",
                component_type=r.catalog_item.component_type if r.catalog_item else "general",
                position=r.installation_position or "",
                date_installed=r.date_installed,
                tsn_hours=_hours(r.tsn_hours),
                csn_cycles=int(r.csn_cycles or 0),
                remaining_hours=r.remaining_hours,
                remaining_cycles=r.remaining_cycles,
            )
            for r in rows
        ]
        return AircraftConfigurationOut(
            aircraft_id=aircraft_id,
            organization_id=aircraft.organization_id,
            installed=installed,
        )
