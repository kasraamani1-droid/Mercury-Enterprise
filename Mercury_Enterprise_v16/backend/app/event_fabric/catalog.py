"""Program 17 — Mercury Enterprise Event Catalog.

Canonical enterprise event types (versioned). Domain bus notifications may use
dotted names (marketplace.order.created); catalog codes are PascalCase product names.
"""

from __future__ import annotations

# (code, family, version, description, severity_default)
EVENT_CATALOG: list[tuple[str, str, str, str, str]] = [
    # Platform
    ("UserCreated", "platform", "1.0", "User account created", "info"),
    ("UserUpdated", "platform", "1.0", "User account updated", "info"),
    ("UserDisabled", "platform", "1.0", "User account disabled", "warning"),
    ("RoleGranted", "platform", "1.0", "Role granted to principal", "info"),
    ("PermissionChanged", "platform", "1.0", "Permission set changed", "warning"),
    ("OrganizationCreated", "platform", "1.0", "Organization created", "info"),
    ("OrganizationUpdated", "platform", "1.0", "Organization updated", "info"),
    # Aircraft
    ("AircraftCreated", "aircraft", "1.0", "Aircraft registry record created", "info"),
    ("AircraftUpdated", "aircraft", "1.0", "Aircraft updated", "info"),
    ("AircraftTransferred", "aircraft", "1.0", "Aircraft ownership/operator transfer", "warning"),
    ("AircraftRetired", "aircraft", "1.0", "Aircraft retired", "warning"),
    ("ConfigurationChanged", "aircraft", "1.0", "Aircraft configuration changed", "info"),
    # Component
    ("ComponentInstalled", "component", "1.0", "Component installed on parent", "info"),
    ("ComponentRemoved", "component", "1.0", "Component removed from parent", "info"),
    ("ComponentTransferred", "component", "1.0", "Component transferred", "info"),
    ("ComponentInspected", "component", "1.0", "Component inspected", "info"),
    ("ComponentRepaired", "component", "1.0", "Component repaired", "info"),
    ("ComponentScrapped", "component", "1.0", "Component scrapped", "warning"),
    # Maintenance
    ("WorkOrderCreated", "maintenance", "1.0", "Work order created", "info"),
    ("WorkOrderAssigned", "maintenance", "1.0", "Work order assigned", "info"),
    ("TaskStarted", "maintenance", "1.0", "Task started", "info"),
    ("TaskCompleted", "maintenance", "1.0", "Task completed", "info"),
    ("InspectionCompleted", "maintenance", "1.0", "Inspection completed", "info"),
    ("FindingRaised", "maintenance", "1.0", "Finding raised", "warning"),
    ("FindingClosed", "maintenance", "1.0", "Finding closed", "info"),
    ("ReleaseSigned", "maintenance", "1.0", "Release / CRS signed", "critical"),
    ("AircraftReleased", "maintenance", "1.0", "Aircraft released to service", "critical"),
    # Inventory
    ("PartReceived", "inventory", "1.0", "Part received into inventory", "info"),
    ("PartReserved", "inventory", "1.0", "Part reserved", "info"),
    ("PartIssued", "inventory", "1.0", "Part issued", "info"),
    ("PartReturned", "inventory", "1.0", "Part returned", "info"),
    ("InventoryAdjusted", "inventory", "1.0", "Inventory adjusted", "warning"),
    # Marketplace
    ("SupplierRegistered", "marketplace", "1.0", "Supplier registered", "info"),
    ("ProductPublished", "marketplace", "1.0", "Product published", "info"),
    ("QuoteRequested", "marketplace", "1.0", "Quote requested", "info"),
    ("OrderCreated", "marketplace", "1.0", "Order created", "info"),
    ("ShipmentDispatched", "marketplace", "1.0", "Shipment dispatched", "info"),
    ("ShipmentDelivered", "marketplace", "1.0", "Shipment delivered", "info"),
    # Training
    ("CourseCompleted", "training", "1.0", "Training course completed", "info"),
    ("CertificateIssued", "training", "1.0", "Certificate issued", "info"),
    ("TrainingExpired", "training", "1.0", "Training expired", "warning"),
    # Authority
    ("AuditScheduled", "authority", "1.0", "Authority audit scheduled", "info"),
    ("AuditCompleted", "authority", "1.0", "Authority audit completed", "info"),
    ("ComplianceUpdated", "authority", "1.0", "Compliance status updated", "warning"),
    # Digital Twin
    ("TwinCreated", "twin", "1.0", "Digital Twin created", "info"),
    ("TwinUpdated", "twin", "1.0", "Digital Twin updated", "info"),
    ("PassportUpdated", "twin", "1.0", "Digital Passport updated", "info"),
    ("RelationshipCreated", "twin", "1.0", "Twin/Fabric relationship created", "info"),
    ("LifecycleChanged", "twin", "1.0", "Twin lifecycle changed", "info"),
    # AI
    ("RecommendationGenerated", "ai", "1.0", "AI recommendation generated (advisory)", "info"),
    ("KnowledgeIndexed", "ai", "1.0", "Knowledge indexed for AI", "info"),
    ("ConversationCompleted", "ai", "1.0", "AI conversation completed", "info"),
]

FAMILIES = (
    "platform",
    "aircraft",
    "component",
    "maintenance",
    "inventory",
    "marketplace",
    "training",
    "authority",
    "twin",
    "ai",
    "system",
)

# Map dotted runtime bus names → catalog codes (when applicable)
# Ownership: domain services emit dotted types on Event Framework; selected
# types dual-write into Event Fabric via maybe_dual_write_to_fabric.
BUS_TO_CATALOG: dict[str, str] = {
    "twin.created": "TwinCreated",
    "twin.updated": "TwinUpdated",
    "marketplace.order.created": "OrderCreated",
    "marketplace.quote.created": "QuoteRequested",
    "marketplace.product.created": "ProductPublished",
    "marketplace.listing.created": "ProductPublished",
    "marketplace.seller.created": "SupplierRegistered",
    "fabric.passport.created": "PassportUpdated",
    "fabric.relationship.created": "RelationshipCreated",
    "plugins.installed": "OrganizationUpdated",
    "fleet.aircraft.created": "AircraftCreated",
    "work_order.created": "WorkOrderCreated",
}

SEVERITIES = ("debug", "info", "warning", "error", "critical")
EVENT_STATUSES = ("published", "delivered", "failed", "replayed", "dead_lettered")
