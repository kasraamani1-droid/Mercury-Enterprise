import { API_BASE } from "./config.js";

const DEFAULT_TIMEOUT_MS = 8000;

export function notifyAuthRequired() {
  if (typeof window === "undefined") return;
  const overlay = document.getElementById("loginOverlay");
  if (overlay && !overlay.classList.contains("hidden")) return;
  window.dispatchEvent(new CustomEvent("mercury:auth-required"));
}

export async function request(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS
  );

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      credentials: "include",
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = `Request failed (${response.status})`;

      try {
        const body = await response.json();
        detail = body.detail || detail;
      } catch {
        // Response did not contain JSON error details.
      }

      if (response.status === 401 && path !== "/auth/login") {
        notifyAuthRequired();
      }

      throw new Error(detail);
    }

    return response;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Backend request timed out");
    }

    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}


export async function getHealth() {
  return (await request("/health")).json();
}

export async function login(payload) {
  return (
    await request("/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function logout() {
  return (
    await request("/auth/logout", {
      method: "POST",
    })
  ).json();
}

export async function getPublicAuthConfig() {
  return (await request("/auth/public-config")).json();
}

export async function getSessionStatus() {
  return (await request("/auth/session")).json();
}

export async function getSessionContext() {
  return (await request("/auth/context")).json();
}

export async function updateSessionContext(payload) {
  return (
    await request("/auth/context", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function requestApproval(payload) {
  return (
    await request("/approvals", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function listApprovals(statusFilter) {
  const suffix = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : "";
  return (await request(`/approvals${suffix}`)).json();
}

export async function approveRequest(approvalId) {
  return (
    await request(`/approvals/${approvalId}/approve`, {
      method: "POST",
    })
  ).json();
}

export async function getIncidents() {
  return (await request("/incidents")).json();
}

export async function getIncident(id) {
  return (await request(`/incidents/${id}`)).json();
}

export async function getAssessment(id) {
  return (await request(`/incidents/${id}/assessment`)).json();
}

export async function createIncident(payload) {
  return (
    await request("/incidents", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function addEvent(id, payload) {
  return (
    await request(`/incidents/${id}/events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function resolveIncident(id, approvalId = null) {
  const payload = {
    status: "resolved",
  };
  if (approvalId) {
    payload.approval_id = approvalId;
  }
  return (
    await request(`/incidents/${id}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function downloadReport(id) {
  return request(`/incidents/${id}/report`);
}
export async function getDashboardSummary() {
    return (await request("/dashboard/summary")).json();
}

export async function listAudit({ action, target_id, limit } = {}) {
  const params = new URLSearchParams();
  if (action) params.set("action", action);
  if (target_id) params.set("target_id", target_id);
  if (limit != null) params.set("limit", String(limit));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return (await request(`/audit${suffix}`)).json();
}
export async function getReportSummary({ start, end } = {}) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return (await request(`/reports/summary${suffix}`)).json();
}

export async function getReportHistory({ start, end, limit } = {}) {
  const params = new URLSearchParams();
  if (start) params.set("start", start);
  if (end) params.set("end", end);
  if (limit != null) params.set("limit", String(limit));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return (await request(`/reports/history${suffix}`)).json();
}

export async function listConnectors() {
  return (await request("/connectors")).json();
}

export async function getConnectorHealth(id) {
  return (await request(`/connectors/${id}/health`)).json();
}

export async function getConnectorHealthHistory(id, limit = 50) {
  return (await request(`/connectors/${id}/health-history?limit=${limit}`)).json();
}

export async function startConnector(id) {
  return (await request(`/connectors/${id}/start`, { method: "POST" })).json();
}

export async function stopConnector(id) {
  return (await request(`/connectors/${id}/stop`, { method: "POST" })).json();
}

export async function recoverConnector(id) {
  return (await request(`/connectors/${id}/recover`, { method: "POST" })).json();
}

export async function pollConnector(id) {
  return (await request(`/connectors/${id}/poll`, { method: "POST" })).json();
}

export async function evaluateDecision(payload) {
  return (await request("/decisions/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })).json();
}

export async function listDecisions(limit = 20) {
  return (await request(`/decisions?limit=${limit}`)).json();
}

export async function getDecision(decisionId) {
  return (await request(`/decisions/${decisionId}`)).json();
}

export async function reviewDecision(decisionId, payload) {
  return (await request(`/decisions/${decisionId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })).json();
}

function qs(params = {}) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export async function listWorkPackages(params = {}) {
  return (await request(`/work-orders/packages${qs(params)}`)).json();
}

export async function createWorkPackage(payload) {
  return (
    await request(`/work-orders/packages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function listWorkOrders(params = {}) {
  return (await request(`/work-orders/orders${qs(params)}`)).json();
}

export async function createWorkOrder(payload) {
  return (
    await request(`/work-orders/orders`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function listJobCards(params = {}) {
  return (await request(`/work-orders/job-cards${qs(params)}`)).json();
}

export async function createJobCard(payload) {
  return (
    await request(`/work-orders/job-cards`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function assignJobCard(jobCardId, payload) {
  return (
    await request(`/work-orders/job-cards/${jobCardId}/assign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function transitionJobCard(jobCardId, payload) {
  return (
    await request(`/work-orders/job-cards/${jobCardId}/transition`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function completeJobCardWork(jobCardId, payload) {
  return (
    await request(`/work-orders/job-cards/${jobCardId}/complete-work`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function inspectJobCard(jobCardId, payload) {
  return (
    await request(`/work-orders/job-cards/${jobCardId}/inspect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function releaseJobCard(jobCardId, payload) {
  return (
    await request(`/work-orders/job-cards/${jobCardId}/release`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function addJobCardAttachment(jobCardId, payload) {
  return (
    await request(`/work-orders/job-cards/${jobCardId}/attachments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
  ).json();
}

export async function getWorkOrderDashboard(params = {}) {
  return (await request(`/work-orders/dashboard${qs(params)}`)).json();
}

export async function getWorkOrderReport(report, params = {}) {
  return (await request(`/work-orders/reports/${encodeURIComponent(report)}${qs(params)}`)).json();
}

export async function listEmployees(params = {}) {
  return (await request(`/personnel/employees${qs(params)}`)).json();
}

export async function listPublications(params = {}) {
  return (await request(`/publications${qs(params)}`)).json();
}
