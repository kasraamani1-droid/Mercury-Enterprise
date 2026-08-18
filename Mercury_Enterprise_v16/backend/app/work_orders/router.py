from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..database import get_db
from ..security.runtime_authz import require_allowed
from .schemas import (
    ExecutionDashboardOut,
    JobCardAssignRequest,
    JobCardAttachmentCreate,
    JobCardAttachmentOut,
    JobCardCompleteWorkRequest,
    JobCardCreate,
    JobCardInspectRequest,
    JobCardOut,
    JobCardReleaseRequest,
    JobCardTransitionRequest,
    ReportSummaryOut,
    WorkOrderCreate,
    WorkOrderOut,
    WorkPackageCreate,
    WorkPackageOut,
)
from .service import WorkOrderService

logger = logging.getLogger("mercury.work_orders")
router = APIRouter(prefix="/api/v1/work-orders", tags=["work-orders"])


def _session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return require_session(request)


def require_wo_read(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("work_order.read", "maintenance.read"),
        any_of=True,
        detail="Insufficient permissions",
    )
    return session


def require_wo_manage(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("work_order.manage", "maintenance.manage"),
        any_of=True,
        detail="Work order management required",
    )
    return session


def require_wo_execute(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("work_order.execute", "certification.sign"),
        any_of=True,
        detail="Work execution permission required",
    )
    return session


def require_wo_inspect(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("inspector.approve", "certification.sign", "work_order.manage"),
        any_of=True,
        detail="Inspection authority required",
    )
    return session


def require_wo_release(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(db, session, ("certification.release",), detail="Aircraft release required")
    return session


def _svc(db: Session) -> WorkOrderService:
    return WorkOrderService(db)


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
    fail_closed: bool = False,
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
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to record work-order audit action=%s target=%s", action, target_id)
        if fail_closed:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Audit persistence failed for certification action",
            ) from exc


