/**
 * Mercury Workspace Engine — object type catalog.
 * Context-oriented workspaces: users work around objects, not menus.
 */

const COMMON_RAIL = ["timeline", "widgets", "activity", "attachments", "comments", "notifications", "search", "ai"];

/** @typedef {{ id: string, label: string, icon?: string }} TabDef */
/** @typedef {{ type: string, label: string, icon: string, color?: string, tabs: TabDef[], quickActions: {id:string,label:string}[], resolveLabel?: (obj:object)=>string }} TypeDef */

/** @type {Record<string, TypeDef>} */
export const OBJECT_TYPES = {
  aircraft: {
    type: "aircraft",
    label: "Aircraft",
    icon: "✈",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "configuration", label: "Configuration" },
      { id: "digitalTwin", label: "Digital Twin" },
      { id: "maintenance", label: "Maintenance" },
      { id: "workOrders", label: "Work Orders" },
      { id: "history", label: "History" },
      { id: "logbook", label: "Logbook" },
      { id: "reliability", label: "Reliability" },
      { id: "sb", label: "SB" },
      { id: "ad", label: "AD" },
      { id: "components", label: "Components" },
      { id: "marketplace", label: "Marketplace" },
      { id: "documents", label: "Documents" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "createWo", label: "Create work order" },
      { id: "openTwin", label: "Open twin" },
      { id: "installComponent", label: "Install component" },
      { id: "logDefect", label: "Log defect" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.registration || o.tail_number || o.name || o.id,
  },
  engine: {
    type: "engine",
    label: "Engine",
    icon: "⚙",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "configuration", label: "Configuration" },
      { id: "digitalTwin", label: "Digital Twin" },
      { id: "maintenance", label: "Maintenance" },
      { id: "workOrders", label: "Work Orders" },
      { id: "history", label: "History" },
      { id: "reliability", label: "Reliability" },
      { id: "llp", label: "LLP" },
      { id: "components", label: "Components" },
      { id: "documents", label: "Documents" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "shopVisit", label: "Plan shop visit" },
      { id: "openTwin", label: "Open twin" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.serial_number || o.esn || o.name || o.id,
  },
  apu: {
    type: "apu",
    label: "APU",
    icon: "⚡",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "configuration", label: "Configuration" },
      { id: "digitalTwin", label: "Digital Twin" },
      { id: "maintenance", label: "Maintenance" },
      { id: "workOrders", label: "Work Orders" },
      { id: "history", label: "History" },
      { id: "reliability", label: "Reliability" },
      { id: "documents", label: "Documents" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "createWo", label: "Create work order" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.serial_number || o.name || o.id,
  },
  workOrder: {
    type: "workOrder",
    label: "Work Order",
    icon: "☰",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "tasks", label: "Tasks / Job cards" },
      { id: "materials", label: "Materials" },
      { id: "labor", label: "Labor" },
      { id: "findings", label: "Findings" },
      { id: "inspections", label: "Inspections" },
      { id: "documents", label: "Documents" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "assign", label: "Assign technician" },
      { id: "transition", label: "Progress work" },
      { id: "requestMaterial", label: "Request material" },
      { id: "openAircraft", label: "Open aircraft" },
      { id: "openLogbook", label: "Aircraft logbook" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.wo_number || o.number || o.work_order_number || o.id,
  },
  jobCard: {
    type: "jobCard",
    label: "Job Card",
    icon: "⚒",
    tabs: [
      { id: "overview", label: "Execution" },
      { id: "materials", label: "Materials" },
      { id: "inspections", label: "Inspection / release" },
      { id: "history", label: "History" },
      { id: "documents", label: "Documents" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "requestMaterial", label: "Request material" },
      { id: "openWorkOrder", label: "Open work order" },
      { id: "openAircraft", label: "Open aircraft" },
      { id: "openLogbook", label: "Aircraft logbook" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.job_card_number || o.title || o.id,
  },
  inspection: {
    type: "inspection",
    label: "Inspection",
    icon: "⌕",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "checklist", label: "Checklist" },
      { id: "findings", label: "Findings" },
      { id: "evidence", label: "Evidence" },
      { id: "documents", label: "Documents" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "pass", label: "Record pass" },
      { id: "fail", label: "Record fail" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.title || o.code || o.id,
  },
  finding: {
    type: "finding",
    label: "Finding",
    icon: "!",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "disposition", label: "Disposition" },
      { id: "related", label: "Related WOs" },
      { id: "documents", label: "Documents" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "defer", label: "Defer / MEL" },
      { id: "createWo", label: "Raise work order" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.defect_number || o.code || o.title || o.id,
  },
  check: {
    type: "check",
    label: "Maintenance Check",
    icon: "◷",
    tabs: [
      { id: "overview", label: "Check" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "generateWp", label: "Generate work package" },
      { id: "openAircraft", label: "Open aircraft" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.check_code || o.title || o.id,
  },
  airworthinessDirective: {
    type: "airworthinessDirective",
    label: "Airworthiness Directive",
    icon: "!",
    tabs: [
      { id: "overview", label: "AD" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [{ id: "pin", label: "Pin object" }],
    resolveLabel: (o) => o.ad_number || o.title || o.id,
  },
  serviceBulletin: {
    type: "serviceBulletin",
    label: "Service Bulletin",
    icon: "▤",
    tabs: [
      { id: "overview", label: "SB" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [{ id: "pin", label: "Pin object" }],
    resolveLabel: (o) => o.sb_number || o.title || o.id,
  },
  engineeringOrder: {
    type: "engineeringOrder",
    label: "Engineering Order",
    icon: "⌬",
    tabs: [
      { id: "overview", label: "EO" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "approveEo", label: "Approve EO" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.eo_number || o.title || o.id,
  },
  melItem: {
    type: "melItem",
    label: "MEL / CDL Item",
    icon: "✓",
    tabs: [
      { id: "overview", label: "Item" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [{ id: "pin", label: "Pin object" }],
    resolveLabel: (o) => o.item_number || o.title || o.id,
  },
  component: {
    type: "component",
    label: "Component",
    icon: "▣",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "installHistory", label: "Install history" },
      { id: "digitalTwin", label: "Digital Twin" },
      { id: "reliability", label: "Reliability" },
      { id: "marketplace", label: "Marketplace" },
      { id: "documents", label: "Documents" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "remove", label: "Remove from aircraft" },
      { id: "openTwin", label: "Open twin" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.serial_number || o.part_number || o.name || o.id,
  },
  marketplaceListing: {
    type: "marketplaceListing",
    label: "Marketplace Listing",
    icon: "◈",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "pricing", label: "Pricing" },
      { id: "inventory", label: "Inventory" },
      { id: "seller", label: "Seller" },
      { id: "reviews", label: "Reviews" },
      { id: "documents", label: "Documents" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "addCart", label: "Add to cart" },
      { id: "requestQuote", label: "Request quote" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.name || o.title || o.sku || o.id,
  },
  supplier: {
    type: "supplier",
    label: "Supplier",
    icon: "⇄",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "catalog", label: "Catalog" },
      { id: "orders", label: "Orders" },
      { id: "performance", label: "Performance" },
      { id: "documents", label: "Documents" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "newPo", label: "New PO" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.name || o.code || o.id,
  },
  organization: {
    type: "organization",
    label: "Organization",
    icon: "⌂",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "sites", label: "Sites" },
      { id: "teams", label: "Teams" },
      { id: "memberships", label: "Memberships" },
      { id: "capabilities", label: "Capabilities" },
      { id: "documents", label: "Documents" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "switchContext", label: "Switch context" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.name || o.code || o.id,
  },
  engineer: {
    type: "engineer",
    label: "Engineer",
    icon: "⌬",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "eoQueue", label: "EO queue" },
      { id: "adSb", label: "AD / SB" },
      { id: "publications", label: "Publications" },
      { id: "projects", label: "Projects" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "newEo", label: "New EO" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.display_name || o.name || o.id,
  },
  planner: {
    type: "planner",
    label: "Planner",
    icon: "◷",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "dueList", label: "Due list" },
      { id: "forecast", label: "Forecast" },
      { id: "hangar", label: "Hangar" },
      { id: "packages", label: "Work packages" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "generateWp", label: "Generate WP" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.display_name || o.name || o.id,
  },
  technician: {
    type: "technician",
    label: "Technician",
    icon: "⚒",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "myWork", label: "My work" },
      { id: "tools", label: "Tools" },
      { id: "materials", label: "Materials" },
      { id: "qualifications", label: "Qualifications" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "clockIn", label: "Clock on card" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.display_name || o.name || o.id,
  },
  qa: {
    type: "qa",
    label: "QA",
    icon: "✓",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "inspectionQueue", label: "Inspection queue" },
      { id: "findings", label: "Findings" },
      { id: "releases", label: "Releases" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "inspect", label: "Start inspection" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.display_name || o.name || o.id,
  },
  project: {
    type: "project",
    label: "Project",
    icon: "▦",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "plan", label: "Plan" },
      { id: "workOrders", label: "Work Orders" },
      { id: "risks", label: "Risks" },
      { id: "documents", label: "Documents" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "addMilestone", label: "Add milestone" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.name || o.code || o.id,
  },
  part: {
    type: "part",
    label: "Part",
    icon: "▦",
    tabs: [
      { id: "overview", label: "Stock" },
      { id: "documents", label: "Documents" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [{ id: "pin", label: "Pin object" }],
    resolveLabel: (o) => o.oem_part_number || o.part_number || o.name || o.id,
  },
  materialRequest: {
    type: "materialRequest",
    label: "Material Request",
    icon: "⇄",
    tabs: [
      { id: "overview", label: "Demand" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "openWorkOrder", label: "Open work order" },
      { id: "openJobCard", label: "Open job card" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.request_number || o.id,
  },
  purchaseOrder: {
    type: "purchaseOrder",
    label: "Purchase Order",
    icon: "☰",
    tabs: [
      { id: "overview", label: "Receiving" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [{ id: "pin", label: "Pin object" }],
    resolveLabel: (o) => o.po_number || o.id,
  },
  tool: {
    type: "tool",
    label: "Tool",
    icon: "⚒",
    tabs: [
      { id: "overview", label: "Crib" },
      { id: "history", label: "History" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [{ id: "pin", label: "Pin object" }],
    resolveLabel: (o) => o.tool_code || o.description || o.id,
  },
  digitalTwin: {
    type: "digitalTwin",
    label: "Digital Twin",
    icon: "◉",
    tabs: [
      { id: "overview", label: "Overview" },
      { id: "passport", label: "Passport" },
      { id: "configuration", label: "Configuration" },
      { id: "history", label: "History" },
      { id: "reliability", label: "Reliability" },
      { id: "relationships", label: "Relationships" },
      { id: "aiAssistant", label: "AI Assistant" },
    ],
    quickActions: [
      { id: "addHistory", label: "Add history event" },
      { id: "pin", label: "Pin object" },
    ],
    resolveLabel: (o) => o.name || o.twin_uuid || o.id,
  },
};

export const RAIL_PANELS = COMMON_RAIL;

export function getObjectType(type) {
  return OBJECT_TYPES[type] || null;
}

export function listObjectTypes() {
  return Object.values(OBJECT_TYPES);
}

export function sessionKey(type, id) {
  return `${type}:${id}`;
}

export function parseSessionKey(key) {
  const idx = String(key).indexOf(":");
  if (idx < 0) return null;
  return { type: key.slice(0, idx), id: key.slice(idx + 1) };
}
