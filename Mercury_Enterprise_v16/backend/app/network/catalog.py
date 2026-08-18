"""Program 14 — Mercury Aviation Network vocabularies.

Secure professional collaboration — not social media.
Organizations isolated by default; cross-org only via explicit partnership/authorization.
"""

from __future__ import annotations

ORG_TYPES = (
    "airline",
    "business_aviation",
    "oem",
    "mro",
    "camo",
    "repair_station",
    "training_organization",
    "supplier",
    "authority",
    "engineering_company",
    "calibration_laboratory",
    "consultant",
    "university",
    "research_center",
)

PROFESSIONAL_ROLES = (
    "ame",
    "engineer",
    "planner",
    "inspector",
    "qa",
    "stores",
    "purchasing",
    "pilot",
    "instructor",
    "manager",
    "executive",
)

PARTNERSHIP_TYPES = (
    "supplier",
    "customer",
    "partner",
    "contractor",
    "training_provider",
    "repair_provider",
    "engineering_provider",
    "oem_relationship",
    "authority_relationship",
)

PARTNERSHIP_STATUSES = ("proposed", "active", "suspended", "expired", "revoked")

COLLABORATION_TYPES = (
    "engineering_support",
    "repair_quotation",
    "technical_assistance",
    "share_publications",
    "share_work_packages",
    "share_digital_records",
    "secure_messaging",
    "shared_project",
    "document_review",
    "approval_workflow",
)

COLLABORATION_STATUSES = ("draft", "requested", "accepted", "in_progress", "completed", "rejected", "cancelled")

SHARE_MODES = ("read_only", "download", "approval_required")

MESSAGE_SCOPES = (
    "org_to_org",
    "user_to_user",
    "project",
    "work_package",
    "marketplace",
)

EVENT_TYPES = (
    "training",
    "conference",
    "webinar",
    "product_release",
    "service_bulletin",
    "job_fair",
    "maintenance_event",
)

DIRECTORY_ENTITY_TYPES = (
    "organization",
    "person",
    "capability",
    "approval",
    "aircraft",
    "engine",
    "training",
    "repair_station",
    "marketplace_listing",
)
