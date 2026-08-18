import { API_BASE } from "../config.js";
import { notifyAuthRequired } from "../api.js";

async function softGet(path) {
  try {
    const response = await fetch(`${API_BASE}${path}`, { credentials: "include" });
    if (!response.ok) {
      if (response.status === 401) notifyAuthRequired();
      return { ok: false, status: response.status, data: null, error: `HTTP ${response.status}` };
    }
    return { ok: true, status: response.status, data: await response.json(), error: null };
  } catch (error) {
    return { ok: false, status: 0, data: null, error: error.message || "Request failed" };
  }
}

async function softMutate(path, { method = "POST", body } = {}) {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      credentials: "include",
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    if (!response.ok) {
      if (response.status === 401) notifyAuthRequired();
      const detail = data?.detail;
      const msg = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : `HTTP ${response.status}`;
      return { ok: false, status: response.status, data, error: msg };
    }
    return { ok: true, status: response.status, data, error: null };
  } catch (error) {
    return { ok: false, status: 0, data: null, error: error.message || "Request failed" };
  }
}

function listify(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.items)) return data.items;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

export async function uxFetchFleetAircraft(params = "") {
  const q = params ? (params.startsWith("?") ? params : `?${params}`) : "?limit=100";
  return softGet(`/fleet/aircraft${q}`);
}

export async function uxFetchFleets() {
  return softGet("/fleet/fleets?limit=50");
}

export async function uxFetchFleetModels() {
  return softGet("/fleet/models");
}

export async function uxFetchFleetStatuses() {
  return softGet("/fleet/statuses");
}

export async function uxCreateAircraft(payload) {
  return softMutate("/fleet/aircraft", { body: payload });
}

export async function uxPatchAircraftStatus(aircraftId, status_code) {
  return softMutate(`/fleet/aircraft/${encodeURIComponent(aircraftId)}/status`, {
    method: "PATCH",
    body: { status_code },
  });
}

export async function uxCreateRegistration(payload) {
  return softMutate("/fleet/registrations", { body: payload });
}

export async function uxPatchRegistration(registrationId, payload) {
  return softMutate(`/fleet/registrations/${encodeURIComponent(registrationId)}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function uxFetchOrgTree() {
  return softGet("/organizations?limit=50");
}

export async function uxFetchMarketplaceProducts() {
  return softGet("/marketplace/products?limit=40");
}

export async function uxFetchMarketplaceCart() {
  return softGet("/marketplace/cart");
}

export async function uxAddMarketplaceCart(payload) {
  return softMutate("/marketplace/cart", { body: payload });
}

export async function uxFetchMarketplaceQuotes() {
  return softGet("/marketplace/quotes?limit=40");
}

export async function uxCreateMarketplaceQuote(payload) {
  return softMutate("/marketplace/quotes", { body: payload });
}

export async function uxFetchTwins() {
  return softGet("/twin/twins?limit=40");
}

export async function uxCreateTwin(payload) {
  return softMutate("/twin/twins", { body: payload });
}

export async function uxFetchAuthority() {
  return softGet("/authority/bodies");
}

export async function uxFetchPlatformSearch(q) {
  const query = encodeURIComponent(q || "");
  return softGet(`/platform/search?q=${query}&limit=20`);
}

export async function uxFetchPlatformNotifications() {
  return softGet("/platform/notifications?limit=30");
}

export async function uxFetchPlugins() {
  return softGet("/plugins/catalog?limit=50");
}

export async function uxFetchPluginInstallations() {
  return softGet("/plugins/installations?limit=50");
}

export async function uxFetchEventCatalog() {
  return softGet("/event-fabric/catalog?limit=50");
}

export async function uxFetchEventSubscriptions() {
  return softGet("/event-fabric/subscriptions?limit=50");
}

export async function uxFetchEventDlq() {
  return softGet("/event-fabric/dlq?limit=50");
}

export async function uxFetchPlanningDue() {
  return softGet("/planning/due-list?limit=30");
}

export async function uxFetchAds() {
  return softGet("/planning/ads?limit=40");
}

export async function uxFetchServiceBulletins() {
  return softGet("/planning/service-bulletins?limit=40");
}

export async function uxFetchEngineeringOrders() {
  return softGet("/planning/engineering-orders?limit=40");
}

export async function uxFetchLogbook(params = "") {
  const q = params ? (params.startsWith("?") ? params : `?${params}`) : "?limit=40";
  return softGet(`/maintenance/logbook${q}`);
}

export async function uxFetchWorkOrders() {
  return softGet("/work-orders/orders?limit=40");
}

export async function uxFetchApprovals(statusFilter) {
  const q = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
  return softGet(`/approvals${q}`);
}

export async function uxApproveRequest(approvalId) {
  return softMutate(`/approvals/${encodeURIComponent(approvalId)}/approve`, { method: "POST" });
}

export { listify, softGet, softMutate };
