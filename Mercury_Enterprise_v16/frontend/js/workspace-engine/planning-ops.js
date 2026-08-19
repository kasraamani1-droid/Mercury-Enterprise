/**
 * Maintenance planning operator UI (Workspace Engine + shared helpers).
 * Uses existing /api/v1/planning routes. No parallel planning workspace objects.
 */

import { esc, toast } from "../utils.js";
import { listify, softMutate } from "../ux2/api.js";
import { mutationErrorMessage, runLocked } from "./logistics-ops.js";

export function normalizeRole(role) {
  return String(role || "").trim();
}

export function sessionCanReadPlanning(role) {
  const value = normalizeRole(role);
  return value === "Viewer" || value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function sessionCanManagePlanning(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Administrator";
}

export function eligibleChecks(checks) {
  return (Array.isArray(checks) ? checks : []).filter((row) => {
    const status = String(row?.status || "").toLowerCase();
    return ["due", "overdue", "planned"].includes(status) && !row.generated_work_package_id;
  });
}

export function filterDueItems(items, { q = "", aircraftId = "", urgency = "", sourceType = "" } = {}) {
  const query = String(q || "").trim().toLowerCase();
  const ac = String(aircraftId || "").trim();
  const urg = String(urgency || "").trim().toLowerCase();
  const src = String(sourceType || "").trim().toLowerCase();
  return (Array.isArray(items) ? items : []).filter((row) => {
    if (ac && String(row.aircraft_id || "") !== ac) return false;
    if (urg && String(row.urgency || "").toLowerCase() !== urg) return false;
    if (src && String(row.source_type || "").toLowerCase() !== src) return false;
    if (!query) return true;
    const hay = `${row.title || ""} ${row.source_type || ""} ${row.source_id || ""} ${row.aircraft_id || ""} ${row.urgency || ""}`.toLowerCase();
    return hay.includes(query);
  });
}

export function forecastRows(forecast) {
  if (!forecast || typeof forecast !== "object") return [];
  return [...(forecast.overdue || []), ...(forecast.due_soon || []), ...(forecast.future || [])];
}

export function filterWorkforceLines(rows, { workPackageId = "", roleCode = "", q = "" } = {}) {
  const wp = String(workPackageId || "").trim();
  const role = String(roleCode || "").trim().toLowerCase();
  const query = String(q || "").trim().toLowerCase();
  return (Array.isArray(rows) ? rows : []).filter((row) => {
    if (wp && String(row.work_package_id || "") !== wp) return false;
    if (role && String(row.role_code || "").toLowerCase() !== role) return false;
    if (!query) return true;
    const hay = `${row.role_code || ""} ${row.employee_id || ""} ${row.status || ""} ${row.shift_code || ""} ${row.work_package_id || ""}`.toLowerCase();
    return hay.includes(query);
  });
}

export function workforceFlagLabel(row) {
  const bits = [];
  if (row?.license_ok) bits.push("license");
  if (row?.authorization_ok) bits.push("auth");
  if (row?.available) bits.push("available");
  return bits.length ? bits.join(" · ") : "flags unset";
}

export function dueObjectTarget(item) {
  const source = String(item?.source_type || "").toLowerCase();
  const id = item?.source_id || item?.id;
  if (!id) return null;
  if (source === "deferred_defect") return { type: "finding", id, label: item.title || item.defect_number || id };
  if (source === "check") return { type: "check", id, label: item.title || item.check_code || id };
  if (source === "ad") return { type: "airworthinessDirective", id, label: item.title || item.ad_number || id };
  if (source === "sb" || source === "service_bulletin") return { type: "serviceBulletin", id, label: item.title || item.sb_number || id };
  if (source === "eo" || source === "engineering_order") return { type: "engineeringOrder", id, label: item.title || item.eo_number || id };
  return null;
}

export function planningOpsCacheKeys(session, mutation = {}) {
  const aircraft = [];
  const workOrders = [];
  const findings = [];
  const checks = [];
  const ads = [];
  const sbs = [];
  const eos = [];
  const mels = [];
  const push = (list, value) => {
    const id = String(value || "").trim();
    if (id && !list.includes(id)) list.push(id);
  };
  if (session?.type === "aircraft") push(aircraft, session.id);
  if (session?.type === "finding") push(findings, session.id);
  if (session?.type === "check") push(checks, session.id);
  if (session?.type === "airworthinessDirective") push(ads, session.id);
  if (session?.type === "serviceBulletin") push(sbs, session.id);
  if (session?.type === "engineeringOrder") push(eos, session.id);
  if (session?.type === "melItem") push(mels, session.id);
  push(aircraft, mutation.aircraftId || session?.record?.aircraft_id);
  push(workOrders, mutation.workOrderId || session?.record?.linked_work_order_id);
  push(findings, mutation.findingId);
  push(checks, mutation.checkId);
  push(ads, mutation.adId);
  push(sbs, mutation.sbId);
  push(eos, mutation.eoId);
  push(mels, mutation.melId);
  const workforcePlanLines = [];
  if (session?.type === "workforcePlanLine") push(workforcePlanLines, session.id);
  push(workforcePlanLines, mutation.workforcePlanLineId);
  return { aircraft, workOrders, findings, checks, ads, sbs, eos, mels, workforcePlanLines };
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

function aircraftOptions(rows, selected) {
  const items = Array.isArray(rows) ? rows : [];
  if (!items.length) return `<option value="">No aircraft loaded</option>`;
  return [`<option value="">Select aircraft</option>`]
    .concat(
      items.map((row) => {
        const id = String(row.id || row.aircraft_id || "");
        const label = row.registration || row.aircraft_id || id;
        return `<option value="${esc(id)}"${id === String(selected || "") ? " selected" : ""}>${esc(label)}</option>`;
      })
    )
    .join("");
}

function contextJumps(record) {
  const bits = [];
  const ac = record?.aircraft_id;
  const wo = record?.linked_work_order_id;
  const wp = record?.generated_work_package_id || record?.work_package_id;
  if (ac) bits.push(`<button type="button" class="mx-chip" data-we-open="aircraft:${esc(String(ac))}" data-we-tab="maintenance">Aircraft</button>`);
  if (wo) bits.push(`<button type="button" class="mx-chip" data-we-open="workOrder:${esc(String(wo))}">Work order</button>`);
  if (wp) bits.push(`<span class="mx-chip">WP ${esc(String(wp))}</span>`);
  return bits.length ? `<div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">${bits.join("")}</div>` : "";
}

export function renderFindingWorkspace(session, record, bundle) {
  const row = record || {};
  const canManage = sessionCanManagePlanning(role(bundle));
  const mels = bundle?.melItems || [];
  return `
    ${loadBanner(bundle?.recordLoad, "Deferred defect")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(row.defect_number || session.id)}</h3><span class="mx-chip">${esc(row.status || "—")}</span></div>
      <p class="mx-subtitle">${esc(row.title || "")} · ${esc(row.deferral_type || "")} · MEL ${esc(row.dispatch_category || "—")} · alert ${esc(row.alert_level || "—")}</p>
      <p class="mx-subtitle">${esc(row.description || "")}</p>
      ${contextJumps(row)}
    </article>
    ${
      canManage
        ? `<p class="mx-subtitle">This record is already a deferred defect. Log additional defects from the aircraft Maintenance tab. Raise work from the aircraft object when no linked work order exists.</p>`
        : `<p class="mx-subtitle">Planning manage is required to create defects. This session is read-only.</p>`
    }
    <article class="mx-card" style="margin-top:12px">
      <div class="mx-card-header"><h3>MEL / CDL catalog</h3></div>
      ${
        mels.length
          ? table(
              ["Item", "Type", "Cat", "Interval"],
              mels
                .slice(0, 20)
                .map(
                  (mel) => `<tr class="we-row-open" data-we-open="melItem:${esc(String(mel.id))}" data-we-label="${esc(mel.item_number || mel.id)}">
                    <td class="mx-mono">${esc(mel.item_number || mel.id)}</td>
                    <td>${esc(mel.list_type || "—")}</td>
                    <td>${esc(mel.dispatch_category || "—")}</td>
                    <td>${esc(String(mel.repair_interval_days ?? "—"))}d</td>
                  </tr>`
                )
                .join("")
            )
          : empty("No MEL/CDL items loaded.")
      }
    </article>
    <p class="mx-subtitle" id="wePlanMsg"></p>
  `;
}

export function renderCheckWorkspace(session, record, bundle) {
  const row = record || {};
  const canManage = sessionCanManagePlanning(role(bundle));
  const eligible = eligibleChecks([row]).length === 1;
  const relatedWo = (bundle?.workOrders || [])
    .map(
      (order) =>
        `<button type="button" class="mx-chip" data-we-open="workOrder:${esc(String(order.id))}" data-we-label="${esc(order.wo_number || order.id)}">${esc(order.wo_number || order.id)}</button>`
    )
    .join("");
  return `
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(row.check_code || session.id)}</h3><span class="mx-chip">${esc(row.status || "—")}</span></div>
      <p class="mx-subtitle">${esc(row.check_type || "")} · ${esc(row.title || "")} · bay ${esc(row.bay || "—")} · due ${esc(String(row.next_due_at || "—").slice(0, 19))}</p>
      ${contextJumps(row)}
      ${relatedWo ? `<div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">${relatedWo}</div>` : ""}
    </article>
    ${
      canManage && eligible
        ? `<form id="wePlanGenerateForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Generate work package</strong>
            <input type="hidden" name="check_id" value="${esc(String(row.id || session.id))}" />
            <label class="mx-field"><input type="checkbox" name="include_mpd_tasks" checked /> Include MPD tasks as job cards</label>
            <button class="mx-btn" type="submit">Generate WP / WO / job cards</button>
          </form>`
        : `<p class="mx-subtitle">${row.generated_work_package_id ? "Package already generated for this check." : "Generate requires a due/overdue/planned check without a package."}</p>`
    }
    <p class="mx-subtitle" id="wePlanMsg"></p>
  `;
}

function directiveBody(kind, number, record, extra = "") {
  return `
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(number || record.id)}</h3><span class="mx-chip">${esc(record.compliance_status || record.status || "—")}</span></div>
      <p class="mx-subtitle">${esc(kind)} · ${esc(record.title || "")} · due ${esc(String(record.due_date || "—").slice(0, 10))}</p>
      <p class="mx-subtitle">${esc(record.applicability || record.effectivity || "")}</p>
      ${contextJumps(record)}
      ${extra}
    </article>
    <p class="mx-subtitle" id="wePlanMsg"></p>
  `;
}

export function renderAdWorkspace(session, record) {
  const row = record || {};
  return directiveBody("AD", row.ad_number, row, `<p class="mx-subtitle">Authority ${esc(row.authority || "—")} · mandatory ${esc(String(row.mandatory))}</p>`);
}

export function renderSbWorkspace(session, record) {
  const row = record || {};
  return directiveBody("SB", row.sb_number, row, `<p class="mx-subtitle">${esc(row.sb_type || "")} · ${esc(row.priority || "")}</p>`);
}

export function renderEoWorkspace(session, record, bundle) {
  const row = record || {};
  const canManage = sessionCanManagePlanning(role(bundle));
  const approvable = ["draft", "in_review"].includes(String(row.status || ""));
  const extra =
    canManage && approvable
      ? `<form id="wePlanEoApproveForm" style="margin-top:12px"><input type="hidden" name="eo_id" value="${esc(String(row.id || session.id))}" /><button class="mx-btn" type="submit">Approve engineering order</button></form>`
      : "";
  return directiveBody("EO", row.eo_number, row, extra);
}

export function renderMelWorkspace(session, record) {
  const row = record || {};
  return `
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(row.item_number || session.id)}</h3><span class="mx-chip">${esc(row.list_type || "—")}</span></div>
      <p class="mx-subtitle">${esc(row.title || "")} · category ${esc(row.dispatch_category || "—")} · ${esc(String(row.repair_interval_days ?? "—"))} days</p>
      <p class="mx-subtitle">${esc(row.dispatch_restrictions || "")}</p>
    </article>
  `;
}

export function renderAircraftDirectives(session, bundle, tabId) {
  const rows = tabId === "sb" ? bundle?.serviceBulletins || [] : bundle?.ads || [];
  const type = tabId === "sb" ? "serviceBulletin" : "airworthinessDirective";
  const numberKey = tabId === "sb" ? "sb_number" : "ad_number";
  if (!rows.length) return empty(tabId === "sb" ? "No service bulletins in this organization." : "No airworthiness directives in this organization.");
  return `
    <p class="mx-subtitle">AD/SB records are organization-scoped. Applicability is a text field — they are not stored per aircraft.</p>
    ${table(
      ["Number", "Title", "Status", "Due"],
      rows
        .slice(0, 40)
        .map(
          (row) => `<tr class="we-row-open" data-we-open="${esc(type)}:${esc(String(row.id))}" data-we-label="${esc(row[numberKey] || row.id)}">
            <td class="mx-mono">${esc(row[numberKey] || row.id)}</td>
            <td>${esc(row.title || "—")}</td>
            <td><span class="mx-chip">${esc(row.compliance_status || row.status || "—")}</span></td>
            <td>${esc(String(row.due_date || "—").slice(0, 10))}</td>
          </tr>`
        )
        .join("")
    )}
  `;
}

export function renderWorkforcePlanWorkspace(session, record, bundle) {
  const row = record || {};
  const canManage = sessionCanManagePlanning(role(bundle));
  const employee = bundle?.employee;
  const employeeLabel = employee?.full_name || employee?.employee_number || row.employee_id || "Employee";
  const orders = bundle?.workOrders || [];
  const orderChips = orders
    .slice(0, 8)
    .map(
      (order) =>
        `<button type="button" class="mx-chip" data-we-open="workOrder:${esc(String(order.id))}" data-we-label="${esc(order.wo_number || order.id)}">${esc(order.wo_number || order.id)}</button>`
    )
    .join("");
  return `
    ${loadBanner(bundle?.recordLoad, "Workforce plan line")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(row.role_code || session.id)}</h3><span class="mx-chip">${esc(row.status || "—")}</span></div>
      <p class="mx-subtitle">Planner-entered assignment on the work package. License / authorization / available flags are not a certification determination.</p>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">
        <span class="mx-chip">Shift ${esc(row.shift_code || "—")}</span>
        <span class="mx-chip">${esc(String(row.workload_hours ?? "0"))} h</span>
        <span class="mx-chip">${esc(workforceFlagLabel(row))}</span>
        ${row.work_package_id ? `<span class="mx-chip">WP ${esc(String(row.work_package_id))}</span>` : ""}
      </div>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">
        ${
          row.employee_id
            ? `<button type="button" class="mx-chip" data-we-open="employee:${esc(String(row.employee_id))}" data-we-label="${esc(employeeLabel)}">${esc(employeeLabel)}</button>`
            : ""
        }
        ${orderChips}
      </div>
    </article>
    ${
      canManage
        ? `<form id="weWorkforceStatusForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Update assignment</strong>
            <input type="hidden" name="line_id" value="${esc(String(row.id || session.id))}" />
            <label class="mx-field">Status
              <select class="mx-input" name="status">
                ${["planned", "assigned", "released", "complete", "cancelled"]
                  .map((status) => `<option value="${esc(status)}"${status === String(row.status || "") ? " selected" : ""}>${esc(status)}</option>`)
                  .join("")}
              </select>
            </label>
            <label class="mx-field">Shift<input class="mx-input" name="shift_code" maxlength="40" value="${esc(row.shift_code || "")}" /></label>
            <label class="mx-field">Workload hours<input class="mx-input" name="workload_hours" type="number" min="0" step="0.25" value="${esc(String(row.workload_hours ?? "0"))}" /></label>
            <label class="mx-field"><input type="checkbox" name="license_ok"${row.license_ok ? " checked" : ""} /> License flag</label>
            <label class="mx-field"><input type="checkbox" name="authorization_ok"${row.authorization_ok ? " checked" : ""} /> Authorization flag</label>
            <label class="mx-field"><input type="checkbox" name="available"${row.available ? " checked" : ""} /> Available flag</label>
            <button class="mx-btn" type="submit">Save workforce line</button>
          </form>`
        : `<p class="mx-subtitle">Planning manage is required to update workforce assignments. This session is read-only.</p>`
    }
    <p class="mx-subtitle" id="wePlanMsg"></p>
  `;
}

export function renderWorkOrderWorkforce(session, record, bundle) {
  const lines = bundle?.workforcePlanLines || [];
  const rows = lines
    .map(
      (line) => `<tr class="we-row-open" data-we-open="workforcePlanLine:${esc(String(line.id))}" data-we-label="${esc(line.role_code || line.id)}">
        <td>${esc(line.role_code || "—")}</td>
        <td class="mx-mono">${esc(line.employee_id || "—")}</td>
        <td>${esc(line.shift_code || "—")}</td>
        <td>${esc(line.status || "—")}</td>
        <td>${esc(workforceFlagLabel(line))}</td>
      </tr>`
    )
    .join("");
  return `<article class="mx-card" style="margin-top:16px">
    <div class="mx-card-header"><h3>Workforce plan</h3></div>
    <p class="mx-subtitle">Assignments on work package ${esc(record?.work_package_id || "—")}. Flags are planner-entered.</p>
    ${loadBanner(bundle?.workforcePlanLinesLoad, "Workforce")}
    ${lines.length ? table(["Role", "Employee", "Shift", "Status", "Flags"], rows) : empty("No workforce plan lines on this package.")}
  </article>`;
}

export function renderAircraftPlanningBridge(session, record, bundle) {
  const canManage = sessionCanManagePlanning(role(bundle));
  const mels = bundle?.melItems || [];
  const defects = (bundle?.defects || []).filter((row) => String(row.aircraft_id) === String(session.id));
  const checks = (bundle?.checks || []).filter((row) => String(row.aircraft_id) === String(session.id));
  const packageIds = new Set((bundle?.workOrders || []).map((row) => String(row.work_package_id || "")).filter(Boolean));
  const workforce = (bundle?.workforcePlanLines || []).filter((row) => !packageIds.size || packageIds.has(String(row.work_package_id || "")));
  const defectList = defects.length
    ? defects
        .slice(0, 8)
        .map(
          (row) =>
            `<button type="button" class="mx-chip" data-we-open="finding:${esc(String(row.id))}" data-we-label="${esc(row.defect_number || row.title || row.id)}">${esc(row.defect_number || row.title)}</button>`
        )
        .join("")
    : `<span class="mx-subtitle">No deferred defects for this aircraft.</span>`;
  const checkList = checks.length
    ? checks
        .slice(0, 8)
        .map(
          (row) =>
            `<button type="button" class="mx-chip" data-we-open="check:${esc(String(row.id))}" data-we-label="${esc(row.check_code || row.id)}">${esc(row.check_code || row.id)}</button>`
        )
        .join("")
    : `<span class="mx-subtitle">No checks for this aircraft.</span>`;
  const workforceList = workforce.length
    ? workforce
        .slice(0, 8)
        .map(
          (row) =>
            `<button type="button" class="mx-chip" data-we-open="workforcePlanLine:${esc(String(row.id))}" data-we-label="${esc(row.role_code || row.id)}">${esc(row.role_code || "line")} · ${esc(row.status || "")}</button>`
        )
        .join("")
    : `<span class="mx-subtitle">No workforce plan lines for this aircraft's packages.</span>`;
  return `<article class="mx-card" style="margin-top:16px">
    <div class="mx-card-header"><h3>Planning</h3></div>
    <p class="mx-subtitle">Checks</p>
    <div class="mx-row" style="flex-wrap:wrap;gap:8px">${checkList}</div>
    <p class="mx-subtitle" style="margin-top:8px">Deferred defects</p>
    <div class="mx-row" style="flex-wrap:wrap;gap:8px">${defectList}</div>
    <p class="mx-subtitle" style="margin-top:8px">Workforce plan</p>
    <div class="mx-row" style="flex-wrap:wrap;gap:8px">${workforceList}</div>
    ${
      canManage
        ? `<form id="wePlanDefectForm" class="we-cfg-form-grid" style="margin-top:12px">
            <input type="hidden" name="aircraft_id" value="${esc(String(session.id))}" />
            <label class="mx-field">Title<input class="mx-input" name="title" required maxlength="300" /></label>
            <label class="mx-field">Type<select class="mx-input" name="deferral_type"><option value="mel">mel</option><option value="cdl">cdl</option><option value="other">other</option></select></label>
            <label class="mx-field">MEL item<select class="mx-input" name="mel_item_id"><option value="">None</option>${mels
              .map((mel) => `<option value="${esc(String(mel.id))}">${esc(mel.item_number || mel.id)} · ${esc(mel.title || "")}</option>`)
              .join("")}</select></label>
            <label class="mx-field">Category<select class="mx-input" name="dispatch_category"><option value="">—</option><option>A</option><option>B</option><option>C</option><option>D</option></select></label>
            <button class="mx-btn" type="submit">Log deferred defect</button>
          </form>`
        : `<p class="mx-subtitle">Defect create requires planning.manage (Operator or Administrator).</p>`
    }
    <p class="mx-subtitle" id="wePlanMsg"></p>
  </article>`;
}

