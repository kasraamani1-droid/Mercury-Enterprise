import { esc, toast } from "../utils.js";
import {
  listify,
  softGet,
  uxAddMarketplaceCart,
  uxApproveRequest,
  uxCreateAircraft,
  uxCreateMarketplaceQuote,
  uxFetchAds,
  uxFetchApprovals,
  uxFetchAuthority,
  uxFetchEngineeringOrders,
  uxFetchEventCatalog,
  uxFetchEventDlq,
  uxFetchEventSubscriptions,
  uxFetchFleetAircraft,
  uxFetchFleetModels,
  uxFetchFleets,
  uxFetchFleetStatuses,
  uxFetchLogbook,
  uxFetchLogisticsDashboard,
  uxFetchMarketplaceCart,
  uxFetchMarketplaceProducts,
  uxFetchMarketplaceQuotes,
  uxFetchOrgTree,
  uxFetchPlanningDashboard,
  uxFetchPlanningDue,
  uxFetchPluginInstallations,
  uxFetchPlugins,
  uxFetchPlatformNotifications,
  uxFetchServiceBulletins,
  uxFetchTwins,
  uxFetchWorkOrderDashboard,
  uxFetchWorkOrders,
} from "./api.js";
import {
  createWorkOrder,
  createWorkPackage,
  getDashboardSummary,
  getHealth,
  getSessionStatus,
  listWorkPackages,
} from "../api.js";
import { sessionCanManageWorkOrders } from "../workspace-engine/maintenance-ops.js";
import { qtyAvailable } from "../workspace-engine/logistics-ops.js";
import { refreshLogisticsWorkspace } from "../logistics.js";
import { refreshPlanningWorkspace } from "../planning.js";
import { refreshTechLibraryWorkspace } from "../library.js";
import { refreshPersonnelWorkspace } from "../personnel.js";

function setHtml(id, html) {
  const node = document.getElementById(id);
  if (node) node.innerHTML = html;
}

function rowsFrom(items, mapFn) {
  if (!items.length) return `<div class="mx-empty">No records yet.</div>`;
  return items.map(mapFn).join("");
}

function table(headers, bodyHtml) {
  return `<div class="mx-table-wrap"><table class="mx-table"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${bodyHtml}</tbody></table></div>`;
}

function filterSortSearch(items, { q = "", statusKey = "status", status = "", sortKey = "", sortDir = "asc" } = {}) {
  let out = [...items];
  const query = String(q || "")
    .trim()
    .toLowerCase();
  if (query) {
    out = out.filter((row) => JSON.stringify(row).toLowerCase().includes(query));
  }
  if (status) {
    out = out.filter((row) => String(row[statusKey] || row.status_code || "").toLowerCase() === status.toLowerCase());
  }
  if (sortKey) {
    out.sort((a, b) => {
      const av = String(a[sortKey] ?? "");
      const bv = String(b[sortKey] ?? "");
      return sortDir === "desc" ? bv.localeCompare(av) : av.localeCompare(bv);
    });
  }
  return out;
}

