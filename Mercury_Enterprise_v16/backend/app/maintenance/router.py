from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..database import get_db
from ..security.authorization import has_permissions
from ..security.operators import operator_store
from .schemas import (
    AiCrossRefCreate,
    AiCrossRefOut,
    AiIndexStubCreate,
    AiIndexStubOut,
    CertifyOut,
    CertifyRequest,
    CriticalPolicyCreate,
    CriticalPolicyOut,
    DigitalSignatureOut,
    FaultCodeCreate,
    FaultCodeOut,
    TaskAuditTrailOut,
    TaskCreate,
    TaskOut,
    TaskTransitionRequest,
    TechnicalLogOut,
)
from .service import MaintenanceService

logger = logging.getLogger("mercury.maintenance")
router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance"])


def _session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return require_session(request)


def require_maintenance_read(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    if not has_permissions(str(session.get("role")), ("maintenance.read",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    return session


def require_maintenance_manage(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    if not has_permissions(str(session.get("role")), ("maintenance.manage",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Maintenance management required")
    return session


def require_logbook_read(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    if not has_permissions(str(session.get("role")), ("logbook.read",)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Logbook read required")
    return session


def require_certification_sign(request: Request) -> dict[str, datetime | str]:
    session = _session(request)
    role = str(session.get("role"))
    if not (
        has_permissions(role, ("certification.sign",))
        or has_permissions(role, ("signature.create",))
        or has_permissions(role, ("maintenance.manage",))
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Certification sign required")
    return session


def _can_release(session: dict[str, datetime | str]) -> bool:
    role = str(session.get("role"))
    username = str(session.get("operator", ""))
    record = operator_store.get(username)
    global_role = record["role"] if record else role
    return (
        has_permissions(role, ("certification.release",))
        or has_permissions(global_role, ("certification.release",))
        or has_permissions(global_role, ("admin.system",))
        or has_permissions(role, ("admin.system",))
        or str(global_role).lower() == "administrator"
        or role.lower() == "administrator"
    )


def _svc(db: Session) -> MaintenanceService:
    return MaintenanceService(db)


def _safe_commit(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _audit(
    db: Session,
    session: dict[str, datetime | str],
    *,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
    organization_id: str | None = None,
) -> None:
    try:
        record_audit(
            db,
            action=action,
            actor=str(session["operator"]),
            actor_role=str(session["role"]),
            organization_id=organization_id or str(session["organization_id"]),
            site_id=str(session["site_id"]),
            target_type=target_type,
            target_id=target_id,
            source="api",
            outcome="success",
            origin="operator",
            details=details,
        )
        _safe_commit(db)
    except Exception:
        db.rollback()
        logger.exception("Failed to record maintenance audit action=%s target=%s", action, target_id)


@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    status: str | None = None,
    task_type: str | None = None,
    priority: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_read),
) -> list[TaskOut]:
    return _svc(db).list_tasks(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        aircraft_id=aircraft_id,
        status=status,
        task_type=task_type,
        priority=priority,
        limit=limit,
        offset=offset,
    )


@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_manage),
) -> TaskOut:
    out = _svc(db).create_task(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="maintenance.task.create",
        target_type="maintenance_task",
        target_id=out.id,
        details=(
            f"task_number={out.task_number};type={out.task_type};aircraft_id={out.aircraft_id};"
            f"publication_id={out.publication_id or ''};revision_id={out.publication_revision_id or ''}"
        ),
        organization_id=out.organization_id,
    )
    return out


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_read),
) -> TaskOut:
    return _svc(db).get_task(task_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.get("/tasks/{task_id}/audit-trail", response_model=TaskAuditTrailOut)
def get_task_audit_trail(
    task_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_read),
) -> TaskAuditTrailOut:
    return _svc(db).get_task_audit_trail(
        task_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.post("/tasks/{task_id}/transition", response_model=TaskOut)
def transition_task(
    task_id: str,
    payload: TaskTransitionRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_manage),
) -> TaskOut:
    out = _svc(db).transition_task(
        task_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="maintenance.task.transition",
        target_type="maintenance_task",
        target_id=out.id,
        details=f"task_number={out.task_number};status={out.status};version={out.version}",
        organization_id=out.organization_id,
    )
    return out


@router.post("/tasks/{task_id}/certify", response_model=CertifyOut)
def certify_task(
    task_id: str,
    payload: CertifyRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_certification_sign),
) -> CertifyOut:
    if payload.step == "aircraft_released" and not _can_release(session):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aircraft release requires certification.release or admin",
        )
    out = _svc(db).sign_action(
        task_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="maintenance.certify",
        target_type="maintenance_task",
        target_id=out.task.id,
        details=(
            f"task_number={out.task.task_number};step={payload.step};"
            f"signature_id={out.signature.id};release_status={out.task.release_status}"
        ),
        organization_id=out.task.organization_id,
    )
    _audit(
        db,
        session,
        action="signature.create",
        target_type="digital_signature",
        target_id=out.signature.id,
        details=f"task_number={out.task.task_number};task_id={out.task.id};step={payload.step}",
        organization_id=out.task.organization_id,
    )
    if out.log_entry_id:
        _audit(
            db,
            session,
            action="logbook.entry.create",
            target_type="technical_log_entry",
            target_id=out.log_entry_id,
            details=(
                f"task_number={out.task.task_number};task_id={out.task.id};"
                f"aircraft_id={out.task.aircraft_id}"
            ),
            organization_id=out.task.organization_id,
        )
    return out


@router.get("/logbook", response_model=list[TechnicalLogOut])
def list_logbook(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_logbook_read),
) -> list[TechnicalLogOut]:
    return _svc(db).list_logbook(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        aircraft_id=aircraft_id,
        limit=limit,
        offset=offset,
    )


@router.get("/critical-policies", response_model=list[CriticalPolicyOut])
def list_critical_policies(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_read),
) -> list[CriticalPolicyOut]:
    return _svc(db).list_critical_policies(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.post("/critical-policies", response_model=CriticalPolicyOut, status_code=201)
def create_critical_policy(
    payload: CriticalPolicyCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_manage),
) -> CriticalPolicyOut:
    out = _svc(db).create_critical_policy(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="maintenance.critical_policy.create",
        target_type="critical_task_policy",
        target_id=out.id,
        details=f"code={out.code};domain={out.domain}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/fault-codes", response_model=list[FaultCodeOut])