@router.get("/packages", response_model=list[WorkPackageOut])
def list_packages(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> list[WorkPackageOut]:
    return _svc(db).list_packages(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        aircraft_id=aircraft_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/packages", response_model=WorkPackageOut, status_code=201)
def create_package(
    payload: WorkPackageCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_manage),
) -> WorkPackageOut:
    out = _svc(db).create_package(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="work_package.create",
        target_type="work_package",
        target_id=out.id,
        details=f"package_number={out.package_number};aircraft_id={out.aircraft_id}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/packages/{package_id}", response_model=WorkPackageOut)
def get_package(
    package_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> WorkPackageOut:
    return _svc(db).get_package(package_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.get("/orders", response_model=list[WorkOrderOut])
def list_orders(
    organization_id: str | None = None,
    work_package_id: str | None = None,
    aircraft_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> list[WorkOrderOut]:
    return _svc(db).list_orders(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        work_package_id=work_package_id,
        aircraft_id=aircraft_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/orders", response_model=WorkOrderOut, status_code=201)
def create_order(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_manage),
) -> WorkOrderOut:
    out = _svc(db).create_order(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="work_order.create",
        target_type="work_order",
        target_id=out.id,
        details=f"wo_number={out.wo_number};package_id={out.work_package_id}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/orders/{order_id}", response_model=WorkOrderOut)
def get_order(
    order_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> WorkOrderOut:
    return _svc(db).get_order(order_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.get("/job-cards", response_model=list[JobCardOut])
def list_job_cards(
    organization_id: str | None = None,
    work_order_id: str | None = None,
    technician_employee_id: str | None = None,
    status: str | None = None,
    aircraft_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> list[JobCardOut]:
    return _svc(db).list_job_cards(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        work_order_id=work_order_id,
        technician_employee_id=technician_employee_id,
        status=status,
        aircraft_id=aircraft_id,
        limit=limit,
        offset=offset,
    )


@router.post("/job-cards", response_model=JobCardOut, status_code=201)
def create_job_card(
    payload: JobCardCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_manage),
) -> JobCardOut:
    out = _svc(db).create_job_card(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="job_card.create",
        target_type="job_card",
        target_id=out.id,
        details=f"job_card_number={out.job_card_number};task_id={out.maintenance_task_id or ''}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/job-cards/{job_card_id}", response_model=JobCardOut)
def get_job_card(
    job_card_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> JobCardOut:
    return _svc(db).get_job_card(job_card_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.post("/job-cards/{job_card_id}/assign", response_model=JobCardOut)
def assign_job_card(
    job_card_id: str,
    payload: JobCardAssignRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_manage),
) -> JobCardOut:
    out = _svc(db).assign_job_card(
        job_card_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="job_card.assign",
        target_type="job_card",
        target_id=out.id,
        details=f"technician={out.technician_employee_id}",
        organization_id=out.organization_id,
    )
    return out


@router.post("/job-cards/{job_card_id}/transition", response_model=JobCardOut)
def transition_job_card(
    job_card_id: str,
    payload: JobCardTransitionRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_execute),
) -> JobCardOut:
    out = _svc(db).transition_job_card(
        job_card_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="job_card.transition",
        target_type="job_card",
        target_id=out.id,
        details=f"status={out.status}",
        organization_id=out.organization_id,
    )
    return out


@router.post("/job-cards/{job_card_id}/complete-work", response_model=JobCardOut)
def complete_job_card_work(
    job_card_id: str,
    payload: JobCardCompleteWorkRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_execute),
) -> JobCardOut:
    out = _svc(db).complete_job_card_work(
        job_card_id,
        employee_id=payload.employee_id,
        method=payload.method,
        credential=payload.credential,
        notes=payload.notes,
        actual_hours=payload.actual_hours,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="job_card.complete_work",
        target_type="job_card",
        target_id=out.id,
        details=f"status={out.status};task_id={out.maintenance_task_id or ''}",
        organization_id=out.organization_id,
        fail_closed=True,
    )
    return out


@router.post("/job-cards/{job_card_id}/inspect", response_model=JobCardOut)
def inspect_job_card(
    job_card_id: str,
    payload: JobCardInspectRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_inspect),
) -> JobCardOut:
    out = _svc(db).inspect_job_card(
        job_card_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="job_card.inspect",
        target_type="job_card",
        target_id=out.id,
        details=f"decision={payload.decision};status={out.status}",
        organization_id=out.organization_id,
        fail_closed=True,
    )
    return out


@router.post("/job-cards/{job_card_id}/release", response_model=JobCardOut)
def release_job_card(
    job_card_id: str,
    payload: JobCardReleaseRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_release),
) -> JobCardOut:
    out = _svc(db).release_job_card(
        job_card_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="job_card.release",
        target_type="job_card",
        target_id=out.id,
        details=f"status={out.status};task_id={out.maintenance_task_id or ''}",
        organization_id=out.organization_id,
        fail_closed=True,
    )
    return out


@router.get("/job-cards/{job_card_id}/attachments", response_model=list[JobCardAttachmentOut])
def list_attachments(
    job_card_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> list[JobCardAttachmentOut]:
    return _svc(db).list_attachments(
        job_card_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.post("/job-cards/{job_card_id}/attachments", response_model=JobCardAttachmentOut, status_code=201)
def add_attachment(
    job_card_id: str,
    payload: JobCardAttachmentCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_execute),
) -> JobCardAttachmentOut:
    out = _svc(db).add_attachment(
        job_card_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="job_card.attachment.create",
        target_type="job_card_attachment",
        target_id=out.id,
        details=f"job_card_id={job_card_id};kind={out.kind}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/dashboard", response_model=ExecutionDashboardOut)
def execution_dashboard(
    organization_id: str | None = None,
    technician_employee_id: str | None = None,
    role: str = "manager",
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> ExecutionDashboardOut:
    return _svc(db).dashboard(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        technician_employee_id=technician_employee_id,
        role=role,
    )


@router.get("/reports/{report}", response_model=ReportSummaryOut)
def execution_report(
    report: str,
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_wo_read),
) -> ReportSummaryOut:
    return _svc(db).report(
        report,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )
