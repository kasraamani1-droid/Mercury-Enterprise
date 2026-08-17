"""Program 15 — Mercury Digital Twin vocabularies.

Digital Twin = complete digital lifecycle of every aviation asset.
Not a 3D model. Passports never disappear; history is immutable.
"""

from __future__ import annotations

TWIN_TYPES = (
    "aircraft",
    "engine",
    "apu",
    "landing_gear",
    "propeller",
    "flight_control",
    "serialized_component",
    "non_serialized_component",
    "tool",
    "test_equipment",
    "gse",
    "hangar",
    "facility",
    "organization",
    "personnel",
)

LIFECYCLE_STATES = (
    "manufactured",
    "delivered",
    "installed",
    "operated",
    "removed",
    "inspected",
    "repaired",
    "modified",
    "transferred",
    "stored",
    "returned",
    "scrapped",
    "retired",
    "archived",
)

HISTORY_KINDS = (
    "ownership",
    "configuration",
    "installation",
    "removal",
    "maintenance",
    "inspection",
    "repair",
    "modification",
    "sb_compliance",
    "ad_compliance",
    "llp",
    "utilization",
    "failure",
    "certificate",
    "document",
    "publication",
    "signature",
    "audit",
    "lifecycle",
)

CONFIG_BASELINES = ("current", "previous", "future_planned")

RELIABILITY_METRICS = (
    "mtbur",
    "mtbf",
    "dispatch_reliability",
    "failure_rate",
    "repeat_defects",
    "deferred_defects",
    "trend_analysis",
)

PASSPORT_KIND_MAP = {
    "aircraft": "aircraft",
    "engine": "component",
    "apu": "component",
    "landing_gear": "component",
    "propeller": "component",
    "flight_control": "component",
    "serialized_component": "component",
    "non_serialized_component": "component",
    "tool": "tool",
    "test_equipment": "tool",
    "gse": "tool",
    "hangar": "organization",
    "facility": "organization",
    "organization": "organization",
    "personnel": "personnel",
}