function toolbarHtml(idPrefix, { searchPlaceholder = "Search…", statuses = [], sorts = [] } = {}) {
  const statusOpts = [`<option value="">All status</option>`, ...statuses.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`)].join(
    ""
  );
  const sortOpts = sorts.map((s) => `<option value="${esc(s.value)}">${esc(s.label)}</option>`).join("");
  return `<div class="ux2-toolbar mx-row" style="gap:8px;flex-wrap:wrap;margin-bottom:12px">
    <input class="mx-input" id="${idPrefix}Search" placeholder="${esc(searchPlaceholder)}" style="min-width:180px;flex:1" />
    <select class="mx-input" id="${idPrefix}Status" style="max-width:160px">${statusOpts}</select>
    <select class="mx-input" id="${idPrefix}Sort" style="max-width:180px">${sortOpts || '<option value="">Default sort</option>'}</select>
    <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" id="${idPrefix}Apply">Apply</button>
  </div>`;
}

function bindToolbar(idPrefix, onApply) {
  const apply = () => {
    const q = document.getElementById(`${idPrefix}Search`)?.value || "";
    const status = document.getElementById(`${idPrefix}Status`)?.value || "";
    const sort = document.getElementById(`${idPrefix}Sort`)?.value || "";
    const [sortKey, sortDir] = sort.includes(":") ? sort.split(":") : [sort, "asc"];
    onApply({ q, status, sortKey, sortDir });
  };
  document.getElementById(`${idPrefix}Apply`)?.addEventListener("click", apply);
  document.getElementById(`${idPrefix}Search`)?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") apply();
  });
}

function kpiValue(ok, value, fallback = "unavailable") {
  if (!ok) return fallback;
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export async function refreshHomeWorkspace() {
  const [health, dash, notes, due, woDash, planDash, approvals, logDash] = await Promise.all([
    getHealth().catch(() => null),
    getDashboardSummary().catch(() => null),
    uxFetchPlatformNotifications(),
    uxFetchPlanningDue(),
    uxFetchWorkOrderDashboard(),
    uxFetchPlanningDashboard(),
    uxFetchApprovals(),
    uxFetchLogisticsDashboard(),
  ]);
  setHtml("homeKpiHealth", health?.status || "unavailable");
  setHtml("homeKpiAlerts", dash ? String(dash.active_alerts ?? dash.alerts?.active ?? "—") : "unavailable");
  setHtml("homeKpiMissions", dash ? String(dash.active_missions ?? dash.missions?.active ?? "—") : "unavailable");
  setHtml("homeKpiDecisions", dash ? String(dash.pending_decisions ?? dash.decisions?.pending_human_review ?? "—") : "unavailable");
  setHtml("homeKpiOpenWo", kpiValue(woDash.ok, woDash.data?.open_work_orders));
  setHtml("homeKpiDelayedWo", kpiValue(woDash.ok, woDash.data?.delayed_work_orders));
  setHtml("homeKpiInspect", kpiValue(woDash.ok, woDash.data?.awaiting_inspection));
  setHtml("homeKpiRelease", kpiValue(woDash.ok, woDash.data?.awaiting_release));
  const hint = document.getElementById("homeKpiMroHint");
  if (hint) hint.textContent = woDash.ok ? "Live work-order dashboard" : woDash.error || "Work-order dashboard unavailable";
  setHtml("homeKpiLowStock", kpiValue(logDash.ok, logDash.data?.low_stock_parts));
  setHtml("homeKpiOpenMr", kpiValue(logDash.ok, logDash.data?.open_material_requests));
  setHtml("homeKpiOpenRsv", kpiValue(logDash.ok, logDash.data?.open_reservations));
  setHtml("homeKpiOpenPo", kpiValue(logDash.ok, logDash.data?.open_purchase_orders));
  const logHint = document.getElementById("homeKpiLogHint");
  if (logHint) logHint.textContent = logDash.ok ? "Live logistics dashboard" : logDash.error || "Logistics dashboard unavailable";

  const dueItems = listify(due.data?.items || due.data?.due || due.data);
  const forecastHint = planDash.ok
    ? `Checks due ${planDash.data?.checks_due ?? "—"} · AD ${planDash.data?.ads_due ?? "—"} · grounded ${planDash.data?.grounded ?? "—"}`
    : planDash.error || "Planning dashboard unavailable";
  const forecastEl = document.getElementById("homeForecastHint");
  if (forecastEl) forecastEl.textContent = forecastHint;
  setHtml(
    "homeDueList",
    rowsFrom(dueItems.slice(0, 8), (item) => {
      const title = item.task_code || item.check_code || item.title || item.id || "Due item";
      const when = item.due_at || item.due_date || item.window || "";
      const aircraftId = item.aircraft_id || "";
      const finding =
        String(item.source_type || "").toLowerCase() === "deferred_defect" && (item.source_id || item.id)
          ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="finding:${esc(String(item.source_id || item.id))}" data-we-label="${esc(String(title))}">Finding</button>`
          : "";
      const acBtn = aircraftId
        ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="aircraft:${esc(String(aircraftId))}" data-we-tab="maintenance">${esc(String(aircraftId))}</button>`
        : "";
      return `<div class="mx-card" style="padding:10px 12px"><strong>${esc(String(title))}</strong><div class="mx-subtitle">${esc(String(item.urgency || ""))} · ${esc(String(when))}</div><div class="mx-row" style="gap:8px;margin-top:8px">${acBtn}${finding}</div></div>`;
    }) || `<div class="mx-empty">${due.ok ? "No due items." : esc(due.error || "Planning unavailable")}</div>`
  );

  const notifications = listify(notes.data);
  const approvalItems = listify(approvals.data);
  const activity = [
    ...approvalItems.slice(0, 5).map((n) => ({
      title: `Approval ${n.status || ""} · ${n.action || n.id}`,
      when: n.created_at || "",
    })),
    ...notifications.slice(0, 8).map((n) => ({
      title: n.title || n.subject || n.channel || "Notification",
      when: n.created_at || n.sent_at || "",
    })),
  ];
  setHtml(
    "homeActivity",
    rowsFrom(activity.slice(0, 10), (n) => {
      return `<div class="mx-timeline-item"><div><div>${esc(String(n.title))}</div><div class="mx-timeline-meta">${esc(String(n.when))}</div></div></div>`;
    }) || `<div class="mx-empty">${notes.ok || approvals.ok ? "No recent operational activity." : "Activity unavailable."}</div>`
  );
}

function renderAircraftTable(items) {
  setHtml(
    "aircraftTableBody",
    items.length
      ? table(
          ["Registration", "Model", "Status", "Serial", "ID"],
          items
            .map((a) => {
              const reg = a.registration || a.registration_mark || a.tail_number || a.id || "";
              const oid = a.id || "";
              return `<tr class="we-row-open" data-we-open="aircraft:${esc(String(oid))}" data-we-label="${esc(String(reg))}">
                <td>${esc(reg || "—")}</td>
                <td>${esc(a.model_name || a.model_id || "—")}</td>
                <td><span class="mx-chip">${esc(a.status || a.status_code || "—")}</span></td>
                <td class="mx-mono">${esc(a.serial_number || "—")}</td>
                <td class="mx-mono">${esc(String(oid))}</td>
              </tr>`;
            })
            .join("")
        )
      : `<div class="mx-empty">No aircraft match filters.</div>`
  );
}

export async function refreshAircraftWorkspace() {
  const [res, models, statuses, fleets] = await Promise.all([
    uxFetchFleetAircraft("?limit=100"),
    uxFetchFleetModels(),
    uxFetchFleetStatuses(),
    uxFetchFleets(),
  ]);
  const items = listify(res.data);
  const modelOpts = listify(models.data)
    .map((m) => `<option value="${esc(m.id)}">${esc(m.name || m.code || m.id)}</option>`)
    .join("");
  const statusOpts = listify(statuses.data)
    .map((s) => `<option value="${esc(s.code || s.id)}">${esc(s.label || s.code || s.id)}</option>`)
    .join("");
  const fleetOpts = [`<option value="">No fleet</option>`]
    .concat(listify(fleets.data).map((f) => `<option value="${esc(f.id)}">${esc(f.name || f.code || f.id)}</option>`))
    .join("");

  setHtml(
    "aircraftControls",
    `${toolbarHtml("ac", {
      searchPlaceholder: "Search registration, serial, id…",
      statuses: [...new Set(items.map((a) => a.status || a.status_code).filter(Boolean))],
      sorts: [
        { value: "registration:asc", label: "Registration A–Z" },
        { value: "registration:desc", label: "Registration Z–A" },
        { value: "status_code:asc", label: "Status" },
        { value: "serial_number:asc", label: "Serial" },
      ],
    })}
    <details class="mx-card" style="margin-bottom:12px;padding:12px">
      <summary><strong>Register aircraft</strong></summary>
      <form id="aircraftCreateForm" class="mx-stack" style="margin-top:12px;gap:8px">
        <div class="mx-grid mx-grid-3">
          <label class="mx-field">Model<select class="mx-input" name="model_id" required>${modelOpts || "<option value=''>No models</option>"}</select></label>
          <label class="mx-field">Serial<input class="mx-input" name="serial_number" required maxlength="120" /></label>
          <label class="mx-field">Registration<input class="mx-input" name="registration_mark" maxlength="40" /></label>
          <label class="mx-field">Status<select class="mx-input" name="status_code">${statusOpts || "<option value='active'>active</option>"}</select></label>
          <label class="mx-field">Fleet<select class="mx-input" name="fleet_id">${fleetOpts}</select></label>
          <label class="mx-field">Year<input class="mx-input" name="year_built" type="number" min="1900" max="2100" /></label>
        </div>
        <label class="mx-field">Notes<input class="mx-input" name="notes" /></label>
        <button class="mx-btn" type="submit">Create aircraft</button>
        <p class="mx-subtitle" id="aircraftCreateMsg"></p>
      </form>
    </details>
    <div id="aircraftTableBody">${res.ok ? "" : `<div class="mx-empty">${esc(res.error || "Fleet API unavailable")}</div>`}</div>`
  );

  if (res.ok) {
    renderAircraftTable(items);
    bindToolbar("ac", ({ q, status, sortKey, sortDir }) => {
      renderAircraftTable(
        filterSortSearch(items, {
          q,
          status,
          statusKey: items.some((i) => i.status_code) ? "status_code" : "status",
          sortKey: sortKey || "registration",
          sortDir,
        })
      );
    });
  }

  document.getElementById("aircraftCreateForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const payload = Object.fromEntries(fd.entries());
    if (!payload.fleet_id) delete payload.fleet_id;
    if (!payload.year_built) delete payload.year_built;
    else payload.year_built = Number(payload.year_built);
    const created = await uxCreateAircraft(payload);
    const msg = document.getElementById("aircraftCreateMsg");
    if (!created.ok) {
      if (msg) msg.textContent = created.error || "Create failed";
      toast(created.error || "Create failed");
      return;
    }
    if (msg) msg.textContent = `Created ${created.data?.id || ""}`;
    toast("Aircraft registered");
    refreshAircraftWorkspace();
  });
}

export async function refreshFleetWorkspace() {
  const res = await uxFetchFleets();
  const items = listify(res.data);
  setHtml(
    "fleetCards",
    rowsFrom(
      items,
      (f) => `<article class="mx-card">
        <div class="mx-label">Fleet</div>
        <div class="mx-title">${esc(f.name || f.code || f.id)}</div>
        <p class="mx-subtitle">${esc(f.description || f.operator_name || "Fleet unit")}</p>
        <div class="mx-row" style="margin-top:8px;gap:8px;flex-wrap:wrap">
          <span class="mx-chip">${esc(String(f.aircraft_count ?? "—"))} aircraft</span>
          <span class="mx-mono">${esc(f.id || "")}</span>
        </div>
      </article>`
    ) || `<div class="mx-empty">${res.ok ? "No fleets." : esc(res.error || "Unavailable")}</div>`
  );
}

function renderWoTable(items) {
  setHtml(
    "workOrdersTableBody",
    table(
      ["Order", "Title", "Status", "Aircraft", "Priority", "Due", "Cards"],
      items.length
        ? items
            .map((o) => {
              const id = o.id || o.work_order_id || "";
              return `<tr class="we-row-open" data-we-open="workOrder:${esc(String(id))}" data-we-label="${esc(String(o.wo_number || id))}">
            <td class="mx-mono">${esc(String(o.wo_number || id))}</td>
            <td>${esc(o.title || "—")}</td>
            <td><span class="mx-chip">${esc(o.status || "—")}</span></td>
            <td>${o.aircraft_id ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="aircraft:${esc(String(o.aircraft_id))}">${esc(o.aircraft_id)}</button>` : "—"}</td>
            <td>${esc(o.priority || "—")}</td>
            <td>${esc(o.due_date ? String(o.due_date).slice(0, 10) : "—")}</td>
            <td>${esc(String(o.job_card_count ?? "—"))}</td>
          </tr>`;
            })
            .join("")
        : `<tr><td colspan="7">No work orders.</td></tr>`
    )
  );
}

