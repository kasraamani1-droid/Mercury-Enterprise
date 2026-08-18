import { getObjectType, listObjectTypes, sessionKey, parseSessionKey } from "./types.js";
import {
  getActiveSessionKey,
  getPinnedObjects,
  getRecentObjects,
  getSessions,
  pushRecentObject,
  saveSessions,
  setActiveSessionKey,
  togglePinnedObject,
} from "./store.js";
import { loadObjectRecord, loadRelatedBundle, searchObjects } from "./loaders.js";
import {
  bindAiPanel,
  bindCommentForm,
  renderHeader,
  renderMainTab,
  renderRail,
  renderShellSkeleton,
  renderTabs,
} from "./render.js";
import { toast } from "../utils.js";
import { createWorkOrder, createWorkPackage } from "../api.js";
import { uxAddMarketplaceCart, uxCreateMarketplaceQuote, uxCreateTwin, uxRemoveSerializedComponent } from "../ux2/api.js";
import { bindConfigurationPanel, configurationMutationCacheKeys, resolveInstallationHoursCycles, sessionCanManageComponents } from "./configuration.js";

let host = null;
let active = null; // { key, type, id, label, tab, record, bundle }
let onAreaNavigate = null;
let onSessionsChanged = null;
const cache = new Map();
let openGeneration = 0;

function ensureHost() {
  host = document.getElementById("contextWorkspace");
  if (!host) return null;
  if (!host.querySelector("#weShell")) {
    host.innerHTML = `<div class="ux2-page-header we-area-header"><div><div class="mx-label">Workspace Engine</div><h1>Object context</h1><p>Work around aircraft, engines, work orders, twins, and people — not menus.</p></div></div>${renderShellSkeleton()}`;
  }
  return host;
}

function emitSessions() {
  onSessionsChanged?.(getOpenObjectSessions());
}

export function getOpenObjectSessions() {
  return getSessions();
}

export function getActiveObjectSession() {
  return active;
}

export async function openObject(type, id, options = {}) {
  const typeDef = getObjectType(type);
  if (!typeDef) {
    toast(`Unknown object type: ${type}`);
    return null;
  }
  const oid = String(id || "").trim();
  if (!oid) {
    toast("Object id required");
    return null;
  }

  ensureHost();
  const key = sessionKey(type, oid);
  const generation = ++openGeneration;
  const existingTab = getSessions().find((s) => s.key === key)?.tab;
  const tab = options.tab || existingTab || "overview";

  let record;
  let bundle;
  if (cache.has(key) && !options.refresh) {
    ({ record, bundle } = cache.get(key));
  } else {
    const loaded = await loadObjectRecord(type, oid);
    if (generation !== openGeneration) return null;
    record = loaded.data || { id: oid };
    bundle = await loadRelatedBundle(type, oid, record);
    if (generation !== openGeneration) return null;
    cache.set(key, { record, bundle });
  }
  if (generation !== openGeneration) return null;

  const label =
    options.label ||
    typeDef.resolveLabel?.(record) ||
    record.registration ||
    record.name ||
    oid;

  const sessions = getSessions().filter((s) => s.key !== key);
  const session = { key, type, id: oid, label, tab };
  sessions.unshift(session);
  saveSessions(sessions);
  setActiveSessionKey(key);
  pushRecentObject({ key, type, id: oid, label });

  active = { ...session, record, bundle };
  mountActive();
  showContextArea();
  emitSessions();

  try {
    history.replaceState({ we: key, tab }, "", `#/object/${type}/${encodeURIComponent(oid)}`);
  } catch {
    /* ignore */
  }
  return active;
}

export function closeObject(key) {
  const sessions = getSessions().filter((s) => s.key !== key);
  saveSessions(sessions);
  cache.delete(key);
  if (active?.key === key) {
    active = null;
    setActiveSessionKey("");
    if (sessions[0]) {
      const next = sessions[0];
      openObject(next.type, next.id, { label: next.label, tab: next.tab });
    } else {
      showArea("home");
      emitSessions();
    }
  } else {
    emitSessions();
  }
}

export function setObjectTab(tabId) {
  if (!active) return;
  active.tab = tabId;
  const sessions = getSessions().map((s) => (s.key === active.key ? { ...s, tab: tabId } : s));
  saveSessions(sessions);
  mountActive();
}

function showContextArea() {
  showArea("context");
}

function showArea(id) {
  if (typeof onAreaNavigate === "function") onAreaNavigate(id);
}

async function refreshActiveObject(mutation = {}) {
  if (!active) return;
  const { type, id, tab, label } = active;
  const keys = configurationMutationCacheKeys(active, mutation);
  cache.delete(sessionKey(type, id));
  keys.components.forEach((componentId) => cache.delete(sessionKey("component", componentId)));
  keys.aircraft.forEach((aircraftId) => cache.delete(sessionKey("aircraft", aircraftId)));
  await openObject(type, id, { refresh: true, tab, label });
}

