/** Mercury UX 2.0 — Workspace registry & navigation model */

export const NAV_SECTIONS = [
  {
    id: "core",
    label: "Core",
    items: [
      { id: "home", label: "Landing Dashboard", icon: "⌂", shortcut: "G H", keywords: "home landing overview" },
      { id: "context", label: "Open Objects", icon: "◉", shortcut: "G X", keywords: "object context workspace engine" },
      { id: "command", label: "Command Ops (SIM)", icon: "◎", shortcut: "G C", keywords: "incidents ops command simulated", simulated: true },
      { id: "aircraft", label: "Aircraft Workspace", icon: "✈", shortcut: "G A", keywords: "aircraft registration" },
      { id: "fleet", label: "Fleet Workspace", icon: "▣", shortcut: "G F", keywords: "fleet registry" },
    ],
  },
  {
    id: "mro",
    label: "Maintenance",
    items: [
      { id: "planning", label: "Maintenance Planning", icon: "◷", shortcut: "G P", keywords: "mpd forecast hangar" },
      { id: "workOrders", label: "Work Orders", icon: "☰", shortcut: "G W", keywords: "work package job card" },
      { id: "maintenance", label: "MRO Execution", icon: "⚙", shortcut: "G M", keywords: "technician qa aca" },
      { id: "logbook", label: "Digital Logbook", icon: "▤", shortcut: "G L", keywords: "tech log release" },
      { id: "engineering", label: "Engineering", icon: "⌬", shortcut: "G E", keywords: "eo sb ad engineering" },
      { id: "techLibrary", label: "Technical Library", icon: "▤", shortcut: "G B", keywords: "publications library ammm" },
      { id: "approvals", label: "Approvals Inbox", icon: "✓", shortcut: "G R", keywords: "approvals inbox" },
    ],
  },
  {
    id: "supply",
    label: "Supply & Market",
    items: [
      { id: "inventory", label: "Inventory", icon: "▦", shortcut: "G I", keywords: "stock warehouse logistics" },
      { id: "logistics", label: "Logistics Ops", icon: "⇄", shortcut: "G O", keywords: "po tools scan" },
      { id: "marketplace", label: "Marketplace", icon: "◈", shortcut: "G K", keywords: "parts quotes sellers" },
    ],
  },
  {
    id: "platform",
    label: "Platform",
    items: [
      { id: "assetTwin", label: "Digital Twin", icon: "◉", shortcut: "G T", keywords: "twin passport lifecycle" },
      { id: "digitalTwin", label: "Ops Twin (SIM)", icon: "⌖", shortcut: "", keywords: "airport twin sim", simulated: true },
      { id: "authority", label: "Authority Portal", icon: "⚖", shortcut: "G U", keywords: "authority compliance" },
      { id: "oem", label: "OEM Portal", icon: "🏭", shortcut: "", keywords: "oem manufacturer" },
      { id: "organization", label: "Organization Portal", icon: "⌂", shortcut: "G N", keywords: "org sites teams" },
      { id: "ai", label: "AI Workspace", icon: "✦", shortcut: "G Q", keywords: "copilot advisory ai" },
    ],
  },
  {
    id: "ops",
    label: "Operations Suite",
    items: [
      { id: "radar", label: "Radar Console (SIM)", icon: "◎", shortcut: "", keywords: "radar sensors simulated", simulated: true },
      { id: "executive", label: "Executive", icon: "▦", shortcut: "", keywords: "kpi executive" },
      { id: "history", label: "History", icon: "↺", shortcut: "", keywords: "archive history" },
    ],
  },
  {
    id: "admin",
    label: "Admin & Build",
    items: [
      { id: "admin", label: "Administration", icon: "⚙", shortcut: "G D", keywords: "admin users roles audit" },
      { id: "developer", label: "Developer Portal", icon: "</>", shortcut: "G V", keywords: "api plugins event fabric" },
      { id: "cloud", label: "Cloud & HA (SIM)", icon: "☁", shortcut: "", keywords: "cloud ha simulated", simulated: true },
      { id: "integrations", label: "Integrations", icon: "⛓", shortcut: "", keywords: "connectors" },
      { id: "compliance", label: "Compliance", icon: "✓", shortcut: "", keywords: "governance" },
    ],
  },
];

export function allWorkspaces() {
  const items = [];
  for (const section of NAV_SECTIONS) {
    for (const item of section.items) items.push({ ...item, section: section.label });
  }
  return items;
}

export function workspaceById(id) {
  return allWorkspaces().find((w) => w.id === id) || null;
}

export const WORKSPACE_IDS = allWorkspaces().map((w) => w.id);

export const SHORTCUT_ACTIONS = [
  { id: "palette", label: "Open command palette", keys: "Ctrl/Cmd+K" },
  { id: "search", label: "Global search", keys: "Ctrl/Cmd+/" },
  { id: "theme", label: "Toggle theme", keys: "Ctrl/Cmd+Shift+L" },
  { id: "sidebar", label: "Toggle sidebar", keys: "[" },
  { id: "notifications", label: "Notifications", keys: "Ctrl/Cmd+Shift+N" },
];
