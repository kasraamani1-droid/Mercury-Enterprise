/**
 * Enterprise logistics operator UI (Workspace Engine + shared helpers).
 * Uses existing /api/v1/logistics routes. No parallel inventory mutation UI.
 */

import { esc, toast } from "../utils.js";
import { listify, softGet, softMutate } from "../ux2/api.js";

const inFlight = new Set();

export function normalizeRole(role) {
  return String(role || "").trim();
}

export function sessionCanReadLogistics(role) {
  const value = normalizeRole(role);
  return value === "Viewer" || value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function sessionCanStores(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Administrator";
}

export function sessionCanPurchase(role) {
  return sessionCanStores(role);
}

export function sessionCanTools(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function parsePositiveQty(value) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) return null;
  return n;
}

export function qtyAvailable(balance) {
  if (!balance) return 0;
  if (balance.qty_available !== undefined && balance.qty_available !== null && balance.qty_available !== "") {
    return Number(balance.qty_available);
  }
  return Number(balance.qty_on_hand || 0) - Number(balance.qty_reserved || 0);
}

export function filterStockRows(rows, { q = "", locationId = "", condition = "" } = {}) {
  const query = String(q || "").trim().toLowerCase();
  const loc = String(locationId || "").trim();
  const cond = String(condition || "").trim().toLowerCase();
  return (Array.isArray(rows) ? rows : []).filter((row) => {
    if (loc && String(row.location_id || "") !== loc && String(row.location_code || "") !== loc) return false;
    if (cond && String(row.condition || "").toLowerCase() !== cond) return false;
    if (!query) return true;
    const hay = `${row.oem_part_number || ""} ${row.part_number || ""} ${row.part_description || ""} ${row.part_master_id || ""} ${row.location_code || ""}`.toLowerCase();
    return hay.includes(query);
  });
}

export function mrLinkedTo(request, { workOrderId = "", jobCardId = "" } = {}) {
  if (!request) return false;
  if (jobCardId && String(request.job_card_id || "") === String(jobCardId)) return true;
  if (workOrderId && String(request.work_order_id || "") === String(workOrderId)) return true;
  return false;
}

export function filterMaterialRequests(rows, { q = "", status = "", workOrderId = "", jobCardId = "" } = {}) {
  const query = String(q || "").trim().toLowerCase();
  const st = String(status || "").trim().toLowerCase();
  return (Array.isArray(rows) ? rows : []).filter((row) => {
    if (st && String(row.status || "").toLowerCase() !== st) return false;
    if ((workOrderId || jobCardId) && !mrLinkedTo(row, { workOrderId, jobCardId })) return false;
    if (!query) return true;
    const hay = `${row.request_number || ""} ${row.work_order_id || ""} ${row.job_card_id || ""} ${row.status || ""} ${row.notes || ""}`.toLowerCase();
    return hay.includes(query);
  });
}

export function transferWarehousesValid(fromId, toId) {
  return Boolean(fromId && toId && String(fromId) !== String(toId));
}

export function scanTargetObject(scan) {
  const targetType = String(scan?.target_type || "");
  const targetId = String(scan?.target_id || "");
  if (targetType === "part" && targetId) return { type: "part", id: targetId, label: scan.title || scan.part?.oem_part_number || targetId };
  if (targetType === "tool" && targetId) return { type: "tool", id: targetId, label: scan.title || scan.tool?.tool_code || targetId };
  if (targetType === "stock_unit") {
    const partId = scan?.part?.id || "";
    if (partId) return { type: "part", id: partId, label: scan.part?.oem_part_number || scan.title || partId };
  }
  return null;
}

export function mutationErrorMessage(result) {
  const status = Number(result?.status || 0);
  const detail = result?.error || "Request failed";
  if (status === 409) return `Conflict: ${detail}`;
  if (status === 403) return `Forbidden: ${detail}`;
  if (status === 422) return `Invalid: ${detail}`;
  return detail;
}

export function waitingPartsCards(jobCards) {
  return (Array.isArray(jobCards) ? jobCards : []).filter((card) => String(card?.status || "") === "waiting_parts");
}

export function demandStatusLabel(request) {
  const status = String(request?.status || "");
  if (status === "shortage" || status === "partial") return status;
  return status || "unknown";
}

export function logisticsOpsCacheKeys(session, mutation = {}) {
  const parts = [];
  const materialRequests = [];
  const purchaseOrders = [];
  const tools = [];
  const workOrders = [];
  const jobCards = [];
  const aircraft = [];
  const push = (list, value) => {
    const id = String(value || "").trim();
    if (id && !list.includes(id)) list.push(id);
  };
  if (session?.type === "part") push(parts, session.id);
  if (session?.type === "materialRequest") push(materialRequests, session.id);
  if (session?.type === "purchaseOrder") push(purchaseOrders, session.id);
  if (session?.type === "tool") push(tools, session.id);
  if (session?.type === "workOrder") push(workOrders, session.id);
  if (session?.type === "jobCard") push(jobCards, session.id);
  push(parts, mutation.partId);
  push(materialRequests, mutation.materialRequestId);
  push(purchaseOrders, mutation.purchaseOrderId);
  push(tools, mutation.toolId);
  push(workOrders, mutation.workOrderId || session?.record?.work_order_id);
  push(jobCards, mutation.jobCardId || session?.record?.job_card_id);
  push(
    aircraft,
    mutation.aircraftId ||
      session?.record?.aircraft_id ||
      session?.bundle?.jobCard?.aircraft_id ||
      session?.bundle?.workOrder?.aircraft_id
  );
  (session?.bundle?.materialRequests || []).forEach((row) => push(materialRequests, row.id));
  return { parts, materialRequests, purchaseOrders, tools, workOrders, jobCards, aircraft };
}

export async function runLocked(key, fn) {
  if (inFlight.has(key)) {
    toast("Request already in progress");
    return null;
  }
  inFlight.add(key);
  try {
    return await fn();
  } finally {
    inFlight.delete(key);
  }
}

function role(bundle) {
  return bundle?.sessionRole || "";
}