function mountActive() {
  if (!ensureHost() || !active) return;
  const typeDef = getObjectType(active.type);
  if (!typeDef) return;

  const header = document.getElementById("weHeader");
  const tabs = document.getElementById("weTabs");
  const main = document.getElementById("weMain");
  const rail = document.getElementById("weRail");
  if (!header || !tabs || !main || !rail) return;

  const headerTypeDef = {
    ...typeDef,
    quickActions: (typeDef.quickActions || []).filter((action) => {
      const canManage = sessionCanManageComponents(active.bundle?.sessionRole);
      if (action.id === "installComponent") return canManage;
      if (action.id === "remove") {
        return canManage && String(active.record?.component_status || "").toLowerCase() === "installed";
      }
      return true;
    }),
  };
  header.innerHTML = renderHeader(active, headerTypeDef, active.record);
  tabs.innerHTML = renderTabs(typeDef, active.tab);
  main.innerHTML = renderMainTab(active, typeDef, active.record, active.bundle, active.tab);
  rail.innerHTML = renderRail(active, typeDef, active.record, active.bundle);

  header.querySelectorAll("[data-we-action]").forEach((btn) => {
    btn.addEventListener("click", () => handleAction(btn.getAttribute("data-we-action")));
  });
  tabs.querySelectorAll("[data-we-tab]").forEach((btn) => {
    btn.addEventListener("click", () => setObjectTab(btn.getAttribute("data-we-tab")));
  });
  document.querySelectorAll("[data-we-open]").forEach((el) => {
    el.addEventListener("click", () => {
      const raw = el.getAttribute("data-we-open");
      const parsed = parseSessionKey(raw);
      if (parsed) openObject(parsed.type, parsed.id);
    });
  });
  bindCommentForm(active.key, () => mountActive());
  bindAiPanel(active, active.record);
  bindConfigurationPanel(active, { onRefresh: refreshActiveObject });

  const search = document.getElementById("weObjectSearch");
  if (search) {
    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      tabs.querySelectorAll(".we-tab").forEach((t) => {
        const show = !q || t.textContent.toLowerCase().includes(q);
        t.style.display = show ? "" : "none";
      });
    });
  }
}

function handleAction(action) {
  if (!active) return;
  if (action === "close") {
    closeObject(active.key);
    return;
  }
  if (action === "pin") {
    togglePinnedObject({ key: active.key, type: active.type, id: active.id, label: active.label });
    toast(getPinnedObjects().some((p) => p.key === active.key) ? "Object pinned" : "Object unpinned");
    emitSessions();
    return;
  }
  if (action === "openTwin") {
    void openOrCreateTwin();
    return;
  }
  if (action === "createWo") {
    void createWorkOrderFromContext();
    return;
  }
  if (action === "addCart") {
    void addListingToCart();
    return;
  }
  if (action === "requestQuote") {
    void requestListingQuote();
    return;
  }
  if (action === "logDefect") {
    onAreaNavigate?.("logbook");
    toast("Open Digital Logbook — create tech-log entry for this aircraft");
    return;
  }
  if (action === "installComponent") {
    if (active.type !== "aircraft") {
      toast("Install component requires an aircraft object");
      return;
    }
    setObjectTab("configuration");
    document.getElementById("weCfgInstallForm")?.scrollIntoView({ block: "nearest" });
    return;
  }
  if (action === "remove") {
    void removeComponentFromHeader();
    return;
  }
  if (action === "attach" || action === "assign" || action === "transition") {
    toast(`${action} — use MRO Execution (object context preserved)`);
    return;
  }
  toast(`${action} queued for ${active.label}`);
}

async function removeComponentFromHeader() {
  if (!active || active.type !== "component") {
    toast("Remove requires a component object");
    return;
  }
  if (!sessionCanManageComponents(active.bundle?.sessionRole)) {
    toast("Component management required");
    return;
  }
  if (String(active.record?.component_status || "").toLowerCase() !== "installed") {
    toast("Component is not installed");
    return;
  }
  const ok = window.confirm(`Remove ${active.label || active.id} from the aircraft to stores?`);
  if (!ok) return;
  const resolved = resolveInstallationHoursCycles(active.record, "", "");
  if (!resolved.ok) {
    toast(resolved.error);
    return;
  }
  const result = await uxRemoveSerializedComponent(active.id, {
    destination_status: "stores",
    aircraft_hours: resolved.hours,
    aircraft_cycles: resolved.cycles,
  });
  if (!result.ok) {
    toast(result.error || "Remove failed");
    return;
  }
  toast("Component removed");
  await refreshActiveObject({
    componentId: active.id,
    sourceAircraftId: active.record?.current_aircraft_id || "",
  });
}

