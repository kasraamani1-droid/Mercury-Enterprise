"""Program A — Platform Foundation data access (org-scoped)."""

from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

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

MAX_PAGE = 500


def _page(limit: int, offset: int) -> tuple[int, int]:
    return min(max(int(limit), 1), MAX_PAGE), max(int(offset), 0)


class PlatformRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, row: object) -> object:
        self.db.add(row)
        return row

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def flush(self) -> None:
        self.db.flush()

    def refresh(self, obj: object) -> None:
        self.db.refresh(obj)

    # --- API keys ---
    def get_api_key(self, organization_id: str, key_id: str) -> PlatformApiKey | None:
        return self.db.scalars(
            select(PlatformApiKey).where(
                PlatformApiKey.id == key_id,
                PlatformApiKey.organization_id == organization_id,
            )
        ).first()

    def list_api_keys(
        self, *, organization_id: str, limit: int = 100, offset: int = 0
    ) -> list[PlatformApiKey]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(PlatformApiKey)
                .where(PlatformApiKey.organization_id == organization_id)
                .order_by(PlatformApiKey.created_at.desc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    def count_api_keys(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformApiKey)
                .where(
                    PlatformApiKey.organization_id == organization_id,
                    PlatformApiKey.status == "active",
                )
            )
            or 0
        )

    # --- PATs ---
    def list_pats(
        self, *, organization_id: str, username: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[PlatformPersonalAccessToken]:
        lim, off = _page(limit, offset)
        stmt: Select[tuple[PlatformPersonalAccessToken]] = select(PlatformPersonalAccessToken).where(
            PlatformPersonalAccessToken.organization_id == organization_id
        )
        if username:
            stmt = stmt.where(PlatformPersonalAccessToken.username == username)
        return list(
            self.db.scalars(
                stmt.order_by(PlatformPersonalAccessToken.created_at.desc()).limit(lim).offset(off)
            ).all()
        )

    def get_pat(self, organization_id: str, pat_id: str) -> PlatformPersonalAccessToken | None:
        return self.db.scalars(
            select(PlatformPersonalAccessToken).where(
                PlatformPersonalAccessToken.id == pat_id,
                PlatformPersonalAccessToken.organization_id == organization_id,
            )
        ).first()

    def count_pats(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformPersonalAccessToken)
                .where(
                    PlatformPersonalAccessToken.organization_id == organization_id,
                    PlatformPersonalAccessToken.status == "active",
                )
            )
            or 0
        )

    # --- MFA ---
    def get_mfa(self, username: str) -> PlatformMfaEnrollment | None:
        return self.db.scalars(
            select(PlatformMfaEnrollment).where(PlatformMfaEnrollment.username == username)
        ).first()

    # --- Business units / cost centers / facilities ---
    def get_business_unit(self, organization_id: str, bu_id: str) -> PlatformBusinessUnit | None:
        return self.db.scalars(
            select(PlatformBusinessUnit).where(
                PlatformBusinessUnit.id == bu_id,
                PlatformBusinessUnit.organization_id == organization_id,
                PlatformBusinessUnit.deleted_at.is_(None),
            )
        ).first()

    def list_business_units(
        self, *, organization_id: str, limit: int = 100, offset: int = 0
    ) -> list[PlatformBusinessUnit]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(PlatformBusinessUnit)
                .where(
                    PlatformBusinessUnit.organization_id == organization_id,
                    PlatformBusinessUnit.deleted_at.is_(None),
                )
                .order_by(PlatformBusinessUnit.code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def get_cost_center(self, organization_id: str, cc_id: str) -> PlatformCostCenter | None:
        return self.db.scalars(
            select(PlatformCostCenter).where(
                PlatformCostCenter.id == cc_id,
                PlatformCostCenter.organization_id == organization_id,
                PlatformCostCenter.deleted_at.is_(None),
            )
        ).first()

    def list_cost_centers(
        self, *, organization_id: str, limit: int = 100, offset: int = 0
    ) -> list[PlatformCostCenter]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(PlatformCostCenter)
                .where(
                    PlatformCostCenter.organization_id == organization_id,
                    PlatformCostCenter.deleted_at.is_(None),
                )
                .order_by(PlatformCostCenter.code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def get_facility(self, organization_id: str, facility_id: str) -> PlatformFacility | None:
        return self.db.scalars(
            select(PlatformFacility).where(
                PlatformFacility.id == facility_id,
                PlatformFacility.organization_id == organization_id,
                PlatformFacility.deleted_at.is_(None),
            )
        ).first()

    def list_facilities(
        self,
        *,
        organization_id: str,
        facility_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PlatformFacility]:
        lim, off = _page(limit, offset)
        stmt = select(PlatformFacility).where(
            PlatformFacility.organization_id == organization_id,
            PlatformFacility.deleted_at.is_(None),
        )
        if facility_type:
            stmt = stmt.where(PlatformFacility.facility_type == facility_type)
        return list(self.db.scalars(stmt.order_by(PlatformFacility.code).limit(lim).offset(off)).all())

    def count_facilities(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformFacility)
                .where(
                    PlatformFacility.organization_id == organization_id,
                    PlatformFacility.deleted_at.is_(None),
                )
            )
            or 0
        )

    # --- RBAC ---
    def list_role_templates(self) -> list[PlatformRoleTemplate]:
        return list(
            self.db.scalars(
                select(PlatformRoleTemplate)
                .where(PlatformRoleTemplate.status == "active")
                .order_by(PlatformRoleTemplate.code)
            ).all()
        )

    def get_role_template_by_code(self, code: str) -> PlatformRoleTemplate | None:
        return self.db.scalars(
            select(PlatformRoleTemplate).where(PlatformRoleTemplate.code == code)
        ).first()

    def list_custom_roles(
        self, *, organization_id: str, limit: int = 100, offset: int = 0
    ) -> list[PlatformCustomRole]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(PlatformCustomRole)
                .where(
                    PlatformCustomRole.organization_id == organization_id,
                    PlatformCustomRole.deleted_at.is_(None),
                )
                .order_by(PlatformCustomRole.code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def count_custom_roles(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformCustomRole)
                .where(
                    PlatformCustomRole.organization_id == organization_id,
                    PlatformCustomRole.deleted_at.is_(None),
                )
            )
            or 0
        )

    def list_temporary_access(
        self, *, organization_id: str, username: str | None = None, limit: int = 100, offset: int = 0
    ) -> list[PlatformTemporaryAccess]:
        lim, off = _page(limit, offset)
        stmt = select(PlatformTemporaryAccess).where(
            PlatformTemporaryAccess.organization_id == organization_id
        )
        if username:
            stmt = stmt.where(PlatformTemporaryAccess.username == username)
        return list(
            self.db.scalars(stmt.order_by(PlatformTemporaryAccess.created_at.desc()).limit(lim).offset(off)).all()
        )

    def list_permission_audits(
        self, *, organization_id: str, limit: int = 100, offset: int = 0
    ) -> list[PlatformPermissionAudit]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(PlatformPermissionAudit)
                .where(PlatformPermissionAudit.organization_id == organization_id)
                .order_by(PlatformPermissionAudit.created_at.desc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    # --- Workflow ---
    def get_workflow_definition(
        self, organization_id: str, definition_id: str
    ) -> PlatformWorkflowDefinition | None:
        return self.db.scalars(
            select(PlatformWorkflowDefinition).where(
                PlatformWorkflowDefinition.id == definition_id,
                PlatformWorkflowDefinition.organization_id == organization_id,
            )
        ).first()

    def get_workflow_definition_by_code(
        self, organization_id: str, code: str
    ) -> PlatformWorkflowDefinition | None:
        return self.db.scalars(
            select(PlatformWorkflowDefinition)
            .where(
                PlatformWorkflowDefinition.organization_id == organization_id,
                PlatformWorkflowDefinition.code == code,
                PlatformWorkflowDefinition.status == "active",
            )
            .order_by(PlatformWorkflowDefinition.version.desc())
        ).first()

    def list_workflow_definitions(
        self, *, organization_id: str, limit: int = 100, offset: int = 0
    ) -> list[PlatformWorkflowDefinition]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(PlatformWorkflowDefinition)
                .where(
                    PlatformWorkflowDefinition.organization_id == organization_id,
                    PlatformWorkflowDefinition.status == "active",
                )
                .order_by(PlatformWorkflowDefinition.code)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def count_workflow_definitions(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformWorkflowDefinition)
                .where(
                    PlatformWorkflowDefinition.organization_id == organization_id,
                    PlatformWorkflowDefinition.status == "active",
                )
            )
            or 0
        )

    def get_workflow_instance(
        self, organization_id: str, instance_id: str
    ) -> PlatformWorkflowInstance | None:
        return self.db.scalars(
            select(PlatformWorkflowInstance).where(
                PlatformWorkflowInstance.id == instance_id,
                PlatformWorkflowInstance.organization_id == organization_id,
            )
        ).first()

    def list_workflow_instances(
        self,
        *,
        organization_id: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PlatformWorkflowInstance]:
        lim, off = _page(limit, offset)
        stmt = select(PlatformWorkflowInstance).where(
            PlatformWorkflowInstance.organization_id == organization_id
        )
        if entity_type:
            stmt = stmt.where(PlatformWorkflowInstance.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(PlatformWorkflowInstance.entity_id == entity_id)
        return list(
            self.db.scalars(stmt.order_by(PlatformWorkflowInstance.updated_at.desc()).limit(lim).offset(off)).all()
        )

    def count_open_workflows(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformWorkflowInstance)
                .where(
                    PlatformWorkflowInstance.organization_id == organization_id,
                    PlatformWorkflowInstance.current_state.notin_(["released", "archived"]),
                )
            )
            or 0
        )

    def list_transition_logs(
        self, *, instance_id: str, limit: int = 100, offset: int = 0
    ) -> list[PlatformWorkflowTransitionLog]:
        lim, off = _page(limit, offset)
        return list(
            self.db.scalars(
                select(PlatformWorkflowTransitionLog)
                .where(PlatformWorkflowTransitionLog.instance_id == instance_id)
                .order_by(PlatformWorkflowTransitionLog.created_at.asc())
                .limit(lim)
                .offset(off)
            ).all()
        )

    # --- Notifications ---
    def list_notifications(
        self,
        *,
        organization_id: str,
        recipient: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PlatformNotification]:
        lim, off = _page(limit, offset)
        stmt = select(PlatformNotification).where(
            PlatformNotification.organization_id == organization_id
        )
        if recipient:
            stmt = stmt.where(PlatformNotification.recipient == recipient)
        if status:
            stmt = stmt.where(PlatformNotification.status == status)
        return list(
            self.db.scalars(stmt.order_by(PlatformNotification.created_at.desc()).limit(lim).offset(off)).all()
        )

    def get_notification(
        self, organization_id: str, notification_id: str
    ) -> PlatformNotification | None:
        return self.db.scalars(
            select(PlatformNotification).where(
                PlatformNotification.id == notification_id,
                PlatformNotification.organization_id == organization_id,
            )
        ).first()

    def count_pending_notifications(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformNotification)
                .where(
                    PlatformNotification.organization_id == organization_id,
                    PlatformNotification.status == "pending",
                )
            )
            or 0
        )

    # --- Files ---
    def list_files(
        self,
        *,
        organization_id: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PlatformFileObject]:
        lim, off = _page(limit, offset)
        stmt = select(PlatformFileObject).where(
            PlatformFileObject.organization_id == organization_id,
            PlatformFileObject.deleted_at.is_(None),
        )
        if entity_type:
            stmt = stmt.where(PlatformFileObject.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(PlatformFileObject.entity_id == entity_id)
        return list(
            self.db.scalars(stmt.order_by(PlatformFileObject.created_at.desc()).limit(lim).offset(off)).all()
        )

    def get_file(self, organization_id: str, file_id: str) -> PlatformFileObject | None:
        return self.db.scalars(
            select(PlatformFileObject).where(
                PlatformFileObject.id == file_id,
                PlatformFileObject.organization_id == organization_id,
                PlatformFileObject.deleted_at.is_(None),
            )
        ).first()

    def latest_file_version(
        self, organization_id: str, entity_type: str, entity_id: str, filename: str
    ) -> int:
        row = self.db.scalars(
            select(PlatformFileObject)
            .where(
                PlatformFileObject.organization_id == organization_id,
                PlatformFileObject.entity_type == entity_type,
                PlatformFileObject.entity_id == entity_id,
                PlatformFileObject.filename == filename,
            )
            .order_by(PlatformFileObject.version.desc())
        ).first()
        return int(row.version) if row else 0

    def count_files(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformFileObject)
                .where(
                    PlatformFileObject.organization_id == organization_id,
                    PlatformFileObject.deleted_at.is_(None),
                )
            )
            or 0
        )

    # --- Search ---
    def upsert_search_document(
        self, organization_id: str, doc_type: str, entity_id: str
    ) -> PlatformSearchDocument | None:
        return self.db.scalars(
            select(PlatformSearchDocument).where(
                PlatformSearchDocument.organization_id == organization_id,
                PlatformSearchDocument.doc_type == doc_type,
                PlatformSearchDocument.entity_id == entity_id,
            )
        ).first()

    def search(
        self,
        *,
        organization_id: str,
        query: str,
        doc_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PlatformSearchDocument]:
        lim, off = _page(limit, offset)
        q = f"%{query.strip()}%"
        stmt = select(PlatformSearchDocument).where(
            PlatformSearchDocument.organization_id == organization_id,
            PlatformSearchDocument.status == "active",
            or_(
                PlatformSearchDocument.title.ilike(q),
                PlatformSearchDocument.body.ilike(q),
                PlatformSearchDocument.keywords.ilike(q),
            ),
        )
        if doc_type:
            stmt = stmt.where(PlatformSearchDocument.doc_type == doc_type)
        return list(
            self.db.scalars(stmt.order_by(PlatformSearchDocument.updated_at.desc()).limit(lim).offset(off)).all()
        )

    def count_search_documents(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformSearchDocument)
                .where(
                    PlatformSearchDocument.organization_id == organization_id,
                    PlatformSearchDocument.status == "active",
                )
            )
            or 0
        )

    # --- Settings / flags ---
    def get_setting(self, organization_id: str, key: str) -> PlatformSetting | None:
        return self.db.scalars(
            select(PlatformSetting).where(
                PlatformSetting.organization_id == organization_id,
                PlatformSetting.key == key,
            )
        ).first()

    def list_settings(
        self, *, organization_id: str, category: str | None = None, limit: int = 200, offset: int = 0
    ) -> list[PlatformSetting]:
        lim, off = _page(limit, offset)
        stmt = select(PlatformSetting).where(PlatformSetting.organization_id == organization_id)
        if category:
            stmt = stmt.where(PlatformSetting.category == category)
        return list(self.db.scalars(stmt.order_by(PlatformSetting.key).limit(lim).offset(off)).all())

    def list_feature_flags(self) -> list[PlatformFeatureFlag]:
        return list(
            self.db.scalars(select(PlatformFeatureFlag).order_by(PlatformFeatureFlag.code)).all()
        )

    def get_feature_flag(self, code: str) -> PlatformFeatureFlag | None:
        return self.db.scalars(
            select(PlatformFeatureFlag).where(PlatformFeatureFlag.code == code)
        ).first()

    def get_org_feature_flag(
        self, organization_id: str, flag_code: str
    ) -> PlatformOrgFeatureFlag | None:
        return self.db.scalars(
            select(PlatformOrgFeatureFlag).where(
                PlatformOrgFeatureFlag.organization_id == organization_id,
                PlatformOrgFeatureFlag.flag_code == flag_code,
            )
        ).first()

    def list_org_feature_flags(self, organization_id: str) -> list[PlatformOrgFeatureFlag]:
        return list(
            self.db.scalars(
                select(PlatformOrgFeatureFlag)
                .where(PlatformOrgFeatureFlag.organization_id == organization_id)
                .order_by(PlatformOrgFeatureFlag.flag_code)
            ).all()
        )

    def count_enabled_org_flags(self, organization_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(PlatformOrgFeatureFlag)
                .where(
                    PlatformOrgFeatureFlag.organization_id == organization_id,
                    PlatformOrgFeatureFlag.enabled == "true",
                )
            )
            or 0
        )
