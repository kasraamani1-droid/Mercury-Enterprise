from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..database import get_db
from ..security.runtime_authz import require_allowed
from .schemas import (
    AdCreate,
    AdOut,
    AircraftStatusOut,
    CheckCreate,
    CheckOut,
    DefectCreate,
    DefectOut,
    DueListOut,
    EoCreate,
    EoOut,
    ForecastOut,
    GeneratePackageOut,
    GeneratePackageRequest,
    HangarPlanCreate,
    HangarPlanOut,
    MelItemCreate,
    MelItemOut,
    MpdTaskCreate,
    MpdTaskOut,
    PlannerDashboardOut,
    ProgramCreate,
    ProgramOut,
    ProgramRevisionCreate,
    ProgramRevisionOut,
    SbCreate,
    SbOut,
    UtilizationOut,
    UtilizationUpsert,
)
from .service import PlanningService

logger = logging.getLogger("mercury.planning")
router = APIRouter(prefix="/api/v1/planning", tags=["planning"])


def _session(request: Request) -> dict[str, datetime | str]:
    from ..main import require_session

    return require_session(request)


def require_planning_read(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("planning.read", "planner.read", "maintenance.read"),
        any_of=True,
        detail="Planning read required",
    )
    return session


def require_planning_manage(request: Request, db: Session = Depends(get_db)) -> dict[str, datetime | str]:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("planning.manage", "work_order.manage", "maintenance.manage"),
        any_of=True,
        detail="Planning manage required",
    )
    return session


def _svc(db: Session) -> PlanningService:
    return PlanningService(db)


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
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("planning audit failed action=%s target=%s", action, target_id)


