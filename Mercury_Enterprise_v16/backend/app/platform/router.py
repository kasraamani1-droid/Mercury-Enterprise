"""Program A — Enterprise Platform Foundation HTTP API."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..security.runtime_authz import require_allowed
from ..shared import ActorContext
from .schemas import (
    ApiKeyCreate,
    ApiKeyOut,
    BusinessUnitCreate,
    BusinessUnitOut,
    CostCenterCreate,
    CostCenterOut,
    CustomRoleCreate,
    CustomRoleOut,
    FacilityCreate,
    FacilityOut,
    FeatureFlagOut,
    FileObjectOut,
    FileRegisterRequest,
    FileUploadMeta,
    MfaEnrollRequest,
    MfaOut,
    NotificationCreate,
    NotificationOut,
    OrgFeatureFlagOut,
    OrgFeatureFlagSet,
    PatCreate,
    PatOut,
    PermissionAuditOut,
    PermissionMatrixOut,
    PlatformOverviewOut,
    RoleTemplateOut,
    SearchHitOut,
    SearchIndexRequest,
    SearchResponse,
    SettingOut,
    SettingUpsert,
    TemporaryAccessCreate,
    TemporaryAccessOut,
    WorkflowDefinitionCreate,
    WorkflowDefinitionOut,
    WorkflowInstanceOut,
    WorkflowStartRequest,
    WorkflowTransitionLogOut,
    WorkflowTransitionRequest,
)
from .service import PlatformService

logger = logging.getLogger("mercury.platform")
router = APIRouter(prefix="/api/v1/platform", tags=["platform"])

Session_ = dict[str, datetime | str]


def _session(request: Request) -> Session_:
    from ..main import require_session

    return require_session(request)


def require_platform_read(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(
        db,
        session,
        ("platform.read", "platform.manage", "org.read"),
        any_of=True,
        detail="Platform read required",
    )
    return session


def require_platform_manage(request: Request, db: Session = Depends(get_db)) -> Session_:
    session = _session(request)
    require_allowed(db, session, ("platform.manage",), detail="Platform manage required")
    return session


def _svc(db: Session) -> PlatformService:
    return PlatformService(db)


def _actor(session: Session_) -> ActorContext:
    return ActorContext(
        username=str(session["operator"]),
        role=str(session["role"]),
        organization_id=str(session["organization_id"]),
        site_id=str(session["site_id"]),
    )


# ---------------------------------------------------------------------------
# Overview / matrix
# ---------------------------------------------------------------------------


@router.get("/overview", response_model=PlatformOverviewOut)
def platform_overview(
    organization_id: str | None = None,
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> PlatformOverviewOut:
    return _svc(db).overview(_actor(session), organization_id=organization_id)


@router.get("/rbac/matrix", response_model=PermissionMatrixOut)
def permission_matrix(
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> PermissionMatrixOut:
    return _svc(db).permission_matrix(_actor(session))


@router.get("/rbac/templates", response_model=list[RoleTemplateOut])
def list_role_templates(
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[RoleTemplateOut]:
    _ = session
    return _svc(db).list_role_templates()


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


@router.post("/identity/api-keys", response_model=ApiKeyOut, status_code=201)
def create_api_key(
    payload: ApiKeyCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> ApiKeyOut:
    return _svc(db).create_api_key(payload, _actor(session))


@router.get("/identity/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> list[ApiKeyOut]:
    return _svc(db).list_api_keys(_actor(session), organization_id=organization_id, limit=limit, offset=offset)


@router.post("/identity/api-keys/{key_id}/revoke", response_model=ApiKeyOut)
def revoke_api_key(
    key_id: str,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> ApiKeyOut:
    return _svc(db).revoke_api_key(key_id, _actor(session))


@router.post("/identity/pats", response_model=PatOut, status_code=201)
def create_pat(
    payload: PatCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> PatOut:
    return _svc(db).create_pat(payload, _actor(session))


@router.get("/identity/pats", response_model=list[PatOut])
def list_pats(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> list[PatOut]:
    return _svc(db).list_pats(_actor(session), organization_id=organization_id, limit=limit, offset=offset)


@router.post("/identity/pats/{pat_id}/revoke", response_model=PatOut)
def revoke_pat(
    pat_id: str,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> PatOut:
    return _svc(db).revoke_pat(pat_id, _actor(session))


@router.post("/identity/mfa/enroll", response_model=MfaOut, status_code=201)
def enroll_mfa(
    payload: MfaEnrollRequest,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> MfaOut:
    return _svc(db).enroll_mfa(payload, _actor(session))


@router.get("/identity/mfa", response_model=MfaOut | None)
def get_mfa(
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> MfaOut | None:
    return _svc(db).get_mfa(_actor(session))


# ---------------------------------------------------------------------------
# Organization extensions
# ---------------------------------------------------------------------------


@router.post("/org/business-units", response_model=BusinessUnitOut, status_code=201)
def create_business_unit(
    payload: BusinessUnitCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> BusinessUnitOut:
    return _svc(db).create_business_unit(payload, _actor(session))


@router.get("/org/business-units", response_model=list[BusinessUnitOut])
def list_business_units(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[BusinessUnitOut]:
    return _svc(db).list_business_units(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )


@router.post("/org/cost-centers", response_model=CostCenterOut, status_code=201)
def create_cost_center(
    payload: CostCenterCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> CostCenterOut:
    return _svc(db).create_cost_center(payload, _actor(session))


@router.get("/org/cost-centers", response_model=list[CostCenterOut])
def list_cost_centers(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[CostCenterOut]:
    return _svc(db).list_cost_centers(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )


@router.post("/org/facilities", response_model=FacilityOut, status_code=201)
def create_facility(
    payload: FacilityCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> FacilityOut:
    return _svc(db).create_facility(payload, _actor(session))


@router.get("/org/facilities", response_model=list[FacilityOut])
def list_facilities(
    organization_id: str | None = None,
    facility_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[FacilityOut]:
    return _svc(db).list_facilities(
        _actor(session),
        organization_id=organization_id,
        facility_type=facility_type,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


@router.post("/rbac/roles", response_model=CustomRoleOut, status_code=201)
def create_custom_role(
    payload: CustomRoleCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> CustomRoleOut:
    return _svc(db).create_custom_role(payload, _actor(session))


@router.get("/rbac/roles", response_model=list[CustomRoleOut])
def list_custom_roles(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[CustomRoleOut]:
    return _svc(db).list_custom_roles(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )


@router.post("/rbac/temporary-access", response_model=TemporaryAccessOut, status_code=201)
def grant_temporary_access(
    payload: TemporaryAccessCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> TemporaryAccessOut:
    return _svc(db).grant_temporary_access(payload, _actor(session))


@router.get("/rbac/temporary-access", response_model=list[TemporaryAccessOut])
def list_temporary_access(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[TemporaryAccessOut]:
    return _svc(db).list_temporary_access(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )


@router.get("/rbac/permission-audits", response_model=list[PermissionAuditOut])
def list_permission_audits(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[PermissionAuditOut]:
    return _svc(db).list_permission_audits(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


@router.post("/workflows/definitions", response_model=WorkflowDefinitionOut, status_code=201)
def create_workflow_definition(
    payload: WorkflowDefinitionCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> WorkflowDefinitionOut:
    return _svc(db).create_workflow_definition(payload, _actor(session))


@router.get("/workflows/definitions", response_model=list[WorkflowDefinitionOut])
def list_workflow_definitions(
    organization_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[WorkflowDefinitionOut]:
    return _svc(db).list_workflow_definitions(
        _actor(session), organization_id=organization_id, limit=limit, offset=offset
    )


@router.post("/workflows/instances", response_model=WorkflowInstanceOut, status_code=201)
def start_workflow(
    payload: WorkflowStartRequest,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> WorkflowInstanceOut:
    return _svc(db).start_workflow(payload, _actor(session))


@router.get("/workflows/instances", response_model=list[WorkflowInstanceOut])
def list_workflow_instances(
    organization_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[WorkflowInstanceOut]:
    return _svc(db).list_workflow_instances(
        _actor(session),
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )


@router.post("/workflows/instances/{instance_id}/transition", response_model=WorkflowInstanceOut)
def transition_workflow(
    instance_id: str,
    payload: WorkflowTransitionRequest,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> WorkflowInstanceOut:
    return _svc(db).transition_workflow(instance_id, payload, _actor(session))


@router.get("/workflows/instances/{instance_id}/logs", response_model=list[WorkflowTransitionLogOut])
def list_workflow_logs(
    instance_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[WorkflowTransitionLogOut]:
    return _svc(db).list_workflow_logs(instance_id, _actor(session), limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@router.post("/notifications", response_model=NotificationOut, status_code=201)
def enqueue_notification(
    payload: NotificationCreate,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> NotificationOut:
    return _svc(db).enqueue_notification(payload, _actor(session))


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    organization_id: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[NotificationOut]:
    return _svc(db).list_notifications(
        _actor(session), organization_id=organization_id, status=status_filter, limit=limit, offset=offset
    )


@router.post("/notifications/{notification_id}/sent", response_model=NotificationOut)
def mark_notification_sent(
    notification_id: str,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> NotificationOut:
    return _svc(db).mark_notification_sent(notification_id, _actor(session))


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: str,
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> NotificationOut:
    return _svc(db).mark_notification_read(notification_id, _actor(session))


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


@router.post("/files", response_model=FileObjectOut, status_code=201)
def register_file(
    payload: FileRegisterRequest,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> FileObjectOut:
    return _svc(db).register_file(payload, _actor(session))


@router.post("/files/upload", response_model=FileObjectOut, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    organization_id: str | None = Form(default=None),
    file_class: str = Form(default="other"),
    entity_type: str = Form(default=""),
    entity_id: str = Form(default=""),
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> FileObjectOut:
    """Write bytes to local disk object store and register metadata."""
    content = await file.read()
    return _svc(db).upload_file_bytes(
        actor=_actor(session),
        filename=file.filename or "upload.bin",
        content=content,
        content_type=file.content_type or "application/octet-stream",
        meta=FileUploadMeta(
            organization_id=organization_id,
            file_class=file_class,
            entity_type=entity_type,
            entity_id=entity_id,
        ),
    )


@router.get("/files", response_model=list[FileObjectOut])
def list_files(
    organization_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[FileObjectOut]:
    return _svc(db).list_files(
        _actor(session),
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )


@router.delete("/files/{file_id}", response_model=FileObjectOut)
def soft_delete_file(
    file_id: str,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> FileObjectOut:
    return _svc(db).soft_delete_file(file_id, _actor(session))


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@router.post("/search/index", response_model=SearchHitOut, status_code=201)
def index_document(
    payload: SearchIndexRequest,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> SearchHitOut:
    return _svc(db).index_document(payload, _actor(session))


@router.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., min_length=1),
    organization_id: str | None = None,
    doc_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> SearchResponse:
    return _svc(db).search(
        _actor(session),
        query=q,
        organization_id=organization_id,
        doc_type=doc_type,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@router.put("/settings", response_model=SettingOut)
def upsert_setting(
    payload: SettingUpsert,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> SettingOut:
    return _svc(db).upsert_setting(payload, _actor(session))


@router.get("/settings", response_model=list[SettingOut])
def list_settings(
    organization_id: str | None = None,
    category: str | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[SettingOut]:
    return _svc(db).list_settings(
        _actor(session), organization_id=organization_id, category=category, limit=limit, offset=offset
    )


@router.get("/feature-flags", response_model=list[FeatureFlagOut])
def list_feature_flags(
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[FeatureFlagOut]:
    _ = session
    return _svc(db).list_feature_flags()


@router.put("/feature-flags/org", response_model=OrgFeatureFlagOut)
def set_org_feature_flag(
    payload: OrgFeatureFlagSet,
    session: Session_ = Depends(require_platform_manage),
    db: Session = Depends(get_db),
) -> OrgFeatureFlagOut:
    return _svc(db).set_org_feature_flag(payload, _actor(session))


@router.get("/feature-flags/org", response_model=list[OrgFeatureFlagOut])
def list_org_feature_flags(
    organization_id: str | None = None,
    session: Session_ = Depends(require_platform_read),
    db: Session = Depends(get_db),
) -> list[OrgFeatureFlagOut]:
    return _svc(db).list_org_feature_flags(_actor(session), organization_id=organization_id)


@router.get("/integrations")
def list_integrations(
    category: str | None = None,
    session: Session_ = Depends(require_platform_read),
) -> list[dict]:
    _ = session
    from .integration_framework import integration_framework

    return [
        {
            "code": d.code,
            "name": d.name,
            "category": d.category,
            "vendor": d.vendor,
            "capabilities": d.capabilities,
            "status": d.status,
        }
        for d in integration_framework.list(category=category)
    ]


@router.get("/integrations/health")
def integrations_health(
    session: Session_ = Depends(require_platform_read),
) -> dict:
    _ = session
    from .integration_framework import integration_framework

    return integration_framework.health_report()
