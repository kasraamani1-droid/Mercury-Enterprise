import { API_BASE } from "../config.js";
import { listify } from "../ux2/api.js";
import { notifyAuthRequired } from "../api.js";

async function softGet(path) {
  try {
    const response = await fetch(`${API_BASE}${path}`, { credentials: "include" });
    if (!response.ok) {
      if (response.status === 401) notifyAuthRequired();
      let error = `HTTP ${response.status}`;
      try {
        const payload = await response.json();
        const detail = payload?.detail;
        if (typeof detail === "string" && detail.trim()) error = detail;
      } catch {
        /* keep HTTP status */
      }
      return { ok: false, status: response.status, data: null, error };
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
    jobCard: `/work-orders/job-cards/${encodeURIComponent(id)}`,
    component: `/components/serialized/${encodeURIComponent(id)}`,
    marketplaceListing: `/marketplace/products/${encodeURIComponent(id)}`,
    organization: `/organizations/${encodeURIComponent(id)}`,
    digitalTwin: `/twin/twins/${encodeURIComponent(id)}`,
    supplier: `/logistics/vendors/${encodeURIComponent(id)}`,
    part: `/logistics/parts/${encodeURIComponent(id)}`,
    materialRequest: `/logistics/material-requests/${encodeURIComponent(id)}`,
    purchaseOrder: `/logistics/purchase-orders/${encodeURIComponent(id)}`,
    tool: `/logistics/tools/${encodeURIComponent(id)}`,
  };

  if (routes[type]) {
    const res = await softGet(routes[type]);
    if (res.ok && res.data) return { ...res, source: "api" };
    return {
      ok: false,
      status: res.status,
      source: "api",
      data: {
        id,
        type,
        name: id,
        status: "unavailable",
        note: res.error || `HTTP ${res.status || 0}`,
      },
      error: res.error,
    };
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
    const [wos, due, twins, cfg, serialized, ata, catalog, fleet, session, logbook, cards] = await Promise.all([
      softGet(`/work-orders/orders?aircraft_id=${encodeURIComponent(id)}&limit=20`),
      softGet(`/planning/due-list?limit=20`),
      softGet(`/twin/twins?limit=40`),
      softGet(`/components/aircraft/${encodeURIComponent(id)}/configuration`),
      softGet(`/components/serialized`),
      softGet(`/components/ata-chapters`),
      softGet(`/components/catalog`),
      softGet(`/fleet/aircraft?limit=100`),
      softGet(`/auth/session`),
      softGet(`/maintenance/logbook?aircraft_id=${encodeURIComponent(id)}&limit=40`),
      softGet(`/work-orders/job-cards?aircraft_id=${encodeURIComponent(id)}&limit=50`),
    ]);
    bundle.workOrdersLoad = { ok: wos.ok, status: wos.status, error: wos.error || "" };
    bundle.workOrders = listify(wos.data);
    bundle.logbookLoad = { ok: logbook.ok, status: logbook.status, error: logbook.error || "" };
    bundle.logbook = listify(logbook.data);
    bundle.jobCardsLoad = { ok: cards.ok, status: cards.status, error: cards.error || "" };
    bundle.jobCards = listify(cards.data);
    bundle.due = listify(due.data?.items || due.data?.due || due.data);
    bundle.configurationLoad = { ok: cfg.ok, status: cfg.status, error: cfg.error || "" };
    bundle.configuration = cfg.ok ? cfg.data : { aircraft_id: id, installed: [] };
    bundle.serializedLoad = { ok: serialized.ok, status: serialized.status, error: serialized.error || "" };
    bundle.serialized = listify(serialized.data);
    bundle.ataLoad = { ok: ata.ok, status: ata.status, error: ata.error || "" };
    bundle.ataChapters = listify(ata.data);
    bundle.catalog = listify(catalog.data);
    bundle.fleetAircraft = listify(fleet.data);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
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
    const aircraftId = record?.aircraft_id;
    const [cards, session, employees, aircraft, logbook, mrs, parts, locations, warehouses] = await Promise.all([
      softGet(`/work-orders/job-cards?work_order_id=${encodeURIComponent(id)}&limit=50`),
      softGet(`/auth/session`),
      softGet(`/personnel/employees?limit=80`),
      aircraftId ? softGet(`/fleet/aircraft/${encodeURIComponent(aircraftId)}`) : Promise.resolve({ ok: false, data: null }),
      aircraftId
        ? softGet(`/maintenance/logbook?aircraft_id=${encodeURIComponent(aircraftId)}&limit=40`)
        : Promise.resolve({ ok: true, status: 200, data: [], error: null }),
      softGet(`/logistics/material-requests?work_order_id=${encodeURIComponent(id)}&limit=50`),
      softGet(`/logistics/parts?limit=80`),
      softGet(`/logistics/locations?limit=80`),
      softGet(`/logistics/warehouses`),
    ]);
    bundle.jobCardsLoad = { ok: cards.ok, status: cards.status, error: cards.error || "" };
    bundle.jobCards = listify(cards.data);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.employees = listify(employees.data);
    bundle.aircraft = aircraft.ok ? aircraft.data : null;
    bundle.logbookLoad = { ok: logbook.ok, status: logbook.status, error: logbook.error || "" };
    bundle.logbook = listify(logbook.data);
    bundle.materialRequestsLoad = { ok: mrs.ok, status: mrs.status, error: mrs.error || "" };
    bundle.materialRequests = listify(mrs.data);
    bundle.parts = listify(parts.data);
    bundle.locations = listify(locations.data);
    bundle.warehouses = listify(warehouses.data);
    bundle.timeline = bundle.jobCards.slice(0, 12).map((card) => ({
      title: `${card.job_card_number || card.id} · ${card.status || ""}`,
      at: card.updated_at || card.created_at || "",
      detail: [card.title, card.technician_employee_id].filter(Boolean).join(" · "),
    }));
  }

  if (type === "jobCard") {
    const orderId = record?.work_order_id;
    const aircraftId = record?.aircraft_id;
    const taskId = record?.maintenance_task_id;
    const [session, employees, attachments, order, aircraft, logbook, audit, mrs, parts, locations, warehouses] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/personnel/employees?limit=80`),
      softGet(`/work-orders/job-cards/${encodeURIComponent(id)}/attachments`),
      orderId ? softGet(`/work-orders/orders/${encodeURIComponent(orderId)}`) : Promise.resolve({ ok: false, data: null }),
      aircraftId ? softGet(`/fleet/aircraft/${encodeURIComponent(aircraftId)}`) : Promise.resolve({ ok: false, data: null }),
      aircraftId
        ? softGet(`/maintenance/logbook?aircraft_id=${encodeURIComponent(aircraftId)}&limit=40`)
        : Promise.resolve({ ok: true, status: 200, data: [], error: null }),
      taskId ? softGet(`/maintenance/tasks/${encodeURIComponent(taskId)}/audit-trail`) : Promise.resolve({ ok: false, data: null }),
      softGet(`/logistics/material-requests?job_card_id=${encodeURIComponent(id)}&limit=50`),
      softGet(`/logistics/parts?limit=80`),
      softGet(`/logistics/locations?limit=80`),
      softGet(`/logistics/warehouses`),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.employees = listify(employees.data);
    bundle.attachmentsLoad = { ok: attachments.ok, status: attachments.status, error: attachments.error || "" };
    bundle.attachments = listify(attachments.data);
    bundle.workOrder = order.ok ? order.data : null;
    bundle.aircraft = aircraft.ok ? aircraft.data : null;
    bundle.logbookLoad = { ok: logbook.ok, status: logbook.status, error: logbook.error || "" };
    bundle.logbook = listify(logbook.data);
    bundle.auditTrail = audit.ok ? audit.data : null;
    bundle.materialRequestsLoad = { ok: mrs.ok, status: mrs.status, error: mrs.error || "" };
    bundle.materialRequests = listify(mrs.data);
    bundle.parts = listify(parts.data);
    bundle.locations = listify(locations.data);
    bundle.warehouses = listify(warehouses.data);
    const events = listify(audit.data?.certification_events);
    bundle.timeline = events.slice(0, 12).map((event) => ({
      title: event.step || event.event_type || "Certification event",
      at: event.occurred_at || event.created_at || "",
      detail: [event.actor_employee_id, event.actor_username, event.notes].filter(Boolean).join(" · "),
    }));
  }

  if (type === "component") {
    const hostId = record?.current_aircraft_id;
    const [history, session, host] = await Promise.all([
      softGet(`/components/serialized/${encodeURIComponent(id)}/history`),
      softGet(`/auth/session`),
      hostId ? softGet(`/fleet/aircraft/${encodeURIComponent(hostId)}`) : Promise.resolve({ ok: false, data: null }),
    ]);
    bundle.historyLoad = { ok: history.ok, status: history.status, error: history.error || "" };
    bundle.installHistory = listify(history.data);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.hostAircraft = host.ok ? host.data : null;
    bundle.timeline = bundle.installHistory.slice(0, 12).map((h) => ({
      title: h.event_type || "History",
      at: h.occurred_at || "",
      detail: [h.position, h.reason, h.actor].filter(Boolean).join(" · "),
    }));
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

  if (type === "part") {
    const [session, balances, units, movements, reservations, locations, warehouses, parts, transfers] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/logistics/stock/balances?part_master_id=${encodeURIComponent(id)}&limit=200`),
      softGet(`/logistics/stock/units?part_master_id=${encodeURIComponent(id)}&limit=200`),
      softGet(`/logistics/stock/movements?part_master_id=${encodeURIComponent(id)}&limit=50`),
      softGet(`/logistics/reservations?part_master_id=${encodeURIComponent(id)}&limit=50`),
      softGet(`/logistics/locations?limit=80`),
      softGet(`/logistics/warehouses`),
      softGet(`/logistics/parts?limit=80`),
      softGet(`/logistics/transfers?limit=30`),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.balancesLoad = { ok: balances.ok, status: balances.status, error: balances.error || "" };
    bundle.balances = listify(balances.data);
    bundle.units = listify(units.data);
    bundle.movements = listify(movements.data);
    bundle.reservations = listify(reservations.data);
    bundle.locations = listify(locations.data);
    bundle.warehouses = listify(warehouses.data);
    bundle.parts = listify(parts.data);
    bundle.transfers = listify(transfers.data);
    bundle.timeline = bundle.movements.slice(0, 12).map((row) => ({
      title: row.movement_type || "Movement",
      at: row.created_at || "",
      detail: [row.qty, row.condition, row.reference_type].filter(Boolean).join(" · "),
    }));
  }

  if (type === "materialRequest") {
    const [session, locations, order, card] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/logistics/locations?limit=80`),
      record?.work_order_id
        ? softGet(`/work-orders/orders/${encodeURIComponent(record.work_order_id)}`)
        : Promise.resolve({ ok: false, data: null }),
      record?.job_card_id
        ? softGet(`/work-orders/job-cards/${encodeURIComponent(record.job_card_id)}`)
        : Promise.resolve({ ok: false, data: null }),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.locations = listify(locations.data);
    bundle.workOrder = order.ok ? order.data : null;
    bundle.jobCard = card.ok ? card.data : null;
    bundle.lines = record?.lines || [];
  }

  if (type === "purchaseOrder") {
    const [session, locations, receipts] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/logistics/locations?limit=80`),
      softGet(`/logistics/receipts?purchase_order_id=${encodeURIComponent(id)}&limit=50`),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.locations = listify(locations.data);
    bundle.receipts = listify(receipts.data);
    const details = await Promise.all(
      bundle.receipts.slice(0, 8).map((row) => softGet(`/logistics/receipts/${encodeURIComponent(row.id)}`))
    );
    bundle.receiptDetails = {};
    details.forEach((res, index) => {
      const rid = bundle.receipts[index]?.id;
      if (rid && res.ok && res.data) {
        bundle.receiptDetails[rid] = res.data;
        bundle.receipts[index] = { ...bundle.receipts[index], ...res.data };
      }
    });
  }

  if (type === "tool") {
    const [session, history] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/logistics/tools/${encodeURIComponent(id)}/history`),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.history = listify(history.data);
    bundle.timeline = bundle.history.slice(0, 12).map((row) => ({
      title: row.event_type || "Tool event",
      at: row.created_at || "",
      detail: row.details || row.performed_by || "",
    }));
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
  const orders = await softGet(`/work-orders/orders?limit=50`);
  if (orders.ok) {
    listify(orders.data)
      .filter((row) => `${row.wo_number || ""} ${row.title || ""} ${row.aircraft_id || ""} ${row.id || ""}`.toLowerCase().includes(q.toLowerCase()))
      .slice(0, 8)
      .forEach((row) => {
        results.push({
          type: "workOrder",
          id: String(row.id),
          label: row.wo_number || row.title || row.id,
          meta: row.status || "work order",
        });
      });
  }
  const parts = await softGet(`/logistics/parts?q=${encodeURIComponent(q)}&limit=20`);
  if (parts.ok) {
    listify(parts.data)
      .slice(0, 8)
      .forEach((row) => {
        results.push({
          type: "part",
          id: String(row.id),
          label: row.oem_part_number || row.description || row.id,
          meta: row.part_class || "part",
        });
      });
  }
  return results;
}

function mapSearchType(kind) {
  const k = String(kind || "").toLowerCase();
  if (k.includes("aircraft")) return "aircraft";
  if (k.includes("job")) return "jobCard";
  if (k.includes("work")) return "workOrder";
  if (k.includes("twin")) return "digitalTwin";
  if (k.includes("product") || k.includes("listing")) return "marketplaceListing";
  if (k.includes("org")) return "organization";
  if (k.includes("component")) return "component";
  if (k.includes("part")) return "part";
  if (k.includes("material")) return "materialRequest";
  if (k.includes("purchase") || k.includes("po")) return "purchaseOrder";
  if (k.includes("tool")) return "tool";
  return "project";
}
