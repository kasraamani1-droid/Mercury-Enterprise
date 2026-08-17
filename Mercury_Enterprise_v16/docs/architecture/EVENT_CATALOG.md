# Enterprise Event Catalog

Families and codes (version `1.0` unless noted).

## Platform
UserCreated, UserUpdated, UserDisabled, RoleGranted, PermissionChanged, OrganizationCreated, OrganizationUpdated

## Aircraft
AircraftCreated, AircraftUpdated, AircraftTransferred, AircraftRetired, ConfigurationChanged

## Component
ComponentInstalled, ComponentRemoved, ComponentTransferred, ComponentInspected, ComponentRepaired, ComponentScrapped

## Maintenance
WorkOrderCreated, WorkOrderAssigned, TaskStarted, TaskCompleted, InspectionCompleted, FindingRaised, FindingClosed, ReleaseSigned, AircraftReleased

## Inventory
PartReceived, PartReserved, PartIssued, PartReturned, InventoryAdjusted

## Marketplace
SupplierRegistered, ProductPublished, QuoteRequested, OrderCreated, ShipmentDispatched, ShipmentDelivered

## Training
CourseCompleted, CertificateIssued, TrainingExpired

## Authority
AuditScheduled, AuditCompleted, ComplianceUpdated

## Digital Twin
TwinCreated, TwinUpdated, PassportUpdated, RelationshipCreated, LifecycleChanged

## AI
RecommendationGenerated, KnowledgeIndexed, ConversationCompleted

API: `GET /api/v1/event-fabric/catalog`
