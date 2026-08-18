"""Program 17 — Enterprise Event Fabric service.

Durable event store + catalog + subscriptions + DLQ + replay.
Publishes through Event Framework for in-process subscribers.
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..org.service import OrganizationService
from ..platform.audit_engine import AuditEngine
from ..platform.event_framework import event_framework
from ..shared import ActorContext, clamp_page
from .catalog import BUS_TO_CATALOG, EVENT_CATALOG, EVENT_STATUSES, SEVERITIES
from .models import (
    EnterpriseEventDeadLetter,
    EnterpriseEventReplay,
    EnterpriseEventStore,
    EnterpriseEventSubscription,
    EnterpriseEventType,
)
from .schemas import EventFabricOverviewOut, ReplayOut

DISCLAIMER = (
    "Mercury Enterprise Event Fabric is the durable, versioned event nervous system. "
    "Distinct from Digital Thread fabric_events and in-memory Event Framework history. "
    "Encryption at rest follows platform datastore controls; AI analytics are future consumers."
)


class EventFabricService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.org = OrganizationService(db)
        self.audit = AuditEngine(db)

    def resolve_org(self, actor: ActorContext, organization_id: str | None = None) -> str:
        org_id = (organization_id or actor.organization_id or "").strip()
        if not org_id:
            raise HTTPException(status_code=400, detail="Organization is required")
        self.org.assert_org_access(
            username=actor.username, session_role=actor.role, organization_id=org_id
        )
        return org_id

    def seed(self, organization_id: str = "org-aviation-east") -> dict[str, int]:
        created = {"types": 0, "events": 0, "subscriptions": 0}
        for code, family, version, desc, severity in EVENT_CATALOG:
            exists = self.db.scalars(
                select(EnterpriseEventType).where(
                    EnterpriseEventType.code == code,
                    EnterpriseEventType.version == version,
                )
            ).first()
            if exists:
                continue
            self.db.add(
                EnterpriseEventType(
                    code=code,
                    family=family,
                    version=version,
                    description=desc,
                    severity_default=severity,
                    schema_json=json.dumps({"type": "object"}),
                    ai_ready="true",
                    status="active",
                )
            )
            created["types"] += 1

        if created["types"]:
            self.db.flush()

        # Demo subscriptions
        for code, name in (
            ("*", "digital-twin-timeline-mirror"),
            ("OrderCreated", "marketplace-fulfillment-watcher"),
            ("ReleaseSigned", "authority-compliance-watcher"),
            ("RecommendationGenerated", "ai-advisory-logger"),
        ):
            exists = self.db.scalars(
                select(EnterpriseEventSubscription).where(
                    EnterpriseEventSubscription.organization_id == organization_id,
                    EnterpriseEventSubscription.event_code == code,
                    EnterpriseEventSubscription.subscriber_name == name,
                )
            ).first()
            if exists:
                continue
            self.db.add(
                EnterpriseEventSubscription(
                    organization_id=organization_id,
                    event_code=code,
                    subscriber_name=name,
                    filter_json="{}",
                    endpoint_hint=f"inproc://{name}",
                    status="active",
                    created_by="system",
                )
            )
            created["subscriptions"] += 1

        # Seed a few durable events for demo
        actor = ActorContext(
            username="system",
            role="Administrator",
            organization_id=organization_id,
            site_id="",
        )
        for code, payload in (
            ("OrganizationUpdated", {"organization_id": organization_id, "action": "seed"}),
            ("TwinCreated", {"serial": "FYXZ", "twin_type": "aircraft"}),
            ("ProductPublished", {"sku": "MS21042L3"}),
            ("WorkOrderCreated", {"work_order": "WO-SEED-1"}),
            ("KnowledgeIndexed", {"domain": "fabric", "ready": True}),
        ):
            exists = self.db.scalars(
                select(EnterpriseEventStore).where(
                    EnterpriseEventStore.organization_id == organization_id,
                    EnterpriseEventStore.event_code == code,
                    EnterpriseEventStore.actor == "system",
                )
            ).first()
            if exists:
                continue
            self.publish(
                actor,
                event_code=code,
                payload_json=json.dumps(payload),
                source_service="event_fabric.seed",
                organization_id=organization_id,
                _seeding=True,
            )
            created["events"] += 1

        if any(created.values()):
            self.db.commit()
        return created

    def overview(
        self, actor: ActorContext, organization_id: str | None = None
    ) -> EventFabricOverviewOut:
        org_id = self.resolve_org(actor, organization_id)
        types = list(
            self.db.scalars(
                select(EnterpriseEventType).where(EnterpriseEventType.status == "active")
            ).all()
        )
        stored = int(
            self.db.scalar(
                select(func.count())
                .select_from(EnterpriseEventStore)
                .where(EnterpriseEventStore.organization_id == org_id)
            )
            or 0
        )
        subs = int(
            self.db.scalar(
                select(func.count())
                .select_from(EnterpriseEventSubscription)
                .where(
                    EnterpriseEventSubscription.organization_id == org_id,
                    EnterpriseEventSubscription.status == "active",
                )
            )
            or 0
        )
        dlq = int(
            self.db.scalar(
                select(func.count())
                .select_from(EnterpriseEventDeadLetter)
                .where(
                    EnterpriseEventDeadLetter.organization_id == org_id,
                    EnterpriseEventDeadLetter.status == "open",
                )
            )
            or 0
        )
        replays = int(
            self.db.scalar(
                select(func.count())
                .select_from(EnterpriseEventReplay)
                .where(EnterpriseEventReplay.organization_id == org_id)
            )
            or 0
        )
        family_counts = dict(
            Counter(
                r.family
                for r in self.db.scalars(
                    select(EnterpriseEventStore).where(
                        EnterpriseEventStore.organization_id == org_id
                    )
                ).all()
            )
        )
        return EventFabricOverviewOut(
            organization_id=org_id,
            catalog_types=len(types),
            stored_events=stored,
            subscriptions=subs,
            dead_letters_open=dlq,
            replays=replays,
            families=family_counts,
            disclaimer=DISCLAIMER,
        )

    def list_catalog(self, *, family: str | None = None) -> list[EnterpriseEventType]:
        stmt = select(EnterpriseEventType).where(EnterpriseEventType.status == "active")
        if family:
            stmt = stmt.where(EnterpriseEventType.family == family)
        return list(
            self.db.scalars(stmt.order_by(EnterpriseEventType.family, EnterpriseEventType.code)).all()
        )

    def _resolve_type(self, event_code: str, version: str = "1.0") -> EnterpriseEventType:
        row = self.db.scalars(
            select(EnterpriseEventType).where(
                EnterpriseEventType.code == event_code,
                EnterpriseEventType.version == version,
                EnterpriseEventType.status == "active",
            )
        ).first()
        if row is None:
            # try any version
            row = self.db.scalars(
                select(EnterpriseEventType).where(
                    EnterpriseEventType.code == event_code,
                    EnterpriseEventType.status == "active",
                )
            ).first()
        if row is None:
            raise HTTPException(status_code=400, detail=f"Unknown event_code: {event_code}")
        return row

    def publish(
        self,
        actor: ActorContext,
        *,
        event_code: str,
        payload_json: str = "{}",
        event_version: str = "1.0",
        source_service: str = "mercury",
        target_service: str = "",
        correlation_id: str = "",
        trace_id: str = "",
        severity: str = "",
        duration_ms: int = 0,
        bus_event_type: str = "",
        organization_id: str | None = None,
        _seeding: bool = False,
    ) -> EnterpriseEventStore:
        org_id = self.resolve_org(actor, organization_id)
        etype = self._resolve_type(event_code, event_version)
        sev = severity or etype.severity_default
        if sev not in SEVERITIES:
            raise HTTPException(status_code=400, detail="Invalid severity")
        corr = correlation_id or str(uuid.uuid4())
        trace = trace_id or corr
        event_id = str(uuid.uuid4())
        bus_type = bus_event_type or f"enterprise.{etype.family}.{event_code}"
        try:
            payload = json.loads(payload_json or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid payload_json") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload_json must be an object")

        row = EnterpriseEventStore(
            organization_id=org_id,
            event_id=event_id,
            event_code=event_code,
            event_version=etype.version,
            family=etype.family,
            bus_event_type=bus_type,
            payload_json=json.dumps(payload),
            actor=actor.username,
            source_service=source_service,
            target_service=target_service,
            correlation_id=corr,
            trace_id=trace,
            severity=sev,
            status="published",
            duration_ms=duration_ms,
            occurred_at=datetime.utcnow(),
        )
        self.db.add(row)
        self.db.flush()

        # Deliver to persisted subscriptions (in-proc simulation)
        self._dispatch_subscriptions(row)

        # Mirror to Event Framework bus (no Fabric dual-write — already durable here)
        event_framework.publish_sync(
            bus_type,
            {
                **payload,
                "enterprise_event_id": event_id,
                "event_code": event_code,
                "event_version": etype.version,
                "trace_id": trace,
                "correlation_id": corr,
                "severity": sev,
                "actor": actor.username,
                "target_service": target_service,
                "duration_ms": duration_ms,
            },
            source=source_service,
            organization_id=org_id,
            dual_write=False,
        )

        if not _seeding:
            self.audit.require(
                actor,
                action="event_fabric.publish",
                target_type="enterprise_event",
                target_id=row.id,
                organization_id=org_id,
                details=event_code,
            )
            self.db.commit()
        return row

    def _dispatch_subscriptions(self, row: EnterpriseEventStore) -> None:
        subs = list(
            self.db.scalars(
                select(EnterpriseEventSubscription).where(
                    EnterpriseEventSubscription.status == "active",
                    EnterpriseEventSubscription.organization_id.in_(
                        ["", row.organization_id]
                    ),
                )
            ).all()
        )
        for sub in subs:
            if sub.event_code not in {"*", row.event_code}:
                continue
            # Architecture: simulate successful delivery; DLQ path available via API
            row.status = "delivered"
        if row.status not in EVENT_STATUSES:
            row.status = "published"

    def list_events(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        event_code: str | None = None,
        family: str | None = None,
        correlation_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EnterpriseEventStore]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(EnterpriseEventStore).where(
            EnterpriseEventStore.organization_id == org_id
        )
        if event_code:
            stmt = stmt.where(EnterpriseEventStore.event_code == event_code)
        if family:
            stmt = stmt.where(EnterpriseEventStore.family == family)
        if correlation_id:
            stmt = stmt.where(EnterpriseEventStore.correlation_id == correlation_id)
        return list(
            self.db.scalars(
                stmt.order_by(EnterpriseEventStore.occurred_at.desc()).limit(lim).offset(off)
            ).all()
        )

    def get_event(
        self, actor: ActorContext, event_id: str, organization_id: str | None = None
    ) -> EnterpriseEventStore:
        org_id = self.resolve_org(actor, organization_id)
        row = self.db.scalars(
            select(EnterpriseEventStore).where(
                EnterpriseEventStore.organization_id == org_id,
                EnterpriseEventStore.event_id == event_id,
            )
        ).first()
        if row is None:
            raise HTTPException(status_code=404, detail="Event not found")
        return row

    def create_subscription(self, actor: ActorContext, **kwargs) -> EnterpriseEventSubscription:
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        code = kwargs["event_code"].strip()
        if code != "*":
            self._resolve_type(code)
        row = EnterpriseEventSubscription(
            organization_id=org_id,
            event_code=code,
            subscriber_name=kwargs["subscriber_name"].strip(),
            filter_json=kwargs.get("filter_json") or "{}",
            endpoint_hint=(kwargs.get("endpoint_hint") or "").strip(),
            status="active",
            created_by=actor.username,
        )
        self.db.add(row)
        try:
            self.db.flush()
            self.audit.require(
                actor,
                action="event_fabric.subscribe",
                target_type="enterprise_event_subscription",
                target_id=row.id,
                organization_id=org_id,
                details=code,
            )
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=409, detail="Subscription already exists") from exc
        return row

    def list_subscriptions(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EnterpriseEventSubscription]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        return list(
            self.db.scalars(
                select(EnterpriseEventSubscription)
                .where(
                    EnterpriseEventSubscription.organization_id == org_id,
                    EnterpriseEventSubscription.status == "active",
                )
                .order_by(EnterpriseEventSubscription.subscriber_name)
                .limit(lim)
                .offset(off)
            ).all()
        )

    def dead_letter(
        self,
        actor: ActorContext,
        *,
        store_event_id: str,
        subscriber_name: str,
        error_message: str,
        organization_id: str | None = None,
    ) -> EnterpriseEventDeadLetter:
        org_id = self.resolve_org(actor, organization_id)
        stored = self.db.get(EnterpriseEventStore, store_event_id)
        if stored is None or stored.organization_id != org_id:
            # also allow lookup by event_id
            stored = self.db.scalars(
                select(EnterpriseEventStore).where(
                    EnterpriseEventStore.organization_id == org_id,
                    EnterpriseEventStore.event_id == store_event_id,
                )
            ).first()
        if stored is None:
            raise HTTPException(status_code=404, detail="Stored event not found")
        row = EnterpriseEventDeadLetter(
            organization_id=org_id,
            store_event_id=stored.id,
            event_code=stored.event_code,
            subscriber_name=subscriber_name.strip(),
            error_message=error_message.strip(),
            retry_count=0,
            status="open",
        )
        stored.status = "dead_lettered"
        self.db.add(row)
        self.db.flush()
        self.audit.require(
            actor,
            action="event_fabric.dlq",
            target_type="enterprise_event_dlq",
            target_id=row.id,
            organization_id=org_id,
            details=stored.event_code,
        )
        self.db.commit()
        return row

    def list_dlq(
        self,
        actor: ActorContext,
        *,
        organization_id: str | None = None,
        status: str | None = "open",
        limit: int = 100,
        offset: int = 0,
    ) -> list[EnterpriseEventDeadLetter]:
        org_id = self.resolve_org(actor, organization_id)
        lim, off = clamp_page(limit, offset)
        stmt = select(EnterpriseEventDeadLetter).where(
            EnterpriseEventDeadLetter.organization_id == org_id
        )
        if status:
            stmt = stmt.where(EnterpriseEventDeadLetter.status == status)
        return list(
            self.db.scalars(
                stmt.order_by(EnterpriseEventDeadLetter.created_at.desc()).limit(lim).offset(off)
            ).all()
        )

    def retry_dlq(
        self, actor: ActorContext, dlq_id: str, organization_id: str | None = None
    ) -> EnterpriseEventDeadLetter:
        org_id = self.resolve_org(actor, organization_id)
        row = self.db.get(EnterpriseEventDeadLetter, dlq_id)
        if row is None or row.organization_id != org_id:
            raise HTTPException(status_code=404, detail="DLQ entry not found")
        row.retry_count += 1
        row.status = "retried"
        row.updated_at = datetime.utcnow()
        stored = self.db.get(EnterpriseEventStore, row.store_event_id)
        if stored:
            stored.status = "delivered"
            # re-publish to bus
            event_framework.publish_sync(
                stored.bus_event_type or f"enterprise.{stored.family}.{stored.event_code}",
                json.loads(stored.payload_json or "{}"),
                source=stored.source_service or "event_fabric.retry",
                organization_id=org_id,
            )
        self.audit.require(
            actor,
            action="event_fabric.retry",
            target_type="enterprise_event_dlq",
            target_id=row.id,
            organization_id=org_id,
            details=str(row.retry_count),
        )
        self.db.commit()
        return row

    def replay(self, actor: ActorContext, **kwargs) -> ReplayOut:
        org_id = self.resolve_org(actor, kwargs.get("organization_id"))
        lim = min(int(kwargs.get("limit") or 100), 1000)
        stmt = select(EnterpriseEventStore).where(
            EnterpriseEventStore.organization_id == org_id
        )
        code = (kwargs.get("event_code") or "").strip()
        if code:
            stmt = stmt.where(EnterpriseEventStore.event_code == code)
        if kwargs.get("from_occurred_at"):
            stmt = stmt.where(EnterpriseEventStore.occurred_at >= kwargs["from_occurred_at"])
        if kwargs.get("to_occurred_at"):
            stmt = stmt.where(EnterpriseEventStore.occurred_at <= kwargs["to_occurred_at"])
        rows = list(
            self.db.scalars(stmt.order_by(EnterpriseEventStore.occurred_at.asc()).limit(lim)).all()
        )
        for stored in rows:
            event_framework.publish_sync(
                stored.bus_event_type or f"enterprise.{stored.family}.{stored.event_code}",
                {
                    **json.loads(stored.payload_json or "{}"),
                    "replay": True,
                    "enterprise_event_id": stored.event_id,
                },
                source="event_fabric.replay",
                organization_id=org_id,
            )
            stored.status = "replayed"
        job = EnterpriseEventReplay(
            organization_id=org_id,
            event_code=code,
            from_occurred_at=kwargs.get("from_occurred_at"),
            to_occurred_at=kwargs.get("to_occurred_at"),
            events_replayed=len(rows),
            status="completed",
            created_by=actor.username,
        )
        self.db.add(job)
        self.db.flush()
        self.audit.require(
            actor,
            action="event_fabric.replay",
            target_type="enterprise_event_replay",
            target_id=job.id,
            organization_id=org_id,
            details=str(len(rows)),
        )
        self.db.commit()
        return ReplayOut.model_validate(job)

    def ingest_bus_event(
        self,
        *,
        organization_id: str,
        bus_event_type: str,
        payload: dict,
        source: str = "mercury",
    ) -> EnterpriseEventStore | None:
        """Optional bridge: map dotted bus types into catalog when known."""
        code = BUS_TO_CATALOG.get(bus_event_type)
        if not code:
            return None
        actor = ActorContext(
            username=str(payload.get("actor") or "system"),
            role="Administrator",
            organization_id=organization_id,
            site_id="",
        )
        return self.publish(
            actor,
            event_code=code,
            payload_json=json.dumps(payload),
            source_service=source,
            bus_event_type=bus_event_type,
            organization_id=organization_id,
            correlation_id=str(payload.get("correlation_id") or ""),
            _seeding=False,
        )
