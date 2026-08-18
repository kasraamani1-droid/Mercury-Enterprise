"""Program 16 — Mercury Plugin Platform catalog.

First-class operational plugins and OEM/system integrations.
Live vendor SDKs are future Connect adapters — architecture readiness only.
SMS here means Safety Management System (not text messaging; see connect sms.generic).
"""

from __future__ import annotations

# (code, name, category, connect_connector, capabilities, readiness, description)
PLUGINS: list[tuple[str, str, str, str, list[str], str, str]] = [
    (
        "garmin",
        "Garmin Plugin",
        "oem_avionics",
        "oem.garmin",
        ["flight_data", "avionics_sync", "efb_bridge"],
        "partial",
        "Garmin avionics / aviation systems integration plugin",
    ),
    (
        "honeywell",
        "Honeywell Plugin",
        "oem_avionics",
        "oem.honeywell",
        ["avionics_sync", "health_monitoring", "publications"],
        "partial",
        "Honeywell aerospace systems integration plugin",
    ),
    (
        "drone_inspection",
        "Drone Inspection",
        "inspection",
        "inspection.drone",
        ["mission_plan", "imagery", "defect_markers", "ndt_handoff"],
        "planned",
        "UAS / drone inspection mission and imagery ingest",
    ),
    (
        "ndt",
        "NDT",
        "inspection",
        "ndt.generic",
        ["technique_catalog", "findings", "certificates", "personnel_quals"],
        "partial",
        "Non-destructive testing workflows and evidence",
    ),
    (
        "flight_ops",
        "Flight Ops",
        "operations",
        "flight_ops.generic",
        ["schedule", "dispatch", "status", "crew_pairing_ready"],
        "planned",
        "Flight operations schedule and status integration",
    ),
    (
        "accounting",
        "Accounting",
        "finance",
        "accounting.generic",
        ["invoices", "gl", "ap_ar", "cost_centers"],
        "ready",
        "Accounting / finance system bridge",
    ),
    (
        "custom_dashboards",
        "Custom Dashboards",
        "analytics",
        "dashboard.custom",
        ["widgets", "layouts", "kpis", "tenant_scoped"],
        "ready",
        "Tenant-defined operational dashboards (not a separate BI product)",
    ),
    (
        "erp",
        "ERP",
        "finance",
        "erp.generic",
        ["master_data", "orders", "inventory", "procurement"],
        "ready",
        "Enterprise resource planning bridge",
    ),
    (
        "sms",
        "SMS (Safety Management System)",
        "safety",
        "safety.sms",
        ["hazards", "reports", "risk", "corrective_actions"],
        "planned",
        "Safety Management System — not cellular SMS messaging",
    ),
    (
        "weather",
        "Weather",
        "operations",
        "weather.generic",
        ["metar", "taf", "sigmet", "briefing_ready"],
        "partial",
        "Aviation weather feed integration",
    ),
    (
        "fuel_planning",
        "Fuel Planning",
        "operations",
        "fuel.planning",
        ["burn_estimate", "tankering_ready", "uplift", "cost_model"],
        "planned",
        "Fuel planning and uplift decision support architecture",
    ),
]

PLUGIN_CATEGORIES = (
    "oem_avionics",
    "inspection",
    "operations",
    "finance",
    "analytics",
    "safety",
)

INSTALL_STATUSES = ("available", "installed", "configured", "disabled")

# Additional Connect connectors for Program 16 (merged into ecosystem CONNECTORS seed)
EXTRA_CONNECTORS: list[tuple[str, str, str, list[str], str]] = [
    ("oem.garmin", "Garmin Aviation", "oem", ["flight_data", "avionics_sync", "efb_bridge"], "partial"),
    ("oem.honeywell", "Honeywell Aerospace", "oem", ["avionics_sync", "health_monitoring", "publications"], "partial"),
    ("inspection.drone", "Drone Inspection", "inspection", ["mission_plan", "imagery", "defect_markers"], "planned"),
    ("ndt.generic", "NDT Systems", "inspection", ["technique_catalog", "findings", "certificates"], "partial"),
    ("dashboard.custom", "Custom Dashboards", "analytics", ["widgets", "layouts", "kpis"], "ready"),
    ("safety.sms", "Safety Management System", "safety", ["hazards", "reports", "risk", "corrective_actions"], "planned"),
    ("fuel.planning", "Fuel Planning", "flight_ops", ["burn_estimate", "uplift", "cost_model"], "planned"),
]
