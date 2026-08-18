"""Program A — Enterprise Platform Foundation service.

Reusable identity, organization extensions, RBAC extensions, generic workflow,
notifications, files, search, and configuration. Domain modules must call these
services rather than re-implementing platform concerns.
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..org.service import OrganizationService
from ..security.authorization import PERMISSIONS_BY_ROLE, Role
from ..shared import ActorContext
from .models import (
    PlatformApiKey,
    PlatformBusinessUnit,
    PlatformCostCenter,
    PlatformCustomRole,
    PlatformFacility,
    PlatformFeatureFlag,
    PlatformFileObject,
    PlatformMfaEnrollment,
    PlatformNotification,
    PlatformOrgFeatureFlag,
    PlatformPermissionAudit,
    PlatformPersonalAccessToken,
    PlatformRoleTemplate,
    PlatformSearchDocument,
    PlatformSetting,
    PlatformTemporaryAccess,
    PlatformWorkflowDefinition,
    PlatformWorkflowInstance,
    PlatformWorkflowTransitionLog,
)
from .repository import PlatformRepository
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

logger = logging.getLogger("mercury.platform")

DEFAULT_STATES = [
    "draft",
    "assigned",
    "in_progress",
    "waiting",
    "inspection",
    "rejected",
    "released",
    "archived",
]

DEFAULT_TRANSITIONS = {
    "draft": ["assigned", "archived"],
    "assigned": ["in_progress", "waiting", "rejected"],
    "in_progress": ["waiting", "inspection", "rejected"],
    "waiting": ["in_progress", "assigned", "rejected"],
    "inspection": ["released", "rejected", "in_progress"],
    "rejected": ["draft", "archived"],
    "released": ["archived"],
    "archived": [],
}

ROLE_TEMPLATES = [
    (
        "aviation.technician",
        "Aviation Technician",
        "Execute maintenance tasks and job cards",
        "task.read,task.manage,work_order.read,work_order.execute,maintenance.read,publication.read,component.read,fleet.read,platform.read",
        "aviation",
    ),
    (
        "aviation.inspector",
        "Aviation Inspector",
        "Inspect and approve completed work",
        "work_order.read,work_order.execute,inspector.approve,qa.read,certification.sign,maintenance.read,platform.read",
        "aviation",
    ),
    (
        "aviation.planner",
        "Maintenance Planner",
        "Plan checks, forecasts, and work packages",
        "planning.read,planning.manage,work_order.read,work_order.manage,fleet.read,maintenance.read,platform.read",
        "aviation",
    ),
    (
        "platform.admin",
        "Platform Administrator",
        "Manage platform identity, RBAC, config, and workflow definitions",
        "platform.read,platform.manage,org.read,audit.read",
        "system",
    ),
]

FEATURE_FLAGS = [
    ("platform.workflow_engine", "Generic workflow engine", "true"),
    ("platform.notifications", "Multi-channel notification platform", "true"),
    ("platform.global_search", "Enterprise global search", "true"),
    ("platform.mfa_required", "Require MFA for privileged roles", "false"),
    ("platform.sso_ready", "SSO integration surface (future)", "false"),
]


def _hash_secret(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _token_pair(prefix_len: int = 8) -> tuple[str, str, str]:
    """Return (prefix, full_secret, hash). Secret shown once to caller."""
    raw = secrets.token_urlsafe(32)
    prefix = raw[:prefix_len]
    return prefix, raw, _hash_secret(raw)


class PlatformService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PlatformRepository(db)
        self.org = OrganizationService(db)

    def _commit_or_conflict(self, *, detail: str) -> None:
        try:
            self.repo.commit()
        except IntegrityError as exc:
            self.repo.rollback()
            raise HTTPException(status_code=409, detail=detail) from exc

    def _audit_required(
        self,
        actor: ActorContext | None,
        *,
        action: str,
        target_type: str,
        target_id: str,
        organization_id: str | None = None,
        details: str = "",
    ) -> None:
        """Fail-closed audit — never bypassable for platform mutations."""
        if actor is None:
            return
        try:
            record_audit(
                self.db,
                action=action,
                actor=actor.username,
                actor_role=actor.role,
                organization_id=organization_id or actor.organization_id,
                site_id=actor.site_id,
                target_type=target_type,
                target_id=target_id,
                source="api",
                outcome="success",
                origin="operator",
                details=details,
            )
            self.repo.flush()
        except Exception as exc:
            self.repo.rollback()
            logger.exception("platform audit failed action=%s target=%s", action, target_id)
            raise HTTPException(
                status_code=500, detail="Audit trail write failed; operation rolled back"
            ) from exc

    def resolve_org_id(self, actor: ActorContext, requested_org_id: str | None = None) -> str:
        org_id = (requested_org_id or actor.organization_id or "").strip()
        if not org_id:
            raise HTTPException(status_code=400, detail="Organization is required")
        self.org.assert_org_access(
            username=actor.username, session_role=actor.role, organization_id=org_id
        )
        return org_id

    def _permission_audit(
        self,
        *,
        org_id: str,
        actor: ActorContext,
        change_type: str,
        target_username: str = "",
        details: str = "",
    ) -> None:
        self.repo.add(
            PlatformPermissionAudit(
                organization_id=org_id,
                actor=actor.username,
                target_username=target_username,
                change_type=change_type,
                details=details,
            )
        )

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------
    def seed_platform(self, organization_id: str = "org-aviation-east") -> dict[str, int]:
        created = {
            "templates": 0,
            "flags": 0,
            "workflow": 0,
            "facilities": 0,
            "settings": 0,
            "search": 0,
        }
        for code, name, desc, perms, ttype in ROLE_TEMPLATES:
            if self.repo.get_role_template_by_code(code) is None:
                self.repo.add(
                    PlatformRoleTemplate(
                        code=code,
                        name=name,
                        description=desc,
                        permissions=perms,
                        template_type=ttype,
                    )
                )
                created["templates"] += 1

        for code, desc, enabled in FEATURE_FLAGS:
            if self.repo.get_feature_flag(code) is None:
                self.repo.add(
                    PlatformFeatureFlag(code=code, description=desc, enabled_global=enabled)
                )
                created["flags"] += 1

        if self.repo.get_workflow_definition_by_code(organization_id, "enterprise.default") is None:
            self.repo.add(
                PlatformWorkflowDefinition(
                    organization_id=organization_id,
                    code="enterprise.default",
                    name="Enterprise Default Lifecycle",
                    states_json=json.dumps(DEFAULT_STATES),
                    transitions_json=json.dumps(DEFAULT_TRANSITIONS),
                    version=1,
                )
            )
            created["workflow"] += 1

        from .workflow_bridge import (
            JOB_CARD_STATES,
            JOB_CARD_TRANSITIONS,
            JOB_CARD_WORKFLOW_CODE,
        )

        if self.repo.get_workflow_definition_by_code(organization_id, JOB_CARD_WORKFLOW_CODE) is None:
            self.repo.add(
                PlatformWorkflowDefinition(
                    organization_id=organization_id,
                    code=JOB_CARD_WORKFLOW_CODE,
                    name="Work Order Job Card Lifecycle",
                    states_json=json.dumps(JOB_CARD_STATES),
                    transitions_json=json.dumps(JOB_CARD_TRANSITIONS),
                    version=1,
                )
            )
            created["workflow"] += 1

        if not self.repo.list_facilities(organization_id=organization_id, limit=1):
            for code, name, ftype in (
                ("HGR-1", "Hangar 1", "hangar"),
                ("SHOP-AV", "Avionics Shop", "shop"),
                ("STN-GATE", "Gate Station", "station"),
            ):
                self.repo.add(
                    PlatformFacility(
                        organization_id=organization_id,
                        code=code,
                        name=name,
                        facility_type=ftype,
                        country_code="US",
                    )
                )
                created["facilities"] += 1

        if self.repo.get_setting(organization_id, "timezone") is None:
            for key, value, category in (
                ("timezone", "America/New_York", "regional"),
                ("units", "imperial", "regional"),
                ("language", "en", "regional"),
                ("license.tier", "enterprise", "license"),
            ):
                self.repo.add(
                    PlatformSetting(
                        organization_id=organization_id,
                        key=key,
                        value=value,
                        category=category,
                        updated_by="system",
                    )
                )
                created["settings"] += 1

        if self.repo.upsert_search_document(organization_id, "organization", organization_id) is None:
            self.repo.add(
                PlatformSearchDocument(
                    organization_id=organization_id,
                    doc_type="organization",
                    entity_id=organization_id,
                    title="Aviation East",
                    body="Primary Mercury aviation organization",
                    keywords="mro,camo,airline,east",
                )
            )
            created["search"] += 1

        self.repo.commit()
        return created

    # ------------------------------------------------------------------
    # Identity — API keys / PATs / MFA
    # ------------------------------------------------------------------
    def create_api_key(self, payload: ApiKeyCreate, actor: ActorContext) -> ApiKeyOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        prefix, secret, hashed = _token_pair()
        row = PlatformApiKey(
            organization_id=org_id,
            name=payload.name.strip(),
            key_prefix=prefix,
            key_hash=hashed,
            scopes=payload.scopes.strip(),
            created_by=actor.username,
            expires_at=payload.expires_at,
        )
        self.repo.add(row)
        self.repo.flush()
        self._audit_required(
            actor,
            action="platform.api_key.create",
            target_type="platform_api_key",
            target_id=row.id,
            organization_id=org_id,
            details=payload.name,
        )
        self._commit_or_conflict(detail="API key conflict")
        out = ApiKeyOut.model_validate(row)
        out.secret = secret
        return out

    def list_api_keys(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[ApiKeyOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [ApiKeyOut.model_validate(r) for r in self.repo.list_api_keys(organization_id=org_id, limit=limit, offset=offset)]

    def revoke_api_key(self, key_id: str, actor: ActorContext) -> ApiKeyOut:
        org_id = self.resolve_org_id(actor)
        row = self.repo.get_api_key(org_id, key_id)
        if row is None:
            raise HTTPException(status_code=404, detail="API key not found")
        row.status = "revoked"
        row.revoked_at = datetime.utcnow()
        self._audit_required(
            actor,
            action="platform.api_key.revoke",
            target_type="platform_api_key",
            target_id=row.id,
            organization_id=org_id,
        )
        self.repo.commit()
        return ApiKeyOut.model_validate(row)

    def create_pat(self, payload: PatCreate, actor: ActorContext) -> PatOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        prefix, secret, hashed = _token_pair()
        row = PlatformPersonalAccessToken(
            organization_id=org_id,
            username=actor.username,
            name=payload.name.strip(),
            token_prefix=prefix,
            token_hash=hashed,
            scopes=payload.scopes.strip(),
            expires_at=payload.expires_at,
        )
        self.repo.add(row)
        self._audit_required(
            actor,
            action="platform.pat.create",
            target_type="platform_pat",
            target_id=row.id,
            organization_id=org_id,
            details=payload.name,
        )
        self._commit_or_conflict(detail="PAT conflict")
        out = PatOut.model_validate(row)
        out.secret = secret
        return out

    def list_pats(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[PatOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            PatOut.model_validate(r)
            for r in self.repo.list_pats(organization_id=org_id, username=actor.username, limit=limit, offset=offset)
        ]

    def revoke_pat(self, pat_id: str, actor: ActorContext) -> PatOut:
        org_id = self.resolve_org_id(actor)
        row = self.repo.get_pat(org_id, pat_id)
        if row is None or row.username != actor.username:
            raise HTTPException(status_code=404, detail="PAT not found")
        row.status = "revoked"
        row.revoked_at = datetime.utcnow()
        self._audit_required(
            actor,
            action="platform.pat.revoke",
            target_type="platform_pat",
            target_id=row.id,
            organization_id=org_id,
        )
        self.repo.commit()
        return PatOut.model_validate(row)

    def enroll_mfa(self, payload: MfaEnrollRequest, actor: ActorContext) -> MfaOut:
        existing = self.repo.get_mfa(actor.username)
        setup_ref = f"vault://mfa/{actor.username}/{uuid.uuid4().hex[:12]}"
        if existing is None:
            existing = PlatformMfaEnrollment(
                username=actor.username,
                method=payload.method,
                secret_ref=setup_ref,
                enabled="false",
            )
            self.repo.add(existing)
        else:
            existing.method = payload.method
            existing.secret_ref = setup_ref
            existing.enabled = "false"
            existing.verified_at = None
            existing.updated_at = datetime.utcnow()
        self._audit_required(
            actor,
            action="platform.mfa.enroll",
            target_type="platform_mfa",
            target_id=existing.id or actor.username,
            details=payload.method,
        )
        self.repo.commit()
        out = MfaOut.model_validate(existing)
        out.setup_ref = setup_ref
        return out

    def get_mfa(self, actor: ActorContext) -> MfaOut | None:
        row = self.repo.get_mfa(actor.username)
        return MfaOut.model_validate(row) if row else None

    # ------------------------------------------------------------------
    # Organization extensions
    # ------------------------------------------------------------------
    def create_business_unit(self, payload: BusinessUnitCreate, actor: ActorContext) -> BusinessUnitOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        row = PlatformBusinessUnit(
            organization_id=org_id,
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
            country_code=payload.country_code.strip().upper(),
        )
        self.repo.add(row)
        self._audit_required(
            actor,
            action="platform.business_unit.create",
            target_type="platform_business_unit",
            target_id=row.id,
            organization_id=org_id,
        )
        self._commit_or_conflict(detail="Business unit code already exists")
        return BusinessUnitOut.model_validate(row)

    def list_business_units(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[BusinessUnitOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            BusinessUnitOut.model_validate(r)
            for r in self.repo.list_business_units(organization_id=org_id, limit=limit, offset=offset)
        ]

    def create_cost_center(self, payload: CostCenterCreate, actor: ActorContext) -> CostCenterOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        if payload.business_unit_id and self.repo.get_business_unit(org_id, payload.business_unit_id) is None:
            raise HTTPException(status_code=404, detail="Business unit not found")
        row = PlatformCostCenter(
            organization_id=org_id,
            business_unit_id=payload.business_unit_id,
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
        )
        self.repo.add(row)
        self._audit_required(
            actor,
            action="platform.cost_center.create",
            target_type="platform_cost_center",
            target_id=row.id,
            organization_id=org_id,
        )
        self._commit_or_conflict(detail="Cost center code already exists")
        return CostCenterOut.model_validate(row)

    def list_cost_centers(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[CostCenterOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            CostCenterOut.model_validate(r)
            for r in self.repo.list_cost_centers(organization_id=org_id, limit=limit, offset=offset)
        ]

    def create_facility(self, payload: FacilityCreate, actor: ActorContext) -> FacilityOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        row = PlatformFacility(
            organization_id=org_id,
            site_id=payload.site_id,
            code=payload.code.strip().upper(),
            name=payload.name.strip(),
            facility_type=payload.facility_type,
            country_code=payload.country_code.strip().upper(),
            address=payload.address.strip(),
        )
        self.repo.add(row)
        self._audit_required(
            actor,
            action="platform.facility.create",
            target_type="platform_facility",
            target_id=row.id,
            organization_id=org_id,
        )
        self._commit_or_conflict(detail="Facility code already exists")
        return FacilityOut.model_validate(row)

    def list_facilities(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        facility_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FacilityOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            FacilityOut.model_validate(r)
            for r in self.repo.list_facilities(
                organization_id=org_id, facility_type=facility_type, limit=limit, offset=offset
            )
        ]

    # ------------------------------------------------------------------
    # RBAC extensions
    # ------------------------------------------------------------------
    def list_role_templates(self) -> list[RoleTemplateOut]:
        return [RoleTemplateOut.model_validate(r) for r in self.repo.list_role_templates()]

    def create_custom_role(self, payload: CustomRoleCreate, actor: ActorContext) -> CustomRoleOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        row = PlatformCustomRole(
            organization_id=org_id,
            code=payload.code.strip().lower(),
            name=payload.name.strip(),
            permissions=payload.permissions.strip(),
            template_id=payload.template_id,
            created_by=actor.username,
        )
        self.repo.add(row)
        self._permission_audit(
            org_id=org_id,
            actor=actor,
            change_type="role",
            details=f"created custom role {row.code}: {row.permissions}",
        )
        self._audit_required(
            actor,
            action="platform.role.create",
            target_type="platform_custom_role",
            target_id=row.id,
            organization_id=org_id,
            details=row.code,
        )
        self._commit_or_conflict(detail="Custom role code already exists")
        return CustomRoleOut.model_validate(row)

    def list_custom_roles(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[CustomRoleOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            CustomRoleOut.model_validate(r)
            for r in self.repo.list_custom_roles(organization_id=org_id, limit=limit, offset=offset)
        ]

    def grant_temporary_access(
        self, payload: TemporaryAccessCreate, actor: ActorContext
    ) -> TemporaryAccessOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        if payload.ends_at <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="ends_at must be in the future")
        row = PlatformTemporaryAccess(
            organization_id=org_id,
            username=payload.username.strip(),
            permissions=payload.permissions.strip(),
            reason=payload.reason.strip(),
            approved_by=actor.username,
            starts_at=payload.starts_at or datetime.utcnow(),
            ends_at=payload.ends_at,
        )
        self.repo.add(row)
        self._permission_audit(
            org_id=org_id,
            actor=actor,
            change_type="temp",
            target_username=row.username,
            details=f"temp grant until {row.ends_at.isoformat()}: {row.permissions}",
        )
        self._audit_required(
            actor,
            action="platform.temp_access.grant",
            target_type="platform_temporary_access",
            target_id=row.id,
            organization_id=org_id,
            details=row.username,
        )
        self.repo.commit()
        return TemporaryAccessOut.model_validate(row)

    def list_temporary_access(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[TemporaryAccessOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            TemporaryAccessOut.model_validate(r)
            for r in self.repo.list_temporary_access(organization_id=org_id, limit=limit, offset=offset)
        ]

    def list_permission_audits(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[PermissionAuditOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            PermissionAuditOut.model_validate(r)
            for r in self.repo.list_permission_audits(organization_id=org_id, limit=limit, offset=offset)
        ]

    def permission_matrix(self, actor: ActorContext) -> PermissionMatrixOut:
        self.resolve_org_id(actor)
        roles = {role.value: sorted(perms) for role, perms in PERMISSIONS_BY_ROLE.items()}
        # Expand Administrator wildcard for documentation clarity
        roles[Role.ADMINISTRATOR.value] = ["*"]
        return PermissionMatrixOut(roles=roles, templates=self.list_role_templates())

    # ------------------------------------------------------------------
    # Workflow engine
    # ------------------------------------------------------------------
    def create_workflow_definition(
        self, payload: WorkflowDefinitionCreate, actor: ActorContext
    ) -> WorkflowDefinitionOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        try:
            states = json.loads(payload.states_json)
            transitions = json.loads(payload.transitions_json)
            if not isinstance(states, list) or not isinstance(transitions, dict):
                raise ValueError("invalid shape")
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid states_json or transitions_json") from exc
        existing = self.repo.get_workflow_definition_by_code(org_id, payload.code.strip())
        version = (existing.version + 1) if existing else 1
        if existing:
            existing.status = "superseded"
        row = PlatformWorkflowDefinition(
            organization_id=org_id,
            code=payload.code.strip(),
            name=payload.name.strip(),
            states_json=json.dumps(states),
            transitions_json=json.dumps(transitions),
            version=version,
        )
        self.repo.add(row)
        self._audit_required(
            actor,
            action="platform.workflow.definition.create",
            target_type="platform_workflow_definition",
            target_id=row.id,
            organization_id=org_id,
            details=f"{row.code}@v{version}",
        )
        self._commit_or_conflict(detail="Workflow definition conflict")
        return WorkflowDefinitionOut.model_validate(row)

    def list_workflow_definitions(
        self, actor: ActorContext, *, organization_id: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[WorkflowDefinitionOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            WorkflowDefinitionOut.model_validate(r)
            for r in self.repo.list_workflow_definitions(organization_id=org_id, limit=limit, offset=offset)
        ]

    def start_workflow(self, payload: WorkflowStartRequest, actor: ActorContext) -> WorkflowInstanceOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        definition = self.repo.get_workflow_definition_by_code(org_id, payload.definition_code.strip())
        if definition is None:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
        states = json.loads(definition.states_json or "[]")
        initial = payload.initial_state.strip() or "draft"
        if states and initial not in states:
            raise HTTPException(status_code=400, detail=f"State '{initial}' not in definition")
        row = PlatformWorkflowInstance(
            organization_id=org_id,
            definition_id=definition.id,
            entity_type=payload.entity_type.strip(),
            entity_id=payload.entity_id.strip(),
            current_state=initial,
            assigned_to=payload.assigned_to.strip(),
            status=initial,
            created_by=actor.username,
        )
        self.repo.add(row)
        self.repo.flush()
        self.repo.add(
            PlatformWorkflowTransitionLog(
                organization_id=org_id,
                instance_id=row.id,
                from_state="",
                to_state=initial,
                performed_by=actor.username,
                comment="workflow started",
            )
        )
        self._audit_required(
            actor,
            action="platform.workflow.start",
            target_type="platform_workflow_instance",
            target_id=row.id,
            organization_id=org_id,
            details=f"{payload.entity_type}:{payload.entity_id}",
        )
        self.repo.commit()
        return WorkflowInstanceOut.model_validate(row)

    def transition_workflow(
        self, instance_id: str, payload: WorkflowTransitionRequest, actor: ActorContext
    ) -> WorkflowInstanceOut:
        org_id = self.resolve_org_id(actor)
        row = self.repo.get_workflow_instance(org_id, instance_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        definition = self.repo.get_workflow_definition(org_id, row.definition_id)
        if definition is None:
            raise HTTPException(status_code=404, detail="Workflow definition not found")
        transitions = json.loads(definition.transitions_json or "{}")
        allowed = transitions.get(row.current_state, [])
        to_state = payload.to_state.strip()
        if to_state not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Transition {row.current_state} → {to_state} not allowed",
            )
        from_state = row.current_state
        row.current_state = to_state
        row.status = to_state
        row.updated_at = datetime.utcnow()
        if payload.assigned_to is not None:
            row.assigned_to = payload.assigned_to.strip()
        if to_state in {"released", "archived"}:
            row.closed_at = datetime.utcnow()
        self.repo.add(
            PlatformWorkflowTransitionLog(
                organization_id=org_id,
                instance_id=row.id,
                from_state=from_state,
                to_state=to_state,
                performed_by=actor.username,
                comment=payload.comment.strip(),
            )
        )
        self._audit_required(
            actor,
            action="platform.workflow.transition",
            target_type="platform_workflow_instance",
            target_id=row.id,
            organization_id=org_id,
            details=f"{from_state}->{to_state}",
        )
        self.repo.commit()
        return WorkflowInstanceOut.model_validate(row)

    def list_workflow_instances(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorkflowInstanceOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            WorkflowInstanceOut.model_validate(r)
            for r in self.repo.list_workflow_instances(
                organization_id=org_id,
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit,
                offset=offset,
            )
        ]

    def list_workflow_logs(
        self, instance_id: str, actor: ActorContext, *, limit: int = 100, offset: int = 0
    ) -> list[WorkflowTransitionLogOut]:
        org_id = self.resolve_org_id(actor)
        if self.repo.get_workflow_instance(org_id, instance_id) is None:
            raise HTTPException(status_code=404, detail="Workflow instance not found")
        return [
            WorkflowTransitionLogOut.model_validate(r)
            for r in self.repo.list_transition_logs(instance_id=instance_id, limit=limit, offset=offset)
        ]

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def enqueue_notification(self, payload: NotificationCreate, actor: ActorContext) -> NotificationOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        row = PlatformNotification(
            organization_id=org_id,
            recipient=payload.recipient.strip(),
            channel=payload.channel,
            event_type=payload.event_type.strip(),
            title=payload.title.strip(),
            body=payload.body.strip(),
            payload_json=payload.payload_json,
            status="pending",
        )
        self.repo.add(row)
        self._audit_required(
            actor,
            action="platform.notification.enqueue",
            target_type="platform_notification",
            target_id=row.id,
            organization_id=org_id,
            details=f"{payload.channel}:{payload.event_type}",
        )
        self.repo.commit()
        return NotificationOut.model_validate(row)

    def list_notifications(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            NotificationOut.model_validate(r)
            for r in self.repo.list_notifications(
                organization_id=org_id, status=status, limit=limit, offset=offset
            )
        ]

    def mark_notification_sent(self, notification_id: str, actor: ActorContext) -> NotificationOut:
        org_id = self.resolve_org_id(actor)
        row = self.repo.get_notification(org_id, notification_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        row.status = "sent"
        row.sent_at = datetime.utcnow()
        self._audit_required(
            actor,
            action="platform.notification.sent",
            target_type="platform_notification",
            target_id=row.id,
            organization_id=org_id,
        )
        self.repo.commit()
        return NotificationOut.model_validate(row)

    def mark_notification_read(self, notification_id: str, actor: ActorContext) -> NotificationOut:
        org_id = self.resolve_org_id(actor)
        row = self.repo.get_notification(org_id, notification_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Notification not found")
        row.status = "read"
        row.read_at = datetime.utcnow()
        self.repo.commit()
        return NotificationOut.model_validate(row)

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------
    def register_file(self, payload: FileRegisterRequest, actor: ActorContext) -> FileObjectOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        version = 1
        if payload.entity_type and payload.entity_id:
            version = (
                self.repo.latest_file_version(
                    org_id, payload.entity_type, payload.entity_id, payload.filename.strip()
                )
                + 1
            )
        row = PlatformFileObject(
            organization_id=org_id,
            filename=payload.filename.strip(),
            content_type=payload.content_type.strip(),
            file_class=payload.file_class,
            storage_uri=payload.storage_uri.strip(),
            sha256=payload.sha256.strip().lower(),
            size_bytes=payload.size_bytes,
            virus_scan_status=payload.virus_scan_status,
            entity_type=payload.entity_type.strip(),
            entity_id=payload.entity_id.strip(),
            version=version,
            uploaded_by=actor.username,
        )
        self.repo.add(row)
        self._audit_required(
            actor,
            action="platform.file.register",
            target_type="platform_file",
            target_id=row.id,
            organization_id=org_id,
            details=f"{row.filename}@v{version}",
        )
        self.repo.commit()
        return FileObjectOut.model_validate(row)

    def upload_file_bytes(
        self,
        *,
        actor: ActorContext,
        filename: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        meta: FileUploadMeta | None = None,
    ) -> FileObjectOut:
        """Persist bytes to local disk and register platform file metadata."""
        from .file_storage import local_disk_store

        meta = meta or FileUploadMeta()
        org_id = self.resolve_org_id(actor, meta.organization_id)
        if not content:
            raise HTTPException(status_code=400, detail="Empty upload")
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Upload exceeds 25 MiB limit")
        uri, digest, size = local_disk_store.put_bytes(
            organization_id=org_id,
            filename=filename,
            content=content,
            content_type=content_type,
        )
        return self.register_file(
            FileRegisterRequest(
                organization_id=org_id,
                filename=filename,
                content_type=content_type or "application/octet-stream",
                file_class=meta.file_class,
                storage_uri=uri,
                sha256=digest,
                size_bytes=size,
                entity_type=meta.entity_type,
                entity_id=meta.entity_id,
                virus_scan_status=meta.virus_scan_status,
            ),
            actor,
        )

    def list_files(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FileObjectOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            FileObjectOut.model_validate(r)
            for r in self.repo.list_files(
                organization_id=org_id,
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit,
                offset=offset,
            )
        ]

    def soft_delete_file(self, file_id: str, actor: ActorContext) -> FileObjectOut:
        org_id = self.resolve_org_id(actor)
        row = self.repo.get_file(org_id, file_id)
        if row is None:
            raise HTTPException(status_code=404, detail="File not found")
        row.status = "deleted"
        row.deleted_at = datetime.utcnow()
        self._audit_required(
            actor,
            action="platform.file.delete",
            target_type="platform_file",
            target_id=row.id,
            organization_id=org_id,
        )
        self.repo.commit()
        return FileObjectOut.model_validate(row)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def index_document(self, payload: SearchIndexRequest, actor: ActorContext) -> SearchHitOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        row = self.repo.upsert_search_document(org_id, payload.doc_type, payload.entity_id)
        if row is None:
            row = PlatformSearchDocument(
                organization_id=org_id,
                doc_type=payload.doc_type.strip(),
                entity_id=payload.entity_id.strip(),
                title=payload.title.strip(),
                body=payload.body.strip(),
                keywords=payload.keywords.strip(),
                ai_metadata_json=payload.ai_metadata_json or json.dumps(
                    {
                        "domain": payload.doc_type,
                        "searchable": True,
                        "embedding_ready": False,
                    }
                ),
            )
            self.repo.add(row)
        else:
            row.title = payload.title.strip()
            row.body = payload.body.strip()
            row.keywords = payload.keywords.strip()
            if payload.ai_metadata_json:
                row.ai_metadata_json = payload.ai_metadata_json
            row.status = "active"
            row.updated_at = datetime.utcnow()
        self._audit_required(
            actor,
            action="platform.search.index",
            target_type="platform_search_document",
            target_id=row.id or payload.entity_id,
            organization_id=org_id,
            details=payload.doc_type,
        )
        self.repo.commit()
        return SearchHitOut.model_validate(row)

    def search(
        self,
        actor: ActorContext,
        *,
        query: str,
        organization_id: str | None = None,
        doc_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SearchResponse:
        org_id = self.resolve_org_id(actor, organization_id)
        if not query.strip():
            raise HTTPException(status_code=400, detail="query is required")
        hits = self.repo.search(
            organization_id=org_id, query=query, doc_type=doc_type, limit=limit, offset=offset
        )
        return SearchResponse(
            query=query.strip(),
            total=len(hits),
            hits=[SearchHitOut.model_validate(h) for h in hits],
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def upsert_setting(self, payload: SettingUpsert, actor: ActorContext) -> SettingOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        row = self.repo.get_setting(org_id, payload.key.strip())
        if row is None:
            row = PlatformSetting(
                organization_id=org_id,
                key=payload.key.strip(),
                value=payload.value,
                category=payload.category,
                updated_by=actor.username,
            )
            self.repo.add(row)
        else:
            row.value = payload.value
            row.category = payload.category
            row.updated_by = actor.username
            row.updated_at = datetime.utcnow()
        self._audit_required(
            actor,
            action="platform.setting.upsert",
            target_type="platform_setting",
            target_id=row.id or payload.key,
            organization_id=org_id,
            details=payload.key,
        )
        self.repo.commit()
        return SettingOut.model_validate(row)

    def list_settings(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        category: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[SettingOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [
            SettingOut.model_validate(r)
            for r in self.repo.list_settings(
                organization_id=org_id, category=category, limit=limit, offset=offset
            )
        ]

    def list_feature_flags(self) -> list[FeatureFlagOut]:
        return [FeatureFlagOut.model_validate(r) for r in self.repo.list_feature_flags()]

    def set_org_feature_flag(self, payload: OrgFeatureFlagSet, actor: ActorContext) -> OrgFeatureFlagOut:
        org_id = self.resolve_org_id(actor, payload.organization_id)
        if self.repo.get_feature_flag(payload.flag_code) is None:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        row = self.repo.get_org_feature_flag(org_id, payload.flag_code)
        enabled = "true" if payload.enabled else "false"
        if row is None:
            row = PlatformOrgFeatureFlag(
                organization_id=org_id, flag_code=payload.flag_code, enabled=enabled
            )
            self.repo.add(row)
        else:
            row.enabled = enabled
            row.updated_at = datetime.utcnow()
        self._audit_required(
            actor,
            action="platform.feature_flag.set",
            target_type="platform_org_feature_flag",
            target_id=row.id or payload.flag_code,
            organization_id=org_id,
            details=f"{payload.flag_code}={enabled}",
        )
        self.repo.commit()
        return OrgFeatureFlagOut.model_validate(row)

    def list_org_feature_flags(
        self, actor: ActorContext, *, organization_id: str | None = None
    ) -> list[OrgFeatureFlagOut]:
        org_id = self.resolve_org_id(actor, organization_id)
        return [OrgFeatureFlagOut.model_validate(r) for r in self.repo.list_org_feature_flags(org_id)]

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------
    def overview(self, actor: ActorContext, *, organization_id: str | None = None) -> PlatformOverviewOut:
        org_id = self.resolve_org_id(actor, organization_id)
        return PlatformOverviewOut(
            organization_id=org_id,
            api_keys=self.repo.count_api_keys(org_id),
            pats=self.repo.count_pats(org_id),
            facilities=self.repo.count_facilities(org_id),
            custom_roles=self.repo.count_custom_roles(org_id),
            workflow_definitions=self.repo.count_workflow_definitions(org_id),
            open_workflows=self.repo.count_open_workflows(org_id),
            pending_notifications=self.repo.count_pending_notifications(org_id),
            files=self.repo.count_files(org_id),
            search_documents=self.repo.count_search_documents(org_id),
            feature_flags_enabled=self.repo.count_enabled_org_flags(org_id),
        )
