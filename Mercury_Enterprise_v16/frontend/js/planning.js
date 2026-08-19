import { el, esc } from "./utils.js";
import { getSessionStatus } from "./api.js";
import { listify, softGet, softMutate } from "./ux2/api.js";
import { mutationErrorMessage, runLocked } from "./workspace-engine/logistics-ops.js";
import {
  dueObjectTarget,
  eligibleChecks,
  filterDueItems,
  forecastRows,
  sessionCanManagePlanning,
  sessionCanReadPlanning,
} from "./workspace-engine/planning-ops.js";

let lastRole = "";
let refreshGeneration = 0;
let lastAircraftStatus = [];

function toast(msg) {
  const t = el("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2800);
}

function setStatus(text) {
  const node = el("planStatus");
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

function woButtons(rows) {
  return (Array.isArray(rows) ? rows : [])
    .map(
      (row) =>
        `<button type="button" class="ghost small" data-we-open="workOrder:${esc(row.id)}" data-we-label="${esc(row.wo_number || row.id)}">${esc(row.wo_number || row.id)}</button>`
    )
    .join(" ");
}

function dueJump(item) {
  const target = dueObjectTarget(item);
  if (!target) return "";
  return `<button type="button" class="ghost small" data-we-open="${esc(target.type)}:${esc(String(target.id))}" data-we-label="${esc(target.label)}">${esc(target.type === "finding" ? "Finding" : target.label)}</button>`;
}

function optionList(rows, valueKey, labelFn, selected) {
  return (Array.isArray(rows) ? rows : [])
    .map((row) => {
      const id = String(row[valueKey] || row.id || "");
      return `<option value="${esc(id)}"${id === String(selected || "") ? " selected" : ""}>${esc(labelFn(row))}</option>`;
    })
    .join("");
}

function fillUtilizationFromAircraft(form, aircraftId) {
  const row = lastAircraftStatus.find((item) => String(item.aircraft_id) === String(aircraftId));
  if (!form || !row) return;
  if (form.ops_status && row.ops_status) form.ops_status.value = row.ops_status;
  if (form.location) form.location.value = row.location || "";
  if (form.flight_hours) form.flight_hours.value = row.flight_hours ?? "";
  if (form.flight_cycles) form.flight_cycles.value = row.flight_cycles ?? "";
}

function renderDesk({ canManage, aircraft, checks, programs, mels, publications, employees, packages }) {
  const host = el("planOpsDesk");
  if (!host) return;
  if (!canManage) {
    host.innerHTML = `<p class="muted">Planning mutations require planning.manage (Operator or Administrator). Viewer/Reviewer can inspect due, forecast, AD/SB/EO, defects, hangar, and workforce plan lines.</p>`;
    return;
  }
  const eligible = eligibleChecks(checks);
  const revisions = programs.filter((row) => row.current_revision_id);
  host.innerHTML = `
    <div class="enterprise-grid" id="planDeskForms">
      <article class="card">
        <h3>Generate work package</h3>
        <form data-plan-action="generate">
          <select name="check_id" required>
            <option value="">Select due/planned check</option>
            ${optionList(eligible, "id", (row) => `${row.check_code || row.id} · ${row.aircraft_id || ""} · ${row.status || ""}`)}
          </select>
          <label class="muted"><input type="checkbox" name="include_mpd_tasks" checked /> Include MPD tasks</label>
          <button type="submit">Generate WP</button>
        </form>
        <p class="muted">Creates WP + WO + job cards on existing work-order APIs. Duplicate generate returns 409.</p>
      </article>
      <article class="card">
        <h3>Log deferred defect</h3>
        <form data-plan-action="defect">
          <select name="aircraft_id" required>
            <option value="">Aircraft</option>
            ${optionList(aircraft, "aircraft_id", (row) => row.registration || row.aircraft_id)}
          </select>
          <input name="title" required maxlength="300" placeholder="Defect title" />
          <select name="deferral_type"><option value="mel">mel</option><option value="cdl">cdl</option><option value="other">other</option></select>
          <select name="mel_item_id"><option value="">MEL item (optional)</option>${optionList(mels, "id", (row) => `${row.item_number} · ${row.title || ""}`)}</select>
          <select name="dispatch_category"><option value="">Category</option><option>A</option><option>B</option><option>C</option><option>D</option></select>
          <button type="submit">Create defect</button>
        </form>
      </article>
      <article class="card">
        <h3>AD / SB / EO</h3>
        <form data-plan-action="ad">
          <input name="ad_number" required maxlength="80" placeholder="AD number" />
          <select name="authority"><option value="easa">easa</option><option value="faa">faa</option><option value="transport_canada">transport_canada</option><option value="manufacturer">manufacturer</option><option value="other">other</option></select>
          <input name="title" required maxlength="300" placeholder="AD title" />
          <select name="publication_id"><option value="">Library publication (optional)</option>${optionList(publications, "id", (row) => `${row.publication_number || row.id} · ${row.title || ""}`)}</select>
          <button type="submit">Create AD</button>
        </form>
        <form data-plan-action="sb">
          <input name="sb_number" required maxlength="80" placeholder="SB number" />
          <select name="sb_type"><option value="sb">sb</option><option value="asb">asb</option><option value="csb">csb</option><option value="rsb">rsb</option></select>
          <input name="title" required maxlength="300" placeholder="SB title" />
          <select name="priority"><option value="recommended">recommended</option><option value="mandatory">mandatory</option></select>
          <select name="publication_id"><option value="">Library publication (optional)</option>${optionList(publications, "id", (row) => `${row.publication_number || row.id} · ${row.title || ""}`)}</select>
          <button type="submit">Create SB</button>
        </form>
        <form data-plan-action="eo">
          <input name="eo_number" required maxlength="80" placeholder="EO number" />
          <input name="title" required maxlength="300" placeholder="EO title" />
          <select name="publication_id"><option value="">Library publication (optional)</option>${optionList(publications, "id", (row) => `${row.publication_number || row.id} · ${row.title || ""}`)}</select>
          <button type="submit">Create EO</button>
        </form>
      </article>
      <article class="card">
        <h3>Check / hangar / utilization / MEL</h3>
        <form data-plan-action="check">
          <select name="aircraft_id" required>
            <option value="">Aircraft</option>
            ${optionList(aircraft, "aircraft_id", (row) => row.registration || row.aircraft_id)}
          </select>
          <select name="program_revision_id"><option value="">Program revision (optional)</option>${optionList(revisions, "current_revision_id", (row) => `${row.program_code} rev`)}</select>
          <input name="check_code" required maxlength="80" placeholder="Check code" />
          <select name="check_type"><option value="a">a</option><option value="daily">daily</option><option value="weekly">weekly</option><option value="c">c</option><option value="special">special</option></select>
          <input name="title" placeholder="Title" />
          <input name="bay" placeholder="Bay" />
          <button type="submit">Create check</button>
        </form>
        <form data-plan-action="hangar">
          <select name="aircraft_id" required>
            <option value="">Aircraft</option>
            ${optionList(aircraft, "aircraft_id", (row) => row.registration || row.aircraft_id)}
          </select>
          <input name="hangar" placeholder="Hangar" />
          <input name="bay" required placeholder="Bay" />
          <input name="team_name" placeholder="Team" />
          <input name="shift_code" placeholder="Shift" />
          <button type="submit">Create hangar plan</button>
        </form>
        <form data-plan-action="workforce">
          <select name="work_package_id" required>
            <option value="">Work package</option>
            ${optionList(packages, "id", (row) => `${row.package_number || row.id} · ${row.aircraft_id || ""}`)}
          </select>
          <select name="employee_id" required>
            <option value="">Employee</option>
            ${optionList(employees, "id", (row) => `${row.employee_number || row.id} · ${row.full_name || ""}`)}
          </select>
          <select name="role_code">
            <option value="technician">technician</option>
            <option value="inspector">inspector</option>
            <option value="ii">ii</option>
            <option value="aca">aca</option>
            <option value="engineer">engineer</option>
            <option value="stores">stores</option>
          </select>
          <input name="shift_code" placeholder="Shift" />
          <input name="workload_hours" type="number" min="0" step="0.25" placeholder="Hours" />
          <select name="status">
            <option value="assigned">assigned</option>
            <option value="planned">planned</option>
            <option value="released">released</option>
            <option value="complete">complete</option>
            <option value="cancelled">cancelled</option>
          </select>
          <button type="submit">Assign workforce line</button>
        </form>
        <form data-plan-action="utilization">
          <select name="aircraft_id" required>
            <option value="">Aircraft</option>
            ${optionList(aircraft, "aircraft_id", (row) => row.registration || row.aircraft_id)}
          </select>
          <select name="ops_status"><option value="available">available</option><option value="grounded">grounded</option><option value="maintenance">maintenance</option><option value="ferry">ferry</option></select>
          <input name="location" placeholder="Location" />
          <input name="flight_hours" type="number" min="0" step="any" placeholder="Flight hours" />
          <input name="flight_cycles" type="number" min="0" step="1" placeholder="Cycles" />
          <button type="submit">Update utilization</button>
        </form>
        <form data-plan-action="mel">
          <select name="list_type"><option value="mel">mel</option><option value="cdl">cdl</option></select>
          <input name="item_number" required maxlength="80" placeholder="Item number" />
          <input name="title" required maxlength="300" placeholder="Title" />
          <select name="dispatch_category"><option>C</option><option>A</option><option>B</option><option>D</option></select>
          <input name="repair_interval_days" type="number" min="1" placeholder="Repair days" />
          <button type="submit">Create MEL/CDL</button>
        </form>
      </article>
    </div>
    <p class="muted" id="planOpsMsg"></p>
  `;
  const utilForm = host.querySelector('form[data-plan-action="utilization"]');
  const aircraftSelect = utilForm?.querySelector('select[name="aircraft_id"]');
  if (utilForm && aircraftSelect) {
    aircraftSelect.addEventListener("change", () => fillUtilizationFromAircraft(utilForm, aircraftSelect.value));
    if (aircraftSelect.value) fillUtilizationFromAircraft(utilForm, aircraftSelect.value);
  }
}

export async function refreshPlanningWorkspace() {
  const generation = ++refreshGeneration;
  setStatus("Loading planning…");
  const session = await getSessionStatus().catch(() => null);
  lastRole = session?.role || "";
  if (!sessionCanReadPlanning(lastRole) && session?.role) {
    setStatus("Planning read is not granted for this session.");
  }

  const [
    dash,
    aircraft,
    due,
    programs,
    mpd,
    checks,
    ads,
    sbs,
    eos,
    defects,
    mels,
    hangar,
    workforce,
    forecast,
    ordersRes,
    publications,
    employees,
    packages,
  ] = await Promise.all([
    softGet("/planning/dashboard"),
    softGet("/planning/aircraft-status"),
    softGet("/planning/due-list"),
    softGet("/planning/programs"),
    softGet("/planning/mpd-tasks?limit=20"),
    softGet("/planning/checks?limit=50"),
    softGet("/planning/ads?limit=40"),
    softGet("/planning/service-bulletins?limit=40"),
    softGet("/planning/engineering-orders?limit=40"),
    softGet("/planning/deferred-defects?limit=40"),
    softGet("/planning/mel-items?limit=40"),
    softGet("/planning/hangar-plans"),
    softGet("/planning/workforce-plan-lines?limit=200"),
    softGet("/planning/forecast?horizon_days=90"),
    softGet("/work-orders/orders?limit=80"),
    softGet("/publications?limit=80"),
    softGet("/personnel/employees?limit=80"),
    softGet("/work-orders/packages?limit=80"),
  ]);
  if (generation !== refreshGeneration) return;

  const failed = [dash, due, checks].filter((res) => !res.ok);
  setStatus(
    failed.length
      ? `Partial load: ${failed.map((res) => res.error || `HTTP ${res.status}`).join("; ")}`
      : "Live planning data."
  );

  const d = dash.data || {};
  const kpi = el("planDashKpis");
  if (kpi) {
    if (!dash.ok) {
      kpi.innerHTML = `<article><span>Dashboard</span><b>unavailable</b></article>`;
    } else {
      kpi.innerHTML = `
        <article><span>Available</span><b>${esc(String(d.available ?? 0))}</b></article>
        <article><span>Grounded</span><b>${esc(String(d.grounded ?? 0))}</b></article>
        <article><span>Checks due</span><b>${esc(String(d.checks_due ?? 0))}</b></article>
        <article><span>AD due</span><b>${esc(String(d.ads_due ?? 0))}</b></article>
        <article><span>SB due</span><b>${esc(String(d.sbs_due ?? 0))}</b></article>
        <article><span>EO due</span><b>${esc(String(d.eos_due ?? 0))}</b></article>
        <article><span>Deferred</span><b>${esc(String(d.deferred_defects ?? 0))}</b></article>
        <article><span>Waiting insp</span><b>${esc(String(d.waiting_inspection ?? 0))}</b></article>`;
    }
  }

  const aircraftRows = listify(aircraft.data);
  lastAircraftStatus = aircraftRows;
  const dueItems = listify(due.data?.items || due.data);
  const programRows = listify(programs.data);
  const mpdRows = listify(mpd.data);
  const checkRows = listify(checks.data);
  const adRows = listify(ads.data);
  const sbRows = listify(sbs.data);
  const eoRows = listify(eos.data);
  const defectRows = listify(defects.data);
  const melRows = listify(mels.data);
  const hangarRows = listify(hangar.data);
  const workforceRows = listify(workforce.data);
  const employeeRows = listify(employees.data);
  const byEmployee = (employeeId) => employeeRows.find((row) => String(row.id) === String(employeeId));
  const orders = listify(ordersRes.data);
  const delayed = orders.filter((row) => String(row.status || "") === "delayed");
  const byAircraft = (aircraftId) => orders.filter((row) => String(row.aircraft_id) === String(aircraftId)).slice(0, 3);

  const q = el("planSearch")?.value || "";
  const acFilter = el("planAircraftFilter")?.value || "";
  const urgFilter = el("planUrgencyFilter")?.value || "";
  const srcFilter = el("planSourceFilter")?.value || "";

  const acFilterEl = el("planAircraftFilter");
  if (acFilterEl && acFilterEl.options.length <= 1) {
    acFilterEl.innerHTML =
      `<option value="">All aircraft</option>` +
      aircraftRows.map((row) => `<option value="${esc(row.aircraft_id)}">${esc(row.registration || row.aircraft_id)}</option>`).join("");
  }

  renderDesk({
    canManage: sessionCanManagePlanning(lastRole),
    aircraft: aircraftRows,
    checks: checkRows,
    programs: programRows,
    mels: melRows,
    publications: listify(publications.data),
    employees: listify(employees.data),
    packages: listify(packages.data),
  });

  renderRows(
    "planAircraftStatus",
    aircraftRows
      .filter((row) => !acFilter || String(row.aircraft_id) === acFilter)
      .map((a) => {
        const related = byAircraft(a.aircraft_id);
        return `<div class="contact-row"><b>${esc(a.registration || a.aircraft_id)}</b><span>${esc(a.ops_status)} · ${esc(a.location)} · FH ${esc(String(a.flight_hours))}</span><em class="tl-${esc(a.traffic_light)}">${esc(a.traffic_light)}</em>
          <div>${a.aircraft_id ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(a.aircraft_id)}" data-we-tab="maintenance" data-we-label="${esc(a.registration || a.aircraft_id)}">Aircraft</button>` : ""} ${woButtons(related)}</div></div>`;
      })
      .join(""),
    aircraft.ok ? "No utilization rows." : aircraft.error || "Aircraft status unavailable"
  );

  const filteredDue = filterDueItems(dueItems, { q, aircraftId: acFilter, urgency: urgFilter, sourceType: srcFilter });
  renderRows(
    "planDueList",
    filteredDue
      .slice(0, 40)
      .map((i) => {
        const related =
          i.source_type === "check"
            ? orders.filter((row) => {
                const check = checkRows.find((c) => String(c.id) === String(i.source_id));
                return check?.generated_work_package_id && String(row.work_package_id) === String(check.generated_work_package_id);
              })
            : byAircraft(i.aircraft_id);
        const ac = i.aircraft_id
          ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(i.aircraft_id)}" data-we-tab="maintenance">Aircraft</button>`
          : "";
        return `<div class="contact-row"><b>${esc(i.urgency)}</b><span>${esc(i.source_type)} · ${esc(i.title)}</span><em>${esc(i.due_at || "—")}</em>
          <div>${ac} ${dueJump(i)} ${woButtons(related)}</div></div>`;
      })
      .join(""),
    due.ok ? "Due list empty." : due.error || "Due list unavailable"
  );

  renderRows(
    "planPrograms",
    programRows
      .map((p) => `<div class="contact-row"><b>${esc(p.program_code)}</b><span>${esc(p.title)} · ${esc(p.status)}</span><em>rev ${esc(p.current_revision_id || "—")}</em></div>`)
      .join(""),
    programs.ok ? "No programs." : programs.error || "Programs unavailable"
  );
  renderRows(
    "planMpd",
    mpdRows
      .map((t) => `<div class="contact-row"><b>${esc(t.task_number)}</b><span>${esc(t.title)}</span><em>${esc(String(t.estimated_manhours))} MH</em></div>`)
      .join(""),
    mpd.ok ? "No MPD tasks." : mpd.error || "MPD unavailable"
  );

  renderRows(
    "planChecks",
    checkRows
      .filter((c) => !acFilter || String(c.aircraft_id) === acFilter)
      .map((c) => {
        const related = c.generated_work_package_id
          ? orders.filter((row) => String(row.work_package_id) === String(c.generated_work_package_id))
          : [];
        return rowOpen(
          "check",
          c.id,
          c.check_code || c.id,
          `<b>${esc(c.check_code)}</b><span>${esc(c.check_type)} · ${esc(c.status)} · Bay ${esc(c.bay || "—")}</span><em>${esc(c.next_due_at || "—")}</em>
          <div>${c.aircraft_id ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(c.aircraft_id)}" data-we-tab="workOrders">Aircraft</button>` : ""} ${woButtons(related)}</div>`
        );
      })
      .join(""),
    checks.ok ? "No checks." : checks.error || "Checks unavailable"
  );

  renderRows(
    "planAds",
    adRows
      .map((a) =>
        rowOpen(
          "airworthinessDirective",
          a.id,
          a.ad_number || a.id,
          `<b>${esc(a.ad_number)}</b><span>${esc(a.authority)} · ${esc(a.compliance_status)}</span><em>${esc(a.due_date || "—")}</em>
          <div>${woButtons(a.linked_work_order_id ? orders.filter((row) => String(row.id) === String(a.linked_work_order_id)) : [])}</div>`
        )
      )
      .join(""),
    ads.ok ? "No ADs." : ads.error || "ADs unavailable"
  );
  renderRows(
    "planSbs",
    sbRows
      .map((a) =>
        rowOpen(
          "serviceBulletin",
          a.id,
          a.sb_number || a.id,
          `<b>${esc(a.sb_number)}</b><span>${esc(a.sb_type)} · ${esc(a.priority)} · ${esc(a.compliance_status)}</span><em>${esc(a.due_date || "—")}</em>
          <div>${woButtons(a.linked_work_order_id ? orders.filter((row) => String(row.id) === String(a.linked_work_order_id)) : [])}</div>`
        )
      )
      .join(""),
    sbs.ok ? "No service bulletins." : sbs.error || "SBs unavailable"
  );
  renderRows(
    "planEos",
    eoRows
      .map((a) =>
        rowOpen(
          "engineeringOrder",
          a.id,
          a.eo_number || a.id,
          `<b>${esc(a.eo_number)}</b><span>${esc(a.title)} · ${esc(a.status)}</span><em>${esc(a.due_date || "—")}</em>
          <div>${woButtons(a.linked_work_order_id ? orders.filter((row) => String(row.id) === String(a.linked_work_order_id)) : [])}</div>`
        )
      )
      .join(""),
    eos.ok ? "No engineering orders." : eos.error || "EOs unavailable"
  );

  renderRows(
    "planDefects",
    defectRows
      .filter((d) => !acFilter || String(d.aircraft_id) === acFilter)
      .map((d) =>
        rowOpen(
          "finding",
          d.id,
          d.defect_number || d.title || d.id,
          `<b>${esc(d.defect_number)}</b><span>${esc(d.title)} · ${esc(d.status)} · MEL ${esc(d.dispatch_category || "—")}</span><em>${esc(d.alert_level)}</em>
          <div>${d.aircraft_id ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(d.aircraft_id)}" data-we-tab="maintenance">Aircraft</button>` : ""} ${woButtons(d.linked_work_order_id ? orders.filter((row) => String(row.id) === String(d.linked_work_order_id)) : [])}</div>`
        )
      )
      .join(""),
    defects.ok ? "No deferred defects." : defects.error || "Defects unavailable"
  );
  renderRows(
    "planMel",
    melRows
      .map((m) =>
        rowOpen(
          "melItem",
          m.id,
          m.item_number || m.id,
          `<b>${esc(m.item_number)}</b><span>${esc(m.list_type)} · ${esc(m.title)} · cat ${esc(m.dispatch_category)}</span><em>${esc(String(m.repair_interval_days ?? "—"))}d</em>`
        )
      )
      .join(""),
    mels.ok ? "No MEL/CDL items." : mels.error || "MEL unavailable"
  );

  renderRows(
    "planHangar",
    hangarRows
      .filter((h) => !acFilter || String(h.aircraft_id) === acFilter)
      .map(
        (h) =>
          `<div class="contact-row"><b>${esc(h.hangar || "Hangar")}</b><span>${esc(h.bay)} · ${esc(h.team_name)} · ${esc(h.shift_code)} · ${esc(h.aircraft_id || "")}</span><em>${esc(h.status)}</em>
            <div>${h.aircraft_id ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(h.aircraft_id)}" data-we-tab="maintenance">Aircraft</button>` : ""} ${h.work_package_id ? `<span class="mx-chip">WP</span>` : ""}</div></div>`
      )
      .join(""),
    hangar.ok ? "No hangar plans." : hangar.error || "Hangar unavailable"
  );

  const packageAircraft = Object.fromEntries(listify(packages.data).map((row) => [String(row.id), row.aircraft_id || ""]));
  renderRows(
    "planWorkforce",
    workforceRows
      .filter((line) => !acFilter || String(packageAircraft[String(line.work_package_id || "")] || "") === acFilter)
      .map((line) => {
        const person = byEmployee(line.employee_id);
        return rowOpen(
          "workforcePlanLine",
          line.id,
          line.role_code || line.id,
          `<b>${esc(line.role_code)}</b><span>${esc(person?.employee_number || line.employee_id || "—")} · ${esc(person?.full_name || "")} · ${esc(line.shift_code || "—")} · WP ${esc(line.work_package_id || "—")}</span><em>${esc(line.status)}</em>
          <div>${line.employee_id ? `<button type="button" class="ghost small" data-we-open="employee:${esc(line.employee_id)}" data-we-label="${esc(person?.full_name || line.employee_id)}">Employee</button>` : ""}</div>`
        );
      })
      .join(""),
    workforce.ok ? "No workforce plan lines." : workforce.error || "Workforce unavailable"
  );

  const fcRows = filterDueItems(forecastRows(forecast.data), { q, aircraftId: acFilter, urgency: urgFilter, sourceType: srcFilter }).slice(0, 50);
  renderRows(
    "planForecast",
    fcRows
      .map((i) => {
        const ac = i.aircraft_id
          ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(i.aircraft_id)}" data-we-tab="maintenance">Aircraft</button>`
          : "";
        return `<div class="contact-row"><b>${esc(i.urgency)}</b><span>${esc(i.source_type)} · ${esc(i.title)} · ${esc(i.due_basis)}</span><em>${esc(i.days_remaining == null ? "—" : String(i.days_remaining) + "d")}</em>
          <div>${ac} ${dueJump(i)} ${woButtons(byAircraft(i.aircraft_id))}</div></div>`;
      })
      .join(""),
    forecast.ok ? "Forecast empty." : forecast.error || "Forecast unavailable"
  );

  renderRows(
    "planDelayedWo",
    delayed
      .map(
        (row) =>
          `<div class="contact-row"><b>${esc(row.wo_number || row.id)}</b><span>${esc(row.title || "")} · ${esc(row.aircraft_id || "")}</span><em>${esc(row.status)}</em>
            <div><button type="button" class="ghost small" data-we-open="workOrder:${esc(row.id)}" data-we-label="${esc(row.wo_number || row.id)}">Open WO</button>
            ${row.aircraft_id ? `<button type="button" class="ghost small" data-we-open="aircraft:${esc(row.aircraft_id)}">Aircraft</button>` : ""}</div></div>`
      )
      .join(""),
    "No delayed work orders (status delayed)."
  );
}

