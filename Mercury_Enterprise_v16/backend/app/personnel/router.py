from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..database import get_db
from ..security.runtime_authz import require_allowed
from .schemas import (
    AuthorizationCreate,
    AuthorizationOut,
    EmployeeCreate,
    EmployeeOut,
    EmployeeUpdate,
    QualificationCreate,
    QualificationOut,
    StampCreate,
    StampOut,
)
from .service import PersonnelService

logger = logging.getLogger("mercury.personnel")
router = APIRouter(prefix="/api/v1/personnel", tags=["personnel"])


def _session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return require_session(request)


def require_personnel_read(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(db, session, ("personnel.read",), detail="Insufficient permissions")
    return session


def require_personnel_manage(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(db, session, ("personnel.manage",), detail="Personnel management required")
    return session


def _svc(db: Session) -> PersonnelService:
    return PersonnelService(db)


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
        logger.exception("Failed to record personnel audit action=%s target=%s", action, target_id)


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    organization_id: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_read),
) -> list[EmployeeOut]:
    return _svc(db).list_employees(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_manage),
) -> EmployeeOut:
    out = _svc(db).create_employee(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="personnel.employee.create",
        target_type="personnel_employee",
        target_id=out.id,
        details=f"employee_number={out.employee_number}",
        organization_id=out.organization_id,
    )
    return out


@router.get("/employees/{employee_id}", response_model=EmployeeOut)
def get_employee(
    employee_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_read),
) -> EmployeeOut:
    return _svc(db).get_employee(
        employee_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_manage),
) -> EmployeeOut:
    out = _svc(db).update_employee(
        employee_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    _audit(
        db,
        session,
        action="personnel.employee.update",
        target_type="personnel_employee",
        target_id=out.id,
        details="metadata_update",
        organization_id=out.organization_id,
    )
    return out


@router.get("/employees/{employee_id}/qualifications", response_model=list[QualificationOut])
def list_qualifications(
    employee_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_read),
) -> list[QualificationOut]:
    return _svc(db).list_qualifications(
        employee_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.post("/employees/{employee_id}/qualifications", response_model=QualificationOut, status_code=201)
def create_qualification(
    employee_id: str,
    payload: QualificationCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_manage),
) -> QualificationOut:
    out = _svc(db).create_qualification(
        employee_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    employee = _svc(db).repo.get_employee(employee_id)
    _audit(
        db,
        session,
        action="personnel.qualification.create",
        target_type="personnel_qualification",
        target_id=out.id,
        details=f"employee_id={employee_id};type={out.qualification_type}",
        organization_id=employee.organization_id if employee else None,
    )
    return out


@router.get("/employees/{employee_id}/authorizations", response_model=list[AuthorizationOut])
def list_authorizations(
    employee_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_read),
) -> list[AuthorizationOut]:
    return _svc(db).list_authorizations(
        employee_id, username=str(session["operator"]), session_role=str(session["role"])
    )


@router.post("/employees/{employee_id}/authorizations", response_model=AuthorizationOut, status_code=201)
def create_authorization(
    employee_id: str,
    payload: AuthorizationCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_manage),
) -> AuthorizationOut:
    out = _svc(db).create_authorization(
        employee_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    employee = _svc(db).repo.get_employee(employee_id)
    _audit(
        db,
        session,
        action="personnel.authorization.create",
        target_type="personnel_authorization",
        target_id=out.id,
        details=f"employee_id={employee_id};type={out.auth_type}",
        organization_id=employee.organization_id if employee else None,
    )
    return out


@router.post("/employees/{employee_id}/stamps", response_model=StampOut, status_code=201)
def create_stamp(
    employee_id: str,
    payload: StampCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_personnel_manage),
) -> StampOut:
    out = _svc(db).create_stamp(
        employee_id,
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
    )
    employee = _svc(db).repo.get_employee(employee_id)
    _audit(
        db,
        session,
        action="personnel.stamp.create",
        target_type="digital_stamp_profile",
        target_id=out.id,
        details=f"employee_id={employee_id};stamp_code={out.stamp_code}",
        organization_id=employee.organization_id if employee else None,
    )
    return out