def list_fault_codes(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_read),
) -> list[FaultCodeOut]:
    return _svc(db).list_fault_codes(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.post("/fault-codes", response_model=FaultCodeOut, status_code=201)
def create_fault_code(
    payload: FaultCodeCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_manage),
) -> FaultCodeOut:
    out = _svc(db).create_fault_code(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="maintenance.fault_code.create",
        target_type="fault_code",
        target_id=out.id,
        details=f"code={out.code}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/ai/index-stubs", response_model=list[AiIndexStubOut])
def list_ai_index_stubs(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_read),
) -> list[AiIndexStubOut]:
    return _svc(db).list_index_stubs(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.post("/ai/index-stubs", response_model=AiIndexStubOut, status_code=201)
def create_ai_index_stub(
    payload: AiIndexStubCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_manage),
) -> AiIndexStubOut:
    out = _svc(db).create_index_stub(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="maintenance.ai_index_stub.create",
        target_type="ai_document_index_stub",
        target_id=out.id,
        details=f"source_type={out.source_type};source_id={out.source_id}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/ai/cross-refs", response_model=list[AiCrossRefOut])
def list_ai_cross_refs(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_read),
) -> list[AiCrossRefOut]:
    return _svc(db).list_cross_refs(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.post("/ai/cross-refs", response_model=AiCrossRefOut, status_code=201)
def create_ai_cross_ref(
    payload: AiCrossRefCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_manage),
) -> AiCrossRefOut:
    out = _svc(db).create_cross_ref(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="maintenance.ai_cross_ref.create",
        target_type="ai_knowledge_cross_ref",
        target_id=out.id,
        details=f"relation={out.relation};from={out.from_type}:{out.from_id}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/signatures/{signature_id}", response_model=DigitalSignatureOut)
def get_signature(
    signature_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_maintenance_read),
) -> DigitalSignatureOut:
    return _svc(db).get_signature(
        signature_id, username=str(session["operator"]), session_role=str(session["role"])
    )
