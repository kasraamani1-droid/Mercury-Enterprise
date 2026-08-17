import { el, esc } from "./utils.js";
import {
  listWorkPackages,
  listWorkOrders,
  listJobCards,
  createWorkPackage,
  getWorkOrderDashboard,
  getWorkOrderReport,
  transitionJobCard,
  assignJobCard,
  completeJobCardWork,
  inspectJobCard,
  releaseJobCard,
  addJobCardAttachment,
  listEmployees,
  listPublications,
} from "./api.js";

const OFFLINE_QUEUE_KEY = "mercury.maintenance.offlineQueue";
const BAYS = ["Bay-1", "Bay-2", "Bay-3", "Bay-4"];

function readOfflineQueue() {
  try {
    return JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || "[]");
  } catch {
    return [];
  }
}

function writeOfflineQueue(items) {
  localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(items.slice(-100)));
}

export function enqueueOfflineAction(action) {
  const q = readOfflineQueue();
  q.push({ ...action, queuedAt: new Date().toISOString() });
  writeOfflineQueue(q);
  renderOfflineQueue();
}

async function flushOfflineQueue() {
  if (!navigator.onLine) return;
  const q = readOfflineQueue();
  if (!q.length) return;
  const remaining = [];
  for (const item of q) {
    try {
      if (item.type === "transition") {
        const target = item.payload?.to_status;
        // Never sync certification-gated statuses via bare transition.
        if (["waiting_inspection", "completed", "released"].includes(target)) {
          remaining.push(item);
          continue;
        }
        if (target === "in_progress") {
          try {
            await transitionJobCard(item.jobCardId, { to_status: "accepted" });
          } catch {
            /* already accepted */
          }
        }
        await transitionJobCard(item.jobCardId, item.payload);
      } else if (item.type === "complete") {
        await completeJobCardWork(item.jobCardId, item.payload);
      } else if (item.type === "note" || item.type === "photo") {
        await addJobCardAttachment(item.jobCardId, item.payload);
      }
    } catch {
      remaining.push(item);
    }
  }
  writeOfflineQueue(remaining);
  renderOfflineQueue();
}

function renderOfflineQueue() {
  const host = el("mroOfflineQueue");
  if (!host) return;
  const q = readOfflineQueue();
  host.innerHTML = q.length
    ? q.map((i) => `<div class="contact-row"><b>${esc(i.type)}</b><span>${esc(i.jobCardId || "")}</span><em>${esc(i.queuedAt || "")}</em></div>`).join("")
    : `<div class="empty">Offline queue empty — ready for hangar sync.</div>`;
}

