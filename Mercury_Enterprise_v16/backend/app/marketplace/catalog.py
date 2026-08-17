"""Program 13 — Mercury Digital Marketplace categories and vocabularies.

Platform owns the marketplace; organizations own inventory and listings.
Verification badges are architectural readiness only — no regulatory claims.
"""

from __future__ import annotations

# Catalog categories (B2B aviation commerce)
CATEGORIES: list[tuple[str, str, str]] = [
    ("aircraft_parts", "Aircraft Parts", "parts"),
    ("rotables", "Rotables", "parts"),
    ("consumables", "Consumables", "parts"),
    ("expendables", "Expendables", "parts"),
    ("special_tools", "Special Tools", "tools"),
    ("gse", "GSE", "tools"),
    ("test_equipment", "Test Equipment", "tools"),
    ("calibration", "Calibration", "calibration"),
    ("component_repairs", "Component Repairs", "repairs"),
    ("engine_repairs", "Engine Repairs", "repairs"),
    ("avionics_repairs", "Avionics Repairs", "repairs"),
    ("engineering_services", "Engineering Services", "services"),
    ("aircraft_painting", "Aircraft Painting", "services"),
    ("aircraft_interior", "Aircraft Interior", "services"),
    ("ndt_services", "NDT Services", "services"),
    ("training", "Training", "training"),
    ("publications", "Publications", "publications"),
    ("software", "Software", "software"),
    ("jobs", "Jobs", "careers"),
    ("consulting", "Consulting", "services"),
]

SELLER_TYPES = (
    "oem",
    "authorized_distributor",
    "pma_manufacturer",
    "amo",
    "repair_station",
    "calibration_laboratory",
    "training_organization",
    "engineering_company",
    "software_vendor",
    "tool_manufacturer",
    "parts_supplier",
    "consultant",
)

BUYER_TYPES = (
    "operator",
    "airline",
    "business_aviation",
    "mro",
    "oem",
    "military",  # future
    "government",
    "training_organization",
)

# Architecture-only verification badges — NOT regulatory verification
VERIFICATION_BADGES = (
    "oem",
    "amo",
    "repair_station",
    "authority_recognition",
    "training_approval",
    "calibration_accreditation",
)

ORDER_STATUSES = (
    "draft",
    "submitted",
    "quoted",
    "accepted",
    "fulfilled",
    "shipped",
    "completed",
    "cancelled",
)

QUOTE_STATUSES = ("draft", "sent", "accepted", "rejected", "expired")