export async function refreshWorkOrdersWorkspace() {
  const [soft, session] = await Promise.all([uxFetchWorkOrders("?limit=100"), getSessionStatus().catch(() => null)]);
  const items = listify(soft.data);
  const loadError = soft.ok ? null : soft.error;
  const canManage = sessionCanManageWorkOrders(session?.role);
  const aircraft = listify((await uxFetchFleetAircraft("?limit=50")).data);
  let createBusy = false;

  setHtml(
    "workOrdersControls",
    `${toolbarHtml("wo", {
      searchPlaceholder: "Search WO / aircraft / package / title…",
      statuses: [...new Set(items.map((o) => o.status).filter(Boolean))],
      sorts: [
        { value: "wo_number:asc", label: "WO number" },
        { value: "status:asc", label: "Status" },
        { value: "priority:asc", label: "Priority" },
        { value: "aircraft_id:asc", label: "Aircraft" },
        { value: "due_date:asc", label: "Due date" },
      ],
    })}
    <div class="mx-row" style="gap:8px;flex-wrap:wrap;margin-bottom:12px">
      <select class="mx-input" id="woPriority" style="max-width:160px">
        <option value="">All priority</option>
        <option value="low">low</option>
        <option value="normal">normal</option>
        <option value="high">high</option>
        <option value="critical">critical</option>
      </select>
      <select class="mx-input" id="woAircraft" style="max-width:220px">
        <option value="">All aircraft</option>
        ${aircraft.map((a) => `<option value="${esc(a.id)}">${esc(a.registration || a.registration_mark || a.id)}</option>`).join("")}
      </select>
    </div>
    ${
      canManage
        ? `<details class="mx-card" style="margin-bottom:12px;padding:12px">
      <summary><strong>Create work package + order</strong></summary>
      <form id="woCreateForm" class="mx-stack" style="margin-top:12px;gap:8px">
        <div class="mx-grid mx-grid-2">
          <label class="mx-field">Aircraft<select class="mx-input" name="aircraft_id" required>
            ${aircraft.map((a) => `<option value="${esc(a.id)}">${esc(a.registration || a.registration_mark || a.id)}</option>`).join("") || "<option value=''>No aircraft</option>"}
          </select></label>
          <label class="mx-field">Priority<select class="mx-input" name="priority"><option value="normal">normal</option><option value="high">high</option><option value="low">low</option><option value="critical">critical</option></select></label>
        </div>
        <label class="mx-field">Title<input class="mx-input" name="title" required maxlength="300" placeholder="Work order title" /></label>
        <label class="mx-field">Description<input class="mx-input" name="description" placeholder="Optional description" /></label>
        <button class="mx-btn" type="submit">Create &amp; open</button>
        <p class="mx-subtitle" id="woCreateMsg"></p>
      </form>
    </details>`
        : `<p class="mx-subtitle">Create is limited to Operator / Administrator. Viewer and Reviewer can open existing orders.</p>`
    }
    <div id="workOrdersTableBody"></div>`
  );

  const applyFilters = ({ q, status, sortKey, sortDir }) => {
    const priority = document.getElementById("woPriority")?.value || "";
    const aircraftId = document.getElementById("woAircraft")?.value || "";
    let rows = filterSortSearch(items, { q, status, sortKey: sortKey || "wo_number", sortDir });
    if (priority) rows = rows.filter((row) => String(row.priority || "").toLowerCase() === priority.toLowerCase());
    if (aircraftId) rows = rows.filter((row) => String(row.aircraft_id || "") === aircraftId);
    renderWoTable(rows);
  };

  if (loadError) {
    setHtml("workOrdersTableBody", `<div class="mx-empty">${esc(loadError)} <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" id="woRetry">Retry</button></div>`);
    document.getElementById("woRetry")?.addEventListener("click", () => refreshWorkOrdersWorkspace());
  } else {
    renderWoTable(items);
    bindToolbar("wo", applyFilters);
    document.getElementById("woPriority")?.addEventListener("change", () => {
      document.getElementById("woApply")?.click();
    });
    document.getElementById("woAircraft")?.addEventListener("change", () => {
      document.getElementById("woApply")?.click();
    });
  }

  try {
    const pkgs = await listWorkPackages({ limit: 12 });
    const list = Array.isArray(pkgs) ? pkgs : listify(pkgs);
    setHtml(
      "workPackageStrip",
      rowsFrom(list.slice(0, 6), (p) => `<div class="mx-chip">${esc(p.description || p.package_number || p.id)} · ${esc(p.status || "")}</div>`) ||
        `<span class="mx-subtitle">No packages</span>`
    );
  } catch (err) {
    setHtml("workPackageStrip", `<span class="mx-subtitle">${esc(err?.message || "Packages unavailable")}</span>`);
  }

  document.getElementById("woCreateForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (createBusy) return;
    const fd = new FormData(e.target);
    const aircraftId = String(fd.get("aircraft_id") || "");
    const title = String(fd.get("title") || "").trim();
    const description = String(fd.get("description") || "");
    const priority = String(fd.get("priority") || "normal");
    const msg = document.getElementById("woCreateMsg");
    createBusy = true;
    try {
      const pkg = await createWorkPackage({ aircraft_id: aircraftId, description: description || `Package · ${title}`, priority });
      const order = await createWorkOrder({
        work_package_id: pkg.id,
        title,
        description,
        priority,
      });
      if (msg) msg.textContent = `Created ${order.wo_number || order.id}`;
      toast("Work order created");
      const openBtn = document.createElement("button");
      openBtn.type = "button";
      openBtn.className = "mx-btn mx-btn-ghost mx-btn-sm";
      openBtn.setAttribute("data-we-open", `workOrder:${order.id}`);
      openBtn.setAttribute("data-we-label", order.wo_number || order.id);
      openBtn.textContent = "Open in Workspace Engine";
      msg?.appendChild(document.createElement("br"));
      msg?.appendChild(openBtn);
      refreshWorkOrdersWorkspace();
    } catch (err) {
      if (msg) msg.textContent = err?.message || "Create failed";
      toast(err?.message || "Create failed");
    } finally {
      createBusy = false;
    }
  });
}

