import { API_BASE } from "./config.js";

const DEFAULT_TIMEOUT_MS = 8000;

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS
  );

  try {
    const response = await fetch(`${API_BASE}${path}`, {
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

export async function resolveIncident(id) {
  return (
    await request(`/incidents/${id}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        status: "resolved",
      }),
    })
  ).json();
}

export async function downloadReport(id) {
  return request(`/incidents/${id}/report`);
}
export async function getDashboardSummary() {
    return (await request("/dashboard/summary")).json();
}