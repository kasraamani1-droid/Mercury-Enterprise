/**
 * Maintenance operations operator UI (Workspace Engine).
 * Work orders, job cards, technical logbook, and planning context.
 * Uses existing /api/v1/work-orders, /maintenance, and /planning routes. No new backend.
 */

import { esc, toast } from "../utils.js";
import { softGet, softMutate } from "../ux2/api.js";

export const JC_TRANSITIONS = {
  draft: ["assigned", "closed"],
  assigned: ["accepted", "draft", "closed"],
  accepted: ["in_progress", "waiting_parts", "waiting_engineering", "closed"],
  in_progress: ["paused", "waiting_parts", "waiting_engineering", "closed"],
  paused: ["in_progress", "waiting_parts", "waiting_engineering", "closed"],
  waiting_parts: ["in_progress", "accepted", "closed"],
  waiting_engineering: ["in_progress", "accepted", "closed"],
  waiting_inspection: [],
  completed: [],
  rejected: ["in_progress", "assigned", "closed"],
  released: ["closed"],
  closed: [],
};

export const CERT_GATED_STATUSES = ["waiting_inspection", "completed", "released"];
const COMPLETE_FROM = new Set(["assigned", "accepted", "in_progress", "paused"]);
const ASSIGN_FROM = new Set(["draft", "assigned", "rejected"]);
const INSPECT_FROM = new Set(["waiting_inspection"]);
const II_FROM = new Set(["completed"]);
const RELEASE_FROM = new Set(["completed"]);
const CLOSE_MANAGE_FROM = new Set(["released"]);

const inFlight = new Set();

export function normalizeRole(role) {
  return String(role || "").trim();
}

export function sessionCanManageWorkOrders(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Administrator";
}

