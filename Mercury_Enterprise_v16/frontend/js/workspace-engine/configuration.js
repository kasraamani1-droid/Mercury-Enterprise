/**
 * Aircraft Components & Configuration operator UI (Workspace Engine).
 * Joins existing configuration + serialized + catalog + ATA APIs. No new backend.
 */

import { esc, toast } from "../utils.js";
import {
  uxCreateSerializedComponent,
  uxFetchAircraftConfiguration,
  uxInstallSerializedComponent,
  uxRemoveSerializedComponent,
  uxTransferSerializedComponent,
} from "../ux2/api.js";

const INSTALLABLE_STATUSES = new Set(["stores", "maintenance"]);
const REMOVE_DESTINATIONS = ["stores", "maintenance", "retired", "quarantine"];
const TRANSFER_STATUSES = ["installed", "stores", "maintenance", "retired", "quarantine"];

export function sessionCanManageComponents(role) {
  const value = String(role || "");
  return value === "Operator" || value === "Administrator";
}

export function joinAircraftConfiguration(bundle) {
  const installed = Array.isArray(bundle?.configuration?.installed) ? bundle.configuration.installed : [];
  const serialized = Array.isArray(bundle?.serialized) ? bundle.serialized : [];
  const catalog = Array.isArray(bundle?.catalog) ? bundle.catalog : [];
  const chapters = Array.isArray(bundle?.ataChapters) ? bundle.ataChapters : [];
  const serialById = Object.fromEntries(serialized.map((row) => [String(row.id), row]));
  const catalogById = Object.fromEntries(catalog.map((row) => [String(row.id), row]));
  const ataById = Object.fromEntries(chapters.map((row) => [String(row.id), row]));

  return installed.map((item) => {
    const serial = serialById[String(item.component_id)] || {};
    const cat = catalogById[String(serial.catalog_item_id || "")] || {};
    const ata = ataById[String(cat.ata_chapter_id || "")] || {};
    const chapter = ata.chapter_number ? String(ata.chapter_number).padStart(2, "0") : "";
    const sub = ata.subchapter ? String(ata.subchapter).padStart(2, "0") : "";
    const ataCode = chapter ? `${chapter}-${sub || "00"}` : "";
    return {
      component_id: item.component_id,
      serial_number: item.serial_number || serial.serial_number || "",
      part_number: item.part_number || serial.part_number || cat.part_number || "",
      component_type: item.component_type || serial.component_type || cat.component_type || "general",
      position: item.position || serial.installation_position || "",
      date_installed: item.date_installed || serial.date_installed || "",
      tsn_hours: item.tsn_hours ?? serial.tsn_hours ?? "",
      csn_cycles: item.csn_cycles ?? serial.csn_cycles ?? "",
      remaining_hours: item.remaining_hours ?? serial.remaining_hours,
      remaining_cycles: item.remaining_cycles ?? serial.remaining_cycles,
      aircraft_hours_at_install: serial.aircraft_hours_at_install,
      aircraft_cycles_at_install: serial.aircraft_cycles_at_install,
      component_status: serial.component_status || "installed",
      catalog_item_id: serial.catalog_item_id || cat.id || "",
      ata_chapter_id: cat.ata_chapter_id || ata.id || "",
      ata_code: ataCode,
      ata_title: ata.title || "",
      manufacturer_name: serial.manufacturer_name || cat.oem_name || "",
    };
  });
}

export function installCandidates(bundle) {
  return (Array.isArray(bundle?.serialized) ? bundle.serialized : []).filter((row) =>
    INSTALLABLE_STATUSES.has(String(row.component_status || "").toLowerCase())
  );
}

export function transferDestinations(bundle, currentAircraftId) {
  return (Array.isArray(bundle?.fleetAircraft) ? bundle.fleetAircraft : []).filter(
    (row) => String(row.id) !== String(currentAircraftId)
  );
}

export function occupiedPositions(installedRows) {
  return [
    ...new Set(
      (Array.isArray(installedRows) ? installedRows : [])
        .map((row) => String(row.position || "").trim().toUpperCase())
        .filter(Boolean)
    ),
  ];
}

export function groupRowsByAta(rows) {
  const groups = new Map();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const key = row.ata_chapter_id || row.ata_code || "unassigned";
    const label = row.ata_code
      ? `${row.ata_code}${row.ata_title ? ` ${row.ata_title}` : ""}`.trim()
      : "Unassigned ATA / system";
    if (!groups.has(key)) groups.set(key, { key, label, rows: [] });
    groups.get(key).rows.push(row);
  });
  return [...groups.values()].sort((a, b) => a.label.localeCompare(b.label));
}