function empty(text) {
  return `<div class="mx-empty">${esc(text)}</div>`;
}

function loadBanner(load, label) {
  if (!load || load.ok) return "";
  return `<div class="mx-empty">${esc(label)} unavailable: ${esc(load.error || `HTTP ${load.status || 0}`)}</div>`;
}

function table(headers, body) {
  return `<table class="data-table we-ops-table"><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table>`;
}

function partOptions(parts, selected) {
  const rows = Array.isArray(parts) ? parts : [];
  if (!rows.length) return `<option value="">No parts loaded</option>`;
  return [`<option value="">Select part</option>`]
    .concat(
      rows.map((part) => {
        const id = String(part.id || "");
        const label = `${part.oem_part_number || id} · ${part.description || part.part_class || ""}`;
        return `<option value="${esc(id)}"${id === String(selected || "") ? " selected" : ""}>${esc(label)}</option>`;
      })
    )
    .join("");
}

function locationOptions(locations, selected, { allowEmpty = true } = {}) {
  const rows = Array.isArray(locations) ? locations : [];
  const first = allowEmpty ? `<option value="">Any / default</option>` : `<option value="">Select location</option>`;
  if (!rows.length) return `<option value="">No locations loaded</option>`;
  return [first]
    .concat(
      rows.map((loc) => {
        const id = String(loc.id || "");
        const label = `${loc.location_code || id} · ${loc.location_type || ""}`;
        return `<option value="${esc(id)}"${id === String(selected || "") ? " selected" : ""}>${esc(label)}</option>`;
      })
    )
    .join("");
}

function warehouseOptions(warehouses, selected) {
  const rows = Array.isArray(warehouses) ? warehouses : [];
  if (!rows.length) return `<option value="">No warehouses</option>`;
  return [`<option value="">Select warehouse</option>`]
    .concat(
      rows.map((wh) => {
        const id = String(wh.id || "");
        return `<option value="${esc(id)}"${id === String(selected || "") ? " selected" : ""}>${esc(wh.code || id)} · ${esc(wh.name || "")}</option>`;
      })
    )
    .join("");
}

function conditionOptions(selected = "serviceable") {
  return ["serviceable", "unserviceable", "quarantine"]
    .map((value) => `<option value="${value}"${value === selected ? " selected" : ""}>${value}</option>`)
    .join("");
}

function contextJumps(record, extra = {}) {
  const wo = record?.work_order_id || extra.workOrderId;
  const jc = record?.job_card_id || extra.jobCardId;
  const ac = record?.aircraft_id || extra.aircraftId;
  const bits = [];
  if (ac) bits.push(`<button type="button" class="mx-chip" data-we-open="aircraft:${esc(String(ac))}">Aircraft</button>`);
  if (wo) bits.push(`<button type="button" class="mx-chip" data-we-open="workOrder:${esc(String(wo))}" data-we-tab="materials">Work order</button>`);
  if (jc) bits.push(`<button type="button" class="mx-chip" data-we-open="jobCard:${esc(String(jc))}" data-we-tab="materials">Job card</button>`);
  return bits.length ? `<div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">${bits.join("")}</div>` : "";
}

