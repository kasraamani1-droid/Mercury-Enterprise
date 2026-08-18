import { el, esc } from "./utils.js";
import { listWorkOrders, request } from "./api.js";

function qs(params = {}) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function getJson(path) {
  return (await request(path)).json();
}

function toast(msg) {
  const t = el("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2800);
}

function renderRows(hostId, rows, empty) {
  const host = el(hostId);
  if (!host) return;
  host.innerHTML = rows.length
    ? rows.join("")
    : `<div class="empty">${esc(empty)}</div>`;
}

export async function refreshPlanningWorkspace() {
  try {
    const [dash, aircraft, due, programs, mpd, checks, ads, defects, hangar, forecast, workOrders] = await Promise.all([
      getJson("/planning/dashboard"),
      getJson("/planning/aircraft-status"),
      getJson("/planning/due-list"),
      getJson("/planning/programs"),
      getJson("/planning/mpd-tasks?limit=20"),
      getJson("/planning/checks?limit=30"),
      getJson("/planning/ads?limit=20"),
      getJson("/planning/deferred-defects?limit=20"),
      getJson("/planning/hangar-plans"),
      getJson("/planning/forecast?horizon_days=90"),
      listWorkOrders({ limit: 80 }).catch(() => []),
    ]);
    const orders = Array.isArray(workOrders) ? workOrders : [];
    const delayed = orders.filter((row) => String(row.status || "") === "delayed");
    const byAircraft = (aircraftId) => orders.filter((row) => String(row.aircraft_id) === String(aircraftId)).slice(0, 3);

    const woButtons = (rows) =>
      rows
        .map(
          (row) =>
            `<button type="button" class="ghost small" data-we-open="workOrder:${esc(row.id)}" data-we-label="${esc(row.wo_number || row.id)}">${esc(row.wo_number || row.id)}</button>`
        )
        .join(" ");

    const kpi = el("planDashKpis");
    if (kpi) {
      kpi.innerHTML = `
        <article><span>Available</span><b>${dash.available}</b></article>
        <article><span>Grounded</span><b>${dash.grounded}</b></article>
        <article><span>Checks due</span><b>${dash.checks_due}</b></article>
        <article><span>AD due</span><b>${dash.ads_due}</b></article>
        <article><span>Deferred</span><b>${dash.deferred_defects}</b></article>
        <article><span>Waiting insp</span><b>${dash.waiting_inspection}</b></article>`;
    }

    renderRows(
      "planAircraftStatus",
      aircraft.map((a) => {
        const related = byAircraft(a.aircraft_id);
        return `<div class="contact-row"><b>${esc(a.registration || a.aircraft_id)}</b><span>${esc(a.ops_status)} · ${esc(a.location)} · FH ${esc(String(a.flight_hours))}</span><em class="tl-${esc(a.traffic_light)}">${esc(a.traffic_light)}</em>
          <div>${a.aircraft_id ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(a.aircraft_id)}" data-we-tab="maintenance" data-we-label="${esc(a.registration || a.aircraft_id)}">Aircraft</button>` : ""} ${woButtons(related)}</div></div>`;
      }),
      "No utilization rows."
    );

    renderRows(
      "planDueList",
      (due.items || []).slice(0, 40).map((i) => {
        const related =
          i.source_type === "check"
            ? orders.filter((row) => {
                const check = checks.find((c) => String(c.id) === String(i.source_id));
                return check?.generated_work_package_id && String(row.work_package_id) === String(check.generated_work_package_id);
              })
            : byAircraft(i.aircraft_id);
        const ac = i.aircraft_id
          ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(i.aircraft_id)}" data-we-tab="maintenance">Aircraft</button>`
          : "";
        const finding =
          String(i.source_type || "").toLowerCase() === "deferred_defect"
            ? `<button type="button" class="ghost small" data-we-open="finding:${esc(i.source_id || i.id)}" data-we-label="${esc(i.title || i.id)}">Finding</button>`
            : "";
        return `<div class="contact-row"><b>${esc(i.urgency)}</b><span>${esc(i.source_type)} · ${esc(i.title)}</span><em>${esc(i.due_at || "—")}</em>
          <div>${ac} ${finding} ${woButtons(related)}</div></div>`;
      }),
      "Due list empty."
    );

    renderRows(
      "planPrograms",
      programs.map(
        (p) =>
          `<div class="contact-row"><b>${esc(p.program_code)}</b><span>${esc(p.title)} · ${esc(p.status)}</span><em>rev ${esc(p.current_revision_id || "—")}</em></div>`
      ),
      "No programs."
    );

    renderRows(
      "planMpd",
      mpd.map(
        (t) =>
          `<div class="contact-row"><b>${esc(t.task_number)}</b><span>${esc(t.title)}</span><em>${esc(String(t.estimated_manhours))} MH</em></div>`
      ),
      "No MPD tasks."
    );

    renderRows(
      "planChecks",
      checks.map((c) => {
        const related = c.generated_work_package_id
          ? orders.filter((row) => String(row.work_package_id) === String(c.generated_work_package_id))
          : [];
        const ac = c.aircraft_id
          ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(c.aircraft_id)}" data-we-tab="workOrders">Aircraft</button>`
          : "";
        return `<div class="contact-row" data-check="${esc(c.id)}"><b>${esc(c.check_code)}</b><span>${esc(c.check_type)} · ${esc(c.status)} · Bay ${esc(c.bay || "—")}</span><em>${esc(c.next_due_at || "—")}</em>
          <div>${ac} ${woButtons(related)} ${c.generated_work_package_id ? `<span class="mx-chip">WP ready</span>` : ""}</div></div>`;
      }),
      "No checks."
    );

    renderRows(
      "planAds",
      ads.map((a) => {
        const linked = a.linked_work_order_id ? orders.filter((row) => String(row.id) === String(a.linked_work_order_id)) : [];
        return `<div class="contact-row"><b>${esc(a.ad_number)}</b><span>${esc(a.authority)} · ${esc(a.compliance_status)}</span><em>${esc(a.due_date || "—")}</em>
          <div>${woButtons(linked)}</div></div>`;
      }),
      "No ADs."
    );

    renderRows(
      "planDefects",
      defects.map((d) => {
        const linked = d.linked_work_order_id ? orders.filter((row) => String(row.id) === String(d.linked_work_order_id)) : [];
        const finding = `<button type="button" class="ghost small" data-we-open="finding:${esc(d.id)}" data-we-label="${esc(d.defect_number || d.title || d.id)}">${esc(d.defect_number || "Finding")}</button>`;
        const ac = d.aircraft_id
          ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(d.aircraft_id)}" data-we-tab="maintenance">Aircraft</button>`
          : "";
        return `<div class="contact-row"><b>${esc(d.defect_number)}</b><span>${esc(d.title)} · ${esc(d.status)} · MEL ${esc(d.dispatch_category || "—")}</span><em>${esc(d.alert_level)}</em>
          <div>${ac} ${finding} ${woButtons(linked)}</div></div>`;
      }),
      "No deferred defects."
    );

    renderRows(
      "planHangar",
      hangar.map(
        (h) =>
          `<div class="contact-row"><b>${esc(h.hangar || "Hangar")}</b><span>${esc(h.bay)} · ${esc(h.team_name)} · ${esc(h.shift_code)}</span><em>${esc(h.status)}</em></div>`
      ),
      "No hangar plans."
    );

    const fcRows = [...(forecast.overdue || []), ...(forecast.due_soon || []), ...(forecast.future || [])].slice(0, 50);
    renderRows(
      "planForecast",
      fcRows.map((i) => {
        const ac = i.aircraft_id
          ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(i.aircraft_id)}" data-we-tab="maintenance">Aircraft</button>`
          : "";
        return `<div class="contact-row"><b>${esc(i.urgency)}</b><span>${esc(i.source_type)} · ${esc(i.title)} · ${esc(i.due_basis)}</span><em>${esc(i.days_remaining == null ? "—" : String(i.days_remaining) + "d")}</em>
          <div>${ac} ${woButtons(byAircraft(i.aircraft_id))}</div></div>`;
      }),
      "Forecast empty."
    );

    renderRows(
      "planDelayedWo",
      delayed.map(
        (row) =>
          `<div class="contact-row"><b>${esc(row.wo_number || row.id)}</b><span>${esc(row.title || "")} · ${esc(row.aircraft_id || "")}</span><em>${esc(row.status)}</em>
            <div><button type="button" class="ghost small" data-we-open="workOrder:${esc(row.id)}" data-we-label="${esc(row.wo_number || row.id)}">Open WO</button>
            ${row.aircraft_id ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(row.aircraft_id)}">Aircraft</button>` : ""}</div></div>`
      ),
      delayed.length ? "No delayed work orders." : "No delayed work orders (status delayed)."
    );

    window.__planDueChecks = checks.filter((c) => ["due", "overdue", "planned"].includes(c.status) && !c.generated_work_package_id);
  } catch (error) {
    toast(error.message || "Unable to refresh planning");
  }
}

export function initializePlanning() {
  let generateBusy = false;
  el("planRefresh")?.addEventListener("click", () => refreshPlanningWorkspace());
  el("planGeneratePkg")?.addEventListener("click", async () => {
    const checks = window.__planDueChecks || [];
    if (!checks.length) return toast("No eligible check to generate");
    if (generateBusy) return;
    generateBusy = true;
    try {
      const res = await request("/planning/checks/generate-package", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ check_id: checks[0].id, include_mpd_tasks: true }),
      });
      const body = await res.json();
      toast(`Generated package ${body.package_number}`);
      await refreshPlanningWorkspace();
      const firstWo = (body.work_order_ids || [])[0];
      if (firstWo) {
        const open = document.createElement("button");
        open.type = "button";
        open.className = "ghost small";
        open.setAttribute("data-we-open", `workOrder:${firstWo}`);
        open.textContent = "Open generated work order";
        el("planGeneratePkg")?.insertAdjacentElement("afterend", open);
      }
    } catch (error) {
      toast(error.message || "Generate failed");
    } finally {
      generateBusy = false;
    }
  });
}