export function configurationMutationCacheKeys(active, mutation = {}) {
  const components = new Set();
  const aircraft = new Set();
  if (active?.type === "component" && active.id) components.add(String(active.id));
  if (active?.type === "aircraft" && active.id) aircraft.add(String(active.id));
  if (mutation.componentId) components.add(String(mutation.componentId));
  if (mutation.sourceAircraftId) aircraft.add(String(mutation.sourceAircraftId));
  if (mutation.destinationAircraftId) aircraft.add(String(mutation.destinationAircraftId));
  (active?.bundle?.configuration?.installed || []).forEach((row) => {
    if (row?.component_id) components.add(String(row.component_id));
  });
  if (active?.record?.current_aircraft_id) aircraft.add(String(active.record.current_aircraft_id));
  return {
    components: [...components].filter(Boolean),
    aircraft: [...aircraft].filter(Boolean),
  };
}

export function destructiveConfirmMessage(kind, ctx = {}) {
  const sn = ctx.serial_number || ctx.component_id || "this component";
  const aircraft = ctx.aircraft_label || ctx.aircraft_id || "this aircraft";
  const pos = ctx.position || "the current position";
  if (kind === "remove") {
    return `Remove ${sn} from ${aircraft} at ${pos} to ${ctx.destination_status || "stores"}? This updates the installed configuration.`;
  }
  if (ctx.to_status === "installed") {
    return `Transfer ${sn} from ${aircraft} onto ${ctx.dest_label || ctx.to_aircraft_id || "the destination aircraft"} at ${ctx.dest_position || "the new position"}?`;
  }
  return `Transfer ${sn} off ${aircraft} to ${ctx.to_status || "another status"}?`;
}

export function serializedForComponent(session, componentId) {
  const id = String(componentId || "");
  if (!id) return null;
  if (session?.type === "component" && String(session.id) === id) {
    return session.record || null;
  }
  const rows = Array.isArray(session?.bundle?.serialized) ? session.bundle.serialized : [];
  return rows.find((row) => String(row.id) === id) || null;
}

/** Resolve hours/cycles for remove/transfer. Never coerce a missing install snapshot to 0. */
export function resolveInstallationHoursCycles(record, formHours, formCycles) {
  const missing = (value) => value === "" || value == null;
  const parseHoursValue = (value) => {
    if (missing(value)) return null;
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0) return false;
    return n;
  };
  const parseCyclesValue = (value) => {
    if (missing(value)) return null;
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0 || !Number.isInteger(n)) return false;
    return n;
  };

  const formH = parseHoursValue(formHours);
  const formC = parseCyclesValue(formCycles);
  if (formH === false || formC === false) {
    return {
      ok: false,
      error: "Aircraft hours and cycles must be zero or greater (cycles must be a whole number).",
    };
  }

  const snapH = parseHoursValue(record?.aircraft_hours_at_install);
  const snapC = parseCyclesValue(record?.aircraft_cycles_at_install);
  if (snapH === false || snapC === false) {
    return { ok: false, error: "Installation hours and cycles on this component record are invalid." };
  }

  const hours = formH != null ? formH : snapH;
  const cycles = formC != null ? formC : snapC;
  if (hours == null || cycles == null) {
    return {
      ok: false,
      error:
        "Installation hours and cycles are not recorded for this component. Enter aircraft hours and cycles at or above the installation values.",
    };
  }
  if (snapH != null && hours < snapH) {
    return { ok: false, error: "Removal hours cannot be less than installation hours." };
  }
  if (snapC != null && cycles < snapC) {
    return { ok: false, error: "Removal cycles cannot be less than installation cycles." };
  }
  return { ok: true, hours, cycles };
}

function configurationErrorMessage(res) {
  if (!res || res.ok) return "";
  if (res.status === 403) return "You do not have permission to read aircraft configuration.";
  if (res.status === 404) return "Aircraft configuration was not found.";
  return res.error || "Unable to load aircraft configuration.";
}

function aircraftLabel(row) {
  return row.current_registration || row.registration || row.tail_number || row.serial_number || row.id;
}

function formatRemaining(hours, cycles) {
  const h = hours == null || hours === "" ? "—" : String(hours);
  const c = cycles == null || cycles === "" ? "—" : String(cycles);
  return `${h} h / ${c} cyc`;
}