function setPlanMessage(text, ok) {
  const node = document.getElementById("wePlanMsg") || document.getElementById("planOpsMsg");
  if (!node) return;
  node.textContent = text || "";
  node.style.color = ok ? "" : "var(--danger, #c44)";
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function refreshHint(active, extra = {}) {
  return {
    aircraftId: extra.aircraftId || active?.record?.aircraft_id || (active?.type === "aircraft" ? active.id : ""),
    workOrderId: extra.workOrderId || active?.record?.linked_work_order_id || "",
    findingId: extra.findingId || (active?.type === "finding" ? active.id : ""),
    checkId: extra.checkId || (active?.type === "check" ? active.id : ""),
    adId: extra.adId || (active?.type === "airworthinessDirective" ? active.id : ""),
    sbId: extra.sbId || (active?.type === "serviceBulletin" ? active.id : ""),
    eoId: extra.eoId || (active?.type === "engineeringOrder" ? active.id : ""),
    melId: extra.melId || (active?.type === "melItem" ? active.id : ""),
    workforcePlanLineId: extra.workforcePlanLineId || (active?.type === "workforcePlanLine" ? active.id : ""),
  };
}

export function bindPlanningOpsPanel(active, { onRefresh } = {}) {
  if (!active) return;
  const fail = (result) => {
    const msg = mutationErrorMessage(result);
    setPlanMessage(msg, false);
    toast(msg);
  };

  document.getElementById("wePlanGenerateForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManagePlanning(role(active.bundle))) return fail({ status: 403, error: "planning.manage required" });
    const values = formValues(event.target);
    if (!window.confirm("Generate a work package, work order, and job cards from this check?")) return;
    const result = await runLocked(`plan-gen:${values.check_id}`, () =>
      softMutate("/planning/checks/generate-package", {
        body: {
          check_id: values.check_id,
          include_mpd_tasks: values.include_mpd_tasks === "on" || values.include_mpd_tasks === "true",
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Generated ${result.data?.package_number || "package"}`);
    const firstWo = (result.data?.work_order_ids || [])[0];
    await onRefresh?.(refreshHint(active, { checkId: values.check_id, workOrderId: firstWo }));
    if (firstWo) {
      document.getElementById("wePlanMsg")?.insertAdjacentHTML(
        "beforeend",
        ` <button type="button" class="mx-chip" data-we-open="workOrder:${esc(String(firstWo))}">Open work order</button>`
      );
    }
  });

  document.getElementById("wePlanEoApproveForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const result = await runLocked(`eo-approve:${values.eo_id}`, () =>
      softMutate(`/planning/engineering-orders/${encodeURIComponent(values.eo_id)}/approve`, { method: "POST" })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Engineering order approved");
    await onRefresh?.(refreshHint(active, { eoId: values.eo_id }));
  });

  document.getElementById("wePlanDefectForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManagePlanning(role(active.bundle))) return fail({ status: 403, error: "planning.manage required" });
    const values = formValues(event.target);
    if (!String(values.title || "").trim()) return fail({ status: 422, error: "Title required" });
    const body = {
      aircraft_id: values.aircraft_id,
      title: String(values.title).trim(),
      deferral_type: values.deferral_type || "mel",
    };
    if (values.mel_item_id) body.mel_item_id = values.mel_item_id;
    if (values.dispatch_category) body.dispatch_category = values.dispatch_category;
    const result = await runLocked(`defect:${values.aircraft_id}`, () => softMutate("/planning/deferred-defects", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Defect ${result.data?.defect_number || ""} logged`);
    await onRefresh?.(refreshHint(active, { findingId: result.data?.id, aircraftId: values.aircraft_id }));
  });

  document.getElementById("weWorkforceStatusForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManagePlanning(role(active.bundle))) return fail({ status: 403, error: "planning.manage required" });
    const values = formValues(event.target);
    const lineId = values.line_id || active.id;
    const body = {
      status: values.status,
      shift_code: values.shift_code || "",
      license_ok: Boolean(values.license_ok),
      authorization_ok: Boolean(values.authorization_ok),
      available: Boolean(values.available),
    };
    if (values.workload_hours !== "") body.workload_hours = Number(values.workload_hours);
    const result = await runLocked(`workforce:${lineId}`, () =>
      softMutate(`/planning/workforce-plan-lines/${encodeURIComponent(lineId)}`, { method: "PATCH", body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Workforce plan line updated");
    await onRefresh?.(refreshHint(active, { workforcePlanLineId: lineId }));
  });
}
