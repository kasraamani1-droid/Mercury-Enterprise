from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .models import JobCard, JobCardAttachment, WorkOrder, WorkPackage


class WorkOrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- packages ---
    def list_packages(
        self,
        *,
        organization_id: str,
        aircraft_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkPackage]:
        stmt = (
            select(WorkPackage)
            .where(WorkPackage.organization_id == organization_id)
            .order_by(WorkPackage.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
        )
        if aircraft_id:
            stmt = stmt.where(WorkPackage.aircraft_id == aircraft_id)
        if status:
            stmt = stmt.where(WorkPackage.status == status)
        return list(self.db.scalars(stmt).all())

    def get_package(self, package_id: str, *, for_update: bool = False) -> WorkPackage | None:
        stmt = select(WorkPackage).where(WorkPackage.id == package_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_package_by_number(self, organization_id: str, package_number: str) -> WorkPackage | None:
        return self.db.scalar(
            select(WorkPackage).where(
                WorkPackage.organization_id == organization_id,
                WorkPackage.package_number == package_number.strip().upper(),
            )
        )

    def count_orders_in_package(self, package_id: str) -> int:
        return int(
            self.db.scalar(select(func.count()).select_from(WorkOrder).where(WorkOrder.work_package_id == package_id))
            or 0
        )

    def add_package(self, row: WorkPackage) -> WorkPackage:
        self.db.add(row)
        return row

    # --- work orders ---
    def list_orders(
        self,
        *,
        organization_id: str,
        work_package_id: str | None = None,
        aircraft_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkOrder]:
        stmt = (
            select(WorkOrder)
            .where(WorkOrder.organization_id == organization_id)
            .order_by(WorkOrder.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
        )
        if work_package_id:
            stmt = stmt.where(WorkOrder.work_package_id == work_package_id)
        if aircraft_id:
            stmt = stmt.where(WorkOrder.aircraft_id == aircraft_id)
        if status:
            stmt = stmt.where(WorkOrder.status == status)
        return list(self.db.scalars(stmt).all())

    def get_order(self, order_id: str, *, for_update: bool = False) -> WorkOrder | None:
        stmt = select(WorkOrder).where(WorkOrder.id == order_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def get_order_by_number(self, organization_id: str, wo_number: str) -> WorkOrder | None:
        return self.db.scalar(
            select(WorkOrder).where(
                WorkOrder.organization_id == organization_id,
                WorkOrder.wo_number == wo_number.strip().upper(),
            )
        )

    def count_cards_in_order(self, work_order_id: str) -> int:
        return int(
            self.db.scalar(select(func.count()).select_from(JobCard).where(JobCard.work_order_id == work_order_id))
            or 0
        )

    def add_order(self, row: WorkOrder) -> WorkOrder:
        self.db.add(row)
        return row

    # --- job cards ---
    def list_job_cards(
        self,
        *,
        organization_id: str,
        work_order_id: str | None = None,
        technician_employee_id: str | None = None,
        status: str | None = None,
        aircraft_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobCard]:
        stmt = (
            select(JobCard)
            .where(JobCard.organization_id == organization_id)
            .order_by(JobCard.updated_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
        )
        if work_order_id:
            stmt = stmt.where(JobCard.work_order_id == work_order_id)
        if technician_employee_id:
            stmt = stmt.where(JobCard.technician_employee_id == technician_employee_id)
        if status:
            stmt = stmt.where(JobCard.status == status)
        if aircraft_id:
            stmt = stmt.where(JobCard.aircraft_id == aircraft_id)
        return list(self.db.scalars(stmt).all())

    def get_job_card(
        self, job_card_id: str, *, for_update: bool = False, with_attachments: bool = False
    ) -> JobCard | None:
        stmt = select(JobCard).where(JobCard.id == job_card_id)
        if with_attachments:
            stmt = stmt.options(selectinload(JobCard.attachments))
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).unique().first()

    def get_job_card_by_number(self, organization_id: str, job_card_number: str) -> JobCard | None:
        return self.db.scalar(
            select(JobCard).where(
                JobCard.organization_id == organization_id,
                JobCard.job_card_number == job_card_number.strip().upper(),
            )
        )

    def add_job_card(self, row: JobCard) -> JobCard:
        self.db.add(row)
        return row

    def list_attachments(self, job_card_id: str) -> list[JobCardAttachment]:
        stmt = (
            select(JobCardAttachment)
            .where(JobCardAttachment.job_card_id == job_card_id)
            .order_by(JobCardAttachment.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def add_attachment(self, row: JobCardAttachment) -> JobCardAttachment:
        self.db.add(row)
        return row

    def count_job_cards_by_status(self, organization_id: str) -> dict[str, int]:
        rows = self.db.execute(
            select(JobCard.status, func.count())
            .where(JobCard.organization_id == organization_id)
            .group_by(JobCard.status)
        ).all()
        return {str(status): int(count) for status, count in rows}

    def count_orders_by_status(self, organization_id: str, status: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(WorkOrder)
                .where(WorkOrder.organization_id == organization_id, WorkOrder.status == status)
            )
            or 0
        )

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    def flush(self) -> None:
        self.db.flush()