export function renderAircraftConfigurationPanel(session, bundle, { dueHtml = "" } = {}) {
  const canManage = sessionCanManageComponents(bundle?.sessionRole);
  const load = bundle?.configurationLoad || { ok: true, error: "", status: 200 };
  if (!load.ok) {
    return `
      <article class="mx-card we-cfg" data-we-cfg-root="1">
        <div class="mx-card-header"><h3>Aircraft configuration</h3><span class="mx-chip mx-chip-warn">Error</span></div>
        <div class="mx-empty">${esc(configurationErrorMessage(load))}</div>
      </article>
      ${dueHtml || ""}
    `;
  }

  const rows = joinAircraftConfiguration(bundle);
  const groups = groupRowsByAta(rows);
  const occupied = occupiedPositions(rows);
  const chapters = Array.isArray(bundle?.ataChapters) ? bundle.ataChapters : [];
  const ataWarn = bundle?.ataLoad && !bundle.ataLoad.ok ? `<span class="mx-chip mx-chip-warn">ATA catalog unavailable</span>` : "";
  const serialWarn =
    bundle?.serializedLoad && !bundle.serializedLoad.ok
      ? `<span class="mx-chip mx-chip-warn">Serialized lookup unavailable — ATA join and install candidates may be incomplete</span>`
      : "";
  const tableBody = rows.length
    ? groups
        .map((group) => {
          const groupRows = group.rows
            .map((row) => {
              const search = [row.ata_code, row.ata_title, row.position, row.part_number, row.serial_number, row.component_type]
                .join(" ")
                .toLowerCase();
              const actions = `
            <div class="we-cfg-actions">
              <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="component:${esc(String(row.component_id))}" data-we-label="${esc(row.serial_number || row.component_id)}">Open</button>
              ${
                canManage
                  ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-cfg-fill="remove" data-we-component-id="${esc(String(row.component_id))}">Remove</button>
                     <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-cfg-fill="transfer" data-we-component-id="${esc(String(row.component_id))}">Transfer</button>`
                  : ""
              }
            </div>`;
              return `<tr class="we-row-open" data-we-cfg-row="1" data-we-cfg-ata="${esc(group.key)}" data-we-cfg-text="${esc(search)}" data-we-open="component:${esc(String(row.component_id))}" data-we-label="${esc(row.serial_number || row.component_id)}">
            <td class="mx-mono">${esc(row.ata_code || "—")}</td>
            <td>${esc(row.ata_title || row.component_type || "—")}</td>
            <td class="mx-mono">${esc(row.position || "—")}</td>
            <td class="mx-mono">${esc(row.part_number || "—")}</td>
            <td class="mx-mono">${esc(row.serial_number || "—")}</td>
            <td><span class="mx-chip">${esc(row.component_type || "—")}</span></td>
            <td><span class="mx-chip">${esc(row.component_status || "installed")}</span></td>
            <td>${esc(String(row.date_installed || "—"))}</td>
            <td>${esc(formatRemaining(row.tsn_hours, row.csn_cycles))}</td>
            <td>${esc(formatRemaining(row.remaining_hours, row.remaining_cycles))}</td>
            <td class="we-cfg-action-cell">${actions}</td>
          </tr>`;
            })
            .join("");
          return `<tr class="we-cfg-group" data-we-cfg-group="1" data-we-cfg-ata="${esc(group.key)}"><td colspan="11">${esc(group.label)} · ${group.rows.length} installed</td></tr>${groupRows}`;
        })
        .join("")
    : "";

  const table = rows.length
    ? `<div class="mx-table-wrap"><table class="mx-table" id="weCfgTable"><thead><tr>
        <th>ATA</th><th>System</th><th>Position</th><th>Part</th><th>Serial</th><th>Type</th><th>Status</th><th>Installed</th><th>TSN / CSN</th><th>Remaining</th><th>Actions</th>
      </tr></thead><tbody>${tableBody}</tbody></table></div>
      <div class="mx-empty" id="weCfgFilterEmpty" hidden>No installed components match this ATA / search filter.</div>`
    : `<div class="mx-empty">No serialized components installed on this aircraft.</div>`;

  const ataOptions = [`<option value="">All ATA chapters</option>`]
    .concat(
      chapters.map(
        (ch) =>
          `<option value="${esc(ch.id)}">${esc(`${String(ch.chapter_number).padStart(2, "0")}-${String(ch.subchapter || "00").padStart(2, "0")} ${ch.title}`)}</option>`
      )
    )
    .join("");

  return `
    <article class="mx-card we-cfg" data-we-cfg-root="1" data-we-aircraft-id="${esc(session.id)}">
      <div class="mx-card-header">
        <h3>Aircraft configuration</h3>
        <span class="mx-chip">${rows.length} installed</span>
        ${ataWarn}
        ${serialWarn}
        ${canManage ? "" : `<span class="mx-chip">Read only</span>`}
      </div>
      <p class="mx-subtitle">Installed serialized components for <strong>${esc(session.label || session.id)}</strong> <span class="mx-mono">${esc(session.id)}</span>. Grouped by ATA / system. Occupied positions: ${esc(occupied.length ? occupied.join(", ") : "none")}.</p>
      <div class="we-cfg-filters">
        <label class="mx-label">ATA / system
          <select class="mx-select" id="weCfgAtaFilter" data-we-cfg-filter="ata">${ataOptions}</select>
        </label>
        <label class="mx-label">Search
          <input class="mx-input" id="weCfgSearchFilter" data-we-cfg-filter="q" placeholder="Position, PN, SN…" />
        </label>
      </div>
      ${table}
      <p class="we-cfg-msg" data-we-cfg-msg></p>
      ${canManage ? renderManageForms(session, bundle, rows) : ""}
    </article>
    ${dueHtml || ""}
  `;
}

function renderManageForms(session, bundle, installedRows) {
  const candidates = installCandidates(bundle);
  const destinations = transferDestinations(bundle, session.id);
  const occupied = occupiedPositions(installedRows);
  const catalog = Array.isArray(bundle?.catalog) ? bundle.catalog : [];
  const noDestNote = destinations.length
    ? ""
    : `<p class="mx-subtitle">No other aircraft in this organization. On-wing transfer is unavailable.</p>`;

  const candidateOpts = candidates.length
    ? candidates
        .map(
          (row) =>
            `<option value="${esc(row.id)}">${esc(`${row.serial_number} · ${row.part_number || row.component_type || ""} · ${row.component_status} (not installed)`)}</option>`
        )
        .join("")
    : `<option value="">No stores / maintenance components</option>`;

  const installedOpts = installedRows.length
    ? installedRows
        .map((row) => `<option value="${esc(row.component_id)}">${esc(`${row.serial_number} · ${row.position || "no position"} · installed`)}</option>`)
        .join("")
    : `<option value="">No installed components</option>`;

  const destOpts = destinations.length
    ? destinations
        .map((row) => `<option value="${esc(row.id)}">${esc(aircraftLabel(row))}</option>`)
        .join("")
    : `<option value="">No destination aircraft</option>`;

  const catalogOpts = catalog
    .map((row) => `<option value="${esc(row.id)}">${esc(`${row.part_number} · ${row.component_type || ""}`)}</option>`)
    .join("");

  const destDisabled = destinations.length ? "" : "disabled";
  const installedDisabled = installedRows.length ? "" : "disabled";
  const candidateDisabled = candidates.length ? "" : "disabled";

  return `
    <div class="we-cfg-forms">
      <article class="mx-card we-cfg-form-card">
        <div class="mx-card-header"><h3>Install onto this aircraft</h3></div>
        <p class="mx-subtitle">Select a stores or maintenance component. Position is unique on this aircraft (occupied: ${esc(occupied.length ? occupied.join(", ") : "none")}).</p>
        <form id="weCfgInstallForm" class="we-cfg-form" data-we-cfg-form="install">
          <div class="we-cfg-form-grid">
            <label class="mx-label">Available component (not installed)
              <select class="mx-select" name="component_id" required ${candidateDisabled}>${candidateOpts}</select>
            </label>
            <label class="mx-label">Position
              <input class="mx-input" name="position" required maxlength="80" placeholder="ENG1" />
            </label>
            <label class="mx-label">Aircraft hours
              <input class="mx-input" name="aircraft_hours" type="number" min="0" step="0.01" value="0" />
            </label>
            <label class="mx-label">Aircraft cycles
              <input class="mx-input" name="aircraft_cycles" type="number" min="0" step="1" value="0" />
            </label>
            <label class="mx-label">Reason
              <input class="mx-input" name="reason" maxlength="200" />
            </label>
            <label class="mx-label">Reference
              <input class="mx-input" name="reference" maxlength="80" placeholder="WO / job card" />
            </label>
          </div>
          <button type="submit" class="mx-btn" ${candidateDisabled}>Install</button>
        </form>
      </article>
      <article class="mx-card we-cfg-form-card">
        <div class="mx-card-header"><h3>Remove from this aircraft</h3></div>
        <form id="weCfgRemoveForm" class="we-cfg-form" data-we-cfg-form="remove">
          <div class="we-cfg-form-grid">
            <label class="mx-label">Installed component
              <select class="mx-select" name="component_id" required ${installedDisabled}>${installedOpts}</select>
            </label>
            <label class="mx-label">Destination
              <select class="mx-select" name="destination_status">${REMOVE_DESTINATIONS.map((s) => `<option value="${s}">${s}</option>`).join("")}</select>
            </label>
            <label class="mx-label">Aircraft hours
              <input class="mx-input" name="aircraft_hours" type="number" min="0" step="0.01" data-we-cfg-hours="snapshot" />
            </label>
            <label class="mx-label">Aircraft cycles
              <input class="mx-input" name="aircraft_cycles" type="number" min="0" step="1" data-we-cfg-cycles="snapshot" />
            </label>
            <label class="mx-label">Reason
              <input class="mx-input" name="reason" maxlength="200" />
            </label>
          </div>
          <button type="submit" class="mx-btn" ${installedDisabled}>Remove</button>
        </form>
      </article>
      <article class="mx-card we-cfg-form-card">
        <div class="mx-card-header"><h3>Transfer</h3></div>
        ${noDestNote}
        <form id="weCfgTransferForm" class="we-cfg-form" data-we-cfg-form="transfer">
          <div class="we-cfg-form-grid">
            <label class="mx-label">Component
              <select class="mx-select" name="component_id" required ${installedDisabled}>${installedOpts}</select>
            </label>
            <label class="mx-label">To status
              <select class="mx-select" name="to_status" data-we-cfg-transfer-status>
                ${TRANSFER_STATUSES.map((s) => {
                  const disableInstall = s === "installed" && !destinations.length ? "disabled" : "";
                  const selected = s === (destinations.length ? "installed" : "stores") ? "selected" : "";
                  const label = s === "installed" ? "Install on another aircraft" : s;
                  return `<option value="${s}" ${disableInstall} ${selected}>${label}</option>`;
                }).join("")}
              </select>
            </label>
            <label class="mx-label" data-we-cfg-transfer-dest hidden>Destination aircraft
              <select class="mx-select" name="to_aircraft_id" ${destDisabled}>${destOpts}</select>
            </label>
            <label class="mx-label" data-we-cfg-transfer-pos hidden>Position
              <input class="mx-input" name="position" maxlength="80" placeholder="ENG1" />
            </label>
            <label class="mx-label">Aircraft hours
              <input class="mx-input" name="aircraft_hours" type="number" min="0" step="0.01" data-we-cfg-hours="snapshot" />
            </label>
            <label class="mx-label">Aircraft cycles
              <input class="mx-input" name="aircraft_cycles" type="number" min="0" step="1" data-we-cfg-cycles="snapshot" />
            </label>
            <label class="mx-label">Reason
              <input class="mx-input" name="reason" maxlength="200" />
            </label>
          </div>
          <button type="submit" class="mx-btn" ${installedDisabled}>Transfer</button>
        </form>
      </article>
      <article class="mx-card we-cfg-form-card">
        <div class="mx-card-header"><h3>Register serialized to stores</h3></div>
        <form id="weCfgRegisterForm" class="we-cfg-form" data-we-cfg-form="register">
          <div class="we-cfg-form-grid">
            <label class="mx-label">Catalog item
              <select class="mx-select" name="catalog_item_id" required>${catalogOpts || `<option value="">No catalog items</option>`}</select>
            </label>
            <label class="mx-label">Serial number
              <input class="mx-input" name="serial_number" required maxlength="120" />
            </label>
          </div>
          <button type="submit" class="mx-btn" ${catalog.length ? "" : "disabled"}>Register to stores</button>
        </form>
      </article>
    </div>
  `;
}

export function renderComponentOverview(session, record, bundle) {
  const canManage = sessionCanManageComponents(bundle?.sessionRole);
  const status = record?.component_status || record?.status || "—";
  const installed = String(status).toLowerCase() === "installed";
  const host = bundle?.hostAircraft;
  const hostLabel = host?.current_registration || host?.registration || record?.current_aircraft_id || "";
  const aircraftCell = record?.current_aircraft_id
    ? `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-open="aircraft:${esc(String(record.current_aircraft_id))}" data-we-label="${esc(hostLabel || record.current_aircraft_id)}">${esc(hostLabel || record.current_aircraft_id)}</button>`
    : "—";
  return `
    <div class="mx-grid mx-grid-3" style="margin-bottom:16px">
      <article class="mx-kpi"><div class="mx-label">Serial</div><div class="mx-kpi-value" style="font-size:18px">${esc(String(record?.serial_number || session.id))}</div></article>
      <article class="mx-kpi"><div class="mx-label">Part</div><div class="mx-kpi-value" style="font-size:18px">${esc(String(record?.part_number || "—"))}</div></article>
      <article class="mx-kpi"><div class="mx-label">Status</div><div class="mx-kpi-value" style="font-size:18px">${esc(String(status))}${installed ? "" : " · not installed"}</div></article>
    </div>
    <article class="mx-card we-cfg" data-we-cfg-root="1">
      <div class="mx-card-header">
        <h3>Component details</h3>
        <span class="mx-chip">${esc(installed ? `Installed · ${record?.installation_position || "position n/a"}` : String(status))}</span>
      </div>
      <div class="mx-table-wrap"><table class="mx-table"><tbody>
        <tr><th>Type</th><td>${esc(String(record?.component_type || "—"))}</td></tr>
        <tr><th>Manufacturer</th><td>${esc(String(record?.manufacturer_name || "—"))}</td></tr>
        <tr><th>Aircraft</th><td>${installed ? aircraftCell : "Not installed"}</td></tr>
        <tr><th>Position</th><td class="mx-mono">${esc(String(record?.installation_position || "—"))}</td></tr>
        <tr><th>Date installed</th><td>${esc(String(record?.date_installed || "—"))}</td></tr>
        <tr><th>Hours / cycles at install</th><td>${esc(formatRemaining(record?.aircraft_hours_at_install, record?.aircraft_cycles_at_install))}</td></tr>
        <tr><th>TSN / CSN</th><td>${esc(formatRemaining(record?.tsn_hours, record?.csn_cycles))}</td></tr>
        <tr><th>TSO / CSO</th><td>${esc(formatRemaining(record?.tso_hours, record?.cso_cycles))}</td></tr>
        <tr><th>Remaining</th><td>${esc(formatRemaining(record?.remaining_hours, record?.remaining_cycles))}</td></tr>
        <tr><th>Notes</th><td>${esc(String(record?.notes || "—"))}</td></tr>
      </tbody></table></div>
      <p class="we-cfg-msg" data-we-cfg-msg></p>
      ${
        canManage && installed
          ? `<form id="weCfgRemoveForm" class="we-cfg-form" data-we-cfg-form="remove" data-we-component-id="${esc(String(session.id))}">
              <div class="we-cfg-form-grid">
                <input type="hidden" name="component_id" value="${esc(String(session.id))}" />
                <label class="mx-label">Destination
                  <select class="mx-select" name="destination_status">${REMOVE_DESTINATIONS.map((s) => `<option value="${s}">${s}</option>`).join("")}</select>
                </label>
                <label class="mx-label">Aircraft hours
                  <input class="mx-input" name="aircraft_hours" type="number" min="0" step="0.01" data-we-cfg-hours="snapshot" />
                </label>
                <label class="mx-label">Aircraft cycles
                  <input class="mx-input" name="aircraft_cycles" type="number" min="0" step="1" data-we-cfg-cycles="snapshot" />
                </label>
                <label class="mx-label">Reason
                  <input class="mx-input" name="reason" maxlength="200" />
                </label>
              </div>
              <button type="submit" class="mx-btn">Remove from aircraft</button>
            </form>`
          : canManage
            ? `<p class="mx-subtitle">This component is not installed. Open an aircraft Configuration tab to install it from stores or maintenance.</p>`
            : ""
      }
    </article>
  `;
}

export function renderComponentInstallHistory(bundle) {
  const load = bundle?.historyLoad;
  if (load && !load.ok) {
    return `<div class="mx-empty">${esc(load.error || "Unable to load install history.")}</div>`;
  }
  const rows = Array.isArray(bundle?.installHistory) ? bundle.installHistory : [];
  if (!rows.length) return `<div class="mx-empty">No installation history for this component.</div>`;
  return `<div class="mx-table-wrap"><table class="mx-table"><thead><tr>
    <th>Event</th><th>Aircraft</th><th>Position</th><th>From</th><th>To</th><th>Actor</th><th>Reason</th><th>When</th>
  </tr></thead><tbody>${rows
    .map(
      (h) => `<tr>
        <td><span class="mx-chip">${esc(h.event_type || "—")}</span></td>
        <td class="mx-mono">${esc(h.aircraft_id || h.to_aircraft_id || "—")}</td>
        <td class="mx-mono">${esc(h.position || "—")}</td>
        <td>${esc(h.from_status || "—")}</td>
        <td>${esc(h.to_status || "—")}</td>
        <td>${esc(h.actor || "—")}</td>
        <td>${esc(h.reason || "—")}</td>
        <td>${esc(String(h.occurred_at || ""))}</td>
      </tr>`
    )
    .join("")}</tbody></table></div>`;
}

function setCfgMessage(text, kind) {
  const node = document.querySelector("[data-we-cfg-msg]");
  if (!node) return;
  node.textContent = text || "";
  node.classList.remove("is-error", "is-ok");
  if (kind) node.classList.add(kind === "error" ? "is-error" : "is-ok");
}

function formValues(form) {
  const data = new FormData(form);
  const out = {};
  data.forEach((value, key) => {
    out[key] = String(value ?? "").trim();
  });
  return out;
}

function parseHours(value) {
  if (value === "" || value == null) return 0;
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) return null;
  return n;
}

function parseCycles(value) {
  if (value === "" || value == null) return 0;
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || !Number.isInteger(n)) return null;
  return n;
}

function applyConfigurationFilter() {
  const ata = String(document.getElementById("weCfgAtaFilter")?.value || "");
  const q = String(document.getElementById("weCfgSearchFilter")?.value || "")
    .trim()
    .toLowerCase();
  const rows = document.querySelectorAll("[data-we-cfg-row]");
  let visible = 0;
  rows.forEach((row) => {
    const ataOk = !ata || row.getAttribute("data-we-cfg-ata") === ata;
    const text = row.getAttribute("data-we-cfg-text") || "";
    const qOk = !q || text.includes(q);
    const show = ataOk && qOk;
    row.hidden = !show;
    if (show) visible += 1;
  });
  document.querySelectorAll("[data-we-cfg-group]").forEach((header) => {
    const key = header.getAttribute("data-we-cfg-ata") || "";
    header.hidden = ![...rows].some((row) => !row.hidden && row.getAttribute("data-we-cfg-ata") === key);
  });
  const empty = document.getElementById("weCfgFilterEmpty");
  if (empty) empty.hidden = visible > 0 || !rows.length;
}

function syncTransferFields(form) {
  if (!form) return;
  const status = form.querySelector("[name='to_status']")?.value;
  const dest = form.querySelector("[data-we-cfg-transfer-dest]");
  const pos = form.querySelector("[data-we-cfg-transfer-pos]");
  const show = status === "installed";
  if (dest) dest.hidden = !show;
  if (pos) pos.hidden = !show;
}

function applySnapshotToForm(form, record) {
  if (!form) return;
  const hoursInput = form.querySelector("[data-we-cfg-hours='snapshot']");
  const cyclesInput = form.querySelector("[data-we-cfg-cycles='snapshot']");
  const resolved = resolveInstallationHoursCycles(record, "", "");
  if (hoursInput) hoursInput.value = resolved.ok ? String(resolved.hours) : "";
  if (cyclesInput) cyclesInput.value = resolved.ok ? String(resolved.cycles) : "";
}

function sourceAircraftId(session) {
  if (session?.type === "aircraft") return String(session.id || "");
  return session?.record?.current_aircraft_id ? String(session.record.current_aircraft_id) : "";
}

function normalizePosition(value) {
  return String(value || "").trim().toUpperCase();
}

function mutationErrorMessage(result) {
  if (!result) return "Request failed";
  if (result.status === 409) return result.error || "Configuration conflict (HTTP 409).";
  if (result.status === 403) return result.error || "You do not have permission to change configuration.";
  return result.error || `HTTP ${result.status}`;
}

async function runMutation(form, work, onRefresh) {
  const submit = form.querySelector("button[type='submit']");
  if (submit) submit.disabled = true;
  setCfgMessage("Working…", "");
  try {
    const result = await work();
    if (!result.ok) {
      const detail = mutationErrorMessage(result);
      setCfgMessage(detail, "error");
      toast(detail);
      return;
    }
    setCfgMessage("Configuration updated.", "ok");
    toast("Configuration updated");
    await onRefresh?.();
  } catch (err) {
    const detail = err?.message || "Request failed";
    setCfgMessage(detail, "error");
    toast(detail);
  } finally {
    if (submit) submit.disabled = false;
  }
}

export function bindConfigurationPanel(session, { onRefresh } = {}) {
  const root = document.querySelector("[data-we-cfg-root]");
  if (!root) return;

  document.getElementById("weCfgAtaFilter")?.addEventListener("change", applyConfigurationFilter);
  document.getElementById("weCfgSearchFilter")?.addEventListener("input", applyConfigurationFilter);

  root.querySelectorAll(".we-cfg-action-cell").forEach((cell) => {
    cell.addEventListener("click", (event) => event.stopPropagation());
  });

  const destOccupancy = new Map();
  const localOccupied = occupiedPositions(joinAircraftConfiguration(session.bundle));

  const bindSnapshotForm = (form) => {
    if (!form) return;
    const select = form.querySelector("[name='component_id']");
    const apply = () => applySnapshotToForm(form, serializedForComponent(session, select?.value));
    select?.addEventListener("change", apply);
    apply();
  };

  const loadDestOccupancy = async (aircraftId) => {
    const id = String(aircraftId || "");
    if (!id) return [];
    if (destOccupancy.has(id)) return destOccupancy.get(id);
    const res = await uxFetchAircraftConfiguration(id);
    const positions = occupiedPositions(res.ok ? res.data?.installed || [] : []);
    destOccupancy.set(id, positions);
    return positions;
  };

  root.querySelectorAll("[data-we-cfg-fill]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const id = btn.getAttribute("data-we-component-id");
      const kind = btn.getAttribute("data-we-cfg-fill");
      const form = document.getElementById(kind === "remove" ? "weCfgRemoveForm" : "weCfgTransferForm");
      const select = form?.querySelector("[name='component_id']");
      if (select && id) select.value = id;
      applySnapshotToForm(form, serializedForComponent(session, id));
      form?.scrollIntoView({ block: "nearest" });
    });
  });

  const transferForm = document.getElementById("weCfgTransferForm");
  transferForm?.querySelector("[data-we-cfg-transfer-status]")?.addEventListener("change", () => syncTransferFields(transferForm));
  transferForm?.querySelector("[name='to_aircraft_id']")?.addEventListener("change", (event) => {
    void loadDestOccupancy(event.target.value);
  });
  syncTransferFields(transferForm);
  bindSnapshotForm(document.getElementById("weCfgRemoveForm"));
  bindSnapshotForm(transferForm);

  document.getElementById("weCfgInstallForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const position = normalizePosition(values.position);
    if (!values.component_id) {
      setCfgMessage("Select a component to install.", "error");
      return;
    }
    if (!position) {
      setCfgMessage("Position is required.", "error");
      return;
    }
    if (localOccupied.includes(position)) {
      setCfgMessage(`Position ${position} is already occupied on this aircraft.`, "error");
      return;
    }
    const hours = parseHours(values.aircraft_hours);
    const cycles = parseCycles(values.aircraft_cycles);
    if (hours == null || cycles == null) {
      setCfgMessage("Aircraft hours and cycles must be zero or greater (cycles must be a whole number).", "error");
      return;
    }
    void runMutation(
      event.target,
      () =>
        uxInstallSerializedComponent(values.component_id, {
          aircraft_id: session.id,
          position,
          aircraft_hours: hours,
          aircraft_cycles: cycles,
          reason: values.reason || "",
          reference: values.reference || "",
        }),
      () =>
        onRefresh?.({
          componentId: values.component_id,
          sourceAircraftId: sourceAircraftId(session),
        })
    );
  });

  document.getElementById("weCfgRemoveForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    if (!values.component_id) {
      setCfgMessage("Select an installed component to remove.", "error");
      return;
    }
    if (!REMOVE_DESTINATIONS.includes(values.destination_status)) {
      setCfgMessage("Choose a valid destination status.", "error");
      return;
    }
    const serial = serializedForComponent(session, values.component_id);
    const resolved = resolveInstallationHoursCycles(serial, values.aircraft_hours, values.aircraft_cycles);
    if (!resolved.ok) {
      setCfgMessage(resolved.error, "error");
      return;
    }
    const confirmed = window.confirm(
      destructiveConfirmMessage("remove", {
        serial_number: serial?.serial_number,
        component_id: values.component_id,
        aircraft_label: session.label,
        aircraft_id: sourceAircraftId(session),
        position: serial?.installation_position || serial?.position,
        destination_status: values.destination_status,
      })
    );
    if (!confirmed) return;
    void runMutation(
      event.target,
      () =>
        uxRemoveSerializedComponent(values.component_id, {
          destination_status: values.destination_status,
          aircraft_hours: resolved.hours,
          aircraft_cycles: resolved.cycles,
          reason: values.reason || "",
        }),
      () =>
        onRefresh?.({
          componentId: values.component_id,
          sourceAircraftId: sourceAircraftId(session),
        })
    );
  });

  document.getElementById("weCfgTransferForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    if (!values.component_id) {
      setCfgMessage("Select a component to transfer.", "error");
      return;
    }
    if (!TRANSFER_STATUSES.includes(values.to_status)) {
      setCfgMessage("Choose a valid transfer status.", "error");
      return;
    }
    const serial = serializedForComponent(session, values.component_id);
    const resolved = resolveInstallationHoursCycles(serial, values.aircraft_hours, values.aircraft_cycles);
    if (!resolved.ok) {
      setCfgMessage(resolved.error, "error");
      return;
    }
    const payload = {
      to_status: values.to_status,
      aircraft_hours: resolved.hours,
      aircraft_cycles: resolved.cycles,
      reason: values.reason || "",
    };
    if (values.to_status === "installed") {
      if (!values.to_aircraft_id) {
        setCfgMessage("On-wing transfer needs a destination aircraft.", "error");
        return;
      }
      const destPosition = normalizePosition(values.position);
      if (!destPosition) {
        setCfgMessage("Position is required to install on another aircraft.", "error");
        return;
      }
      payload.to_aircraft_id = values.to_aircraft_id;
      payload.position = destPosition;
    }
    const destRow = (session.bundle?.fleetAircraft || []).find((row) => String(row.id) === String(values.to_aircraft_id));
    const confirmed = window.confirm(
      destructiveConfirmMessage("transfer", {
        serial_number: serial?.serial_number,
        component_id: values.component_id,
        aircraft_label: session.label,
        aircraft_id: sourceAircraftId(session),
        to_status: values.to_status,
        to_aircraft_id: values.to_aircraft_id,
        dest_label: destRow ? destRow.current_registration || destRow.id : values.to_aircraft_id,
        dest_position: payload.position,
      })
    );
    if (!confirmed) return;
    void (async () => {
      if (values.to_status === "installed") {
        const destTaken = await loadDestOccupancy(values.to_aircraft_id);
        if (destTaken.includes(normalizePosition(payload.position))) {
          setCfgMessage(`Position ${payload.position} is already occupied on the destination aircraft.`, "error");
          return;
        }
      }
      await runMutation(
        event.target,
        () => uxTransferSerializedComponent(values.component_id, payload),
        () =>
          onRefresh?.({
            componentId: values.component_id,
            sourceAircraftId: sourceAircraftId(session),
            destinationAircraftId: values.to_status === "installed" ? values.to_aircraft_id : "",
          })
      );
    })();
  });

  document.getElementById("weCfgRegisterForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    if (!values.catalog_item_id || !values.serial_number) {
      setCfgMessage("Catalog item and serial number are required.", "error");
      return;
    }
    void runMutation(
      event.target,
      () =>
        uxCreateSerializedComponent({
          catalog_item_id: values.catalog_item_id,
          serial_number: values.serial_number,
          component_status: "stores",
        }),
      () => onRefresh?.({ sourceAircraftId: sourceAircraftId(session) })
    );
  });
}