async function handleDeskSubmit(form) {
  const action = form.getAttribute("data-plan-action");
  const values = Object.fromEntries(new FormData(form).entries());
  const msg = el("planOpsMsg");
  const fail = (result) => {
    const text = mutationErrorMessage(result);
    if (msg) msg.textContent = text;
    toast(text);
  };
  const ok = async (text) => {
    if (msg) msg.textContent = text;
    toast(text);
    await refreshPlanningWorkspace();
  };

  if (action === "generate") {
    if (!values.check_id) return fail({ status: 422, error: "Select a check" });
    if (!window.confirm("Generate work package, work order, and job cards from this check?")) return;
    const result = await runLocked(`desk-gen:${values.check_id}`, () =>
      softMutate("/planning/checks/generate-package", {
        body: { check_id: values.check_id, include_mpd_tasks: Boolean(values.include_mpd_tasks) },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    const firstWo = (result.data?.work_order_ids || [])[0];
    await ok(`Generated ${result.data?.package_number || "package"}`);
    if (firstWo) {
      el("planOpsMsg")?.insertAdjacentHTML(
        "beforeend",
        ` <button type="button" class="ghost small" data-we-open="workOrder:${esc(String(firstWo))}">Open work order</button>`
      );
    }
    return;
  }
  if (action === "defect") {
    const body = {
      aircraft_id: values.aircraft_id,
      title: String(values.title || "").trim(),
      deferral_type: values.deferral_type || "mel",
    };
    if (!body.title) return fail({ status: 422, error: "Title required" });
    if (values.mel_item_id) body.mel_item_id = values.mel_item_id;
    if (values.dispatch_category) body.dispatch_category = values.dispatch_category;
    const result = await runLocked(`desk-defect:${body.aircraft_id}`, () => softMutate("/planning/deferred-defects", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok(`Defect ${result.data?.defect_number || ""} created`);
  }
  if (action === "ad") {
    const body = { ad_number: values.ad_number, authority: values.authority, title: values.title, mandatory: true };
    if (values.publication_id) body.publication_id = values.publication_id;
    const result = await runLocked(`desk-ad:${values.ad_number}`, () => softMutate("/planning/ads", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok(`AD ${result.data?.ad_number || ""} created`);
  }
  if (action === "sb") {
    const body = { sb_number: values.sb_number, sb_type: values.sb_type, title: values.title, priority: values.priority };
    if (values.publication_id) body.publication_id = values.publication_id;
    const result = await runLocked(`desk-sb:${values.sb_number}`, () => softMutate("/planning/service-bulletins", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok(`SB ${result.data?.sb_number || ""} created`);
  }
  if (action === "eo") {
    const body = { eo_number: values.eo_number, title: values.title };
    if (values.publication_id) body.publication_id = values.publication_id;
    const result = await runLocked(`desk-eo:${values.eo_number}`, () => softMutate("/planning/engineering-orders", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok(`EO ${result.data?.eo_number || ""} created`);
  }
  if (action === "check") {
    const body = {
      aircraft_id: values.aircraft_id,
      check_code: values.check_code,
      check_type: values.check_type,
      title: values.title || "",
      bay: values.bay || "",
    };
    if (values.program_revision_id) body.program_revision_id = values.program_revision_id;
    const result = await runLocked(`desk-check:${values.check_code}`, () => softMutate("/planning/checks", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok(`Check ${result.data?.check_code || ""} created`);
  }
  if (action === "hangar") {
    const result = await runLocked(`desk-hangar:${values.aircraft_id}`, () =>
      softMutate("/planning/hangar-plans", {
        body: {
          aircraft_id: values.aircraft_id,
          hangar: values.hangar || "",
          bay: values.bay,
          team_name: values.team_name || "",
          shift_code: values.shift_code || "",
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok("Hangar plan created");
  }
  if (action === "workforce") {
    const body = {
      work_package_id: values.work_package_id,
      employee_id: values.employee_id,
      role_code: values.role_code || "technician",
      shift_code: values.shift_code || "",
      status: values.status || "assigned",
      license_ok: true,
      authorization_ok: true,
      available: true,
    };
    if (values.workload_hours !== "") body.workload_hours = Number(values.workload_hours);
    const result = await runLocked(`desk-workforce:${body.work_package_id}:${body.employee_id}`, () =>
      softMutate("/planning/workforce-plan-lines", { body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok("Workforce plan line assigned");
  }
  if (action === "utilization") {
    const body = {
      aircraft_id: values.aircraft_id,
      ops_status: values.ops_status || "available",
      location: values.location || "",
    };
    if (values.flight_hours !== "") body.flight_hours = Number(values.flight_hours);
    if (values.flight_cycles !== "") body.flight_cycles = Number(values.flight_cycles);
    const result = await runLocked(`desk-util:${values.aircraft_id}`, () =>
      softMutate("/planning/utilization", { method: "PUT", body })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok("Utilization updated");
  }
  if (action === "mel") {
    const body = {
      list_type: values.list_type || "mel",
      item_number: values.item_number,
      title: values.title,
      dispatch_category: values.dispatch_category || "C",
    };
    if (values.repair_interval_days) body.repair_interval_days = Number(values.repair_interval_days);
    const result = await runLocked(`desk-mel:${values.item_number}`, () => softMutate("/planning/mel-items", { body }));
    if (!result) return;
    if (!result.ok) return fail(result);
    return ok(`MEL ${result.data?.item_number || ""} created`);
  }
}

export function initializePlanning() {
  el("planRefresh")?.addEventListener("click", () => refreshPlanningWorkspace());
  el("planApplyFilters")?.addEventListener("click", () => refreshPlanningWorkspace());
  el("planSearch")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") refreshPlanningWorkspace();
  });
  el("planningWorkspace")?.addEventListener("submit", (event) => {
    const form = event.target?.closest?.("[data-plan-action]");
    if (!form) return;
    event.preventDefault();
    handleDeskSubmit(form);
  });
}