function storesForms(bundle, defaults = {}) {
  if (!sessionCanStores(role(bundle))) {
    return `<p class="mx-subtitle">Stock mutations require logistics.stores (Operator or Administrator). This session is read-only for stores.</p>`;
  }
  const parts = bundle?.parts || [];
  const locations = bundle?.locations || [];
  const warehouses = bundle?.warehouses || [];
  const reservations = (bundle?.reservations || []).filter((row) => String(row.status || "") === "open");
  const transfers = (bundle?.transfers || []).filter((row) => String(row.status || "") !== "completed");
  const partId = defaults.partId || "";
  return `
    <div class="mx-grid mx-grid-2" style="gap:12px;margin-top:12px">
      <form id="weLogReceiveForm" class="mx-card" style="padding:12px">
        <strong>Receive stock</strong>
        <div class="we-cfg-form-grid">
          <label class="mx-field">Part<select class="mx-input" name="part_master_id" required>${partOptions(parts, partId)}</select></label>
          <label class="mx-field">Location<select class="mx-input" name="location_id" required>${locationOptions(locations, "", { allowEmpty: false })}</select></label>
          <label class="mx-field">Qty<input class="mx-input" name="qty" type="number" min="0.0001" step="any" required /></label>
          <label class="mx-field">Condition<select class="mx-input" name="condition">${conditionOptions()}</select></label>
          <label class="mx-field">Serial<input class="mx-input" name="serial_number" /></label>
          <label class="mx-field">Lot<input class="mx-input" name="lot_number" /></label>
        </div>
        <button class="mx-btn" type="submit">Receive</button>
      </form>
      <form id="weLogIssueForm" class="mx-card" style="padding:12px">
        <strong>Issue stock</strong>
        <p class="mx-subtitle">Direct issue uses reference_type/reference_id only. Prefer material-request issue for job-card linkage.</p>
        <div class="we-cfg-form-grid">
          <label class="mx-field">Part<select class="mx-input" name="part_master_id" required>${partOptions(parts, partId)}</select></label>
          <label class="mx-field">Location<select class="mx-input" name="location_id">${locationOptions(locations)}</select></label>
          <label class="mx-field">Qty<input class="mx-input" name="qty" type="number" min="0.0001" step="any" required /></label>
          <label class="mx-field">Condition<select class="mx-input" name="condition">${conditionOptions()}</select></label>
          <label class="mx-field">Reference type<input class="mx-input" name="reference_type" placeholder="job_card" /></label>
          <label class="mx-field">Reference id<input class="mx-input" name="reference_id" /></label>
        </div>
        <button class="mx-btn" type="submit">Issue</button>
      </form>
      <form id="weLogReserveForm" class="mx-card" style="padding:12px">
        <strong>Manual reservation</strong>
        <p class="mx-subtitle">source_type is manual|work_package|material_request|tool_plan. Job-card demand should use a material request.</p>
        <div class="we-cfg-form-grid">
          <label class="mx-field">Part<select class="mx-input" name="part_master_id" required>${partOptions(parts, partId)}</select></label>
          <label class="mx-field">Qty<input class="mx-input" name="qty" type="number" min="0.0001" step="any" required /></label>
          <label class="mx-field">Location<select class="mx-input" name="location_id">${locationOptions(locations)}</select></label>
          <label class="mx-field">Source type<select class="mx-input" name="source_type"><option value="manual">manual</option><option value="work_package">work_package</option><option value="material_request">material_request</option><option value="tool_plan">tool_plan</option></select></label>
          <label class="mx-field">Source id<input class="mx-input" name="source_id" /></label>
        </div>
        <button class="mx-btn" type="submit">Reserve</button>
      </form>
      <form id="weLogReleaseForm" class="mx-card" style="padding:12px">
        <strong>Release reservation</strong>
        <label class="mx-field">Open reservation<select class="mx-input" name="reservation_id" required>${
          reservations.length
            ? reservations.map((row) => `<option value="${esc(row.id)}">${esc(row.id)} · qty ${esc(String(row.qty))}</option>`).join("")
            : `<option value="">No open reservations</option>`
        }</select></label>
        <button class="mx-btn" type="submit">Release</button>
      </form>
      <form id="weLogAdjustForm" class="mx-card" style="padding:12px">
        <strong>Adjust stock</strong>
        <div class="we-cfg-form-grid">
          <label class="mx-field">Part<select class="mx-input" name="part_master_id" required>${partOptions(parts, partId)}</select></label>
          <label class="mx-field">Location<select class="mx-input" name="location_id" required>${locationOptions(locations, "", { allowEmpty: false })}</select></label>
          <label class="mx-field">Qty delta<input class="mx-input" name="qty_delta" type="number" step="any" required /></label>
          <label class="mx-field">Condition<select class="mx-input" name="condition">${conditionOptions()}</select></label>
          <label class="mx-field">Reason<input class="mx-input" name="reason" minlength="1" required /></label>
        </div>
        <button class="mx-btn" type="submit">Adjust</button>
      </form>
      <form id="weLogTransferForm" class="mx-card" style="padding:12px">
        <strong>Warehouse transfer</strong>
        <p class="mx-subtitle">API requires two distinct warehouses. Same-warehouse bin moves are not a separate endpoint.</p>
        <div class="we-cfg-form-grid">
          <label class="mx-field">From warehouse<select class="mx-input" name="from_warehouse_id" required>${warehouseOptions(warehouses)}</select></label>
          <label class="mx-field">To warehouse<select class="mx-input" name="to_warehouse_id" required>${warehouseOptions(warehouses)}</select></label>
          <label class="mx-field">From location<select class="mx-input" name="from_location_id">${locationOptions(locations)}</select></label>
          <label class="mx-field">To location<select class="mx-input" name="to_location_id">${locationOptions(locations)}</select></label>
          <label class="mx-field">Part<select class="mx-input" name="part_master_id" required>${partOptions(parts, partId)}</select></label>
          <label class="mx-field">Qty<input class="mx-input" name="qty" type="number" min="0.0001" step="any" required /></label>
        </div>
        <button class="mx-btn" type="submit">Create transfer</button>
      </form>
      <form id="weLogTransferCompleteForm" class="mx-card" style="padding:12px">
        <strong>Complete transfer</strong>
        <label class="mx-field">Open transfer<select class="mx-input" name="transfer_id" required>${
          transfers.length
            ? transfers.map((row) => `<option value="${esc(row.id)}">${esc(row.transfer_number || row.id)}</option>`).join("")
            : `<option value="">No open transfers</option>`
        }</select></label>
        <label class="mx-field">Dest location override<select class="mx-input" name="to_location_id">${locationOptions(locations)}</select></label>
        <button class="mx-btn" type="submit">Complete</button>
      </form>
    </div>
  `;
}

function mrLifecycleButtons(request, canStores) {
  if (!canStores || !request?.id) return "";
  const status = String(request.status || "");
  const id = esc(String(request.id));
  const btn = (action, label) =>
    `<button type="button" class="mx-btn mx-btn-sm mx-btn-ghost" data-log-mr-action="${esc(action)}" data-log-mr-id="${id}">${esc(label)}</button>`;
  const bits = [];
  if (status === "requested") bits.push(btn("approve", "Approve"));
  if (status === "approved") bits.push(btn("reserve", "Reserve"));
  if (status === "reserved") bits.push("");
  if (["requested", "approved", "reserved"].includes(status)) bits.push(btn("cancel", "Cancel"));
  return bits.filter(Boolean).length ? `<div class="mx-row" style="gap:8px;flex-wrap:wrap;margin-top:8px">${bits.join("")}</div>` : "";
}

function mrCreateForm(bundle, { workOrderId = "", jobCardId = "" } = {}) {
  if (!sessionCanStores(role(bundle))) return "";
  return `<form id="weLogMrCreateForm" class="mx-card" style="padding:12px;margin-top:12px">
    <strong>Create material request</strong>
    <input type="hidden" name="work_order_id" value="${esc(workOrderId)}" />
    <input type="hidden" name="job_card_id" value="${esc(jobCardId)}" />
    <div class="we-cfg-form-grid">
      <label class="mx-field">Part<select class="mx-input" name="part_master_id" required>${partOptions(bundle?.parts)}</select></label>
      <label class="mx-field">Qty<input class="mx-input" name="qty_requested" type="number" min="0.0001" step="any" value="1" required /></label>
      <label class="mx-field">Notes<input class="mx-input" name="notes" maxlength="400" /></label>
    </div>
    <button class="mx-btn" type="submit">Request material</button>
  </form>`;
}