export function sessionCanExecuteWork(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function sessionCanInspect(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function sessionCanRelease(role) {
  const value = normalizeRole(role);
  return value === "Reviewer" || value === "Administrator";
}

export function sessionCanReadLogbook(role) {
  const value = normalizeRole(role);
  return value === "Viewer" || value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function sessionCanAmendLogbook(role) {
  return sessionCanManageWorkOrders(role);
}

export function sessionCanManagePlanning(role) {
  return sessionCanManageWorkOrders(role);
}

export function allowedTransitions(status) {
  return [...(JC_TRANSITIONS[String(status || "")] || [])];
}

export function inspectionReleaseState(card) {
  const status = String(card?.status || "");
  return {
    status,
    awaitingInspection: status === "waiting_inspection",
    awaitingIndependent: status === "completed" && Boolean(card?.independent_inspection_required) && !card?.independent_inspector_employee_id,
    awaitingRelease: status === "completed",
    released: status === "released",
    closed: status === "closed",
    performer: card?.technician_employee_id || "",
    inspector: card?.inspector_employee_id || "",
    independentInspector: card?.independent_inspector_employee_id || "",
    aca: card?.aca_employee_id || "",
    updatedAt: card?.updated_at || card?.created_at || "",
  };
}

export function linkLogbookToWorkOrders(entries, jobCards) {
  const cards = Array.isArray(jobCards) ? jobCards : [];
  const byTask = Object.fromEntries(
    cards.filter((card) => card?.maintenance_task_id).map((card) => [String(card.maintenance_task_id), card])
  );
  return (Array.isArray(entries) ? entries : []).map((entry) => {
    const card = byTask[String(entry?.task_id || "")] || null;
    return {
      ...entry,
      job_card_id: card?.id || "",
      job_card_number: card?.job_card_number || "",
      work_order_id: card?.work_order_id || "",
    };
  });
}

export function filterDueForAircraft(dueItems, aircraftId) {
  const id = String(aircraftId || "");
  const items = Array.isArray(dueItems) ? dueItems : [];
  if (!id) return items;
  return items.filter((item) => !item.aircraft_id || String(item.aircraft_id) === id);
}

export function relatedWorkOrdersForDueItem(item, workOrders, checks) {
  const orders = Array.isArray(workOrders) ? workOrders : [];
  const checkRows = Array.isArray(checks) ? checks : [];
  const source = String(item?.source_type || "").toLowerCase();
  const sourceId = String(item?.source_id || item?.id || "");
  const found = [];
  if (item?.linked_work_order_id) {
    const hit = orders.find((row) => String(row.id) === String(item.linked_work_order_id));
    if (hit) found.push(hit);
  }
  if (source === "check") {
    const check = checkRows.find((row) => String(row.id) === sourceId);
    if (check?.generated_work_package_id) {
      found.push(...orders.filter((row) => String(row.work_package_id) === String(check.generated_work_package_id)));
    }
  }
  const unique = [];
  const seen = new Set();
  found.forEach((row) => {
    const id = String(row.id || "");
    if (!id || seen.has(id)) return;
    seen.add(id);
    unique.push(row);
  });
  if (unique.length) return unique;
  const aircraftId = item?.aircraft_id;
  if (!aircraftId) return [];
  return orders.filter((row) => String(row.aircraft_id) === String(aircraftId)).slice(0, 4);
}

export function mutationErrorMessage(result) {
  const status = Number(result?.status || 0);
  const detail = String(result?.error || "").trim() || `HTTP ${status || "error"}`;
  if (status === 400) return detail;
  if (status === 401) return "Sign in required.";
  if (status === 403) return detail || "Not permitted for this role.";
  if (status === 404) return detail || "Record not found.";
  if (status === 409) return `Conflict: ${detail}`;
  if (status === 422) return `Validation: ${detail}`;
  if (status >= 500) return detail || "Server error.";
  return detail;
}

export function httpErrorMessage(status, error) {
  return mutationErrorMessage({ status, error });
}

export function maintenanceOpsCacheKeys(session, mutation = {}) {
  const aircraft = [];
  const workOrders = [];
  const jobCards = [];
  const push = (list, value) => {
    const id = String(value || "").trim();
    if (id && !list.includes(id)) list.push(id);
  };
  if (session?.type === "aircraft") push(aircraft, session.id);
  if (session?.type === "workOrder") push(workOrders, session.id);
  if (session?.type === "jobCard") push(jobCards, session.id);
  push(aircraft, session?.record?.aircraft_id);
  push(aircraft, session?.bundle?.aircraft?.id);
  push(aircraft, mutation.aircraftId);
  push(workOrders, session?.record?.work_order_id);
  push(workOrders, mutation.workOrderId);
  push(jobCards, mutation.jobCardId);
  (session?.bundle?.jobCards || []).forEach((card) => push(jobCards, card.id));
  (session?.bundle?.workOrders || []).forEach((order) => push(workOrders, order.id));
  return { aircraft, workOrders, jobCards };
}

export function formatTs(value) {
  if (!value) return "—";
  const text = String(value);
  return text.length > 19 ? text.slice(0, 19).replace("T", " ") : text.replace("T", " ");
}

function role(bundle) {
  return bundle?.sessionRole || "";
}

function empty(msg) {
  return `<div class="mx-empty">${esc(msg)}</div>`;
}

function table(headers, body) {
  return `<div class="mx-table-wrap"><table class="mx-table"><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function employeeOptions(employees, selected) {
  const rows = Array.isArray(employees) ? employees : [];
  if (!rows.length) return `<option value="">No personnel loaded</option>`;
  return [`<option value="">Select employee</option>`]
    .concat(
      rows.map((emp) => {
        const id = String(emp.id || "");
        const label = `${emp.employee_number || id} · ${emp.full_name || emp.position_title || ""}`;
        const sel = String(selected || "") === id ? " selected" : "";
        return `<option value="${esc(id)}"${sel}>${esc(label)}</option>`;
      })
    )
    .join("");
}

function contextJumps(record, extra = "") {
  const aircraftId = record?.aircraft_id || "";
  const workOrderId = record?.work_order_id || record?.id || "";
  const registration = record?.registration || aircraftId;
  return `<div class="mx-row we-ops-jumps" style="flex-wrap:wrap;gap:8px;margin:12px 0">
    ${aircraftId ? `<button type="button" class="mx-chip" data-we-open="aircraft:${esc(String(aircraftId))}" data-we-label="${esc(String(registration))}">Aircraft</button>` : ""}
    ${aircraftId ? `<button type="button" class="mx-chip" data-we-open="aircraft:${esc(String(aircraftId))}" data-we-tab="logbook" data-we-label="${esc(String(registration))}">Technical Logbook</button>` : ""}
    ${aircraftId ? `<button type="button" class="mx-chip" data-we-open="aircraft:${esc(String(aircraftId))}" data-we-tab="configuration" data-we-label="${esc(String(registration))}">Configuration</button>` : ""}
    ${workOrderId && record?.work_order_id ? `<button type="button" class="mx-chip" data-we-open="workOrder:${esc(String(workOrderId))}" data-we-label="${esc(String(record.wo_number || workOrderId))}">Work order</button>` : ""}
    <button type="button" class="mx-chip" data-ux2-goto="planning">Planning</button>
    <button type="button" class="mx-chip" data-ux2-goto="workOrders">Work Orders board</button>
    <button type="button" class="mx-chip" data-ux2-goto="maintenance">MRO Execution</button>
    <button type="button" class="mx-chip" data-ux2-goto="logbook">Logbook area</button>
    ${extra}
  </div>`;
}

function loadBanner(load, label) {
  if (!load || load.ok) return "";
  return `<div class="mx-empty">${esc(label)}: ${esc(httpErrorMessage(load.status, load.error))}</div>`;
}

export function renderWorkOrderOverview(session, record, bundle) {
  const order = record || {};
  const cards = bundle?.jobCards || [];
  const byStatus = {};
  cards.forEach((card) => {
    const status = String(card.status || "unknown");
    byStatus[status] = (byStatus[status] || 0) + 1;
  });
  const awaitingInsp = cards.filter((card) => card.status === "waiting_inspection").length;
  const awaitingRel = cards.filter((card) => card.status === "completed").length;
  return `
    ${loadBanner(bundle?.jobCardsLoad, "Job cards")}
    <div class="mx-grid mx-grid-3" style="margin-bottom:16px">
      <article class="mx-kpi"><div class="mx-label">Status</div><div class="mx-kpi-value" style="font-size:18px">${esc(order.status || "—")}</div><div class="mx-kpi-hint">Priority ${esc(order.priority || "—")}</div></article>
      <article class="mx-kpi"><div class="mx-label">Due / target</div><div class="mx-kpi-value" style="font-size:18px">${esc(formatTs(order.due_date))}</div><div class="mx-kpi-hint">${esc(String(order.job_card_count ?? cards.length))} job cards</div></article>
      <article class="mx-kpi"><div class="mx-label">Inspection / release</div><div class="mx-kpi-value" style="font-size:18px">${esc(String(awaitingInsp))}/${esc(String(awaitingRel))}</div><div class="mx-kpi-hint">Waiting inspection / ACA</div></article>
    </div>
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(order.wo_number || session.id)}</h3><span class="mx-chip">${esc(order.status || "—")}</span></div>
      <p class="mx-subtitle">${esc(order.title || order.description || "Work order")}</p>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">
        <span class="mx-chip">Aircraft ${esc(order.aircraft_id || "—")}</span>
        <span class="mx-chip">Package ${esc(order.work_package_id || "—")}</span>
        <span class="mx-chip">Planner ${esc(order.planner_employee_id || "—")}</span>
        <span class="mx-chip">Supervisor ${esc(order.supervisor_employee_id || "—")}</span>
        <span class="mx-chip">Updated ${esc(formatTs(order.updated_at))}</span>
      </div>
      ${contextJumps(order)}
    </article>
    ${cards.length ? `<p class="mx-subtitle" style="margin-top:12px">${esc(Object.entries(byStatus).map(([k, v]) => `${k}: ${v}`).join(" · "))}</p>` : empty("No job cards on this work order.")}
  `;
}

export function renderWorkOrderTasks(session, record, bundle) {
  const cards = bundle?.jobCards || [];
  const canManage = sessionCanManageWorkOrders(role(bundle));
  const canExecute = sessionCanExecuteWork(role(bundle));
  const rows = cards
    .map((card) => {
      const state = inspectionReleaseState(card);
      return `<tr class="we-row-open" data-we-open="jobCard:${esc(String(card.id))}" data-we-label="${esc(card.job_card_number || card.title || card.id)}">
        <td class="mx-mono">${esc(card.job_card_number || card.id)}</td>
        <td>${esc(card.title || "—")}</td>
        <td><span class="mx-chip">${esc(card.status || "—")}</span></td>
        <td>${esc(card.technician_employee_id || "unassigned")}</td>
        <td>${esc(state.awaitingInspection ? "inspection" : state.awaitingRelease ? "release" : formatTs(card.updated_at))}</td>
      </tr>`;
    })
    .join("");
  const createForm = canManage
    ? `<details class="mx-card we-ops-form-card" style="margin-top:16px;padding:12px">
        <summary><strong>Create job card</strong></summary>
        <form id="weOpsCreateCardForm" class="mx-stack" style="margin-top:12px;gap:8px">
          <label class="mx-field">Title<input class="mx-input" name="title" required maxlength="300" /></label>
          <label class="mx-field">Description<input class="mx-input" name="description" maxlength="400" /></label>
          <div class="we-cfg-form-grid">
            <label class="mx-field">Priority<select class="mx-input" name="priority"><option value="normal">normal</option><option value="high">high</option><option value="low">low</option><option value="critical">critical</option></select></label>
            <label class="mx-field">Technician<select class="mx-input" name="technician_employee_id">${employeeOptions(bundle.employees)}</select></label>
          </div>
          <button class="mx-btn" type="submit"${canManage ? "" : " disabled"}>Create job card</button>
        </form>
      </details>`
    : `<p class="mx-subtitle">Job-card create requires work-order manage (Operator / Administrator). Backend remains authoritative.</p>`;
  return `
    ${loadBanner(bundle?.jobCardsLoad, "Job cards")}
    ${cards.length ? table(["Card", "Title", "Status", "Technician", "Gate"], rows) : empty("No job cards. Create one or generate a package from Planning.")}
    ${createForm}
    ${canExecute ? "" : `<p class="mx-subtitle">Execution actions are hidden for this session role.</p>`}
    <p class="mx-subtitle" id="weOpsMsg"></p>
  `;
}

export function renderWorkOrderInspections(session, record, bundle) {
  const cards = bundle?.jobCards || [];
  const queue = cards.filter((card) => ["waiting_inspection", "completed", "released", "rejected"].includes(card.status));
  if (!queue.length) return empty("No inspection or release-state job cards on this order.");
  const canInspect = sessionCanInspect(role(bundle));
  const canRelease = sessionCanRelease(role(bundle));
  return `
    ${table(
      ["Card", "Status", "Technician", "Inspector", "ACA", "Open"],
      queue
        .map((card) => {
          const state = inspectionReleaseState(card);
          return `<tr>
            <td class="mx-mono">${esc(card.job_card_number || card.id)}</td>
            <td><span class="mx-chip">${esc(card.status)}</span>${state.awaitingInspection ? ' <span class="mx-chip mx-chip-warn">inspect</span>' : ""}${state.awaitingRelease ? ' <span class="mx-chip mx-chip-warn">release</span>' : ""}</td>
            <td>${esc(card.technician_employee_id || "—")}</td>
            <td>${esc(card.inspector_employee_id || "—")}</td>
            <td>${esc(card.aca_employee_id || "—")}</td>
            <td><button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="jobCard:${esc(String(card.id))}" data-we-label="${esc(card.job_card_number || card.id)}">Open</button></td>
          </tr>`;
        })
        .join("")
    )}
    <p class="mx-subtitle">Inspect ${canInspect ? "available" : "not offered for this role"}; ACA release ${canRelease ? "available" : "requires certification.release (Reviewer / Administrator)"}.</p>
  `;
}

export function renderWorkOrderHistory(session, record, bundle) {
  const cards = bundle?.jobCards || [];
  const logEntries = linkLogbookToWorkOrders(bundle?.logbook || [], cards).filter(
    (entry) => !entry.work_order_id || String(entry.work_order_id) === String(record?.id || session.id)
  );
  const cardEvents = cards.map((card) => ({
    title: `${card.job_card_number || card.id} · ${card.status}`,
    detail: [card.technician_employee_id, card.inspector_employee_id, card.notes].filter(Boolean).join(" · "),
    at: card.updated_at || card.created_at || "",
  }));
  const logEvents = logEntries.map((entry) => ({
    title: entry.summary || "Tech log",
    detail: `Task ${entry.task_id || "—"} · sig ${entry.release_signature_id || "—"}`,
    at: entry.occurred_at || "",
  }));
  const events = [...cardEvents, ...logEvents].sort((a, b) => String(b.at).localeCompare(String(a.at)));
  if (!events.length) return empty("No status history loaded for this work order.");
  return `<div class="mx-timeline">${events
    .slice(0, 20)
    .map(
      (event) => `<div class="mx-timeline-item"><div><strong>${esc(event.title)}</strong>
      <div class="mx-subtitle">${esc(event.detail)}</div>
      <div class="mx-timeline-meta">${esc(formatTs(event.at))}</div></div></div>`
    )
    .join("")}</div>${loadBanner(bundle?.logbookLoad, "Logbook")}`;
}

export function renderJobCardWorkspace(session, record, bundle) {
  const card = record || {};
  const state = inspectionReleaseState(card);
  const canManage = sessionCanManageWorkOrders(role(bundle));
  const canExecute = sessionCanExecuteWork(role(bundle));
  const canInspect = sessionCanInspect(role(bundle));
  const canRelease = sessionCanRelease(role(bundle));
  const transitions = allowedTransitions(card.status).filter((status) => {
    if (status === "closed" && CLOSE_MANAGE_FROM.has(card.status)) return canManage;
    return canExecute;
  });
  const events = bundle?.auditTrail?.certification_events || [];
  const signatures = bundle?.auditTrail?.signatures || [];
  const attachments = bundle?.attachments || [];
  const signForm = (id, title, extraFields, enabled) =>
    enabled
      ? `<form id="${id}" class="mx-stack we-ops-sign-form" style="gap:8px;margin-top:8px">
          <strong>${esc(title)}</strong>
          <label class="mx-field">Employee<select class="mx-input" name="employee_id" required>${employeeOptions(bundle.employees, card.technician_employee_id)}</select></label>
          <label class="mx-field">Method<select class="mx-input" name="method"><option value="password">password</option><option value="pin">pin</option></select></label>
          <label class="mx-field">Credential<input class="mx-input" name="credential" type="password" autocomplete="off" /></label>
          <label class="mx-field">Notes<input class="mx-input" name="notes" maxlength="400" /></label>
          ${extraFields || ""}
          <button class="mx-btn" type="submit">Submit</button>
        </form>`
      : "";

  return `
    ${loadBanner(bundle?.recordLoad, "Job card")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(card.job_card_number || session.id)}</h3><span class="mx-chip">${esc(card.status || "—")}</span></div>
      <p>${esc(card.title || "")}</p>
      <p class="mx-subtitle">${esc(card.description || "")}</p>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px">
        <span class="mx-chip">Priority ${esc(card.priority || "—")}</span>
        <span class="mx-chip">Hours ${esc(String(card.actual_hours ?? "0"))}/${esc(String(card.estimated_hours ?? "0"))}</span>
        <span class="mx-chip">II ${esc(card.independent_inspection_required ? "required" : "no")}</span>
        <span class="mx-chip">ACA ${esc(card.aca_required ? "required" : "no")}</span>
        <span class="mx-chip">Updated ${esc(formatTs(card.updated_at))}</span>
      </div>
      ${contextJumps(card)}
    </article>
    <div class="mx-grid mx-grid-3" style="margin:16px 0">
      <article class="mx-kpi"><div class="mx-label">Technician</div><div class="mx-kpi-value" style="font-size:16px">${esc(state.performer || "—")}</div></article>
      <article class="mx-kpi"><div class="mx-label">Inspector</div><div class="mx-kpi-value" style="font-size:16px">${esc(state.inspector || "—")}</div></article>
      <article class="mx-kpi"><div class="mx-label">ACA</div><div class="mx-kpi-value" style="font-size:16px">${esc(state.aca || "—")}</div></article>
    </div>
    ${
      canManage && ASSIGN_FROM.has(card.status)
        ? `<form id="weOpsAssignForm" class="mx-card" style="padding:12px;margin-bottom:12px">
            <strong>Assign technician</strong>
            <div class="we-cfg-form-grid">
              <label class="mx-field">Technician<select class="mx-input" name="technician_employee_id" required>${employeeOptions(bundle.employees, card.technician_employee_id)}</select></label>
              <label class="mx-field">Hangar bay<input class="mx-input" name="hangar_bay" value="${esc(card.hangar_bay || "")}" /></label>
            </div>
            <button class="mx-btn" type="submit">Assign</button>
          </form>`
        : ""
    }
    ${
      canExecute && transitions.length
        ? `<form id="weOpsTransitionForm" class="mx-card" style="padding:12px;margin-bottom:12px">
            <strong>Progress work</strong>
            <p class="mx-subtitle">Certification-gated statuses are not available here — use complete-work, inspect, or release.</p>
            <div class="we-cfg-form-grid">
              <label class="mx-field">Next status<select class="mx-input" name="to_status">${transitions
                .map((status) => `<option value="${esc(status)}">${esc(status)}</option>`)
                .join("")}</select></label>
              <label class="mx-field">Notes<input class="mx-input" name="notes" maxlength="400" /></label>
            </div>
            <input type="hidden" name="expected_version" value="${esc(String(card.version ?? ""))}" />
            <button class="mx-btn" type="submit">Transition</button>
          </form>`
        : ""
    }
    ${signForm("weOpsCompleteForm", "Complete work (performed)", `<label class="mx-field">Actual hours<input class="mx-input" name="actual_hours" type="number" min="0" step="0.01" /></label>`, canExecute && COMPLETE_FROM.has(card.status))}
    ${signForm(
      "weOpsInspectForm",
      "Inspect",
      `<label class="mx-field">Decision<select class="mx-input" name="decision">${
        INSPECT_FROM.has(card.status)
          ? `<option value="approve">approve</option><option value="reject">reject</option><option value="rework">rework</option>`
          : `<option value="independent_inspection">independent_inspection</option>`
      }</select></label>`,
      canInspect && (INSPECT_FROM.has(card.status) || (II_FROM.has(card.status) && card.independent_inspection_required))
    )}
    ${signForm("weOpsReleaseForm", "ACA release", "", canRelease && RELEASE_FROM.has(card.status))}
    ${!canRelease && RELEASE_FROM.has(card.status) ? `<p class="mx-subtitle">ACA release requires certification.release. This session role cannot call /release.</p>` : ""}
    <p class="mx-subtitle" id="weOpsMsg"></p>
    <article class="mx-card" style="margin-top:16px">
      <div class="mx-card-header"><h3>Certification / action events</h3></div>
      ${
        events.length
          ? `<div class="mx-timeline">${events
              .map(
                (event) => `<div class="mx-timeline-item"><div><strong>${esc(event.step || event.event_type || "event")}</strong>
                <div class="mx-subtitle">${esc(event.actor_employee_id || event.employee_id || event.actor || "")} · ${esc(event.actor_username || "")}</div>
                <div class="mx-timeline-meta">${esc(formatTs(event.occurred_at || event.created_at))}${event.notes ? ` · ${esc(event.notes)}` : ""}</div></div></div>`
              )
              .join("")}</div>`
          : empty("No certification events yet.")
      }
      ${signatures.length ? `<p class="mx-subtitle">${esc(String(signatures.length))} signature record(s).</p>` : ""}
    </article>
    ${
      attachments.length
        ? table(
            ["Kind", "Title", "By", "When"],
            attachments
              .map(
                (att) => `<tr><td>${esc(att.kind || "—")}</td><td>${esc(att.title || att.storage_uri || "—")}</td><td>${esc(att.created_by || "—")}</td><td>${esc(formatTs(att.created_at))}</td></tr>`
              )
              .join("")
          )
        : empty("No attachment metadata.")
    }
  `;
}

export function renderAircraftWorkOrders(session, bundle) {
  const rows = bundle?.workOrders || [];
  if (bundle?.workOrdersLoad && !bundle.workOrdersLoad.ok) {
    return loadBanner(bundle.workOrdersLoad, "Work orders");
  }
  if (!rows.length) return empty("No work orders for this aircraft.");
  return table(
    ["WO", "Title", "Status", "Priority", "Due", "Cards"],
    rows
      .map((order) => `<tr class="we-row-open" data-we-open="workOrder:${esc(String(order.id))}" data-we-label="${esc(order.wo_number || order.id)}">
        <td class="mx-mono">${esc(order.wo_number || order.id)}</td>
        <td>${esc(order.title || "—")}</td>
        <td><span class="mx-chip">${esc(order.status || "—")}</span></td>
        <td>${esc(order.priority || "—")}</td>
        <td>${esc(formatTs(order.due_date))}</td>
        <td>${esc(String(order.job_card_count ?? "—"))}</td>
      </tr>`)
      .join("")
  );
}

export function renderAircraftLogbook(session, bundle) {
  const linked = linkLogbookToWorkOrders(bundle?.logbook || [], bundle?.jobCards || []);
  const canAmend = sessionCanAmendLogbook(role(bundle));
  if (bundle?.logbookLoad && !bundle.logbookLoad.ok) {
    return loadBanner(bundle.logbookLoad, "Technical logbook");
  }
  const list = linked.length
    ? `<div class="mx-timeline">${linked
        .map((entry) => {
          const woBtn = entry.work_order_id
            ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="workOrder:${esc(String(entry.work_order_id))}">Work order</button>`
            : "";
          const cardBtn = entry.job_card_id
            ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="jobCard:${esc(String(entry.job_card_id))}">Job card</button>`
            : "";
          return `<div class="mx-timeline-item" data-we-log="${esc(String(entry.id))}"><div>
            <strong>${esc(entry.summary || entry.id)}</strong>
            <div class="mx-subtitle">${esc(entry.details || "Technical log entry")}</div>
            <div class="mx-timeline-meta">${esc(entry.registration || session.id)} · ${esc(formatTs(entry.occurred_at))} · mechanic ${esc(entry.mechanic_employee_id || "—")} · inspector ${esc(entry.inspector_employee_id || "—")} · ACA ${esc(entry.aca_employee_id || "—")}${entry.release_signature_id ? " · signed" : ""}</div>
            <div class="mx-row" style="gap:8px;margin-top:8px">${woBtn}${cardBtn}</div>
            ${
              canAmend
                ? `<form class="we-ops-amend-form mx-stack" style="margin-top:8px;gap:6px" data-entry-id="${esc(String(entry.id))}">
                    <input class="mx-input" name="summary" maxlength="400" placeholder="Amendment summary (optional)" />
                    <input class="mx-input" name="reason" minlength="3" required placeholder="Amendment reason (min 3 chars)" />
                    <button class="mx-btn mx-btn-sm mx-btn-ghost" type="submit">Amend (append-only)</button>
                  </form>`
                : ""
            }
          </div></div>`;
        })
        .join("")}</div>`
    : empty("No technical log entries for this aircraft. ACA release writes the first entry — there is no create-log API.");
  return `${list}<p class="mx-subtitle" id="weOpsMsg"></p>`;
}

export function renderAircraftMaintenance(session, bundle) {
  const due = filterDueForAircraft(bundle?.due || [], session.id);
  const orders = bundle?.workOrders || [];
  const checks = bundle?.checks || [];
  if (!due.length && !orders.length) {
    return empty("No due items or work orders in this aircraft context.");
  }
  const dueHtml = due.length
    ? due
        .slice(0, 12)
        .map((item) => {
          const related = relatedWorkOrdersForDueItem(item, orders, checks);
          const woBtns = related
            .map(
              (order) =>
                `<button type="button" class="mx-chip" data-we-open="workOrder:${esc(String(order.id))}" data-we-label="${esc(order.wo_number || order.id)}">${esc(order.wo_number || order.id)}</button>`
            )
            .join("");
          const finding =
            String(item.source_type || "").toLowerCase() === "deferred_defect" && item.source_id
              ? `<button type="button" class="mx-chip" data-we-open="finding:${esc(String(item.source_id))}" data-we-label="${esc(item.title || item.source_id)}">${esc(item.title || "Finding")}</button>`
              : "";
          return `<div class="mx-card" style="padding:10px 12px">
            <strong>${esc(item.urgency || "")} · ${esc(item.title || item.task_code || item.id)}</strong>
            <div class="mx-subtitle">${esc(item.source_type || "")} · ${esc(formatTs(item.due_at || item.due_date))}</div>
            <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">${woBtns || '<span class="mx-subtitle">No generated work order</span>'}${finding}</div>
          </div>`;
        })
        .join("")
    : empty("No due / forecast items for this aircraft.");
  return `<div class="mx-stack">${dueHtml}</div>
    <div class="mx-row" style="margin-top:12px;gap:8px">
      <button type="button" class="mx-btn mx-btn-ghost" data-ux2-goto="planning">Return to Planning</button>
      <button type="button" class="mx-btn mx-btn-ghost" data-we-open="aircraft:${esc(session.id)}" data-we-tab="workOrders">Aircraft work orders</button>
    </div>`;
}

function setOpsMessage(text, ok) {
  const node = document.getElementById("weOpsMsg");
  if (!node) return;
  node.textContent = text;
  node.classList.toggle("is-error", !ok);
  node.classList.toggle("is-ok", Boolean(ok));
}

async function runLocked(key, fn) {
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

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

export function bindMaintenanceOpsPanel(active, { onRefresh } = {}) {
  if (!active) return;
  const type = active.type;
  const record = active.record || {};

  document.getElementById("weOpsCreateCardForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManageWorkOrders(role(active.bundle))) {
      setOpsMessage("Work-order manage required.", false);
      return;
    }
    const values = formValues(event.target);
    const payload = {
      work_order_id: record.id,
      title: String(values.title || "").trim(),
      description: String(values.description || ""),
      priority: values.priority || "normal",
    };
    if (values.technician_employee_id) payload.technician_employee_id = values.technician_employee_id;
    const result = await runLocked(`create:${record.id}`, () =>
      softMutate("/work-orders/job-cards", { body: payload })
    );
    if (!result) return;
    if (!result.ok) {
      setOpsMessage(mutationErrorMessage(result), false);
      toast(mutationErrorMessage(result));
      return;
    }
    setOpsMessage(`Created ${result.data?.job_card_number || result.data?.id || ""}`, true);
    toast("Job card created");
    await onRefresh?.({ jobCardId: result.data?.id, workOrderId: record.id, aircraftId: record.aircraft_id });
  });

  document.getElementById("weOpsAssignForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const result = await runLocked(`assign:${record.id}`, () =>
      softMutate(`/work-orders/job-cards/${encodeURIComponent(record.id)}/assign`, {
        body: {
          technician_employee_id: values.technician_employee_id,
          hangar_bay: values.hangar_bay || "",
          expected_version: record.version ?? null,
        },
      })
    );
    if (!result) return;
    if (!result.ok) {
      setOpsMessage(mutationErrorMessage(result), false);
      toast(mutationErrorMessage(result));
      return;
    }
    toast("Technician assigned");
    await onRefresh?.({ jobCardId: record.id, workOrderId: record.work_order_id, aircraftId: record.aircraft_id });
  });

  document.getElementById("weOpsTransitionForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    if (CERT_GATED_STATUSES.includes(values.to_status)) {
      setOpsMessage("Certification-gated status requires complete-work, inspect, or release.", false);
      return;
    }
    const result = await runLocked(`transition:${record.id}`, () =>
      softMutate(`/work-orders/job-cards/${encodeURIComponent(record.id)}/transition`, {
        body: {
          to_status: values.to_status,
          notes: values.notes || "",
          expected_version: record.version ?? null,
        },
      })
    );
    if (!result) return;
    if (!result.ok) {
      setOpsMessage(mutationErrorMessage(result), false);
      toast(mutationErrorMessage(result));
      return;
    }
    toast(`Status ${values.to_status}`);
    await onRefresh?.({ jobCardId: record.id, workOrderId: record.work_order_id, aircraftId: record.aircraft_id });
  });

  const signSubmit = (formId, path, extra) => {
    document.getElementById(formId)?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const values = formValues(event.target);
      const body = {
        employee_id: values.employee_id,
        method: values.method || "password",
        credential: values.credential || null,
        notes: values.notes || "",
        ...extra(values),
      };
      const result = await runLocked(`${formId}:${record.id}`, () =>
        softMutate(`/work-orders/job-cards/${encodeURIComponent(record.id)}/${path}`, { body })
      );
      if (!result) return;
      if (!result.ok) {
        setOpsMessage(mutationErrorMessage(result), false);
        toast(mutationErrorMessage(result));
        return;
      }
      toast("Action recorded");
      await onRefresh?.({ jobCardId: record.id, workOrderId: record.work_order_id, aircraftId: record.aircraft_id });
    });
  };

  signSubmit("weOpsCompleteForm", "complete-work", (values) => ({
    actual_hours: values.actual_hours ? Number(values.actual_hours) : null,
  }));
  signSubmit("weOpsInspectForm", "inspect", (values) => ({ decision: values.decision }));
  signSubmit("weOpsReleaseForm", "release", () => ({}));

  document.querySelectorAll(".we-ops-amend-form").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!sessionCanAmendLogbook(role(active.bundle))) {
        setOpsMessage("maintenance.manage required to amend.", false);
        return;
      }
      const entryId = form.getAttribute("data-entry-id");
      const values = formValues(form);
      const result = await runLocked(`amend:${entryId}`, () =>
        softMutate(`/maintenance/logbook/${encodeURIComponent(entryId)}/amend`, {
          body: { reason: String(values.reason || "").trim(), summary: String(values.summary || "").trim() },
        })
      );
      if (!result) return;
      if (!result.ok) {
        setOpsMessage(mutationErrorMessage(result), false);
        toast(mutationErrorMessage(result));
        return;
      }
      toast("Amendment appended");
      await onRefresh?.({ aircraftId: record.aircraft_id || active.id });
    });
  });
}

export async function fetchWorkOrderDashboard() {
  return softGet("/work-orders/dashboard");
}

export async function fetchPlanningDashboard() {
  return softGet("/planning/dashboard");
}
