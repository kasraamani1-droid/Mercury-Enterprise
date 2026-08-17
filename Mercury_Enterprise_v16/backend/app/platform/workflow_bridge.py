"""Workflow Bridge — domains resolve transitions from the generic workflow engine."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..shared import ActorContext
from .models import PlatformWorkflowDefinition, PlatformWorkflowInstance
from .repository import PlatformRepository
from .service import PlatformService
from .schemas import WorkflowStartRequest, WorkflowTransitionRequest


# Canonical job-card definition used by work_orders (replaces hardcoded transition map at runtime).
JOB_CARD_WORKFLOW_CODE = "work_order.job_card"
JOB_CARD_STATES = [
    "draft",
    "assigned",
    "accepted",
    "in_progress",
    "paused",
    "waiting_parts",
    "waiting_engineering",
    "waiting_inspection",
    "completed",
    "rejected",
    "released",
    "closed",
]
JOB_CARD_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["assigned", "closed"],
    "assigned": ["accepted", "draft", "closed"],
    "accepted": ["in_progress", "waiting_parts", "waiting_engineering", "closed"],
    "in_progress": ["paused", "waiting_parts", "waiting_engineering", "closed"],
    "paused": ["in_progress", "waiting_parts", "waiting_engineering", "closed"],
    "waiting_parts": ["in_progress", "accepted", "closed"],
    "waiting_engineering": ["in_progress", "accepted", "closed"],
    "waiting_inspection": [],
    "completed": [],
    "rejected": ["in_progress", "assigned", "closed"],
    "released": ["closed"],
    "closed": [],
}


# Canonical purchase-order definition used by logistics (replaces ad-hoc status gates).
PO_WORKFLOW_CODE = "logistics.purchase_order"
PO_STATES = [
    "open",
    "partial",
    "received",
    "closed",
    "cancelled",
    "returned",
]
PO_TRANSITIONS: dict[str, list[str]] = {
    "open": ["partial", "received", "closed", "cancelled"],
    "partial": ["partial", "received", "closed", "cancelled"],
    "received": ["closed", "returned", "cancelled"],
    "closed": [],
    "cancelled": [],
    "returned": ["closed"],
}


class WorkflowBridge:
    """Domain modules must use this bridge — never hardcode transition tables long-term."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PlatformRepository(db)
        self.platform = PlatformService(db)

    def ensure_definition(
        self,
        organization_id: str,
        code: str,
        name: str,
        states: list[str],
        transitions: dict[str, list[str]],
    ) -> PlatformWorkflowDefinition:
        existing = self.repo.get_workflow_definition_by_code(organization_id, code)
        if existing is not None:
            return existing
        row = PlatformWorkflowDefinition(
            organization_id=organization_id,
            code=code,
            name=name,
            states_json=json.dumps(states),
            transitions_json=json.dumps(transitions),
            version=1,
        )
        self.repo.add(row)
        self.repo.commit()
        return row

    def ensure_job_card_definition(self, organization_id: str) -> PlatformWorkflowDefinition:
        return self.ensure_definition(
            organization_id,
            JOB_CARD_WORKFLOW_CODE,
            "Work Order Job Card Lifecycle",
            JOB_CARD_STATES,
            JOB_CARD_TRANSITIONS,
        )

    def ensure_purchase_order_definition(self, organization_id: str) -> PlatformWorkflowDefinition:
        return self.ensure_definition(
            organization_id,
            PO_WORKFLOW_CODE,
            "Logistics Purchase Order Lifecycle",
            PO_STATES,
            PO_TRANSITIONS,
        )

    def allowed_transitions(
        self, organization_id: str, definition_code: str, from_state: str
    ) -> set[str]:
        definition = self.repo.get_workflow_definition_by_code(organization_id, definition_code)
        if definition is None and definition_code == JOB_CARD_WORKFLOW_CODE:
            # Fallback seed path for cold start before seed_platform ran
            return set(JOB_CARD_TRANSITIONS.get(from_state, []))
        if definition is None and definition_code == PO_WORKFLOW_CODE:
            return set(PO_TRANSITIONS.get(from_state, []))
        if definition is None:
            raise HTTPException(status_code=404, detail=f"Workflow definition '{definition_code}' not found")
        try:
            transitions = json.loads(definition.transitions_json or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail="Corrupt workflow transitions_json") from exc
        return set(transitions.get(from_state, []))

    def assert_transition(
        self, organization_id: str, definition_code: str, from_state: str, to_state: str
    ) -> None:
        allowed = self.allowed_transitions(organization_id, definition_code, from_state)
        if to_state not in allowed:
            raise HTTPException(
                status_code=409,
                detail=f"Invalid transition from '{from_state}' to '{to_state}'",
            )

    def sync_instance(
        self,
        actor: ActorContext,
        *,
        organization_id: str,
        definition_code: str,
        entity_type: str,
        entity_id: str,
        to_state: str,
        comment: str = "",
    ) -> PlatformWorkflowInstance | None:
        """Best-effort dual-write of domain status onto a platform workflow instance."""
        instances = self.repo.list_workflow_instances(
            organization_id=organization_id,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=1,
        )
        if not instances:
            try:
                out = self.platform.start_workflow(
                    WorkflowStartRequest(
                        organization_id=organization_id,
                        definition_code=definition_code,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        initial_state=to_state,
                    ),
                    actor,
                )
                return self.repo.get_workflow_instance(organization_id, out.id)
            except Exception:
                return None
        instance = instances[0]
        if instance.current_state == to_state:
            return instance
        try:
            self.platform.transition_workflow(
                instance.id,
                WorkflowTransitionRequest(to_state=to_state, comment=comment),
                actor,
            )
        except Exception:
            # Domain transition already validated; platform sync must not block aviation work
            return instance
        return self.repo.get_workflow_instance(organization_id, instance.id)
