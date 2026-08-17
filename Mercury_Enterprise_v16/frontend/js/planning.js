import { el, esc } from "./utils.js";
import { request } from "./api.js";

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
    const [dash, aircraft, due, programs, mpd, checks, ads, defects, hangar, forecast] = await Promise.all([
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
    ]);

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
      aircraft.map(
        (a) =>
          `<div class="contact-row"><b>${esc(a.registration || a.aircraft_id)}</b><span>${esc(a.ops_status)} · ${esc(a.location)} · FH ${esc(String(a.flight_hours))}</span><em class="tl-${esc(a.traffic_light)}">${esc(a.traffic_light)}</em></div>`
      ),
      "No utilization rows."
    );

    renderRows(
      "planDueList",
      due.items.slice(0, 40).map(
        (i) =>
          `<div class="contact-row"><b>${esc(i.urgency)}</b><span>${esc(i.source_type)} · ${esc(i.title)}</span><em>${esc(i.due_at || "—")}</em></div>`
      ),
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
      checks.map(
        (c) =>
          `<div class="contact-row" data-check="${esc(c.id)}"><b>${esc(c.check_code)}</b><span>${esc(c.check_type)} · ${esc(c.status)} · Bay ${esc(c.bay || "—")}</span><em>${esc(c.next_due_at || "—")}</em></div>`
      ),
      "No checks."
    );

    renderRows(
      "planAds",
      ads.map(
        (a) =>
          `<div class="contact-row"><b>${esc(a.ad_number)}</b><span>${esc(a.authority)} · ${esc(a.compliance_status)}</span><em>${esc(a.due_date || "—")}</em></div>`
      ),
      "No ADs."
    );

    renderRows(
      "planDefects",
      defects.map(
        (d) =>
          `<div class="contact-row"><b>${esc(d.defect_number)}</b><span>${esc(d.title)} · ${esc(d.status)} · MEL ${esc(d.dispatch_category || "—")}</span><em>${esc(d.alert_level)}</em></div>`
      ),
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

    const fcRows = [...forecast.overdue, ...forecast.due_soon, ...forecast.future].slice(0, 50);
    renderRows(
      "planForecast",
      fcRows.map(
        (i) =>
          `<div class="contact-row"><b>${esc(i.urgency)}</b><span>${esc(i.source_type)} · ${esc(i.title)} · ${esc(i.due_basis)}</span><em>${esc(i.days_remaining == null ? "—" : String(i.days_remaining) + "d")}</em></div>`
      ),
      "Forecast empty."
    );

    window.__planDueChecks = checks.filter((c) => ["due", "overdue", "planned"].includes(c.status) && !c.generated_work_package_id);
  } catch (error) {
    toast(error.message || "Unable to refresh planning");
  }
}

export function initializePlanning() {
  el("planRefresh")?.addEventListener("click", () => refreshPlanningWorkspace());
  el("planGeneratePkg")?.addEventListener("click", async () => {
    const checks = window.__planDueChecks || [];
    if (!checks.length) return toast("No eligible check to generate");
    try {
      const res = await request("/planning/checks/generate-package", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ check_id: checks[0].id, include_mpd_tasks: true }),
      });
      const body = await res.json();
      toast(`Generated package ${body.package_number}`);
      await refreshPlanningWorkspace();
    } catch (error) {
      toast(error.message || "Generate failed");
    }
  });
}