@router.get("/programs", response_model=list[ProgramOut])
def list_programs(
    organization_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[ProgramOut]:
    return _svc(db).list_programs(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )


@router.post("/programs", response_model=ProgramOut, status_code=201)
def create_program(
    payload: ProgramCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> ProgramOut:
    out = _svc(db).create_program(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.program.create", target_type="maintenance_program", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/programs/{program_id}/revisions", response_model=list[ProgramRevisionOut])
def list_revisions(
    program_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[ProgramRevisionOut]:
    return _svc(db).list_revisions(program_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.post("/programs/{program_id}/revisions", response_model=ProgramRevisionOut, status_code=201)
def add_revision(
    program_id: str,
    payload: ProgramRevisionCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> ProgramRevisionOut:
    out = _svc(db).add_program_revision(
        program_id, payload, username=str(session["operator"]), session_role=str(session["role"])
    )
    _audit(db, session, action="planning.program.revision.create", target_type="maintenance_program_revision", target_id=out.id, organization_id=out.organization_id, details=f"revision={out.revision_number}")
    return out


@router.get("/mpd-tasks", response_model=list[MpdTaskOut])
def list_mpd(
    organization_id: str | None = None,
    program_revision_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[MpdTaskOut]:
    return _svc(db).list_mpd(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        program_revision_id=program_revision_id,
        limit=limit,
        offset=offset,
    )


@router.post("/mpd-tasks", response_model=MpdTaskOut, status_code=201)
def create_mpd(
    payload: MpdTaskCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> MpdTaskOut:
    out = _svc(db).create_mpd_task(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.mpd.create", target_type="mpd_task", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/checks", response_model=list[CheckOut])
def list_checks(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[CheckOut]:
    return _svc(db).list_checks(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        aircraft_id=aircraft_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/checks", response_model=CheckOut, status_code=201)
def create_check(
    payload: CheckCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> CheckOut:
    out = _svc(db).create_check(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.check.create", target_type="maintenance_check", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/checks/{check_id}", response_model=CheckOut)
def get_check(
    check_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> CheckOut:
    return _svc(db).get_check(check_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.post("/checks/generate-package", response_model=GeneratePackageOut, status_code=201)
def generate_package(
    payload: GeneratePackageRequest,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> GeneratePackageOut:
    out = _svc(db).generate_work_package_from_check(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(
        db,
        session,
        action="planning.check.generate_package",
        target_type="work_package",
        target_id=out.work_package_id,
        details=f"check_id={out.check_id};cards={len(out.job_card_ids)}",
    )
    return out


@router.get("/ads", response_model=list[AdOut])
def list_ads(
    organization_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[AdOut]:
    return _svc(db).list_ads(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )


@router.post("/ads", response_model=AdOut, status_code=201)
def create_ad(
    payload: AdCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> AdOut:
    out = _svc(db).create_ad(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.ad.create", target_type="airworthiness_directive", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/ads/{ad_id}", response_model=AdOut)
def get_ad(
    ad_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> AdOut:
    return _svc(db).get_ad(ad_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.get("/service-bulletins", response_model=list[SbOut])
def list_sbs(
    organization_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[SbOut]:
    return _svc(db).list_sbs(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )


@router.post("/service-bulletins", response_model=SbOut, status_code=201)
def create_sb(
    payload: SbCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> SbOut:
    out = _svc(db).create_sb(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.sb.create", target_type="service_bulletin", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/service-bulletins/{sb_id}", response_model=SbOut)
def get_sb(
    sb_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> SbOut:
    return _svc(db).get_sb(sb_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.get("/engineering-orders", response_model=list[EoOut])
def list_eos(
    organization_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[EoOut]:
    return _svc(db).list_eos(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )


@router.post("/engineering-orders", response_model=EoOut, status_code=201)
def create_eo(
    payload: EoCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> EoOut:
    out = _svc(db).create_eo(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.eo.create", target_type="engineering_order", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/engineering-orders/{eo_id}", response_model=EoOut)
def get_eo(
    eo_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> EoOut:
    return _svc(db).get_eo(eo_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.post("/engineering-orders/{eo_id}/approve", response_model=EoOut)
def approve_eo(
    eo_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> EoOut:
    out = _svc(db).approve_eo(eo_id, username=str(session["operator"]), session_role=str(session["role"]))
    _audit(db, session, action="planning.eo.approve", target_type="engineering_order", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/deferred-defects", response_model=list[DefectOut])
def list_defects(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[DefectOut]:
    return _svc(db).list_defects(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        aircraft_id=aircraft_id,
        status=status,
        limit=limit,
    )


@router.post("/deferred-defects", response_model=DefectOut, status_code=201)
def create_defect(
    payload: DefectCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> DefectOut:
    out = _svc(db).create_defect(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.defect.create", target_type="deferred_defect", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/deferred-defects/{defect_id}", response_model=DefectOut)
def get_defect(
    defect_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> DefectOut:
    return _svc(db).get_defect(defect_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.get("/mel-items", response_model=list[MelItemOut])
def list_mel(
    organization_id: str | None = None,
    list_type: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[MelItemOut]:
    return _svc(db).list_mel(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        list_type=list_type,
        limit=limit,
    )


@router.post("/mel-items", response_model=MelItemOut, status_code=201)
def create_mel(
    payload: MelItemCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> MelItemOut:
    out = _svc(db).create_mel(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.mel.create", target_type="mel_item", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/mel-items/{mel_id}", response_model=MelItemOut)
def get_mel(
    mel_id: str,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> MelItemOut:
    return _svc(db).get_mel(mel_id, username=str(session["operator"]), session_role=str(session["role"]))


@router.put("/utilization", response_model=UtilizationOut)
def upsert_utilization(
    payload: UtilizationUpsert,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> UtilizationOut:
    out = _svc(db).upsert_utilization(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.utilization.update", target_type="aircraft_utilization", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/hangar-plans", response_model=list[HangarPlanOut])
def list_hangar(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[HangarPlanOut]:
    return _svc(db).list_hangar_plans(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.post("/hangar-plans", response_model=HangarPlanOut, status_code=201)
def create_hangar(
    payload: HangarPlanCreate,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_manage),
) -> HangarPlanOut:
    out = _svc(db).create_hangar_plan(
        payload,
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
    )
    _audit(db, session, action="planning.hangar.create", target_type="hangar_plan", target_id=out.id, organization_id=out.organization_id)
    return out


@router.get("/forecast", response_model=ForecastOut)
def forecast(
    organization_id: str | None = None,
    aircraft_id: str | None = None,
    horizon_days: int = 90,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> ForecastOut:
    return _svc(db).forecast(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
        aircraft_id=aircraft_id,
        horizon_days=horizon_days,
    )


@router.get("/due-list", response_model=DueListOut)
def due_list(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> DueListOut:
    return _svc(db).due_list(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.get("/dashboard", response_model=PlannerDashboardOut)
def dashboard(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> PlannerDashboardOut:
    return _svc(db).planner_dashboard(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )


@router.get("/aircraft-status", response_model=list[AircraftStatusOut])
def aircraft_status(
    organization_id: str | None = None,
    db: Session = Depends(get_db),
    session: dict[str, datetime | str] = Depends(require_planning_read),
) -> list[AircraftStatusOut]:
    return _svc(db).aircraft_status(
        username=str(session["operator"]),
        session_role=str(session["role"]),
        session_org_id=str(session["organization_id"]),
        organization_id=organization_id,
    )
