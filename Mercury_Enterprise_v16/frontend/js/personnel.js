import { el, esc } from "./utils.js";
import { getSessionStatus } from "./api.js";
import { listify, softGet, softMutate } from "./ux2/api.js";
import { mutationErrorMessage, runLocked } from "./workspace-engine/logistics-ops.js";
import {
  filterEmployees,
  qualificationAlert,
  sessionCanManagePersonnel,
  sessionCanReadPersonnel,
} from "./workspace-engine/personnel-ops.js";

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
  const node = el("persStatus");
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

function renderDesk(canManage) {
  const host = el("persOpsDesk");
  if (!host) return;
  if (!canManage) {
    host.innerHTML = `<p class="muted">Personnel mutations require personnel.manage (Operator or Administrator). Viewer/Reviewer can inspect employees, qualifications, authorizations, and stamps.</p>`;
    return;
  }
  host.innerHTML = `
    <article class="card">
      <h3>Create employee</h3>
      <form data-pers-action="employee">
        <input name="employee_number" required maxlength="80" placeholder="Employee number" />
        <input name="full_name" required maxlength="200" placeholder="Full name" />
        <input name="position_title" maxlength="200" placeholder="Position" />
        <input name="email" maxlength="200" placeholder="Email" />
        <input name="user_username" maxlength="80" placeholder="Linked username (optional)" />
        <select name="status"><option value="active">active</option><option value="inactive">inactive</option><option value="suspended">suspended</option></select>
        <button type="submit">Create employee</button>
      </form>
    </article>
    <p class="muted" id="persOpsMsg"></p>
  `;
}

export async function refreshPersonnelWorkspace() {
  const generation = ++refreshGeneration;
  setStatus("Loading personnel…");
  const session = await getSessionStatus().catch(() => null);
  lastRole = session?.role || "";
  if (!sessionCanReadPersonnel(lastRole) && session?.role) {
    setStatus("Personnel read is not granted for this session.");
  }

  const q = el("persSearch")?.value || "";
  const status = el("persStatusFilter")?.value || "";
  const employees = await softGet("/personnel/employees?limit=100");
  if (generation !== refreshGeneration) return;
  setStatus(employees.ok ? "Live personnel data." : employees.error || `HTTP ${employees.status}`);

  const rows = filterEmployees(listify(employees.data), { q, status });
  renderDesk(sessionCanManagePersonnel(lastRole));

  const kpi = el("persDashKpis");
  if (kpi) {
    const all = listify(employees.data);
    kpi.innerHTML = `
      <article><span>Employees</span><b>${esc(String(all.length))}</b></article>
      <article><span>Active</span><b>${esc(String(all.filter((row) => row.status === "active").length))}</b></article>
      <article><span>Filtered</span><b>${esc(String(rows.length))}</b></article>`;
  }

  const detailBlocks = await Promise.all(
    rows.slice(0, 12).map(async (row) => {
      const [quals, auths, stamps] = await Promise.all([
        softGet(`/personnel/employees/${encodeURIComponent(row.id)}/qualifications`),
        softGet(`/personnel/employees/${encodeURIComponent(row.id)}/authorizations`),
        softGet(`/personnel/employees/${encodeURIComponent(row.id)}/stamps`),
      ]);
      const qualRows = listify(quals.data);
      const alerts = qualRows.map((item) => qualificationAlert(item)).filter((item) => item === "expired" || item === "expiring");
      return { row, stamps: listify(stamps.data), auths: listify(auths.data), alerts };
    })
  );

  renderRows(
    "persEmployees",
    rows
      .map((row) =>
        rowOpen(
          "employee",
          row.id,
          row.full_name || row.employee_number || row.id,
          `<b>${esc(row.employee_number)}</b><span>${esc(row.full_name)} · ${esc(row.position_title || "")}</span><em>${esc(row.status)}</em>`
        )
      )
      .join(""),
    employees.ok ? "No employees." : employees.error || "Employees unavailable"
  );

  renderRows(
    "persAlerts",
    detailBlocks
      .filter((item) => item.alerts.length)
      .map(
        (item) =>
          `<div class="contact-row"><b>${esc(item.row.employee_number)}</b><span>${esc(item.row.full_name)} · ${esc(item.alerts.join(", "))}</span>
            <button type="button" class="ghost small" data-we-open="employee:${esc(item.row.id)}">Open</button></div>`
      )
      .join(""),
    "No expiring or expired qualifications in the loaded set."
  );

  renderRows(
    "persStamps",
    detailBlocks
      .flatMap((item) =>
        item.stamps.map(
          (stamp) =>
            `<div class="contact-row"><b>${esc(stamp.stamp_code)}</b><span>${esc(item.row.full_name)} · ${esc(stamp.label || "")}</span><em>${esc(stamp.status)}</em>
              <div><button type="button" class="ghost small" data-we-open="employee:${esc(item.row.id)}">Employee</button></div></div>`
        )
      )
      .join(""),
    "No stamp profiles in the loaded set."
  );
}

async function handleDeskSubmit(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  const msg = el("persOpsMsg");
  const fail = (result) => {
    const text = mutationErrorMessage(result);
    if (msg) msg.textContent = text;
    toast(text);
  };
  const body = {
    employee_number: values.employee_number,
    full_name: String(values.full_name || "").trim(),
    position_title: values.position_title || "",
    email: values.email || "",
    status: values.status || "active",
  };
  if (values.user_username) body.user_username = values.user_username;
  const result = await runLocked(`emp:${body.employee_number}`, () => softMutate("/personnel/employees", { body }));
  if (!result) return;
  if (!result.ok) return fail(result);
  if (msg) msg.textContent = `Created ${result.data?.employee_number || ""}`;
  toast("Employee created");
  await refreshPersonnelWorkspace();
}

export function initializePersonnel() {
  el("persRefresh")?.addEventListener("click", () => refreshPersonnelWorkspace());
  el("persApplyFilters")?.addEventListener("click", () => refreshPersonnelWorkspace());
  el("persSearch")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") refreshPersonnelWorkspace();
  });
  el("personnelWorkspace")?.addEventListener("submit", (event) => {
    const form = event.target?.closest?.("[data-pers-action]");
    if (!form) return;
    event.preventDefault();
    handleDeskSubmit(form);
  });
}
