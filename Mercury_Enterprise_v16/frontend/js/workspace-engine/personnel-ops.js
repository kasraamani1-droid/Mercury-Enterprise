/**
 * Personnel qualifications / authorizations / stamps operator UI.
 * Uses existing /api/v1/personnel routes. Does not invent certification rules.
 */

import { esc, toast } from "../utils.js";
import { softMutate } from "../ux2/api.js";
import { mutationErrorMessage, runLocked } from "./logistics-ops.js";

export function normalizeRole(role) {
  return String(role || "").trim();
}

export function sessionCanReadPersonnel(role) {
  const value = normalizeRole(role);
  return value === "Viewer" || value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function sessionCanManagePersonnel(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Administrator";
}

export function filterEmployees(rows, { q = "", status = "" } = {}) {
  const query = String(q || "").trim().toLowerCase();
  const st = String(status || "").trim().toLowerCase();
  return (Array.isArray(rows) ? rows : []).filter((row) => {
    if (st && String(row.status || "").toLowerCase() !== st) return false;
    if (!query) return true;
    const hay = `${row.employee_number || ""} ${row.full_name || ""} ${row.position_title || ""} ${row.email || ""} ${row.user_username || ""} ${row.id || ""}`.toLowerCase();
    return hay.includes(query);
  });
}

export function qualificationAlert(row, nowMs = Date.now()) {
  if (!row?.expires_at) return "none";
  const exp = Date.parse(row.expires_at);
  if (!Number.isFinite(exp)) return "none";
  if (exp < nowMs) return "expired";
  if (exp < nowMs + 30 * 86400000) return "expiring";
  return "ok";
}

export function personnelOpsCacheKeys(session, mutation = {}) {
  const employees = [];
  const workOrders = [];
  const jobCards = [];
  const push = (list, value) => {
    const id = String(value || "").trim();
    if (id && !list.includes(id)) list.push(id);
  };
  if (session?.type === "employee") push(employees, session.id);
  push(employees, mutation.employeeId);
  push(workOrders, mutation.workOrderId);
  push(jobCards, mutation.jobCardId);
  return { employees, workOrders, jobCards };
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

export function employeeChip(row) {
  if (!row?.id) return "";
  return `<button type="button" class="mx-chip" data-we-open="employee:${esc(String(row.id))}" data-we-label="${esc(row.full_name || row.employee_number || row.id)}">${esc(row.employee_number || "")} ${esc(row.full_name || "")}</button>`;
}

export function renderEmployeeWorkspace(session, record, bundle) {
  const row = record || {};
  const canManage = sessionCanManagePersonnel(role(bundle));
  const quals = bundle?.qualifications || [];
  const auths = bundle?.authorizations || [];
  const stamps = bundle?.stamps || [];
  return `
    ${loadBanner(bundle?.recordLoad, "Employee")}
    ${loadBanner(bundle?.stampsLoad, "Stamps")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(row.full_name || session.id)}</h3><span class="mx-chip">${esc(row.status || "—")}</span></div>
      <p class="mx-subtitle">${esc(row.employee_number || "")} · ${esc(row.position_title || "")} · ${esc(row.email || "")}</p>
      <p class="mx-subtitle">Linked username ${esc(row.user_username || "—")}. Stamp/qualification checks for inspect/release stay on job-card certification APIs.</p>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">
        <button type="button" class="mx-chip" data-ux2-goto="personnel">Personnel</button>
        <button type="button" class="mx-chip" data-ux2-goto="workOrders">Work Orders</button>
        <button type="button" class="mx-chip" data-ux2-goto="maintenance">MRO Execution</button>
      </div>
    </article>
    <article class="mx-card" style="margin-top:12px">
      <div class="mx-card-header"><h3>Qualifications</h3></div>
      ${
        quals.length
          ? table(
              ["Type", "Code", "Authority", "Expires", "Status"],
              quals
                .map((item) => {
                  const alert = qualificationAlert(item);
                  return `<tr>
                    <td>${esc(item.qualification_type || "—")}</td>
                    <td class="mx-mono">${esc(item.code || "—")}</td>
                    <td>${esc(item.authority || "—")}</td>
                    <td>${esc(String(item.expires_at || "—").slice(0, 10))}${alert !== "none" && alert !== "ok" ? ` · ${esc(alert)}` : ""}</td>
                    <td><span class="mx-chip">${esc(item.status || "—")}</span></td>
                  </tr>`;
                })
                .join("")
            )
          : empty("No qualifications.")
      }
    </article>
    <article class="mx-card" style="margin-top:12px">
      <div class="mx-card-header"><h3>Authorizations</h3></div>
      ${
        auths.length
          ? table(
              ["Type", "Scope", "Expires", "Status"],
              auths
                .map(
                  (item) => `<tr>
                    <td>${esc(item.auth_type || "—")}</td>
                    <td>${esc(item.scope || "—")}</td>
                    <td>${esc(String(item.expires_at || "—").slice(0, 10))}</td>
                    <td><span class="mx-chip">${esc(item.status || "—")}</span></td>
                  </tr>`
                )
                .join("")
            )
          : empty("No authorizations.")
      }
    </article>
    <article class="mx-card" style="margin-top:12px">
      <div class="mx-card-header"><h3>Digital stamps</h3></div>
      <p class="mx-subtitle">Rotate by creating a new profile. Prior rows remain; this UI does not invent retirement rules beyond stored status.</p>
      ${
        stamps.length
          ? table(
              ["Code", "Label", "Status"],
              stamps
                .map(
                  (item) => `<tr>
                    <td class="mx-mono">${esc(item.stamp_code || "—")}</td>
                    <td>${esc(item.label || "—")}</td>
                    <td><span class="mx-chip">${esc(item.status || "—")}</span></td>
                  </tr>`
                )
                .join("")
            )
          : empty("No stamp profiles.")
      }
    </article>
    ${
      canManage
        ? `<div class="enterprise-grid" style="margin-top:12px">
            <form id="wePersQualForm" class="mx-card" style="padding:12px">
              <strong>Add qualification</strong>
              <input type="hidden" name="employee_id" value="${esc(String(row.id || session.id))}" />
              <label class="mx-field">Type<select class="mx-input" name="qualification_type">
                <option value="ame_license">ame_license</option>
                <option value="rating">rating</option>
                <option value="type_rating">type_rating</option>
                <option value="aca">aca</option>
                <option value="training">training</option>
                <option value="other">other</option>
              </select></label>
              <label class="mx-field">Code<input class="mx-input" name="code" maxlength="80" /></label>
              <label class="mx-field">Description<input class="mx-input" name="description" maxlength="300" /></label>
              <label class="mx-field">Authority<input class="mx-input" name="authority" maxlength="120" /></label>
              <button class="mx-btn" type="submit">Create qualification</button>
            </form>
            <form id="wePersAuthForm" class="mx-card" style="padding:12px">
              <strong>Add authorization</strong>
              <input type="hidden" name="employee_id" value="${esc(String(row.id || session.id))}" />
              <label class="mx-field">Type<select class="mx-input" name="auth_type">
                <option value="aca">aca</option>
                <option value="independent_inspection">independent_inspection</option>
                <option value="stamp">stamp</option>
              </select></label>
              <label class="mx-field">Scope<input class="mx-input" name="scope" maxlength="200" /></label>
              <button class="mx-btn" type="submit">Create authorization</button>
            </form>
            <form id="wePersStampForm" class="mx-card" style="padding:12px">
              <strong>Add stamp profile</strong>
              <input type="hidden" name="employee_id" value="${esc(String(row.id || session.id))}" />
              <label class="mx-field">Stamp code<input class="mx-input" name="stamp_code" required maxlength="80" /></label>
              <label class="mx-field">Label<input class="mx-input" name="label" maxlength="200" /></label>
              <button class="mx-btn" type="submit">Create stamp</button>
            </form>
          </div>`
        : `<p class="mx-subtitle">Create qualification/authorization/stamp requires personnel.manage (Operator or Administrator).</p>`
    }
    <p class="mx-subtitle" id="wePersMsg"></p>
  `;
}

export function renderJobCardPersonnelBridge(session, record, bundle) {
  const employees = bundle?.employees || [];
  const byId = Object.fromEntries(employees.map((row) => [String(row.id), row]));
  const ids = [record?.technician_employee_id, record?.inspector_employee_id, record?.aca_employee_id].filter(Boolean);
  const chips = ids
    .map((id) => byId[String(id)] || { id, employee_number: id, full_name: "" })
    .map((row) => employeeChip(row))
    .join("");
  return `<article class="mx-card" style="margin-top:12px">
    <div class="mx-card-header"><h3>Personnel context</h3></div>
    <p class="mx-subtitle">Assigned people open employee objects. Inspect/release still use job-card certification APIs — this panel does not grant extra authority.</p>
    <div class="mx-row" style="flex-wrap:wrap;gap:8px">${chips || `<span class="mx-subtitle">No assigned employees on this card.</span>`}</div>
    <button type="button" class="mx-chip" style="margin-top:8px" data-ux2-goto="personnel">Personnel desk</button>
  </article>`;
}

function setPersMessage(text, ok) {
  const node = document.getElementById("wePersMsg") || document.getElementById("persOpsMsg");
  if (!node) return;
  node.textContent = text || "";
  node.style.color = ok ? "" : "var(--danger, #c44)";
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

export function bindPersonnelOpsPanel(active, { onRefresh } = {}) {
  if (!active) return;
  const fail = (result) => {
    const msg = mutationErrorMessage(result);
    setPersMessage(msg, false);
    toast(msg);
  };

  document.getElementById("wePersQualForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManagePersonnel(role(active.bundle))) return fail({ status: 403, error: "personnel.manage required" });
    const values = formValues(event.target);
    const body = {
      qualification_type: values.qualification_type,
      code: values.code || "",
      description: values.description || "",
      authority: values.authority || "",
    };
    const result = await runLocked(`qual:${values.employee_id}`, () =>
      softMutate(`/personnel/employees/${encodeURIComponent(values.employee_id)}/qualifications`, { body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Qualification created");
    await onRefresh?.({ employeeId: values.employee_id });
  });

  document.getElementById("wePersAuthForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const result = await runLocked(`auth:${values.employee_id}`, () =>
      softMutate(`/personnel/employees/${encodeURIComponent(values.employee_id)}/authorizations`, {
        body: { auth_type: values.auth_type, scope: values.scope || "" },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Authorization created");
    await onRefresh?.({ employeeId: values.employee_id });
  });

  document.getElementById("wePersStampForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const result = await runLocked(`stamp:${values.employee_id}`, () =>
      softMutate(`/personnel/employees/${encodeURIComponent(values.employee_id)}/stamps`, {
        body: { stamp_code: values.stamp_code, label: values.label || "" },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Stamp profile created");
    await onRefresh?.({ employeeId: values.employee_id });
  });
}
