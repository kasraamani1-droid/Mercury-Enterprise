import { el, esc } from "./utils.js";
import { getSessionStatus } from "./api.js";
import { listify, softGet, softMutate } from "./ux2/api.js";
import {
  filterMaterialRequests,
  filterStockRows,
  mutationErrorMessage,
  parsePositiveQty,
  qtyAvailable,
  runLocked,
  scanTargetObject,
  sessionCanPurchase,
  sessionCanReadLogistics,
  sessionCanStores,
  sessionCanTools,
  transferWarehousesValid,
  waitingPartsCards,
} from "./workspace-engine/logistics-ops.js";
import { openObject } from "./workspace-engine/index.js";

let lastRole = "";
let refreshGeneration = 0;

function toast(msg) {
  const t = el("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2800);
}

function setStatus(text) {
  const node = el("logStatus");
  if (node) node.textContent = text || "";
}

function empty(text) {
  return `<div class="empty">${esc(text)}</div>`;
}

function rowOpen(type, id, label, inner) {
  return `<div class="contact-row we-row-open" data-we-open="${esc(type)}:${esc(String(id))}" data-we-label="${esc(label || id)}">${inner}</div>`;
}

function renderRows(hostId, html, fallback) {
  const host = el(hostId);
  if (!host) return;
  host.innerHTML = html || empty(fallback);
}

export async function refreshLogisticsWorkspace() {
  const generation = ++refreshGeneration;
  setStatus("Loading logistics…");
  const session = await getSessionStatus().catch(() => null);
  lastRole = session?.role || "";
  if (!sessionCanReadLogistics(lastRole) && session?.role) {
    setStatus("Logistics read is not granted for this session.");
  }

  const [
    dash,
    warehouses,
    locations,
    parts,
    balances,
    tools,
    mrs,
    pos,
    vendors,
    shortages,
    reservations,
    movements,
    waitingCards,
  ] = await Promise.all([
    softGet("/logistics/dashboard"),
    softGet("/logistics/warehouses"),
    softGet("/logistics/locations?limit=80"),
    softGet("/logistics/parts?limit=80"),
    softGet("/logistics/stock/balances?limit=80"),
    softGet("/logistics/tools?limit=40"),
    softGet("/logistics/material-requests?limit=40"),
    softGet("/logistics/purchase-orders?limit=30"),
    softGet("/logistics/vendors"),
    softGet("/logistics/shortages"),
    softGet("/logistics/reservations?limit=40"),
    softGet("/logistics/stock/movements?limit=30"),
    softGet("/work-orders/job-cards?status=waiting_parts&limit=40"),
  ]);
  if (generation !== refreshGeneration) return;

  const failed = [dash, warehouses, locations, parts, balances].filter((res) => !res.ok);
  setStatus(
    failed.length
      ? `Partial load: ${failed.map((res) => res.error || `HTTP ${res.status}`).join("; ")}`
      : "Live logistics data."
  );

  const kpi = el("logDashKpis");
  if (kpi) {
    if (!dash.ok) {
      kpi.innerHTML = `<article><span>Dashboard</span><b>unavailable</b></article>`;
    } else {
      const d = dash.data || {};
      kpi.innerHTML = `
        <article><span>Low stock</span><b>${esc(String(d.low_stock_parts ?? 0))}</b></article>
        <article><span>On hand</span><b>${esc(String(d.total_on_hand ?? 0))}</b></article>
        <article><span>Reserved</span><b>${esc(String(d.total_reserved ?? 0))}</b></article>
        <article><span>Open MRs</span><b>${esc(String(d.open_material_requests ?? 0))}</b></article>
        <article><span>Open reservations</span><b>${esc(String(d.open_reservations ?? 0))}</b></article>
        <article><span>Open POs</span><b>${esc(String(d.open_purchase_orders ?? 0))}</b></article>
        <article><span>Movements today</span><b>${esc(String(d.movements_today ?? 0))}</b></article>
        <article><span>Cal due</span><b>${esc(String(d.tools_calibration_due_30d ?? 0))}</b></article>`;
    }
  }

  const q = el("logSearch")?.value || "";
  const loc = el("logLocationFilter")?.value || "";
  const cond = el("logConditionFilter")?.value || "";
  const mrStatus = el("logMrStatus")?.value || "";

  const locItems = listify(locations.data);
  const locFilter = el("logLocationFilter");
  if (locFilter && locFilter.options.length <= 1) {
    locFilter.innerHTML =
      `<option value="">All locations</option>` +
      locItems.map((row) => `<option value="${esc(row.id)}">${esc(row.location_code || row.id)}</option>`).join("");
  }

  const stockRows = filterStockRows(listify(balances.data), { q, locationId: loc, condition: cond });
  renderRows(
    "logBalances",
    stockRows
      .map((b) =>
        rowOpen(
          "part",
          b.part_master_id,
          b.oem_part_number || b.part_number || b.part_master_id,
          `<b>${esc(b.oem_part_number || b.part_number || b.part_master_id)}</b><span>${esc(b.part_description || "")} · ${esc(b.location_code || b.location_id || "")} · OH ${esc(String(b.qty_on_hand))} RSV ${esc(String(b.qty_reserved))} AVL ${esc(String(qtyAvailable(b)))}</span><em>${esc(b.condition || "")}</em>`
        )
      )
      .join(""),
    balances.ok ? "No stock balances." : balances.error || "Stock unavailable"
  );

  renderRows(
    "logWarehouses",
    listify(warehouses.data)
      .map(
        (w) =>
          `<div class="contact-row"><b>${esc(w.code)}</b><span>${esc(w.name)} · ${esc(w.warehouse_type)}</span><em>${esc(w.status)}</em></div>`
      )
      .join(""),
    warehouses.ok ? "No warehouses." : warehouses.error || "Warehouses unavailable"
  );

  renderRows(
    "logLocations",
    locItems
      .slice(0, 30)
      .map(
        (l) =>
          `<div class="contact-row"><b>${esc(l.location_code)}</b><span>${esc(l.location_type)} · ${esc(l.warehouse_id || "")}</span><em>${esc(l.status)}</em></div>`
      )
      .join(""),
    locations.ok ? "No locations." : locations.error || "Locations unavailable"
  );

  const partRows = listify(parts.data).filter((p) => {
    if (!q) return true;
    return `${p.oem_part_number || ""} ${p.description || ""}`.toLowerCase().includes(String(q).toLowerCase());
  });
  renderRows(
    "logParts",
    partRows
      .map((p) =>
        rowOpen(
          "part",
          p.id,
          p.oem_part_number || p.id,
          `<b>${esc(p.oem_part_number)}</b><span>${esc(p.description)} · ${esc(p.part_class)}</span><em>${esc(p.issue_policy || "")}</em>`
        )
      )
      .join(""),
    parts.ok ? "No parts." : parts.error || "Parts unavailable"
  );

  renderRows(
    "logTools",
    listify(tools.data)
      .map((t) =>
        rowOpen(
          "tool",
          t.id,
          t.tool_code || t.id,
          `<b>${esc(t.tool_code)}</b><span>${esc(t.description)} · cal ${esc(t.calibration_status)}</span><em>${esc(t.status)}</em>`
        )
      )
      .join(""),
    tools.ok ? "No tools." : tools.error || "Tools unavailable"
  );

  const mrRows = filterMaterialRequests(listify(mrs.data), { q, status: mrStatus });
  renderRows(
    "logMaterialRequests",
    mrRows
      .map((m) =>
        rowOpen(
          "materialRequest",
          m.id,
          m.request_number || m.id,
          `<b>${esc(m.request_number)}</b><span>WO ${esc(m.work_order_id || "—")} · JC ${esc(m.job_card_id || "—")}</span><em>${esc(m.status)}</em>`
        )
      )
      .join(""),
    mrs.ok ? "No material requests." : mrs.error || "Material requests unavailable"
  );

  renderRows(
    "logPurchaseOrders",
    listify(pos.data)
      .map((p) =>
        rowOpen(
          "purchaseOrder",
          p.id,
          p.po_number || p.id,
          `<b>${esc(p.po_number)}</b><span>${esc(p.currency)} · ${esc(p.vendor_id || "")}</span><em>${esc(p.status)}</em>`
        )
      )
      .join(""),
    pos.ok ? "No purchase orders." : pos.error || "Purchase orders unavailable"
  );

  renderRows(
    "logVendors",
    listify(vendors.data)
      .map(
        (v) =>
          `<div class="contact-row"><b>${esc(v.code)}</b><span>${esc(v.name)} · ${esc(v.vendor_type)}</span><em>★ ${esc(String(v.rating))}</em></div>`
      )
      .join(""),
    vendors.ok ? "No vendors." : vendors.error || "Vendors unavailable"
  );

  const shortageItems = listify(shortages.data?.items || shortages.data);
  renderRows(
    "logShortages",
    shortageItems
      .slice(0, 30)
      .map((s) =>
        rowOpen(
          "part",
          s.part_master_id,
          s.oem_part_number || s.part_master_id,
          `<b>${esc(s.oem_part_number || s.part_number || s.part_master_id)}</b><span>AVL ${esc(String(s.qty_available ?? ""))} · ROP ${esc(String(s.reorder_point ?? ""))}</span><em>${esc(s.status || "")}</em>`
        )
      )
      .join(""),
    shortages.ok ? "No shortages." : shortages.error || "Shortages unavailable"
  );

  const waiting = waitingPartsCards(listify(waitingCards.data));
  renderRows(
    "logWaitingParts",
    waiting
      .map(
        (card) =>
          `<div class="contact-row we-row-open" data-we-open="jobCard:${esc(String(card.id))}" data-we-tab="materials" data-we-label="${esc(card.job_card_number || card.id)}"><b>${esc(card.job_card_number || card.id)}</b><span>WO ${esc(card.work_order_id || "—")} · ${esc(card.title || "")}</span><em>waiting_parts</em></div>`
      )
      .join(""),
    waitingCards.ok ? "No job cards waiting on parts." : waitingCards.error || "Job cards unavailable"
  );

  renderRows(
    "logReservations",
    listify(reservations.data)
      .slice(0, 30)
      .map(
        (row) =>
          `<div class="contact-row"><b>${esc(row.id)}</b><span>${esc(row.part_master_id)} · qty ${esc(String(row.qty))} · ${esc(row.source_type || "")} ${esc(row.source_id || "")}</span><em>${esc(row.status)}</em></div>`
      )
      .join(""),
    reservations.ok ? "No reservations." : reservations.error || "Reservations unavailable"
  );

  renderRows(
    "logMovements",
    listify(movements.data)
      .slice(0, 25)
      .map(
        (row) =>
          `<div class="contact-row"><b>${esc(row.movement_type)}</b><span>${esc(String(row.qty))} · ${esc(row.part_master_id)} · ${esc(row.from_location_id || "—")} → ${esc(row.to_location_id || "—")}</span><em>${esc(String(row.created_at || "").slice(0, 19))}</em></div>`
      )
      .join(""),
    movements.ok ? "No movements." : movements.error || "Movements unavailable"
  );

  renderOpsDesk({
    parts: listify(parts.data),
    locations: locItems,
    warehouses: listify(warehouses.data),
    reservations: listify(reservations.data),
  });
}

function optionList(items, valueKey, labelFn, emptyLabel) {
  if (!items.length) return `<option value="">${esc(emptyLabel)}</option>`;
  return [`<option value="">${esc(emptyLabel)}</option>`]
    .concat(items.map((item) => `<option value="${esc(item[valueKey])}">${esc(labelFn(item))}</option>`))
    .join("");
}

function renderOpsDesk({ parts, locations, warehouses, reservations }) {
  const host = el("logOpsDesk");
  if (!host) return;
  const canStores = sessionCanStores(lastRole);
  const canTools = sessionCanTools(lastRole);
  const canPurchase = sessionCanPurchase(lastRole);
  const partOpts = optionList(parts, "id", (p) => `${p.oem_part_number} · ${p.description || ""}`, "Select part");
  const locOpts = optionList(locations, "id", (l) => `${l.location_code} · ${l.location_type || ""}`, "Select location");
  const locAny = optionList(locations, "id", (l) => `${l.location_code}`, "Any / default");
  const whOpts = optionList(warehouses, "id", (w) => `${w.code} · ${w.name || ""}`, "Select warehouse");
  const openRsv = (reservations || []).filter((row) => String(row.status || "") === "open");
  host.innerHTML = `
    <p class="muted" id="logOpsMsg"></p>
    <p class="muted">Session role ${esc(lastRole || "unknown")}: stores ${canStores ? "allowed" : "hidden"} · tools ${canTools ? "allowed" : "hidden"} · purchase ${canPurchase ? "allowed" : "read"}.</p>
    ${
      canStores
        ? `<div class="enterprise-grid">
      <article class="card"><h3>Receive</h3>
        <form data-log-action="receive" class="stack-form">
          <label>Part <select name="part_master_id" required>${partOpts}</select></label>
          <label>Location <select name="location_id" required>${locOpts}</select></label>
          <label>Qty <input name="qty" type="number" min="0.0001" step="any" required /></label>
          <label>Condition <select name="condition"><option>serviceable</option><option>unserviceable</option><option>quarantine</option></select></label>
          <button type="submit">Receive</button>
        </form>
      </article>
      <article class="card"><h3>Issue</h3>
        <form data-log-action="issue" class="stack-form">
          <label>Part <select name="part_master_id" required>${partOpts}</select></label>
          <label>Location <select name="location_id">${locAny}</select></label>
          <label>Qty <input name="qty" type="number" min="0.0001" step="any" required /></label>
          <label>Condition <select name="condition"><option>serviceable</option><option>unserviceable</option><option>quarantine</option></select></label>
          <label>Reference type <input name="reference_type" placeholder="job_card" /></label>
          <label>Reference id <input name="reference_id" /></label>
          <button type="submit">Issue</button>
        </form>
      </article>
      <article class="card"><h3>Reserve</h3>
        <form data-log-action="reserve" class="stack-form">
          <label>Part <select name="part_master_id" required>${partOpts}</select></label>
          <label>Qty <input name="qty" type="number" min="0.0001" step="any" required /></label>
          <label>Location <select name="location_id">${locAny}</select></label>
          <label>Source type <select name="source_type"><option value="manual">manual</option><option value="work_package">work_package</option><option value="material_request">material_request</option></select></label>
          <label>Source id <input name="source_id" /></label>
          <button type="submit">Reserve</button>
        </form>
        <form data-log-action="release" class="stack-form">
          <label>Open reservation <select name="reservation_id" required>${
            openRsv.length
              ? openRsv.map((row) => `<option value="${esc(row.id)}">${esc(row.id)} · ${esc(String(row.qty))}</option>`).join("")
              : `<option value="">None open</option>`
          }</select></label>
          <button type="submit">Release</button>
        </form>
      </article>
      <article class="card"><h3>Adjust / transfer</h3>
        <form data-log-action="adjust" class="stack-form">
          <label>Part <select name="part_master_id" required>${partOpts}</select></label>
          <label>Location <select name="location_id" required>${locOpts}</select></label>
          <label>Qty delta <input name="qty_delta" type="number" step="any" required /></label>
          <label>Reason <input name="reason" required /></label>
          <button type="submit">Adjust</button>
        </form>
        <form data-log-action="transfer" class="stack-form">
          <label>From warehouse <select name="from_warehouse_id" required>${whOpts}</select></label>
          <label>To warehouse <select name="to_warehouse_id" required>${whOpts}</select></label>
          <label>Part <select name="part_master_id" required>${partOpts}</select></label>
          <label>Qty <input name="qty" type="number" min="0.0001" step="any" required /></label>
          <button type="submit">Create transfer</button>
        </form>
      </article>
    </div>`
        : `<p class="muted">Stores mutations are hidden for this role. Viewer/Reviewer can inspect stock and demand; Operator/Administrator can receive, reserve, issue, and transfer.</p>`
    }
    ${canTools ? `<p class="muted">Tool issue/return/calibrate is on the tool object workspace (open a tool row).</p>` : ""}
    ${canPurchase ? `<p class="muted">PO receive/inspect/putaway is on the purchase-order object (open a PO row). Payments are not configured.</p>` : ""}
  `;
}

async function handleDeskSubmit(form) {
  const action = form.getAttribute("data-log-action");
  const values = Object.fromEntries(new FormData(form).entries());
  const msg = el("logOpsMsg");
  const fail = (result) => {
    const text = mutationErrorMessage(result);
    if (msg) msg.textContent = text;
    toast(text);
  };
  const ok = async (text, extraRefresh = true) => {
    if (msg) msg.textContent = text;
    toast(text);
    if (extraRefresh) await refreshLogisticsWorkspace();
  };

  if (action === "receive") {
    const qty = parsePositiveQty(values.qty);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    const result = await runLocked(`desk-receive:${values.part_master_id}`, () =>
      softMutate("/logistics/stock/receive", {
        body: {
          part_master_id: values.part_master_id,
          location_id: values.location_id,
          qty,
          condition: values.condition || "serviceable",
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok("Stock received");
  }
  if (action === "issue") {
    const qty = parsePositiveQty(values.qty);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    if (!window.confirm(`Issue ${qty} from stores?`)) return;
    const body = {
      part_master_id: values.part_master_id,
      qty,
      condition: values.condition || "serviceable",
      reference_type: values.reference_type || "",
      reference_id: values.reference_id || "",
    };
    if (values.location_id) body.location_id = values.location_id;
    const result = await runLocked(`desk-issue:${values.part_master_id}`, () => softMutate("/logistics/stock/issue", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok("Stock issued");
  }
  if (action === "reserve") {
    const qty = parsePositiveQty(values.qty);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    const body = {
      part_master_id: values.part_master_id,
      qty,
      source_type: values.source_type || "manual",
      source_id: values.source_id || "",
    };
    if (values.location_id) body.location_id = values.location_id;
    const result = await runLocked(`desk-reserve:${values.part_master_id}`, () => softMutate("/logistics/reservations", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok("Reserved");
  }
  if (action === "release") {
    if (!values.reservation_id) return fail({ status: 422, error: "Reservation required" });
    const result = await runLocked(`desk-release:${values.reservation_id}`, () =>
      softMutate(`/logistics/reservations/${encodeURIComponent(values.reservation_id)}/release`, { method: "POST" })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok("Reservation released");
  }
  if (action === "adjust") {
    const delta = Number(values.qty_delta);
    if (!Number.isFinite(delta) || delta === 0) return fail({ status: 422, error: "qty_delta must be non-zero" });
    if (!window.confirm(`Apply stock adjustment of ${delta}?`)) return;
    const result = await runLocked(`desk-adjust:${values.part_master_id}`, () =>
      softMutate("/logistics/stock/adjust", {
        body: {
          part_master_id: values.part_master_id,
          location_id: values.location_id,
          qty_delta: delta,
          condition: "serviceable",
          reason: String(values.reason || "").trim(),
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok("Stock adjusted");
  }
  if (action === "transfer") {
    if (!transferWarehousesValid(values.from_warehouse_id, values.to_warehouse_id)) {
      return fail({ status: 422, error: "Source and destination warehouses must be different" });
    }
    const qty = parsePositiveQty(values.qty);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    const result = await runLocked(`desk-transfer:${values.from_warehouse_id}`, () =>
      softMutate("/logistics/transfers", {
        body: {
          from_warehouse_id: values.from_warehouse_id,
          to_warehouse_id: values.to_warehouse_id,
          lines: [{ part_master_id: values.part_master_id, qty }],
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok(`Transfer ${result.data?.transfer_number || ""} created`);
  }
}

export function initializeLogistics() {
  el("logRefresh")?.addEventListener("click", () => refreshLogisticsWorkspace());
  el("logApplyFilters")?.addEventListener("click", () => refreshLogisticsWorkspace());
  el("logSearch")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") refreshLogisticsWorkspace();
  });
  el("logisticsWorkspace")?.addEventListener("submit", (event) => {
    const form = event.target?.closest?.("[data-log-action]");
    if (!form) return;
    event.preventDefault();
    handleDeskSubmit(form);
  });
  el("logScanBtn")?.addEventListener("click", async () => {
    const value = el("logScanValue")?.value?.trim();
    if (!value) return toast("Enter a scan value");
    const result = await runLocked(`scan:${value}`, () => softMutate("/logistics/scan", { body: { value } }));
    if (!result) return;
    const host = el("logScanResult");
    if (!result.ok) {
      if (host) host.innerHTML = empty(mutationErrorMessage(result));
      toast(mutationErrorMessage(result));
      return;
    }
    const body = result.data || {};
    if (host) {
      host.innerHTML = `<div class="contact-row"><b>${esc(body.target_type || "unknown")}</b><span>${esc(body.title || body.value || "")} · ${esc(body.subtitle || "")}</span><em>${esc(body.resolved ? "resolved" : "unresolved")}</em></div>`;
    }
    const target = scanTargetObject(body);
    if (target) {
      toast(`Scan resolved: ${target.label}`);
      openObject(target.type, target.id, { refresh: true, label: target.label });
    } else {
      toast(body.resolved ? "Scan resolved without an object type" : "No identifier match");
    }
  });
}