export async function refreshLogbookWorkspace() {
  const aircraft = listify((await uxFetchFleetAircraft("?limit=50")).data);
  const selected = document.getElementById("logbookAircraftFilter")?.value || "";
  const query = selected ? `?aircraft_id=${encodeURIComponent(selected)}&limit=80` : "?limit=80";
  const res = await uxFetchLogbook(query);
  const items = listify(res.data);
  const options = [`<option value="">All aircraft in session org</option>`]
    .concat(aircraft.map((a) => `<option value="${esc(a.id)}"${selected === a.id ? " selected" : ""}>${esc(a.registration || a.registration_mark || a.id)}</option>`))
    .join("");
  setHtml(
    "logbookTimeline",
    `<div class="ux2-toolbar mx-row" style="gap:8px;flex-wrap:wrap;margin-bottom:12px">
      <select class="mx-input" id="logbookAircraftFilter" style="max-width:240px">${options}</select>
      <input class="mx-input" id="logbookSearch" placeholder="Search summary / registration / task…" style="flex:1;min-width:180px" />
      <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" id="logbookApply">Apply</button>
    </div>
    ${
      res.ok
        ? items.length
          ? `<div class="mx-timeline" id="logbookEntries">${items
              .map((e) => {
                const title = e.summary || e.id || "Tech log entry";
                const meta = [e.registration || e.aircraft_id, e.occurred_at, e.mechanic_employee_id ? `mech ${e.mechanic_employee_id}` : "", e.release_signature_id ? "signed" : ""]
                  .filter(Boolean)
                  .join(" · ");
                return `<div class="mx-timeline-item" data-log-text="${esc(`${title} ${e.details || ""} ${e.aircraft_id || ""} ${e.task_id || ""}`.toLowerCase())}"><div>
                <strong>${esc(String(title))}</strong>
                <div class="mx-subtitle">${esc(e.details || "Technical log entry")}</div>
                <div class="mx-timeline-meta">${esc(meta)}</div>
                <div class="mx-row" style="gap:8px;margin-top:8px">
                  ${e.aircraft_id ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="aircraft:${esc(e.aircraft_id)}" data-we-tab="logbook" data-we-label="${esc(e.registration || e.aircraft_id)}">Aircraft logbook</button>` : ""}
                  ${e.task_id ? `<span class="mx-chip">task ${esc(e.task_id)}</span>` : ""}
                </div>
              </div></div>`;
              })
              .join("")}</div>`
          : `<div class="mx-empty">No technical log entries yet. ACA release in job-card / MRO Execution writes here. There is no free-form create API.</div>`
        : `<div class="mx-empty">${esc(res.error || "Logbook API unavailable")} <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" id="logbookRetry">Retry</button></div>`
    }`
  );
  document.getElementById("logbookApply")?.addEventListener("click", () => refreshLogbookWorkspace());
  document.getElementById("logbookAircraftFilter")?.addEventListener("change", () => refreshLogbookWorkspace());
  document.getElementById("logbookRetry")?.addEventListener("click", () => refreshLogbookWorkspace());
  document.getElementById("logbookSearch")?.addEventListener("input", (event) => {
    const q = String(event.target.value || "").trim().toLowerCase();
    document.querySelectorAll("#logbookEntries .mx-timeline-item").forEach((node) => {
      const hay = node.getAttribute("data-log-text") || "";
      node.style.display = !q || hay.includes(q) ? "" : "none";
    });
  });
}

export async function refreshEngineeringWorkspace() {
  const [ads, sbs, eos] = await Promise.all([uxFetchAds(), uxFetchServiceBulletins(), uxFetchEngineeringOrders()]);
  const panel = (title, res, mapRow) => {
    const items = listify(res.data);
    return `<article class="mx-card"><div class="mx-card-header"><h3>${esc(title)}</h3><span class="mx-chip">${res.ok ? items.length : "err"}</span></div>
      ${
        res.ok
          ? rowsFrom(items.slice(0, 20), mapRow) || `<div class="mx-empty">No ${esc(title)} records.</div>`
          : `<div class="mx-empty">${esc(res.error || "Unavailable")}</div>`
      }
    </article>`;
  };
  setHtml(
    "engineeringBoard",
    `<div class="mx-grid mx-grid-3">
      ${panel("Airworthiness Directives", ads, (i) => `<div style="padding:8px 0;border-bottom:1px solid var(--mx-border)" class="we-row-open" data-we-open="airworthinessDirective:${esc(String(i.id || ""))}" data-we-label="${esc(i.ad_number || i.id)}"><strong>${esc(i.ad_number || i.code || i.id)}</strong><div class="mx-subtitle">${esc(i.title || "")} · ${esc(i.compliance_status || i.status || "")}</div></div>`)}
      ${panel("Service Bulletins", sbs, (i) => `<div style="padding:8px 0;border-bottom:1px solid var(--mx-border)" class="we-row-open" data-we-open="serviceBulletin:${esc(String(i.id || ""))}" data-we-label="${esc(i.sb_number || i.id)}"><strong>${esc(i.sb_number || i.code || i.id)}</strong><div class="mx-subtitle">${esc(i.title || "")} · ${esc(i.compliance_status || i.status || "")}</div></div>`)}
      ${panel("Engineering Orders", eos, (i) => `<div style="padding:8px 0;border-bottom:1px solid var(--mx-border)" class="we-row-open" data-we-open="engineeringOrder:${esc(String(i.id || ""))}" data-we-label="${esc(i.eo_number || i.id)}"><strong>${esc(i.eo_number || i.code || i.id)}</strong><div class="mx-subtitle">${esc(i.title || "")} · ${esc(i.status || "")}</div></div>`)}
    </div>
    <div class="mx-row" style="margin-top:12px;gap:8px">
      <button type="button" class="mx-btn mx-btn-ghost" data-ux2-goto="planning">Open Maintenance Planning</button>
      <button type="button" class="mx-btn mx-btn-ghost" data-ux2-goto="techLibrary">Technical Library</button>
    </div>`
  );
}

export async function refreshInventoryWorkspace() {
  const [balances, warehouses, shortages] = await Promise.all([
    softGet("/logistics/stock/balances?limit=40"),
    softGet("/logistics/warehouses?limit=20"),
    softGet("/logistics/shortages"),
  ]);
  const balItems = listify(balances.data);
  const whItems = listify(warehouses.data);
  const shortageItems = listify(shortages.data?.items || shortages.data);
  setHtml(
    "inventoryHero",
    `<div class="mx-grid mx-grid-3">
      <article class="mx-kpi"><div class="mx-label">Balance rows</div><div class="mx-kpi-value">${balances.ok ? balItems.length : "—"}</div><div class="mx-kpi-hint">${balances.ok ? "Logistics stock" : esc(balances.error || "API error")}</div></article>
      <article class="mx-kpi"><div class="mx-label">Warehouses</div><div class="mx-kpi-value">${warehouses.ok ? whItems.length : "—"}</div><div class="mx-kpi-hint">Sites &amp; cribs</div></article>
      <article class="mx-kpi"><div class="mx-label">Shortage items</div><div class="mx-kpi-value">${shortages.ok ? shortageItems.length : "—"}</div><div class="mx-kpi-hint">${shortages.ok ? "Below reorder / no stock" : esc(shortages.error || "API error")}</div></article>
    </div>
    <div style="margin-top:16px">${
      balItems.length
        ? table(
            ["Part", "On hand", "Reserved", "Available", "Condition", "Location"],
            balItems
              .slice(0, 25)
              .map(
                (b) => `<tr class="we-row-open" data-we-open="part:${esc(String(b.part_master_id || ""))}" data-we-label="${esc(b.oem_part_number || b.part_number || b.part_master_id || "")}">
              <td>${esc(b.oem_part_number || b.part_number || b.part_master_id || "—")}</td>
              <td>${esc(String(b.qty_on_hand ?? "—"))}</td>
              <td>${esc(String(b.qty_reserved ?? "—"))}</td>
              <td>${esc(String(qtyAvailable(b)))}</td>
              <td>${esc(b.condition || "—")}</td>
              <td>${esc(b.location_code || b.location_id || "—")}</td>
            </tr>`
              )
              .join("")
          )
        : `<div class="mx-empty">${balances.ok ? "No stock balances." : esc(balances.error || "Logistics unavailable")}</div>`
    }</div>
    <p class="mx-subtitle" style="margin-top:12px">Mutations (receive/issue/reserve/PO) are on Logistics Ops. Inventory does not duplicate the stores desk.</p>
    <div style="margin-top:16px"><button type="button" class="mx-btn" data-ux2-goto="logistics">Open Logistics Ops</button></div>`
  );
}

function renderMarketplaceProducts(items) {
  setHtml(
    "marketplaceGrid",
    rowsFrom(items, (p) => {
      const id = p.id || "";
      return `<article class="mx-card">
      <div class="mx-label">${esc(p.category || p.product_type || "Product")}</div>
      <div class="mx-title we-row-open" style="font-size:16px;cursor:pointer" data-we-open="marketplaceListing:${esc(String(id))}" data-we-label="${esc(p.name || p.title || id)}">${esc(p.name || p.title || p.sku || p.id)}</div>
      <p class="mx-subtitle">${esc(p.description || p.condition || "Marketplace listing")}</p>
      <div class="mx-row" style="margin-top:10px;gap:8px;flex-wrap:wrap">
        <span class="mx-chip">${esc(p.status || "listed")}</span>
        <button type="button" class="mx-btn mx-btn-sm mx-btn-ghost" data-mp-cart="${esc(String(id))}">Add to cart</button>
        <button type="button" class="mx-btn mx-btn-sm mx-btn-ghost" data-mp-quote="${esc(String(id))}">Request quote</button>
      </div>
    </article>`;
    }) || `<div class="mx-empty">No products match filters.</div>`
  );

  document.querySelectorAll("[data-mp-cart]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const res = await uxAddMarketplaceCart({ product_id: btn.getAttribute("data-mp-cart"), qty: 1 });
      toast(res.ok ? "Added to cart" : res.error || "Cart failed");
      if (res.ok) refreshMarketplaceWorkspace();
    });
  });
  document.querySelectorAll("[data-mp-quote]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const notes = window.prompt("Quote notes (optional)", "") ?? "";
      const res = await uxCreateMarketplaceQuote({ product_id: btn.getAttribute("data-mp-quote"), qty: 1, notes });
      toast(res.ok ? `Quote ${res.data?.quote_number || ""} requested` : res.error || "Quote failed");
      if (res.ok) refreshMarketplaceWorkspace();
    });
  });
}

export async function refreshMarketplaceWorkspace() {
  const [products, cart, quotes] = await Promise.all([
    uxFetchMarketplaceProducts(),
    uxFetchMarketplaceCart(),
    uxFetchMarketplaceQuotes(),
  ]);
  const items = listify(products.data);
  const cartItems = listify(cart.data);
  const quoteItems = listify(quotes.data);

  setHtml(
    "marketplaceControls",
    `${toolbarHtml("mp", {
      searchPlaceholder: "Search products…",
      statuses: [...new Set(items.map((p) => p.status).filter(Boolean))],
      sorts: [
        { value: "name:asc", label: "Name A–Z" },
        { value: "status:asc", label: "Status" },
        { value: "sku:asc", label: "SKU" },
      ],
    })}
    <div class="mx-grid mx-grid-2" style="margin-bottom:16px">
      <article class="mx-card"><div class="mx-card-header"><h3>Cart</h3><span class="mx-chip">${cart.ok ? cartItems.length : "err"}</span></div>
        ${
          cart.ok
            ? rowsFrom(cartItems, (c) => `<div style="padding:6px 0;border-bottom:1px solid var(--mx-border)"><strong class="mx-mono">${esc(c.product_id)}</strong> × ${esc(String(c.qty))}<div class="mx-subtitle">${esc(c.notes || "")}</div></div>`) ||
              `<div class="mx-empty">Cart empty. Payments are out of RC scope.</div>`
            : `<div class="mx-empty">${esc(cart.error || "Cart unavailable")}</div>`
        }
      </article>
      <article class="mx-card"><div class="mx-card-header"><h3>Quotes</h3><span class="mx-chip">${quotes.ok ? quoteItems.length : "err"}</span></div>
        ${
          quotes.ok
            ? rowsFrom(
                quoteItems.slice(0, 12),
                (q) =>
                  `<div style="padding:6px 0;border-bottom:1px solid var(--mx-border)"><strong>${esc(q.quote_number || q.id)}</strong><div class="mx-subtitle">${esc(q.product_id)} · ${esc(q.status || "")}</div></div>`
              ) || `<div class="mx-empty">No quotes yet.</div>`
            : `<div class="mx-empty">${esc(quotes.error || "Quotes unavailable")}</div>`
        }
      </article>
    </div>
    <p class="mx-subtitle" style="margin-bottom:8px">Catalog · click title for product workspace · no payment checkout in RC</p>`
  );

  if (!products.ok) {
    setHtml("marketplaceGrid", `<div class="mx-empty">${esc(products.error || "Marketplace unavailable")}</div>`);
    return;
  }
  renderMarketplaceProducts(items);
  bindToolbar("mp", ({ q, status, sortKey, sortDir }) => {
    renderMarketplaceProducts(filterSortSearch(items, { q, status, sortKey: sortKey || "name", sortDir }));
  });
}

export async function refreshAssetTwinWorkspace() {
  const res = await uxFetchTwins();
  const items = listify(res.data);
  const first = items[0];
  setHtml(
    "assetTwinStage",
    `<div class="mx-twin-stage">
      <div class="mx-twin-hud"><span class="mx-chip">Digital Twin</span><span class="mx-chip mx-chip-ok">Not a 3D model</span><span class="mx-chip">Lifecycle registry</span></div>
      <div class="mx-twin-orbit"></div>
      <div class="mx-twin-core">${esc(first?.display_name || first?.name || first?.twin_uuid || "Asset<br>Twin")}</div>
      <div class="mx-twin-node" style="left:12%;top:28%">Passport</div>
      <div class="mx-twin-node" style="right:14%;top:34%">Config</div>
      <div class="mx-twin-node" style="left:18%;bottom:22%">History</div>
      <div class="mx-twin-node" style="right:16%;bottom:26%">Reliability</div>
    </div>`
  );
  setHtml(
    "assetTwinList",
    table(
      ["Name", "UUID", "Lifecycle", "Entity"],
      items.length
        ? items
            .map(
              (t) => `<tr class="we-row-open" data-we-open="digitalTwin:${esc(String(t.id || ""))}" data-we-label="${esc(t.display_name || t.name || t.twin_uuid || t.id || "")}">
            <td>${esc(t.display_name || t.name || "—")}</td>
            <td class="mx-mono">${esc(t.twin_uuid || t.id || "")}</td>
            <td><span class="mx-chip">${esc(t.lifecycle_state || t.status || "—")}</span></td>
            <td>${esc([t.fabric_entity_type || t.entity_type, t.fabric_entity_id || t.linked_entity_id].filter(Boolean).join(" · ") || "—")}</td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="4">${res.ok ? "No twins registered." : esc(res.error || "Twin API unavailable")}</td></tr>`
    )
  );
}

export async function refreshAuthorityWorkspace() {
  const res = await uxFetchAuthority();
  const items = listify(res.data);
  setHtml(
    "authorityList",
    rowsFrom(
      items,
      (b) =>
        `<article class="mx-card"><div class="mx-label">Authority</div><div class="mx-title" style="font-size:16px">${esc(b.name || b.code)}</div><p class="mx-subtitle">${esc(b.region || b.description || "Readiness metadata only — not regulatory verification.")}</p></article>`
    ) || `<div class="mx-empty">${res.ok ? "No authority bodies." : esc(res.error || "Unavailable")}</div>`
  );
}

export async function refreshOrganizationWorkspace() {
  const res = await uxFetchOrgTree();
  const items = listify(res.data);
  setHtml(
    "organizationList",
    table(
      ["Organization", "Code", "Type", "ID"],
      items.length
        ? items
            .map(
              (o) => `<tr class="we-row-open" data-we-open="organization:${esc(String(o.id || ""))}" data-we-label="${esc(o.name || o.code || o.id || "")}">
            <td>${esc(o.name || "—")}</td>
            <td>${esc(o.code || "—")}</td>
            <td>${esc(o.org_type || o.type || "—")}</td>
            <td class="mx-mono">${esc(o.id || "")}</td>
          </tr>`
            )
            .join("")
        : `<tr><td colspan="4">${res.ok ? "No organizations." : esc(res.error || "Org API unavailable")}</td></tr>`
    )
  );
}

export async function refreshAiWorkspace() {
  setHtml(
    "aiWorkspaceBody",
    `<div class="mx-grid mx-grid-2">
      <article class="mx-card">
        <div class="mx-card-header"><h3>Advisory Copilot</h3><span class="mx-chip mx-chip-warn">Advisory only</span></div>
        <p class="mx-subtitle">AI outputs are decision-support. Humans remain in control. Open Command Ops for live Copilot.</p>
        <button type="button" class="mx-btn" data-ux2-goto="command">Open Command Copilot</button>
      </article>
      <article class="mx-card">
        <div class="mx-card-header"><h3>Index readiness</h3></div>
        <div class="mx-timeline">
          <div class="mx-timeline-item"><div><strong>Search metadata</strong><div class="mx-subtitle">Platform search + ai_metadata_json</div></div></div>
          <div class="mx-timeline-item"><div><strong>Document stubs</strong><div class="mx-subtitle">Maintenance AI index stubs — no embeddings computed</div></div></div>
        </div>
      </article>
    </div>`
  );
}

export async function refreshDeveloperWorkspace() {
  const [plugins, events, installs, subs, dlq] = await Promise.all([
    uxFetchPlugins(),
    uxFetchEventCatalog(),
    uxFetchPluginInstallations(),
    uxFetchEventSubscriptions(),
    uxFetchEventDlq(),
  ]);
  setHtml(
    "developerPlugins",
    rowsFrom(listify(plugins.data).slice(0, 12), (p) => `<div style="padding:8px 0;border-bottom:1px solid var(--mx-border)"><strong>${esc(p.name || p.code)}</strong><div class="mx-subtitle">${esc(p.category || p.vendor || "")}</div></div>`) ||
      `<div class="mx-empty">${plugins.ok ? "No plugins." : esc(plugins.error || "Unavailable")}</div>`
  );
  setHtml(
    "developerEvents",
    rowsFrom(listify(events.data).slice(0, 12), (e) => `<div style="padding:8px 0;border-bottom:1px solid var(--mx-border)"><strong class="mx-mono">${esc(e.code || e.event_type || e.name || e.id)}</strong><div class="mx-subtitle">v${esc(String(e.version || "1.0"))}</div></div>`) ||
      `<div class="mx-empty">${events.ok ? "No catalog entries." : esc(events.error || "Unavailable")}</div>`
  );
  setHtml(
    "developerInstalls",
    rowsFrom(listify(installs.data).slice(0, 20), (i) => `<div style="padding:8px 0;border-bottom:1px solid var(--mx-border)"><strong>${esc(i.plugin_code || i.plugin_id || i.id)}</strong><div class="mx-subtitle">${esc(i.status || "")} · ${esc(i.organization_id || "")}</div></div>`) ||
      `<div class="mx-empty">${installs.ok ? "No installations." : esc(installs.error || "Unavailable")}</div>`
  );
  setHtml(
    "developerSubs",
    rowsFrom(listify(subs.data).slice(0, 20), (s) => `<div style="padding:8px 0;border-bottom:1px solid var(--mx-border)"><strong class="mx-mono">${esc(s.event_type || s.code || s.id)}</strong><div class="mx-subtitle">${esc(s.endpoint_url || s.transport || s.status || "")}</div></div>`) ||
      `<div class="mx-empty">${subs.ok ? "No subscriptions." : esc(subs.error || "Unavailable")}</div>`
  );
  setHtml(
    "developerDlq",
    rowsFrom(listify(dlq.data).slice(0, 20), (d) => `<div style="padding:8px 0;border-bottom:1px solid var(--mx-border)"><strong>${esc(d.event_type || d.id)}</strong><div class="mx-subtitle">${esc(d.error_message || d.status || d.created_at || "")}</div></div>`) ||
      `<div class="mx-empty">${dlq.ok ? "DLQ empty." : esc(dlq.error || "Unavailable")}</div>`
  );
}

export async function refreshApprovalsWorkspace() {
  const res = await uxFetchApprovals("pending");
  const items = listify(res.data);
  setHtml(
    "approvalsBoard",
    res.ok
      ? items.length
        ? table(
            ["Request", "Action", "Status", "Target", "Requested by", "Action"],
            items
              .map((a) => {
                const id = a.approval_id || a.id || "";
                return `<tr>
                  <td class="mx-mono">${esc(String(id))}</td>
                  <td>${esc(a.action || a.request_type || "—")}</td>
                  <td><span class="mx-chip">${esc(a.status || "pending")}</span></td>
                  <td>${esc(a.target_id || "—")}</td>
                  <td>${esc(a.requested_by || a.requester || "—")}</td>
                  <td><button type="button" class="mx-btn mx-btn-sm" data-approve="${esc(String(id))}">Approve</button></td>
                </tr>`;
              })
              .join("")
          )
        : `<div class="mx-empty">No pending approvals.</div>`
      : `<div class="mx-empty">${esc(res.error || "Approvals API unavailable")}</div>`
  );
  document.querySelectorAll("[data-approve]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-approve");
      const out = await uxApproveRequest(id);
      toast(out.ok ? "Approved" : out.error || "Approve failed");
      if (out.ok) refreshApprovalsWorkspace();
    });
  });
}

export async function refreshOemWorkspace() {
  const res = await softGet("/oem/manufacturers");
  const items = listify(res.data);
  setHtml(
    "oemBoard",
    res.ok
      ? rowsFrom(
          items,
          (m) =>
            `<article class="mx-card"><div class="mx-label">OEM</div><div class="mx-title" style="font-size:16px">${esc(m.name || m.code)}</div><p class="mx-subtitle">${esc(m.description || "Manufacturer readiness catalog — not a full OEM portal.")}</p><span class="mx-mono">${esc(m.code || m.id || "")}</span></article>`
        ) || `<div class="mx-empty">No manufacturers seeded.</div>`
      : `<div class="mx-empty">${esc(res.error || "OEM API unavailable")}</div>`
  );
}

const LOADERS = {
  home: refreshHomeWorkspace,
  aircraft: refreshAircraftWorkspace,
  fleet: refreshFleetWorkspace,
  workOrders: refreshWorkOrdersWorkspace,
  logbook: refreshLogbookWorkspace,
  engineering: refreshEngineeringWorkspace,
  inventory: refreshInventoryWorkspace,
  logistics: refreshLogisticsWorkspace,
  planning: refreshPlanningWorkspace,
  marketplace: refreshMarketplaceWorkspace,
  assetTwin: refreshAssetTwinWorkspace,
  authority: refreshAuthorityWorkspace,
  organization: refreshOrganizationWorkspace,
  ai: refreshAiWorkspace,
  developer: refreshDeveloperWorkspace,
  approvals: refreshApprovalsWorkspace,
  techLibrary: refreshTechLibraryWorkspace,
  personnel: refreshPersonnelWorkspace,
  oem: refreshOemWorkspace,
};

export function refreshUxWorkspace(id) {
  const loader = LOADERS[id];
  if (loader) return loader();
  return Promise.resolve();
}
