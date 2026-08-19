import { API_BASE } from "../config.js";
import { listify } from "../ux2/api.js";
import { notifyAuthRequired } from "../api.js";
import { matchTwinToEntity } from "./twin-ops.js";

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
    finding: `/planning/deferred-defects/${encodeURIComponent(id)}`,
    check: `/planning/checks/${encodeURIComponent(id)}`,
    airworthinessDirective: `/planning/ads/${encodeURIComponent(id)}`,
    serviceBulletin: `/planning/service-bulletins/${encodeURIComponent(id)}`,
    engineeringOrder: `/planning/engineering-orders/${encodeURIComponent(id)}`,
    melItem: `/planning/mel-items/${encodeURIComponent(id)}`,
    publication: `/publications/${encodeURIComponent(id)}`,
    employee: `/personnel/employees/${encodeURIComponent(id)}`,
  };

  if (routes[type]) {
    const res = await softGet(routes[type]);
    if (res.ok && res.data) return { ...res, source: "api" };
    if (type === "digitalTwin" && res.status === 404) {
      const byUuid = await softGet(`/twin/twins/by-uuid/${encodeURIComponent(id)}`);
      if (byUuid.ok && byUuid.data) return { ...byUuid, source: "api" };
    }
    if (type === "finding") {
      const listed = await softGet("/planning/deferred-defects?limit=100");
      const hit = listify(listed.data).find(
        (row) => String(row.id) === String(id) || String(row.defect_number || "") === String(id)
      );
      if (hit) {
        return { ok: true, status: 200, source: "api", data: { ...hit, name: hit.defect_number || hit.title || id }, error: null };
      }
    }
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

async function hydrateTwinDetails(bundle, twinId, { asPrimaryTimeline = false } = {}) {
  if (!twinId) return;
  const [hist, cfg, rel, relationships, passport] = await Promise.all([
    softGet(`/twin/twins/${encodeURIComponent(twinId)}/history?limit=30`),
    softGet(`/twin/twins/${encodeURIComponent(twinId)}/configurations?limit=20`),
    softGet(`/twin/twins/${encodeURIComponent(twinId)}/reliability?limit=20`),
    softGet(`/twin/twins/${encodeURIComponent(twinId)}/relationships`),
    softGet(`/twin/twins/${encodeURIComponent(twinId)}/passport`),
  ]);
  bundle.historyLoad = { ok: hist.ok, status: hist.status, error: hist.error || "" };
  bundle.twinHistory = listify(hist.data);
  if (asPrimaryTimeline) {
    bundle.history = bundle.twinHistory;
    bundle.timeline = bundle.twinHistory.map((row) => ({
      title: row.title || row.history_kind || row.event_type || row.summary || "Twin event",
      at: row.occurred_at || row.created_at || "",
      detail: [row.summary, row.related_ref, row.actor].filter(Boolean).join(" · "),
    }));
  }
  bundle.configurationsLoad = { ok: cfg.ok, status: cfg.status, error: cfg.error || "" };
  bundle.configurations = listify(cfg.data);
  bundle.reliabilityLoad = { ok: rel.ok, status: rel.status, error: rel.error || "" };
  bundle.reliability = listify(rel.data);
  bundle.relationshipsLoad = { ok: relationships.ok, status: relationships.status, error: relationships.error || "" };
  bundle.relationships = relationships.ok ? relationships.data : null;
  bundle.passportLoad = { ok: passport.ok, status: passport.status, error: passport.error || "" };
  bundle.passport = passport.ok ? passport.data : null;
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
    const [wos, due, twins, cfg, serialized, ata, catalog, fleet, session, logbook, cards, checks, ads, sbs, eos, defects, mels, pubs] = await Promise.all([
      softGet(`/work-orders/orders?aircraft_id=${encodeURIComponent(id)}&limit=20`),
      softGet(`/planning/due-list?limit=20`),
      softGet(`/twin/twins?limit=100`),
      softGet(`/components/aircraft/${encodeURIComponent(id)}/configuration`),
      softGet(`/components/serialized`),
      softGet(`/components/ata-chapters`),
      softGet(`/components/catalog`),
      softGet(`/fleet/aircraft?limit=100`),
      softGet(`/auth/session`),
      softGet(`/maintenance/logbook?aircraft_id=${encodeURIComponent(id)}&limit=40`),
      softGet(`/work-orders/job-cards?aircraft_id=${encodeURIComponent(id)}&limit=50`),
      softGet(`/planning/checks?aircraft_id=${encodeURIComponent(id)}&limit=50`),
      softGet(`/planning/ads?limit=40`),
      softGet(`/planning/service-bulletins?limit=40`),
      softGet(`/planning/engineering-orders?limit=40`),
      softGet(`/planning/deferred-defects?aircraft_id=${encodeURIComponent(id)}&limit=50`),
      softGet(`/planning/mel-items?limit=40`),
      softGet(`/publications/by-aircraft/${encodeURIComponent(id)}`),
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
    bundle.checks = listify(checks.data);
    bundle.ads = listify(ads.data);
    bundle.serviceBulletins = listify(sbs.data);
    bundle.engineeringOrders = listify(eos.data);
    bundle.defects = listify(defects.data);
    bundle.melItems = listify(mels.data);
    bundle.publicationsLoad = { ok: pubs.ok, status: pubs.status, error: pubs.error || "" };
    bundle.publications = listify(pubs.data);
    bundle.twinsLoad = { ok: twins.ok, status: twins.status, error: twins.error || "" };
    const twinList = listify(twins.data);
    bundle.twin = matchTwinToEntity(twinList, { entityId: id, entityType: "aircraft" });
    if (bundle.twin?.id) await hydrateTwinDetails(bundle, bundle.twin.id, { asPrimaryTimeline: false });
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
    const [history, session, host, pubs, twins] = await Promise.all([
      softGet(`/components/serialized/${encodeURIComponent(id)}/history`),
      softGet(`/auth/session`),
      hostId ? softGet(`/fleet/aircraft/${encodeURIComponent(hostId)}`) : Promise.resolve({ ok: false, data: null }),
      softGet(`/publications/by-component/${encodeURIComponent(id)}`),
      softGet(`/twin/twins?limit=100`),
    ]);
    bundle.historyLoad = { ok: history.ok, status: history.status, error: history.error || "" };
    bundle.installHistory = listify(history.data);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.hostAircraft = host.ok ? host.data : null;
    bundle.componentPublicationsLoad = { ok: pubs.ok, status: pubs.status, error: pubs.error || "" };
    bundle.componentPublications = pubs.ok ? pubs.data : null;
    bundle.twinsLoad = { ok: twins.ok, status: twins.status, error: twins.error || "" };
    bundle.twin = matchTwinToEntity(listify(twins.data), { entityId: id, entityType: "component" });
    if (bundle.twin?.id) await hydrateTwinDetails(bundle, bundle.twin.id, { asPrimaryTimeline: false });
    bundle.timeline = bundle.installHistory.slice(0, 12).map((h) => ({
      title: h.event_type || "History",
      at: h.occurred_at || "",
      detail: [h.position, h.reason, h.actor].filter(Boolean).join(" · "),
    }));
  }

  if (type === "digitalTwin") {
    const twinId = record?.id || id;
    const session = await softGet(`/auth/session`);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    await hydrateTwinDetails(bundle, twinId, { asPrimaryTimeline: true });
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
    const [session, history, twins] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/logistics/tools/${encodeURIComponent(id)}/history`),
      softGet(`/twin/twins?twin_type=tool&limit=100`),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.toolHistory = listify(history.data);
    bundle.history = bundle.toolHistory;
    bundle.twinsLoad = { ok: twins.ok, status: twins.status, error: twins.error || "" };
    bundle.twin = matchTwinToEntity(listify(twins.data), { entityId: id, entityType: "tool" });
    if (bundle.twin?.id) await hydrateTwinDetails(bundle, bundle.twin.id, { asPrimaryTimeline: false });
    if (!bundle.timeline?.length) {
      bundle.timeline = bundle.toolHistory.slice(0, 12).map((row) => ({
        title: row.event_type || "Tool event",
        at: row.created_at || "",
        detail: row.details || row.performed_by || "",
      }));
    }
  }

  if (
    type === "finding" ||
    type === "check" ||
    type === "airworthinessDirective" ||
    type === "serviceBulletin" ||
    type === "engineeringOrder" ||
    type === "melItem"
  ) {
    const aircraftId = record?.aircraft_id;
    const woId = record?.linked_work_order_id;
    const wpId = record?.generated_work_package_id || record?.work_package_id;
    const pubId = record?.publication_id;
    const [session, mels, aircraft, order, pkgOrders, linkedPub] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/planning/mel-items?limit=40`),
      aircraftId ? softGet(`/fleet/aircraft/${encodeURIComponent(aircraftId)}`) : Promise.resolve({ ok: false, data: null }),
      woId ? softGet(`/work-orders/orders/${encodeURIComponent(woId)}`) : Promise.resolve({ ok: false, data: null }),
      wpId
        ? softGet(`/work-orders/orders?work_package_id=${encodeURIComponent(wpId)}&limit=20`)
        : Promise.resolve({ ok: false, data: null }),
      pubId ? softGet(`/publications/${encodeURIComponent(pubId)}`) : Promise.resolve({ ok: false, data: null }),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.melItems = listify(mels.data);
    bundle.aircraft = aircraft.ok ? aircraft.data : null;
    bundle.workOrder = order.ok ? order.data : null;
    const fromPackage = pkgOrders.ok ? listify(pkgOrders.data) : [];
    if (order.ok && order.data) {
      bundle.workOrders = [order.data, ...fromPackage.filter((row) => String(row.id) !== String(order.data.id))];
    } else if (fromPackage.length) {
      bundle.workOrders = fromPackage;
      bundle.workOrder = fromPackage[0];
    }
    bundle.publications = linkedPub.ok && linkedPub.data ? [linkedPub.data] : [];
  }

  if (type === "publication") {
    const [session, revisions, ata] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/publications/${encodeURIComponent(id)}/revisions`),
      softGet(`/components/ata-chapters`),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.revisionsLoad = { ok: revisions.ok, status: revisions.status, error: revisions.error || "" };
    bundle.revisions = listify(revisions.data);
    bundle.ataChapters = listify(ata.data);
    bundle.timeline = bundle.revisions.slice(0, 12).map((row) => ({
      title: `Revision ${row.revision_number || row.id} · ${row.status || ""}`,
      at: row.updated_at || row.created_at || "",
      detail: row.change_summary || row.storage_kind || "",
    }));
  }

  if (type === "employee") {
    const [session, quals, auths, stamps] = await Promise.all([
      softGet(`/auth/session`),
      softGet(`/personnel/employees/${encodeURIComponent(id)}/qualifications`),
      softGet(`/personnel/employees/${encodeURIComponent(id)}/authorizations`),
      softGet(`/personnel/employees/${encodeURIComponent(id)}/stamps`),
    ]);
    bundle.sessionRole = session.ok ? session.data?.role || "" : "";
    bundle.qualificationsLoad = { ok: quals.ok, status: quals.status, error: quals.error || "" };
    bundle.qualifications = listify(quals.data);
    bundle.authorizations = listify(auths.data);
    bundle.stampsLoad = { ok: stamps.ok, status: stamps.status, error: stamps.error || "" };
    bundle.stamps = listify(stamps.data);
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
  const twinsSearch = await softGet(`/twin/search?q=${encodeURIComponent(q)}&limit=20`);
  if (twinsSearch.ok) {
    listify(twinsSearch.data?.items || twinsSearch.data)
      .slice(0, 8)
      .forEach((row) => {
        results.push({
          type: "digitalTwin",
          id: String(row.twin_id || row.id),
          label: row.title || row.twin_uuid || row.serial_number || row.id,
          meta: row.twin_type || "twin",
        });
      });
  }
  const pubs = await softGet(`/publications?q=${encodeURIComponent(q)}&limit=20`);
  if (pubs.ok) {
    listify(pubs.data)
      .slice(0, 8)
      .forEach((row) => {
        results.push({
          type: "publication",
          id: String(row.id),
          label: row.publication_number || row.title || row.id,
          meta: row.publication_code || "publication",
        });
      });
  }
  const people = await softGet(`/personnel/employees?limit=50`);
  if (people.ok) {
    listify(people.data)
      .filter((row) => `${row.full_name || ""} ${row.employee_number || ""} ${row.id || ""}`.toLowerCase().includes(q.toLowerCase()))
      .slice(0, 8)
      .forEach((row) => {
        results.push({
          type: "employee",
          id: String(row.id),
          label: row.full_name || row.employee_number || row.id,
          meta: row.employee_number || "employee",
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
  if (k.includes("defect") || k.includes("finding")) return "finding";
  if (k.includes("check")) return "check";
  if (k.includes("directive") || k === "ad") return "airworthinessDirective";
  if (k.includes("bulletin") || k === "sb") return "serviceBulletin";
  if (k.includes("engineering") || k === "eo") return "engineeringOrder";
  if (k.includes("mel")) return "melItem";
  if (k.includes("publication") || k.includes("library") || k.includes("manual")) return "publication";
  if (k.includes("employee") || k.includes("personnel")) return "employee";
  return "project";
}
