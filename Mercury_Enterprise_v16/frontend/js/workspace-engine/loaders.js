import { API_BASE } from "../config.js";
import { listify } from "../ux2/api.js";
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

export async function loadObjectRecord(type, id) {
  const routes = {
    aircraft: `/fleet/aircraft/${encodeURIComponent(id)}`,
    workOrder: `/work-orders/orders/${encodeURIComponent(id)}`,
    component: `/components/serialized/${encodeURIComponent(id)}`,
    marketplaceListing: `/marketplace/products/${encodeURIComponent(id)}`,
    organization: `/organizations/${encodeURIComponent(id)}`,
    digitalTwin: `/twin/twins/${encodeURIComponent(id)}`,
    supplier: `/logistics/vendors/${encodeURIComponent(id)}`,
  };

  if (routes[type]) {
    const res = await softGet(routes[type]);
    if (res.ok && res.data) return { ...res, source: "api" };
  }

  if (type === "finding") {
    const res = await softGet("/planning/deferred-defects?limit=100");
    const hit = listify(res.data).find(
      (row) => String(row.id) === String(id) || String(row.defect_number || "") === String(id)
    );
    if (hit) {
      return {
        ok: true,
        status: 200,
        source: "api",
        data: { ...hit, name: hit.defect_number || hit.title || id },
        error: null,
      };
    }
  }

  // Persona / synthetic / unresolved — local context shell
  return {
    ok: true,
    status: 200,
    source: "context",
    data: {
      id,
      type,
      name: id,
      status: "context",
      note: "Context workspace — live record may be incomplete or persona-scoped.",
    },
    error: null,
  };
}

export async function loadRelatedBundle(type, id, record) {
  const bundle = {
    timeline: [],
    workOrders: [],
    notifications: [],
    twin: null,
    due: [],
  };

  if (type === "aircraft") {
    const [wos, due, twins] = await Promise.all([
      softGet(`/work-orders/orders?aircraft_id=${encodeURIComponent(id)}&limit=20`),
      softGet(`/planning/due-list?limit=20`),
      softGet(`/twin/twins?limit=40`),
    ]);
    bundle.workOrders = listify(wos.data);
    bundle.due = listify(due.data?.items || due.data?.due || due.data);
    const twinList = listify(twins.data);
    bundle.twin =
      twinList.find(
        (t) =>
          String(t.fabric_entity_id || t.linked_entity_id || t.entity_id || "") === String(id) &&
          String(t.fabric_entity_type || t.linked_entity_type || t.entity_type || "aircraft")
            .toLowerCase()
            .includes("aircraft")
      ) ||
      twinList.find((t) => String(t.fabric_entity_id || t.linked_entity_id || t.entity_id || "") === String(id)) ||
      null;
  }

  if (type === "workOrder") {
    const cards = await softGet(`/work-orders/job-cards?work_order_id=${encodeURIComponent(id)}&limit=30`);
    bundle.jobCards = listify(cards.data);
  }

  if (type === "digitalTwin") {
    const [hist, cfg, rel, relationships] = await Promise.all([
      softGet(`/twin/twins/${encodeURIComponent(id)}/history?limit=30`),
      softGet(`/twin/twins/${encodeURIComponent(id)}/configurations?limit=20`),
      softGet(`/twin/twins/${encodeURIComponent(id)}/reliability?limit=20`),
      softGet(`/twin/twins/${encodeURIComponent(id)}/relationships`),
    ]);
    bundle.timeline = listify(hist.data).map((h) => ({
      title: h.event_type || h.summary || "Twin event",
      at: h.occurred_at || h.created_at || "",
      detail: h.details || h.payload_json || "",
    }));
    bundle.configurations = listify(cfg.data);
    bundle.reliability = listify(rel.data);
    bundle.relationships = relationships.ok ? relationships.data : null;
  }

  if (type === "marketplaceListing") {
    const pricing = await softGet(`/marketplace/products/${encodeURIComponent(id)}/pricing`);
    bundle.pricing = pricing.ok ? pricing.data : null;
  }

  if (type === "organization") {
    const sites = await softGet(`/organizations/${encodeURIComponent(id)}/sites`);
    bundle.sites = listify(sites.data);
  }

  // Synthetic timeline seed from record
  if (!bundle.timeline.length) {
    bundle.timeline = [
      { title: "Workspace opened", at: new Date().toISOString(), detail: `${type} ${id}` },
      {
        title: record?.status ? `Status · ${record.status}` : "Context ready",
        at: record?.updated_at || record?.created_at || "",
        detail: record?.note || "Object context loaded",
      },
    ];
  }

  return bundle;
}

export async function searchObjects(query) {
  const q = String(query || "").trim();
  if (q.length < 2) return [];
  const results = [];
  const platform = await softGet(`/platform/search?q=${encodeURIComponent(q)}&limit=12`);
  if (platform.ok) {
    const hits = listify(platform.data?.hits || platform.data);
    hits.forEach((h) => {
      results.push({
        type: mapSearchType(h.entity_type || h.kind),
        id: String(h.entity_id || h.id || h.document_id || ""),
        label: h.title || h.name || h.summary || "Result",
        meta: h.entity_type || "search",
      });
    });
  }
  const aircraft = await softGet(`/fleet/aircraft?limit=50`);
  if (aircraft.ok) {
    listify(aircraft.data)
      .filter((a) => `${a.registration || ""} ${a.id || ""}`.toLowerCase().includes(q.toLowerCase()))
      .slice(0, 8)
      .forEach((a) => {
        results.push({
          type: "aircraft",
          id: String(a.id),
          label: a.registration || a.id,
          meta: "aircraft",
        });
      });
  }
  return results;
}

function mapSearchType(kind) {
  const k = String(kind || "").toLowerCase();
  if (k.includes("aircraft")) return "aircraft";
  if (k.includes("work")) return "workOrder";
  if (k.includes("twin")) return "digitalTwin";
  if (k.includes("product") || k.includes("listing")) return "marketplaceListing";
  if (k.includes("org")) return "organization";
  if (k.includes("component")) return "component";
  return "project";
}
