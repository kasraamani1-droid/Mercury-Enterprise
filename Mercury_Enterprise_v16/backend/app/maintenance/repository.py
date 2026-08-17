from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    AiDocumentIndexStub,
    AiEmbeddingStub,
    AiKnowledgeCrossRef,
    CertificationEvent,
    CriticalTaskPolicy,
    DigitalSignature,
    FaultCode,
    MaintenanceTask,
    TechnicalLogEntry,
)


class MaintenanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- fault codes ---
    def list_fault_codes(
        self, *, organization_id: str, active_only: bool = True
    ) -> list[FaultCode]:
        stmt = (
            select(FaultCode)
            .where(FaultCode.organization_id == organization_id)
            .order_by(FaultCode.code)
        )
        if active_only:
            stmt = stmt.where(FaultCode.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_fault_code(self, fault_code_id: str) -> FaultCode | None:
        return self.db.get(FaultCode, fault_code_id)

    def get_fault_by_code(self, organization_id: str, code: str) -> FaultCode | None:
        return self.db.scalar(
            select(FaultCode).where(
                FaultCode.organization_id == organization_id,
                FaultCode.code == code.strip().upper(),
            )
        )

    def add_fault_code(self, row: FaultCode) -> FaultCode:
        self.db.add(row)
        return row

    # --- critical policies ---
    def list_critical_policies(
        self, *, organization_id: str, active_only: bool = True
    ) -> list[CriticalTaskPolicy]:
        stmt = (
            select(CriticalTaskPolicy)
            .where(CriticalTaskPolicy.organization_id == organization_id)
            .order_by(CriticalTaskPolicy.domain, CriticalTaskPolicy.code)
        )
        if active_only:
            stmt = stmt.where(CriticalTaskPolicy.status == "active")
        return list(self.db.scalars(stmt).all())

    def get_critical_policy(self, policy_id: str) -> CriticalTaskPolicy | None:
        return self.db.get(CriticalTaskPolicy, policy_id)

    def get_critical_policy_by_code(self, organization_id: str, code: str) -> CriticalTaskPolicy | None:
        return self.db.scalar(
            select(CriticalTaskPolicy).where(
                CriticalTaskPolicy.organization_id == organization_id,
                CriticalTaskPolicy.code == code.strip().upper(),
            )
        )

    def add_critical_policy(self, row: CriticalTaskPolicy) -> CriticalTaskPolicy:
        self.db.add(row)
        return row

    # --- tasks ---
    def list_tasks(
        self,
        *,
        organization_id: str,
        aircraft_id: str | None = None,
        status: str | None = None,
        task_type: str | None = None,
        priority: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[MaintenanceTask]:
        stmt = (
            select(MaintenanceTask)
            .where(MaintenanceTask.organization_id == organization_id)
            .order_by(MaintenanceTask.created_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
        )
        if aircraft_id:
            stmt = stmt.where(MaintenanceTask.aircraft_id == aircraft_id)
        if status:
            stmt = stmt.where(MaintenanceTask.status == status)
        if task_type:
            stmt = stmt.where(MaintenanceTask.task_type == task_type)
        if priority:
            stmt = stmt.where(MaintenanceTask.priority == priority)
        return list(self.db.scalars(stmt).all())

    def get_task(
        self,
        task_id: str,
        *,
        for_update: bool = False,
        with_events: bool = False,
    ) -> MaintenanceTask | None:
        stmt = select(MaintenanceTask).where(MaintenanceTask.id == task_id)
        if with_events:
            stmt = stmt.options(selectinload(MaintenanceTask.certification_events))
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalars(stmt).unique().first()

    def get_task_by_number(self, organization_id: str, task_number: str) -> MaintenanceTask | None:
        return self.db.scalar(
            select(MaintenanceTask).where(
                MaintenanceTask.organization_id == organization_id,
                MaintenanceTask.task_number == task_number.strip().upper(),
            )
        )

    def add_task(self, row: MaintenanceTask) -> MaintenanceTask:
        self.db.add(row)
        return row

    # --- signatures / events / logbook ---
    def get_signature(self, signature_id: str) -> DigitalSignature | None:
        return self.db.get(DigitalSignature, signature_id)

    def add_signature(self, row: DigitalSignature) -> DigitalSignature:
        self.db.add(row)
        return row

    def list_certification_events(self, task_id: str) -> list[CertificationEvent]:
        stmt = (
            select(CertificationEvent)
            .where(CertificationEvent.task_id == task_id)
            .order_by(CertificationEvent.occurred_at)
        )
        return list(self.db.scalars(stmt).all())

    def add_certification_event(self, row: CertificationEvent) -> CertificationEvent:
        self.db.add(row)
        return row

    def list_logbook(
        self,
        *,
        organization_id: str,
        aircraft_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[TechnicalLogEntry]:
        stmt = (
            select(TechnicalLogEntry)
            .where(TechnicalLogEntry.organization_id == organization_id)
            .order_by(TechnicalLogEntry.occurred_at.desc())
            .offset(max(0, offset))
            .limit(max(1, min(limit, 500)))
        )
        if aircraft_id:
            stmt = stmt.where(TechnicalLogEntry.aircraft_id == aircraft_id)
        return list(self.db.scalars(stmt).all())

    def list_logbook_for_task(self, task_id: str) -> list[TechnicalLogEntry]:
        stmt = (
            select(TechnicalLogEntry)
            .where(TechnicalLogEntry.task_id == task_id)
            .order_by(TechnicalLogEntry.occurred_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def list_signatures_by_ids(self, signature_ids: list[str]) -> list[DigitalSignature]:
        if not signature_ids:
            return []
        stmt = select(DigitalSignature).where(DigitalSignature.id.in_(signature_ids))
        return list(self.db.scalars(stmt).all())

    def get_log_entry(self, entry_id: str) -> TechnicalLogEntry | None:
        return self.db.get(TechnicalLogEntry, entry_id)

    def add_log_entry(self, row: TechnicalLogEntry) -> TechnicalLogEntry:
        self.db.add(row)
        return row

    # --- AI stubs ---
    def list_index_stubs(
        self, *, organization_id: str | None = None
    ) -> list[AiDocumentIndexStub]:
        stmt = select(AiDocumentIndexStub).order_by(AiDocumentIndexStub.created_at.desc())
        if organization_id:
            stmt = stmt.where(AiDocumentIndexStub.organization_id == organization_id)
        return list(self.db.scalars(stmt).all())

    def get_index_stub(self, index_id: str) -> AiDocumentIndexStub | None:
        return self.db.get(AiDocumentIndexStub, index_id)

    def add_index_stub(self, row: AiDocumentIndexStub) -> AiDocumentIndexStub:
        self.db.add(row)
        return row

    def add_embedding_stub(self, row: AiEmbeddingStub) -> AiEmbeddingStub:
        self.db.add(row)
        return row

    def list_cross_refs(self, *, organization_id: str) -> list[AiKnowledgeCrossRef]:
        stmt = (
            select(AiKnowledgeCrossRef)
            .where(AiKnowledgeCrossRef.organization_id == organization_id)
            .order_by(AiKnowledgeCrossRef.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def add_cross_ref(self, row: AiKnowledgeCrossRef) -> AiKnowledgeCrossRef:
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