export function renderPartWorkspace(session, record, bundle) {
  const part = record || {};
  const balances = bundle?.balances || [];
  const units = bundle?.units || [];
  const movements = bundle?.movements || [];
  const reservations = bundle?.reservations || [];
  return `
    ${loadBanner(bundle?.recordLoad, "Part")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(part.oem_part_number || session.id)}</h3><span class="mx-chip">${esc(part.status || "—")}</span></div>
      <p>${esc(part.description || "")}</p>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px">
        <span class="mx-chip">${esc(part.part_class || "—")}</span>
        <span class="mx-chip">UOM ${esc(part.unit_of_measure || "EA")}</span>
        <span class="mx-chip">Policy ${esc(part.issue_policy || "—")}</span>
        <span class="mx-chip">Min ${esc(String(part.min_stock ?? "—"))}</span>
        <span class="mx-chip">Reorder ${esc(String(part.reorder_point ?? "—"))}</span>
      </div>
    </article>
    ${loadBanner(bundle?.balancesLoad, "Balances")}
    ${
      balances.length
        ? table(
            ["Part", "Location", "Condition", "On hand", "Reserved", "Available"],
            balances
              .map(
                (row) => `<tr>
              <td class="mx-mono">${esc(row.part_number || part.oem_part_number || row.part_master_id)}</td>
              <td>${esc(row.location_code || row.location_id || "—")}</td>
              <td>${esc(row.condition || "—")}</td>
              <td>${esc(String(row.qty_on_hand ?? "—"))}</td>
              <td>${esc(String(row.qty_reserved ?? "—"))}</td>
              <td>${esc(String(qtyAvailable(row)))}</td>
            </tr>`
              )
              .join("")
          )
        : empty("No stock balances for this part.")
    }
    <article class="mx-card" style="margin-top:16px">
      <div class="mx-card-header"><h3>Serialized / lot units</h3></div>
      ${
        units.length
          ? table(
              ["Serial", "Lot", "Batch", "Qty", "Condition", "Location", "Aircraft"],
              units
                .map(
                  (unit) => `<tr>
                <td class="mx-mono">${esc(unit.serial_number || "—")}</td>
                <td>${esc(unit.lot_number || "—")}</td>
                <td>${esc(unit.batch_number || "—")}</td>
                <td>${esc(String(unit.qty ?? "—"))}</td>
                <td>${esc(unit.condition || "—")}</td>
                <td>${esc(unit.location_id || "—")}</td>
                <td>${unit.current_aircraft_id ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="aircraft:${esc(String(unit.current_aircraft_id))}">${esc(unit.current_aircraft_id)}</button>` : "—"}</td>
              </tr>`
                )
                .join("")
            )
          : empty("No stock units.")
      }
    </article>
    <article class="mx-card" style="margin-top:16px">
      <div class="mx-card-header"><h3>Reservations</h3></div>
      ${
        reservations.length
          ? table(
              ["Id", "Qty", "Status", "Source", "Source id"],
              reservations
                .map(
                  (row) => `<tr>
                <td class="mx-mono">${esc(row.id)}</td>
                <td>${esc(String(row.qty ?? "—"))}</td>
                <td><span class="mx-chip">${esc(row.status || "—")}</span></td>
                <td>${esc(row.source_type || "—")}</td>
                <td class="mx-mono">${esc(row.source_id || "—")}</td>
              </tr>`
                )
                .join("")
            )
          : empty("No reservations for this part.")
      }
    </article>
    <article class="mx-card" style="margin-top:16px">
      <div class="mx-card-header"><h3>Movements</h3></div>
      ${
        movements.length
          ? table(
              ["Type", "Qty", "From", "To", "Ref", "When"],
              movements
                .slice(0, 30)
                .map(
                  (row) => `<tr>
                <td>${esc(row.movement_type || "—")}</td>
                <td>${esc(String(row.qty ?? "—"))}</td>
                <td class="mx-mono">${esc(row.from_location_id || "—")}</td>
                <td class="mx-mono">${esc(row.to_location_id || "—")}</td>
                <td>${esc(row.reference_type || "")} ${esc(row.reference_id || "")}</td>
                <td>${esc(String(row.created_at || "").slice(0, 19))}</td>
              </tr>`
                )
                .join("")
            )
          : empty("No movements.")
      }
    </article>
    ${storesForms(bundle, { partId: session.id })}
    <p class="mx-subtitle" id="weLogMsg"></p>
  `;
}

export function renderMaterialRequestWorkspace(session, record, bundle) {
  const request = record || {};
  const lines = request.lines || bundle?.lines || [];
  const canStores = sessionCanStores(role(bundle));
  const locations = bundle?.locations || [];
  return `
    ${loadBanner(bundle?.recordLoad, "Material request")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(request.request_number || session.id)}</h3><span class="mx-chip">${esc(demandStatusLabel(request))}</span></div>
      <p class="mx-subtitle">${esc(request.notes || "")}</p>
      ${contextJumps(request, {
        aircraftId: bundle?.jobCard?.aircraft_id || bundle?.workOrder?.aircraft_id,
        workOrderId: request.work_order_id || bundle?.workOrder?.id,
        jobCardId: request.job_card_id || bundle?.jobCard?.id,
      })}
      ${mrLifecycleButtons(request, canStores)}
    </article>
    ${
      lines.length
        ? table(
            ["Part", "Requested", "Reserved", "Issued", "Returned", "Status"],
            lines
              .map(
                (line) => `<tr>
              <td class="mx-mono"><button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="part:${esc(String(line.part_master_id))}">${esc(line.part_master_id)}</button></td>
              <td>${esc(String(line.qty_requested ?? "—"))}</td>
              <td>${esc(String(line.qty_reserved ?? "—"))}</td>
              <td>${esc(String(line.qty_issued ?? "—"))}</td>
              <td>${esc(String(line.qty_returned ?? "—"))}</td>
              <td><span class="mx-chip">${esc(line.status || "—")}</span></td>
            </tr>`
              )
              .join("")
          )
        : empty("No lines on this request.")
    }
    ${
      canStores && String(request.status) === "reserved"
        ? `<form id="weLogMrIssueForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Issue to demand</strong>
            <input type="hidden" name="request_id" value="${esc(String(request.id))}" />
            <label class="mx-field">Location<select class="mx-input" name="location_id">${locationOptions(locations)}</select></label>
            <label class="mx-field">Notes<input class="mx-input" name="notes" /></label>
            <button class="mx-btn" type="submit">Issue</button>
          </form>`
        : ""
    }
    ${
      canStores && String(request.status) === "issued"
        ? `<form id="weLogMrReturnForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Return unused material</strong>
            <input type="hidden" name="request_id" value="${esc(String(request.id))}" />
            <label class="mx-field">Location<select class="mx-input" name="location_id" required>${locationOptions(locations, "", { allowEmpty: false })}</select></label>
            ${(lines || [])
              .map(
                (line) => `<div class="we-cfg-form-grid">
              <label class="mx-field">Line ${esc(line.id.slice(0, 8))} qty<input class="mx-input" name="qty_${esc(line.id)}" type="number" min="0" step="any" value="${esc(String(line.qty_issued || 0))}" /></label>
              <label class="mx-field">Condition<select class="mx-input" name="condition_${esc(line.id)}">${conditionOptions()}</select></label>
            </div>`
              )
              .join("")}
            <button class="mx-btn" type="submit">Return</button>
          </form>`
        : ""
    }
    <p class="mx-subtitle" id="weLogMsg"></p>
  `;
}

export function renderPurchaseOrderWorkspace(session, record, bundle) {
  const po = record || {};
  const lines = po.lines || [];
  const receipts = bundle?.receipts || [];
  const canStores = sessionCanStores(role(bundle));
  const locations = bundle?.locations || [];
  return `
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(po.po_number || session.id)}</h3><span class="mx-chip">${esc(po.status || "—")}</span></div>
      <p class="mx-subtitle">Vendor ${esc(po.vendor_id || "—")} · ${esc(po.currency || "")}</p>
    </article>
    ${
      lines.length
        ? table(
            ["Line", "Part", "Ordered", "Received", "Backorder", "Status"],
            lines
              .map(
                (line) => `<tr>
              <td class="mx-mono">${esc(line.id)}</td>
              <td><button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="part:${esc(String(line.part_master_id))}">${esc(line.part_master_id)}</button></td>
              <td>${esc(String(line.qty_ordered ?? "—"))}</td>
              <td>${esc(String(line.qty_received ?? "—"))}</td>
              <td>${esc(String(line.qty_backordered ?? "—"))}</td>
              <td>${esc(line.status || "—")}</td>
            </tr>`
              )
              .join("")
          )
        : empty("No purchase-order lines.")
    }
    ${
      canStores && lines.length && !["closed", "cancelled"].includes(String(po.status || ""))
        ? `<form id="weLogPoReceiveForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Receive against PO</strong>
            <p class="mx-subtitle">Goods-in only. On-hand increases after inspect + putaway.</p>
            <label class="mx-field">Receiving location<select class="mx-input" name="location_id">${locationOptions(locations)}</select></label>
            ${lines
              .map(
                (line) => `<label class="mx-field">Qty for ${esc(line.part_master_id)}<input class="mx-input" name="qty_${esc(line.id)}" type="number" min="0" step="any" value="${esc(String(line.qty_backordered || line.qty_ordered || 0))}" /></label>`
              )
              .join("")}
            <button class="mx-btn" type="submit">Receive</button>
          </form>`
        : ""
    }
    <article class="mx-card" style="margin-top:16px">
      <div class="mx-card-header"><h3>Receipts</h3></div>
      ${
        receipts.length
          ? receipts
              .map((rcpt) => {
                const detail = rcpt.lines ? rcpt : bundle?.receiptDetails?.[rcpt.id] || rcpt;
                const rlines = detail.lines || [];
                return `<div class="mx-card" style="padding:10px;margin-bottom:8px">
                  <strong>${esc(detail.receipt_number || rcpt.id)}</strong> <span class="mx-chip">${esc(rcpt.status || "—")}</span>
                  ${
                    canStores && rlines.length && ["receiving", "inspection"].includes(String(rcpt.status || ""))
                      ? `<form class="weLogReceiptInspectForm" data-receipt-id="${esc(rcpt.id)}" style="margin-top:8px">
                          ${rlines
                            .map(
                              (line) => `<label class="mx-field">${esc(line.part_master_id)} accept
                            <select class="mx-input" name="accept_${esc(line.id)}"><option value="true">accept</option><option value="false">reject</option></select>
                          </label>`
                            )
                            .join("")}
                          <button class="mx-btn mx-btn-sm" type="submit">Inspect</button>
                        </form>`
                      : ""
                  }
                  ${
                    canStores && String(rcpt.status || "") === "inspection"
                      ? `<form class="weLogReceiptPutawayForm" data-receipt-id="${esc(rcpt.id)}" style="margin-top:8px">
                          <label class="mx-field">Putaway location<select class="mx-input" name="location_id">${locationOptions(locations)}</select></label>
                          <label class="mx-field">Quarantine location<select class="mx-input" name="quarantine_location_id">${locationOptions(locations)}</select></label>
                          <button class="mx-btn mx-btn-sm" type="submit">Putaway</button>
                        </form>`
                      : ""
                  }
                </div>`;
              })
              .join("")
          : empty("No receipts for this PO.")
      }
    </article>
    <p class="mx-subtitle" id="weLogMsg"></p>
  `;
}

export function renderToolWorkspace(session, record, bundle) {
  const tool = record || {};
  const canTools = sessionCanTools(role(bundle));
  const history = bundle?.history || [];
  return `
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(tool.tool_code || session.id)}</h3><span class="mx-chip">${esc(tool.status || "—")}</span></div>
      <p>${esc(tool.description || "")}</p>
      <div class="mx-row" style="gap:8px;flex-wrap:wrap">
        <span class="mx-chip">Cal ${esc(tool.calibration_status || "—")}</span>
        <span class="mx-chip">Due ${esc(String(tool.calibration_due_at || "—").slice(0, 10))}</span>
      </div>
    </article>
    ${
      canTools
        ? `<div class="mx-grid mx-grid-2" style="gap:12px;margin-top:12px">
        <form id="weLogToolIssueForm" class="mx-card" style="padding:12px">
          <strong>Issue tool</strong>
          <label class="mx-field">Issued to<input class="mx-input" name="issued_to" required /></label>
          <label class="mx-field">Work package id<input class="mx-input" name="work_package_id" /></label>
          <button class="mx-btn" type="submit">Issue</button>
        </form>
        <form id="weLogToolReturnForm" class="mx-card" style="padding:12px">
          <strong>Return tool</strong>
          <p class="mx-subtitle">POST /tools/{id}/return — no body.</p>
          <button class="mx-btn" type="submit">Return</button>
        </form>
        <form id="weLogToolCalibrateForm" class="mx-card" style="padding:12px">
          <strong>Calibrate</strong>
          <label class="mx-field">Certificate<input class="mx-input" name="certificate_number" /></label>
          <label class="mx-field">Notes<input class="mx-input" name="notes" /></label>
          <button class="mx-btn" type="submit">Calibrate</button>
        </form>
      </div>`
        : `<p class="mx-subtitle">Tool mutations require logistics.tools (Operator, Reviewer, or Administrator).</p>`
    }
    ${
      history.length
        ? table(
            ["Event", "Detail", "By", "When"],
            history
              .map(
                (row) => `<tr><td>${esc(row.event_type || "—")}</td><td>${esc(row.details || "")}</td><td>${esc(row.performed_by || "—")}</td><td>${esc(String(row.created_at || "").slice(0, 19))}</td></tr>`
              )
              .join("")
          )
        : empty("No tool history.")
    }
    <p class="mx-subtitle" id="weLogMsg"></p>
  `;
}

function mrListHtml(requests) {
  if (!requests.length) return empty("No material requests in this context.");
  return table(
    ["Request", "Status", "WO", "Job card", "Open"],
    requests
      .map((row) => `<tr class="we-row-open" data-we-open="materialRequest:${esc(String(row.id))}" data-we-label="${esc(row.request_number || row.id)}">
        <td class="mx-mono">${esc(row.request_number || row.id)}</td>
        <td><span class="mx-chip">${esc(demandStatusLabel(row))}</span></td>
        <td>${row.work_order_id ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="workOrder:${esc(String(row.work_order_id))}" data-we-tab="materials">${esc(row.work_order_id)}</button>` : "—"}</td>
        <td>${row.job_card_id ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="jobCard:${esc(String(row.job_card_id))}" data-we-tab="materials">${esc(row.job_card_id)}</button>` : "—"}</td>
        <td><button type="button" class="mx-btn mx-btn-sm" data-we-open="materialRequest:${esc(String(row.id))}">Open</button></td>
      </tr>`)
      .join("")
  );
}

export function renderWorkOrderMaterials(session, record, bundle) {
  const requests = bundle?.materialRequests || [];
  const waiting = waitingPartsCards(bundle?.jobCards || []);
  return `
    ${loadBanner(bundle?.materialRequestsLoad, "Material requests")}
    ${
      waiting.length
        ? `<article class="mx-card" style="margin-bottom:12px"><div class="mx-card-header"><h3>Waiting parts</h3></div>
          ${waiting
            .map(
              (card) => `<div class="mx-row" style="gap:8px"><button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="jobCard:${esc(String(card.id))}" data-we-tab="materials">${esc(card.job_card_number || card.id)}</button><span class="mx-chip">${esc(card.status)}</span></div>`
            )
            .join("")}</article>`
        : ""
    }
    ${mrListHtml(requests)}
    ${mrCreateForm(bundle, { workOrderId: session.id, jobCardId: "" })}
    <p class="mx-subtitle">Job-card linkage uses material-request job_card_id. Direct /stock/issue has no typed work-order field.</p>
    <p class="mx-subtitle" id="weLogMsg"></p>
  `;
}

export function renderJobCardMaterials(session, record, bundle) {
  const requests = bundle?.materialRequests || [];
  const waiting = String(record?.status || "") === "waiting_parts";
  return `
    ${loadBanner(bundle?.materialRequestsLoad, "Material requests")}
    ${waiting ? `<article class="mx-card"><strong>This card is waiting_parts.</strong><p class="mx-subtitle">Create or progress a material request, then return the card to in_progress after issue.</p>${contextJumps(record)}</article>` : contextJumps(record)}
    ${mrListHtml(requests)}
    ${mrCreateForm(bundle, { workOrderId: record?.work_order_id || "", jobCardId: session.id })}
    <p class="mx-subtitle" id="weLogMsg"></p>
  `;
}

export function renderJobCardMaterialsBridge(session, record, bundle) {
  const requests = bundle?.materialRequests || [];
  const waiting = String(record?.status || "") === "waiting_parts";
  const openCount = requests.filter((row) => !["cancelled", "returned"].includes(String(row.status || ""))).length;
  return `<article class="mx-card" style="margin-top:16px">
    <div class="mx-card-header"><h3>Materials</h3>
      <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="jobCard:${esc(String(session.id))}" data-we-tab="materials" data-we-label="${esc(record?.job_card_number || session.id)}">Open materials</button>
    </div>
    <p class="mx-subtitle">${waiting ? "Card is waiting_parts. " : ""}${esc(String(openCount))} open material request(s). ${esc(String(requests.length))} total in this job-card context.</p>
  </article>`;
}

function setLogMessage(text, ok) {
  const node = document.getElementById("weLogMsg") || document.getElementById("logOpsMsg");
  if (!node) return;
  node.textContent = text || "";
  node.style.color = ok ? "" : "var(--danger, #c44)";
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function refreshHint(active, extra = {}) {
  return {
    partId: extra.partId || (active?.type === "part" ? active.id : ""),
    materialRequestId: extra.materialRequestId || (active?.type === "materialRequest" ? active.id : ""),
    purchaseOrderId: extra.purchaseOrderId || (active?.type === "purchaseOrder" ? active.id : ""),
    toolId: extra.toolId || (active?.type === "tool" ? active.id : ""),
    workOrderId: extra.workOrderId || active?.record?.work_order_id || (active?.type === "workOrder" ? active.id : ""),
    jobCardId: extra.jobCardId || active?.record?.job_card_id || (active?.type === "jobCard" ? active.id : ""),
    aircraftId:
      extra.aircraftId ||
      active?.record?.aircraft_id ||
      active?.bundle?.jobCard?.aircraft_id ||
      active?.bundle?.workOrder?.aircraft_id ||
      "",
  };
}

export function bindLogisticsOpsPanel(active, { onRefresh } = {}) {
  if (!active) return;
  const record = active.record || {};

  const fail = (result) => {
    const msg = mutationErrorMessage(result);
    setLogMessage(msg, false);
    toast(msg);
  };

  document.getElementById("weLogReceiveForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanStores(role(active.bundle))) return fail({ status: 403, error: "stores required" });
    const values = formValues(event.target);
    const qty = parsePositiveQty(values.qty);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    const result = await runLocked(`receive:${values.part_master_id}`, () =>
      softMutate("/logistics/stock/receive", {
        body: {
          part_master_id: values.part_master_id,
          location_id: values.location_id,
          qty,
          condition: values.condition || "serviceable",
          serial_number: values.serial_number || "",
          lot_number: values.lot_number || "",
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Stock received");
    await onRefresh?.(refreshHint(active, { partId: values.part_master_id }));
  });

  document.getElementById("weLogIssueForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanStores(role(active.bundle))) return fail({ status: 403, error: "stores required" });
    const values = formValues(event.target);
    const qty = parsePositiveQty(values.qty);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    if (!window.confirm(`Issue ${qty} of this part from stores?`)) return;
    const body = {
      part_master_id: values.part_master_id,
      qty,
      condition: values.condition || "serviceable",
      reference_type: values.reference_type || "",
      reference_id: values.reference_id || "",
    };
    if (values.location_id) body.location_id = values.location_id;
    const result = await runLocked(`issue:${values.part_master_id}`, () => softMutate("/logistics/stock/issue", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Stock issued");
    await onRefresh?.(refreshHint(active, { partId: values.part_master_id }));
  });

  document.getElementById("weLogReserveForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanStores(role(active.bundle))) return fail({ status: 403, error: "stores required" });
    const values = formValues(event.target);
    const qty = parsePositiveQty(values.qty);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    const body = {
      part_master_id: values.part_master_id,
      qty,
      source_type: values.source_type || "manual",
      source_id: values.source_id || "",
    };
    if (values.location_id) body.location_id = values.location_id;
    const result = await runLocked(`reserve:${values.part_master_id}`, () => softMutate("/logistics/reservations", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Reserved");
    await onRefresh?.(refreshHint(active, { partId: values.part_master_id }));
  });

  document.getElementById("weLogReleaseForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    if (!values.reservation_id) return fail({ status: 422, error: "Reservation required" });
    const result = await runLocked(`release:${values.reservation_id}`, () =>
      softMutate(`/logistics/reservations/${encodeURIComponent(values.reservation_id)}/release`, { method: "POST" })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Reservation released");
    await onRefresh?.(refreshHint(active));
  });

  document.getElementById("weLogAdjustForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const delta = Number(values.qty_delta);
    if (!Number.isFinite(delta) || delta === 0) return fail({ status: 422, error: "qty_delta must be a non-zero number" });
    if (!String(values.reason || "").trim()) return fail({ status: 422, error: "Reason required" });
    if (!window.confirm(`Apply stock adjustment of ${delta}?`)) return;
    const result = await runLocked(`adjust:${values.part_master_id}`, () =>
      softMutate("/logistics/stock/adjust", {
        body: {
          part_master_id: values.part_master_id,
          location_id: values.location_id,
          qty_delta: delta,
          condition: values.condition || "serviceable",
          reason: String(values.reason).trim(),
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Stock adjusted");
    await onRefresh?.(refreshHint(active, { partId: values.part_master_id }));
  });

  document.getElementById("weLogTransferForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    if (!transferWarehousesValid(values.from_warehouse_id, values.to_warehouse_id)) {
      return fail({ status: 422, error: "Source and destination warehouses must be different" });
    }
    const qty = parsePositiveQty(values.qty);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    const body = {
      from_warehouse_id: values.from_warehouse_id,
      to_warehouse_id: values.to_warehouse_id,
      notes: values.notes || "",
      lines: [{ part_master_id: values.part_master_id, qty }],
    };
    if (values.from_location_id) body.from_location_id = values.from_location_id;
    if (values.to_location_id) body.to_location_id = values.to_location_id;
    const result = await runLocked(`transfer:${values.from_warehouse_id}:${values.to_warehouse_id}`, () =>
      softMutate("/logistics/transfers", { body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Transfer ${result.data?.transfer_number || ""} created`);
    await onRefresh?.(refreshHint(active, { partId: values.part_master_id }));
  });

  document.getElementById("weLogTransferCompleteForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    if (!values.transfer_id) return fail({ status: 422, error: "Transfer required" });
    if (!window.confirm("Complete this warehouse transfer?")) return;
    const body = {};
    if (values.to_location_id) body.to_location_id = values.to_location_id;
    const result = await runLocked(`transfer-complete:${values.transfer_id}`, () =>
      softMutate(`/logistics/transfers/${encodeURIComponent(values.transfer_id)}/complete`, { body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Transfer completed");
    await onRefresh?.(refreshHint(active));
  });

  document.getElementById("weLogMrCreateForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanStores(role(active.bundle))) return fail({ status: 403, error: "stores required" });
    const values = formValues(event.target);
    const qty = parsePositiveQty(values.qty_requested);
    if (qty === null) return fail({ status: 422, error: "Quantity must be greater than zero" });
    const body = {
      notes: values.notes || "",
      lines: [{ part_master_id: values.part_master_id, qty_requested: qty }],
    };
    if (values.work_order_id) body.work_order_id = values.work_order_id;
    if (values.job_card_id) body.job_card_id = values.job_card_id;
    const result = await runLocked(`mr-create:${values.job_card_id || values.work_order_id || "x"}`, () =>
      softMutate("/logistics/material-requests", { body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Material request ${result.data?.request_number || ""} created`);
    await onRefresh?.(refreshHint(active, { materialRequestId: result.data?.id, partId: values.part_master_id }));
  });

  document.querySelectorAll("[data-log-mr-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const action = btn.getAttribute("data-log-mr-action");
      const id = btn.getAttribute("data-log-mr-id");
      if (!id || !action) return;
      if (action === "cancel" && !window.confirm("Cancel this material request?")) return;
      const result = await runLocked(`mr:${action}:${id}`, () =>
        softMutate(`/logistics/material-requests/${encodeURIComponent(id)}/${action}`, { method: "POST" })
      );
      if (!result) return;
      if (!result.ok) return fail(result);
      toast(`Material request ${action}`);
      await onRefresh?.(refreshHint(active, { materialRequestId: id }));
    });
  });

  document.getElementById("weLogMrIssueForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const id = values.request_id || record.id;
    const body = { notes: values.notes || "" };
    if (values.location_id) body.location_id = values.location_id;
    const result = await runLocked(`mr-issue:${id}`, () =>
      softMutate(`/logistics/material-requests/${encodeURIComponent(id)}/issue`, { body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Material issued to request");
    await onRefresh?.(refreshHint(active, { materialRequestId: id }));
  });

  document.getElementById("weLogMrReturnForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const id = values.request_id || record.id;
    if (!values.location_id) return fail({ status: 422, error: "Return location required" });
    const lines = (record.lines || []).map((line) => {
      const qty = Number(values[`qty_${line.id}`] || 0);
      return qty > 0
        ? { line_id: line.id, qty, condition: values[`condition_${line.id}`] || "serviceable" }
        : null;
    }).filter(Boolean);
    if (!lines.length) return fail({ status: 422, error: "Return quantity required" });
    const result = await runLocked(`mr-return:${id}`, () =>
      softMutate(`/logistics/material-requests/${encodeURIComponent(id)}/return`, {
        body: { location_id: values.location_id, lines },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Material returned");
    await onRefresh?.(refreshHint(active, { materialRequestId: id }));
  });

  document.getElementById("weLogPoReceiveForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const lines = (record.lines || [])
      .map((line) => {
        const qty = Number(values[`qty_${line.id}`] || 0);
        return qty > 0 ? { purchase_order_line_id: line.id, part_master_id: line.part_master_id, qty } : null;
      })
      .filter(Boolean);
    if (!lines.length) return fail({ status: 422, error: "Receive quantity required" });
    const body = { lines };
    if (values.location_id) body.location_id = values.location_id;
    const result = await runLocked(`po-receive:${record.id}`, () =>
      softMutate(`/logistics/purchase-orders/${encodeURIComponent(record.id)}/receive`, { body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Receipt ${result.data?.receipt_number || ""} recorded (inspect/putaway still required)`);
    await onRefresh?.(refreshHint(active, { purchaseOrderId: record.id }));
  });

  document.querySelectorAll(".weLogReceiptInspectForm").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const receiptId = form.getAttribute("data-receipt-id");
      const values = formValues(form);
      const detail = await softGet(`/logistics/receipts/${encodeURIComponent(receiptId)}`);
      const rlines = listify(detail.data?.lines);
      const lines = rlines.map((line) => ({
        line_id: line.id,
        accept: String(values[`accept_${line.id}`] || "true") !== "false",
      }));
      if (!lines.length) return fail({ status: 422, error: "Receipt lines unavailable" });
      const result = await runLocked(`inspect:${receiptId}`, () =>
        softMutate(`/logistics/receipts/${encodeURIComponent(receiptId)}/inspect`, { body: { lines } })
      );
      if (!result) return;
      if (!result.ok) return fail(result);
      toast("Receipt inspected");
      await onRefresh?.(refreshHint(active));
    });
  });

  document.querySelectorAll(".weLogReceiptPutawayForm").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const receiptId = form.getAttribute("data-receipt-id");
      const values = formValues(form);
      const body = { notes: values.notes || "" };
      if (values.location_id) body.location_id = values.location_id;
      if (values.quarantine_location_id) body.quarantine_location_id = values.quarantine_location_id;
      const result = await runLocked(`putaway:${receiptId}`, () =>
        softMutate(`/logistics/receipts/${encodeURIComponent(receiptId)}/putaway`, { body })
      );
      if (!result) return;
      if (!result.ok) return fail(result);
      toast("Receipt put away");
      await onRefresh?.(refreshHint(active));
    });
  });

  document.getElementById("weLogToolIssueForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanTools(role(active.bundle))) return fail({ status: 403, error: "tools required" });
    const values = formValues(event.target);
    const body = { issued_to: String(values.issued_to || "").trim() };
    if (!body.issued_to) return fail({ status: 422, error: "issued_to required" });
    if (values.work_package_id) body.work_package_id = values.work_package_id;
    const result = await runLocked(`tool-issue:${record.id}`, () =>
      softMutate(`/logistics/tools/${encodeURIComponent(record.id)}/issue`, { body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Tool issued");
    await onRefresh?.(refreshHint(active, { toolId: record.id }));
  });

  document.getElementById("weLogToolReturnForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const result = await runLocked(`tool-return:${record.id}`, () =>
      softMutate(`/logistics/tools/${encodeURIComponent(record.id)}/return`, { method: "POST" })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Tool returned");
    await onRefresh?.(refreshHint(active, { toolId: record.id }));
  });

  document.getElementById("weLogToolCalibrateForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const result = await runLocked(`tool-cal:${record.id}`, () =>
      softMutate(`/logistics/tools/${encodeURIComponent(record.id)}/calibrate`, {
        body: { certificate_number: values.certificate_number || "", notes: values.notes || "" },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Tool calibrated");
    await onRefresh?.(refreshHint(active, { toolId: record.id }));
  });
}

export { listify, softGet, softMutate };