async function createWorkOrderFromContext() {
  if (!active || active.type !== "aircraft") {
    toast("Create work order requires an aircraft object");
    return;
  }
  const aircraftId = active.id;
  const title = window.prompt("Work order title", `WO · ${active.label || aircraftId}`);
  if (!title) return;
  try {
    const pkg = await createWorkPackage({
      aircraft_id: aircraftId,
      description: `Package for ${active.label || aircraftId}`,
      priority: "normal",
    });
    const packageId = pkg?.id;
    if (!packageId) throw new Error("Work package create failed");
    const order = await createWorkOrder({
      work_package_id: packageId,
      title: String(title).trim(),
      description: `Created from aircraft workspace ${active.label || aircraftId}`,
      priority: "normal",
    });
    const orderId = order?.id;
    if (!orderId) throw new Error("Work order create failed");
    toast(`Work order ${order.wo_number || orderId} created`);
    cache.delete(active.key);
    await openObject("workOrder", orderId, { refresh: true, label: order.wo_number || orderId });
  } catch (err) {
    toast(err?.message || "Failed to create work order");
  }
}

async function openOrCreateTwin() {
  if (!active) return;
  let twinId = active.bundle?.twin?.id;
  if (!twinId && active.type === "digitalTwin") {
    twinId = active.id;
  }
  if (twinId) {
    await openObject("digitalTwin", twinId, { refresh: true });
    return;
  }
  if (active.type !== "aircraft") {
    toast("No twin linked for this object");
    return;
  }
  const ok = window.confirm(`No twin linked to ${active.label || active.id}. Create an aircraft twin?`);
  if (!ok) return;
  const created = await uxCreateTwin({
    twin_type: "aircraft",
    display_name: String(active.label || active.id),
    serial_number: String(active.record?.serial_number || ""),
    fabric_entity_type: "aircraft",
    fabric_entity_id: String(active.id),
    lifecycle_state: "in_service",
    ensure_passport: true,
  });
  if (!created.ok || !created.data?.id) {
    toast(created.error || "Twin create failed");
    return;
  }
  toast("Twin registered");
  cache.delete(active.key);
  active.bundle = { ...(active.bundle || {}), twin: created.data };
  await openObject("digitalTwin", created.data.id, { refresh: true, label: created.data.display_name });
}

async function addListingToCart() {
  if (!active || active.type !== "marketplaceListing") {
    toast("Add to cart requires a marketplace listing");
    return;
  }
  const res = await uxAddMarketplaceCart({ product_id: active.id, qty: 1 });
  if (!res.ok) {
    toast(res.error || "Cart add failed");
    return;
  }
  toast("Added to cart");
  onAreaNavigate?.("marketplace");
}

async function requestListingQuote() {
  if (!active || active.type !== "marketplaceListing") {
    toast("Request quote requires a marketplace listing");
    return;
  }
  const notes = window.prompt("Quote notes (optional)", "") ?? "";
  const res = await uxCreateMarketplaceQuote({ product_id: active.id, qty: 1, notes });
  if (!res.ok) {
    toast(res.error || "Quote request failed");
    return;
  }
  toast(`Quote ${res.data?.quote_number || res.data?.id || ""} requested`);
  onAreaNavigate?.("marketplace");
}

export function focusSession(key) {
  const parsed = parseSessionKey(key);
  if (!parsed) return;
  const existing = getSessions().find((s) => s.key === key);
  openObject(parsed.type, parsed.id, { label: existing?.label, tab: existing?.tab });
}

export function initializeWorkspaceEngine(options = {}) {
  onAreaNavigate = options.onAreaNavigate || null;
  onSessionsChanged = options.onSessionsChanged || null;
  ensureHost();

  document.addEventListener("click", (e) => {
    const open = e.target?.closest?.("[data-we-open]");
    if (open) {
      e.preventDefault();
      const parsed = parseSessionKey(open.getAttribute("data-we-open"));
      if (parsed) openObject(parsed.type, parsed.id, { label: open.getAttribute("data-we-label") || undefined });
    }
  });

  const hash = (location.hash || "").replace(/^#\/?/, "");
  const m = hash.match(/^object\/([^/]+)\/(.+)$/);
  if (m) {
    openObject(decodeURIComponent(m[1]), decodeURIComponent(m[2]));
  } else {
    const activeKey = getActiveSessionKey();
    if (activeKey && getSessions().some((s) => s.key === activeKey)) {
      // restore only when deep-linked or explicitly requested
    }
  }

  return {
    openObject,
    closeObject,
    focusSession,
    getOpenObjectSessions,
    getActiveObjectSession,
    listObjectTypes,
    searchObjects,
    getRecentObjects,
    getPinnedObjects,
  };
}

export { listObjectTypes, searchObjects, getRecentObjects, getPinnedObjects };