function toast(msg) {
  const t = el("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2800);
}

async function ensureStartable(jobCardId) {
  // Assigned → Accepted → In Progress (validated matrix).
  try {
    await transitionJobCard(jobCardId, { to_status: "accepted" });
  } catch {
    /* already accepted / in progress */
  }
  await transitionJobCard(jobCardId, { to_status: "in_progress" });
}

async function refreshPlanner() {
  const packages = await listWorkPackages({ limit: 50 });
  const host = el("mroPackageList");
  if (host) {
    host.innerHTML = packages.length
      ? packages
          .map(
            (p) =>
              `<div class="contact-row" draggable="true" data-package="${esc(p.id)}" data-bay="${esc(p.hangar_bay || "")}">
                <b>${esc(p.package_number)}</b>
                <span>${esc(p.registration || p.aircraft_id)} · ${esc(p.status)} · ${esc(p.shift_code || "—")}</span>
                <em>${esc(p.priority)}</em>
              </div>`
          )
          .join("")
      : `<div class="empty">No work packages.</div>`;
  }
  const bayHost = el("mroBayBoard");
  if (bayHost) {
    bayHost.innerHTML = BAYS.map((bay) => {
      const inBay = packages.filter((p) => (p.hangar_bay || "") === bay);
      return `<div class="bay-slot" data-bay="${esc(bay)}">
        <strong>${esc(bay)}</strong>
        ${
          inBay.length
            ? inBay.map((p) => `<div class="contact-row"><b>${esc(p.package_number)}</b><span>${esc(p.registration || "")}</span></div>`).join("")
            : `<div class="empty">Drop package / assign bay</div>`
        }
      </div>`;
    }).join("");
  }
  const orders = await listWorkOrders({ limit: 50 });
  const oh = el("mroOrderList");
  if (oh) {
    oh.innerHTML = orders.length
      ? orders
          .map(
            (o) =>
              `<div class="contact-row"><b>${esc(o.wo_number)}</b><span>${esc(o.title)} · ${esc(o.status)}</span><em>${esc(String(o.job_card_count))} cards</em></div>`
          )
          .join("")
      : `<div class="empty">No work orders.</div>`;
  }
}

async function refreshTechnician(employeeId) {
  const cards = await listJobCards({
    technician_employee_id: employeeId || undefined,
    limit: 100,
  });
  const host = el("mroTechCards");
  if (!host) return;
  host.innerHTML = cards.length
    ? cards
        .map(
          (c) => `<div class="contact-row" data-card="${esc(c.id)}">
            <b>${esc(c.job_card_number)}</b>
            <span>${esc(c.title)} · ${esc(c.status)} · ${esc(c.hangar_bay || "Bay —")}</span>
            <em>
              <button class="ghost small" data-act="start" data-id="${esc(c.id)}">Start</button>
              <button class="ghost small" data-act="pause" data-id="${esc(c.id)}">Pause</button>
              <button class="ghost small" data-act="resume" data-id="${esc(c.id)}">Resume</button>
              <button class="ghost small" data-act="parts" data-id="${esc(c.id)}">Parts</button>
              <button class="ghost small" data-act="eng" data-id="${esc(c.id)}">Engineering</button>
              <button class="ghost small" data-act="complete" data-id="${esc(c.id)}">Complete</button>
            </em>
          </div>`
        )
        .join("")
    : `<div class="empty">No assigned job cards.</div>`;
}

async function refreshSupervisor() {
  const cards = await listJobCards({ limit: 100 });
  const host = el("mroSupervisorBoard");
  if (!host) return;
  host.innerHTML = cards.length
    ? cards
        .map(
          (c) =>
            `<div class="contact-row" data-fill-assign="${esc(c.id)}" data-tech="${esc(c.technician_employee_id || "")}">
              <b>${esc(c.job_card_number)}</b>
              <span>${esc(c.status)} · tech ${esc(c.technician_employee_id || "unassigned")} · ${esc(c.hangar_bay || "—")}</span>
              <em>${esc(c.priority)}</em>
            </div>`
        )
        .join("")
    : `<div class="empty">No job cards.</div>`;
}

async function refreshQaAca() {
  const waiting = await listJobCards({ status: "waiting_inspection", limit: 100 });
  const completed = await listJobCards({ status: "completed", limit: 100 });
  const qa = el("mroQaQueue");
  if (qa) {
    const iiPending = completed.filter((c) => c.independent_inspection_required && !c.independent_inspector_employee_id);
    const qaRows = [
      ...waiting.map(
        (c) =>
          `<div class="contact-row"><b>${esc(c.job_card_number)}</b><span>${esc(c.title)}${c.independent_inspection_required ? " · II req" : ""}</span><em>
            <button class="ghost small" data-qa="approve" data-id="${esc(c.id)}">Approve</button>
            <button class="ghost small" data-qa="rework" data-id="${esc(c.id)}">Rework</button>
            <button class="ghost small" data-qa="reject" data-id="${esc(c.id)}">Reject</button>
          </em></div>`
      ),
      ...iiPending.map(
        (c) =>
          `<div class="contact-row"><b>${esc(c.job_card_number)}</b><span>${esc(c.title)} · awaiting independent</span><em>
            <button class="ghost small" data-qa="independent_inspection" data-id="${esc(c.id)}">Independent</button>
          </em></div>`
      ),
    ];
    qa.innerHTML = qaRows.length ? qaRows.join("") : `<div class="empty">No cards waiting inspection.</div>`;
  }
  const aca = el("mroAcaQueue");
  if (aca) {
    aca.innerHTML = completed.length
      ? completed
          .map(
            (c) =>
              `<div class="contact-row"><b>${esc(c.job_card_number)}</b><span>${esc(c.title)}</span><em><button class="ghost small" data-aca="release" data-id="${esc(c.id)}">Release</button></em></div>`
          )
          .join("")
      : `<div class="empty">No cards awaiting ACA release.</div>`;
  }
}

async function refreshDashboards() {
  const roles = ["manager", "planner", "supervisor", "technician", "qa", "aca"];
  for (const role of roles) {
    const dash = await getWorkOrderDashboard({ role });
    const host = el(`mroDash_${role}`);
    if (!host) continue;
    host.innerHTML = `
      <div><span>Open WOs</span><b>${dash.open_work_orders}</b></div>
      <div><span>Delayed</span><b>${dash.delayed_work_orders}</b></div>
      <div><span>Awaiting inspection</span><b>${dash.awaiting_inspection}</b></div>
      <div><span>Awaiting release</span><b>${dash.awaiting_release}</b></div>`;
  }
}

async function refreshReports() {
  const key = el("mroReportSelect")?.value || "open_work_orders";
  const report = await getWorkOrderReport(key);
  const host = el("mroReportBody");
  if (!host) return;
  host.innerHTML = report.rows.length
    ? report.rows
        .map((r) => {
          const a = r.wo_number || r.job_card_number || r.package_number || r.technician_employee_id || r.aircraft_id || "—";
          const b = r.title || r.registration || r.estimated_hours || r.cards || "—";
          const c = r.status || r.actual_hours || "—";
          const d = r.priority || r.hangar_bay || r.actual_hours || "";
          return `<tr><td>${esc(String(a))}</td><td>${esc(String(b))}</td><td>${esc(String(c))}</td><td>${esc(String(d))}</td></tr>`;
        })
        .join("")
    : `<tr><td colspan="4">No rows for ${esc(key)}.</td></tr>`;
}

async function refreshLibraryShortcuts() {
  const pubs = await listPublications({ limit: 40 });
  const host = el("mroLibraryShortcuts");
  if (!host) return;
  const wanted = new Set(["AMM", "IPC", "AIPC", "WDM", "FIM", "CMM", "SRM", "SDM", "TSM"]);
  const rows = pubs.filter((p) => wanted.has(p.publication_code));
  host.innerHTML = rows.length
    ? rows
        .map(
          (p) =>
            `<div class="contact-row"><b>${esc(p.publication_code)}</b><span>${esc(p.title)}</span><em>Rev ${esc(p.current_revision_number || "—")}</em></div>`
        )
        .join("")
    : `<div class="empty">Library publications load after sign-in.</div>`;
}

export async function refreshMaintenanceWorkspace() {
  try {
    await flushOfflineQueue();
    const employees = await listEmployees();
    const tech = employees.find((e) => e.employee_number === "E-1001");
    if (el("mroTechEmployeeId")) el("mroTechEmployeeId").value = tech?.id || "";
    await Promise.allSettled([
      refreshPlanner(),
      refreshTechnician(tech?.id),
      refreshSupervisor(),
      refreshQaAca(),
      refreshDashboards(),
      refreshReports(),
      refreshLibraryShortcuts(),
    ]);
    renderOfflineQueue();
  } catch (error) {
    toast(error.message || "Unable to refresh maintenance workspace");
  }
}

export function initializeMaintenance() {
  window.addEventListener("online", () => flushOfflineQueue());
  el("mroRefresh")?.addEventListener("click", () => refreshMaintenanceWorkspace());
  el("mroReportSelect")?.addEventListener("change", () => refreshReports());

  el("mroCreatePackageForm")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      await createWorkPackage({
        aircraft_id: el("mroPkgAircraft")?.value?.trim(),
        description: el("mroPkgDesc")?.value?.trim(),
        hangar_bay: el("mroPkgBay")?.value?.trim() || "",
        shift_code: el("mroPkgShift")?.value?.trim() || "",
        priority: "high",
      });
      await refreshMaintenanceWorkspace();
      toast("Work package created");
    } catch (error) {
      toast(error.message || "Create package failed");
    }
  });

  el("mroTechCards")?.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button[data-act]");
    if (!btn) return;
    const id = btn.dataset.id;
    const act = btn.dataset.act;
    const employeeId = el("mroTechEmployeeId")?.value;
    const credential = el("mroCredential")?.value || "";
    try {
      if (!navigator.onLine) {
        if (act === "complete") {
          enqueueOfflineAction({
            type: "complete",
            jobCardId: id,
            payload: {
              employee_id: employeeId,
              method: "password",
              credential,
              notes: "Completed offline — synced on reconnect",
            },
          });
          toast("Complete queued offline — will sync with signature");
          return;
        }
        const statusMap = {
          start: "in_progress",
          pause: "paused",
          resume: "in_progress",
          parts: "waiting_parts",
          eng: "waiting_engineering",
        };
        enqueueOfflineAction({
          type: "transition",
          jobCardId: id,
          payload: { to_status: statusMap[act] || "in_progress" },
        });
        toast("Queued offline — will sync when online");
        return;
      }
      if (act === "start" || act === "resume") await ensureStartable(id);
      if (act === "pause") await transitionJobCard(id, { to_status: "paused" });
      if (act === "parts") await transitionJobCard(id, { to_status: "waiting_parts" });
      if (act === "eng") await transitionJobCard(id, { to_status: "waiting_engineering" });
      if (act === "complete") {
        await completeJobCardWork(id, {
          employee_id: employeeId,
          method: "password",
          credential,
          notes: "Completed from technician UI",
        });
      }
      await refreshMaintenanceWorkspace();
      toast("Job card updated");
    } catch (error) {
      toast(error.message || "Action failed");
    }
  });

  el("mroQaQueue")?.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button[data-qa]");
    if (!btn) return;
    const employees = await listEmployees();
    const inspector = employees.find((e) => e.employee_number === "E-2001") || employees[0];
    const independent = employees.find((e) => e.employee_number === "E-3001") || inspector;
    const credential = el("mroCredential")?.value || "";
    const decision = btn.dataset.qa;
    try {
      await inspectJobCard(btn.dataset.id, {
        employee_id: decision === "independent_inspection" ? independent.id : inspector.id,
        method: "password",
        credential,
        decision,
        notes:
          decision === "approve"
            ? "QA approved"
            : decision === "rework"
              ? "Rework required"
              : decision === "reject"
                ? "Rejected"
                : "Independent inspection complete",
      });
      await refreshMaintenanceWorkspace();
      toast("Inspection recorded");
    } catch (error) {
      toast(error.message || "Inspection failed");
    }
  });

  el("mroAcaQueue")?.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button[data-aca]");
    if (!btn) return;
    const employees = await listEmployees();
    const aca = employees.find((e) => e.employee_number === "E-2001") || employees[0];
    const credential = el("mroCredential")?.value || "";
    try {
      await releaseJobCard(btn.dataset.id, {
        employee_id: aca.id,
        method: "password",
        credential,
        notes: "ACA release from UI",
      });
      await refreshMaintenanceWorkspace();
      toast("Aircraft / job card released");
    } catch (error) {
      toast(error.message || "Release failed");
    }
  });

  el("mroAssignForm")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const jobCardId = el("mroAssignCardId")?.value?.trim();
    const techId = el("mroAssignTechId")?.value?.trim();
    const bay = el("mroAssignBay")?.value?.trim() || "";
    if (!jobCardId || !techId) return toast("Job card and technician required");
    try {
      await assignJobCard(jobCardId, { technician_employee_id: techId, hangar_bay: bay });
      await refreshMaintenanceWorkspace();
      toast("Assigned");
    } catch (error) {
      toast(error.message || "Assign failed");
    }
  });

  el("mroSupervisorBoard")?.addEventListener("click", (ev) => {
    const row = ev.target.closest("[data-fill-assign]");
    if (!row) return;
    if (el("mroAssignCardId")) el("mroAssignCardId").value = row.dataset.fillAssign || "";
    if (el("mroAssignTechId") && row.dataset.tech) el("mroAssignTechId").value = row.dataset.tech;
  });

  el("mroAddNote")?.addEventListener("click", async () => {
    const jobCardId = el("mroNoteCardId")?.value?.trim();
    const notes = el("mroNoteText")?.value?.trim();
    if (!jobCardId || !notes) return toast("Card and note required");
    const payload = { kind: "note", title: "Technician note", notes };
    try {
      if (!navigator.onLine) {
        enqueueOfflineAction({ type: "note", jobCardId, payload });
        toast("Note queued offline");
        return;
      }
      await addJobCardAttachment(jobCardId, payload);
      toast("Note saved");
    } catch (error) {
      toast(error.message || "Note failed");
    }
  });

  el("mroAddPhoto")?.addEventListener("click", async () => {
    const jobCardId = el("mroNoteCardId")?.value?.trim();
    const uri = el("mroNoteText")?.value?.trim();
    if (!jobCardId || !uri) return toast("Card id and photo URI required");
    const payload = { kind: "photo", title: "Hangar photo", storage_uri: uri, content_type: "image/jpeg" };
    try {
      if (!navigator.onLine) {
        enqueueOfflineAction({ type: "photo", jobCardId, payload });
        toast("Photo queued offline");
        return;
      }
      await addJobCardAttachment(jobCardId, payload);
      toast("Photo attachment saved");
    } catch (error) {
      toast(error.message || "Photo failed");
    }
  });

  // Lightweight hangar bay DnD: drag package row → bay slot updates assign bay via toast guidance.
  let dragPackageId = null;
  el("mroPackageList")?.addEventListener("dragstart", (ev) => {
    const row = ev.target.closest("[data-package]");
    if (!row) return;
    dragPackageId = row.dataset.package;
    ev.dataTransfer?.setData("text/plain", dragPackageId);
  });
  el("mroBayBoard")?.addEventListener("dragover", (ev) => {
    if (ev.target.closest(".bay-slot")) ev.preventDefault();
  });
  el("mroBayBoard")?.addEventListener("drop", (ev) => {
    const slot = ev.target.closest(".bay-slot");
    if (!slot || !dragPackageId) return;
    ev.preventDefault();
    toast(`Bay ${slot.dataset.bay}: set hangar_bay on assign / package planning for ${dragPackageId}`);
    if (el("mroAssignBay")) el("mroAssignBay").value = slot.dataset.bay || "";
    dragPackageId = null;
  });
}
