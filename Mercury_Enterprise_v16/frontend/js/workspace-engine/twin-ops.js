/**
 * Digital Twin operator UI (Workspace Engine + shared helpers).
 * Uses existing /api/v1/twin routes. Not a 3D modeler. No invented analytics.
 */

import { esc, toast } from "../utils.js";
import { listify, softMutate } from "../ux2/api.js";
import { mutationErrorMessage, runLocked } from "./logistics-ops.js";

export const TWIN_TYPES = [
  "aircraft",
  "engine",
  "apu",
  "landing_gear",
  "propeller",
  "flight_control",
  "serialized_component",
  "non_serialized_component",
  "tool",
  "test_equipment",
  "gse",
  "hangar",
  "facility",
  "organization",
  "personnel",
];

export const LIFECYCLE_STATES = [
  "manufactured",
  "delivered",
  "installed",
  "operated",
  "removed",
  "inspected",
  "repaired",
  "modified",
  "transferred",
  "stored",
  "returned",
  "scrapped",
  "retired",
  "archived",
];

export const HISTORY_KINDS = [
  "ownership",
  "configuration",
  "installation",
  "removal",
  "maintenance",
  "inspection",
  "repair",
  "modification",
  "sb_compliance",
  "ad_compliance",
  "llp",
  "utilization",
  "failure",
  "certificate",
  "document",
  "publication",
  "signature",
  "audit",
  "lifecycle",
];

export const CONFIG_BASELINES = ["current", "previous", "future_planned"];

export const RELIABILITY_METRICS = [
  "mtbur",
  "mtbf",
  "dispatch_reliability",
  "failure_rate",
  "repeat_defects",
  "deferred_defects",
  "trend_analysis",
];

export const PASSPORT_KIND_MAP = {
  aircraft: "aircraft",
  engine: "component",
  apu: "component",
  landing_gear: "component",
  propeller: "component",
  flight_control: "component",
  serialized_component: "component",
  non_serialized_component: "component",
  tool: "tool",
  test_equipment: "tool",
  gse: "tool",
  hangar: "organization",
  facility: "organization",
  organization: "organization",
  personnel: "personnel",
};

export function normalizeRole(role) {
  return String(role || "").trim();
}

export function sessionCanReadTwins(role) {
  const value = normalizeRole(role);
  return value === "Viewer" || value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function sessionCanManageTwins(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Administrator";
}

export function defaultLifecycleForType(twinType) {
  return String(twinType || "") === "aircraft" ? "operated" : "delivered";
}

export function isTerminalLifecycle(state) {
  return ["retired", "archived", "scrapped"].includes(String(state || ""));
}

export function fabricEntityTypeForTwinType(twinType) {
  return PASSPORT_KIND_MAP[String(twinType || "")] || String(twinType || "");
}

export function bindTwinType(hostType) {
  if (hostType === "aircraft") return "aircraft";
  if (hostType === "tool") return "tool";
  if (hostType === "component") return "serialized_component";
  return "serialized_component";
}

export function bindFabricEntityType(hostType) {
  if (hostType === "aircraft") return "aircraft";
  if (hostType === "tool") return "tool";
  if (hostType === "component") return "serialized_component";
  return String(hostType || "");
}

export function matchTwinToEntity(twins, { entityId, entityType = "" } = {}) {
  const id = String(entityId || "");
  const type = String(entityType || "").toLowerCase();
  const rows = Array.isArray(twins) ? twins : [];
  if (!id) return null;
  const typed = type
    ? rows.find(
        (row) =>
          String(row.fabric_entity_id || row.linked_entity_id || row.entity_id || "") === id &&
          String(row.fabric_entity_type || row.linked_entity_type || row.entity_type || "")
            .toLowerCase()
            .includes(type)
      )
    : null;
  return (
    typed ||
    rows.find((row) => String(row.fabric_entity_id || row.linked_entity_id || row.entity_id || "") === id) ||
    null
  );
}

export function filterTwins(rows, { q = "", twinType = "", lifecycle = "" } = {}) {
  const query = String(q || "").trim().toLowerCase();
  const type = String(twinType || "").trim().toLowerCase();
  const life = String(lifecycle || "").trim().toLowerCase();
  return (Array.isArray(rows) ? rows : []).filter((row) => {
    if (type && String(row.twin_type || "").toLowerCase() !== type) return false;
    if (life && String(row.lifecycle_state || "").toLowerCase() !== life) return false;
    if (!query) return true;
    const hay = `${row.display_name || ""} ${row.name || ""} ${row.twin_uuid || ""} ${row.serial_number || ""} ${row.part_number || ""} ${row.passport_id || ""} ${row.fabric_entity_id || ""} ${row.id || ""}`.toLowerCase();
    return hay.includes(query);
  });
}

export function twinSearchQuery({ q = "", twinType = "" } = {}) {
  const params = new URLSearchParams();
  if (q) params.set("q", String(q).trim());
  if (twinType) params.set("twin_type", twinType);
  params.set("limit", "40");
  return `/twin/search?${params.toString()}`;
}

export function twinRelationshipRows(rel) {
  if (!rel) return [];
  if (Array.isArray(rel)) return rel;
  if (Array.isArray(rel.fabric_relationships)) return rel.fabric_relationships;
  if (Array.isArray(rel.links)) return rel.links;
  if (Array.isArray(rel.relationships)) return rel.relationships;
  if (Array.isArray(rel.items)) return rel.items;
  return [];
}

export function linkedAssetTarget(record) {
  const entityType = String(record?.fabric_entity_type || "").toLowerCase();
  const entityId = String(record?.fabric_entity_id || "").trim();
  if (!entityId) return null;
  if (entityType.includes("aircraft")) return { type: "aircraft", id: entityId, label: entityId };
  if (entityType.includes("tool") || entityType === "gse") return { type: "tool", id: entityId, label: entityId };
  if (entityType.includes("component")) return { type: "component", id: entityId, label: entityId };
  return null;
}

export function twinOpsCacheKeys(session, mutation = {}) {
  const twins = [];
  const aircraft = [];
  const components = [];
  const tools = [];
  const push = (list, value) => {
    const id = String(value || "").trim();
    if (id && !list.includes(id)) list.push(id);
  };
  if (session?.type === "digitalTwin") push(twins, session.id);
  if (session?.type === "aircraft") push(aircraft, session.id);
  if (session?.type === "component") push(components, session.id);
  if (session?.type === "tool") push(tools, session.id);
  push(twins, mutation.twinId);
  push(aircraft, mutation.aircraftId);
  push(components, mutation.componentId);
  push(tools, mutation.toolId);
  const twin = session?.record || {};
  const linked = linkedAssetTarget(twin);
  if (linked?.type === "aircraft") push(aircraft, linked.id);
  if (linked?.type === "component") push(components, linked.id);
  if (linked?.type === "tool") push(tools, linked.id);
  return { twins, aircraft, components, tools };
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

function optionHtml(values, selected) {
  return (Array.isArray(values) ? values : [])
    .map((value) => `<option value="${esc(value)}"${String(value) === String(selected || "") ? " selected" : ""}>${esc(value)}</option>`)
    .join("");
}

function twinChip(row) {
  if (!row?.id) return "";
  const label = row.display_name || row.name || row.twin_uuid || row.id;
  return `<button type="button" class="mx-chip" data-we-open="digitalTwin:${esc(String(row.id))}" data-we-label="${esc(label)}">${esc(label)}</button>`;
}

function linkedAssetButton(record) {
  const target = linkedAssetTarget(record);
  if (!target) return "";
  return `<button type="button" class="mx-chip" data-we-open="${esc(target.type)}:${esc(target.id)}" data-we-label="${esc(target.label)}">Open ${esc(target.type)} ${esc(target.id)}</button>`;
}

export function renderTwinOverview(session, record, bundle) {
  const row = record || {};
  const canManage = sessionCanManageTwins(role(bundle));
  const label = row.display_name || row.name || session.label || session.id;
  return `
    ${loadBanner(bundle?.recordLoad, "Twin")}
    <div class="mx-grid mx-grid-3" style="margin-bottom:16px">
      <article class="mx-kpi"><div class="mx-label">Twin</div><div class="mx-kpi-value" style="font-size:18px">${esc(String(label))}</div></article>
      <article class="mx-kpi"><div class="mx-label">Type</div><div class="mx-kpi-value" style="font-size:18px">${esc(row.twin_type || "—")}</div></article>
      <article class="mx-kpi"><div class="mx-label">Lifecycle</div><div class="mx-kpi-value" style="font-size:18px">${esc(row.lifecycle_state || row.status || "—")}</div></article>
    </div>
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(label)}</h3><span class="mx-chip">${esc(row.status || "active")}</span></div>
      <p class="mx-subtitle">UUID ${esc(row.twin_uuid || "—")} · serial ${esc(row.serial_number || "—")} · PN ${esc(row.part_number || "—")}</p>
      <p class="mx-subtitle">Passport ${esc(row.passport_id || "—")} · entity ${esc(row.fabric_entity_type || "—")} ${esc(row.fabric_entity_id || "")}</p>
      <p class="mx-subtitle">History ${esc(String(row.history_count ?? bundle?.history?.length ?? "—"))} · configurations ${esc(String(row.configuration_count ?? bundle?.configurations?.length ?? "—"))} · reliability ${esc(String(row.reliability_count ?? bundle?.reliability?.length ?? "—"))}</p>
      <p class="mx-subtitle">${esc(row.disclaimer || "Mercury Digital Twin is the complete digital lifecycle of aviation assets — not a 3D model. Passports never disappear; history is immutable.")}</p>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">
        ${twinChip(row)}
        ${linkedAssetButton(row)}
        <button type="button" class="mx-chip" data-ux2-goto="assetTwin">Digital Twin desk</button>
      </div>
    </article>
    ${
      canManage
        ? `<form id="weTwinLifecycleForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Lifecycle transition</strong>
            <input type="hidden" name="twin_id" value="${esc(String(row.id || session.id))}" />
            <label class="mx-field">To state<select class="mx-input" name="to_state" required>${optionHtml(LIFECYCLE_STATES, row.lifecycle_state)}</select></label>
            <label class="mx-field">Summary<input class="mx-input" name="summary" maxlength="400" placeholder="Reason / reference" /></label>
            <label class="mx-field">Related ref<input class="mx-input" name="related_ref" maxlength="200" placeholder="WO / finding / other" /></label>
            <button class="mx-btn" type="submit">Transition lifecycle</button>
            <p class="mx-subtitle">Retired / archived / scrapped retain the twin row. Passports never disappear.</p>
          </form>`
        : `<p class="mx-subtitle">Lifecycle transitions require twin.manage (Operator or Administrator). Viewer/Reviewer can inspect.</p>`
    }
    <p class="mx-subtitle" id="weTwinMsg"></p>
  `;
}

export function renderTwinPassport(session, record, bundle) {
  const passport = bundle?.passport || {};
  const row = record || {};
  return `
    ${loadBanner(bundle?.passportLoad, "Passport")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>Digital Passport</h3><span class="mx-chip mx-chip-ok">Never disappears</span></div>
      <p class="mx-subtitle">Twin UUID ${esc(passport.twin_uuid || row.twin_uuid || "—")}</p>
      <p class="mx-subtitle">Passport ${esc(passport.passport_id || row.passport_id || "—")} · number ${esc(passport.passport_number || "—")} · lifecycle ${esc(passport.passport_lifecycle || "—")}</p>
      <p class="mx-subtitle">Entity ${esc(passport.entity_type || row.fabric_entity_type || "—")} ${esc(passport.entity_id || row.fabric_entity_id || "")}</p>
      <p class="mx-subtitle">History immutable: ${esc(String(passport.history_immutable ?? true))} · never disappears: ${esc(String(passport.never_disappears ?? true))}</p>
      <p class="mx-subtitle">${esc(passport.disclaimer || row.disclaimer || "Not a 3D model.")}</p>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">${linkedAssetButton(row)}</div>
    </article>
  `;
}

export function renderTwinConfiguration(session, record, bundle) {
  const rows = bundle?.configurations || [];
  const canManage = sessionCanManageTwins(role(bundle));
  const twinId = record?.id || session.id;
  return `
    ${loadBanner(bundle?.configurationsLoad, "Configurations")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>Configuration baselines</h3><span class="mx-chip">current / previous / planned</span></div>
      ${
        rows.length
          ? table(
              ["Baseline", "Version", "Status", "Created"],
              rows
                .map(
                  (row) => `<tr>
                    <td>${esc(row.baseline || "—")}</td>
                    <td class="mx-mono">${esc(row.version_label || row.id || "—")}</td>
                    <td><span class="mx-chip">${esc(row.status || "—")}</span></td>
                    <td>${esc(String(row.created_at || "—").slice(0, 19))}</td>
                  </tr>`
                )
                .join("")
            )
          : empty("No configuration snapshots for this twin.")
      }
    </article>
    ${
      canManage
        ? `<form id="weTwinConfigForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Record configuration snapshot</strong>
            <input type="hidden" name="twin_id" value="${esc(String(twinId))}" />
            <label class="mx-field">Baseline<select class="mx-input" name="baseline">${optionHtml(CONFIG_BASELINES, "current")}</select></label>
            <label class="mx-field">Version label<input class="mx-input" name="version_label" maxlength="80" placeholder="CFG-2" /></label>
            <label class="mx-field">Configuration JSON<textarea class="mx-textarea" name="configuration_json" rows="3">{}</textarea></label>
            <label class="mx-field"><input type="checkbox" name="set_as_current" checked /> Set as current when baseline is current</label>
            <button class="mx-btn" type="submit">Create configuration</button>
          </form>`
        : `<p class="mx-subtitle">Configuration create requires twin.manage (Operator or Administrator).</p>`
    }
    <p class="mx-subtitle" id="weTwinMsg"></p>
  `;
}

export function renderTwinHistory(session, record, bundle) {
  const rows = bundle?.history || bundle?.twinHistory || [];
  const canManage = sessionCanManageTwins(role(bundle));
  const twinId = record?.id || session.id;
  return `
    ${loadBanner(bundle?.historyLoad, "History")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>Immutable history</h3><span class="mx-chip">Append-only</span></div>
      ${
        rows.length
          ? table(
              ["When", "Kind", "Title", "Actor", "Ref"],
              rows
                .map(
                  (row) => `<tr>
                    <td>${esc(String(row.occurred_at || row.created_at || "—").slice(0, 19))}</td>
                    <td>${esc(row.history_kind || "—")}</td>
                    <td>${esc(row.title || row.summary || "—")}</td>
                    <td>${esc(row.actor || "—")}</td>
                    <td class="mx-mono">${esc(row.related_ref || "—")}</td>
                  </tr>`
                )
                .join("")
            )
          : empty("No history entries.")
      }
    </article>
    ${
      canManage
        ? `<form id="weTwinHistoryForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Append history event</strong>
            <input type="hidden" name="twin_id" value="${esc(String(twinId))}" />
            <label class="mx-field">Kind<select class="mx-input" name="history_kind" required>${optionHtml(HISTORY_KINDS, "inspection")}</select></label>
            <label class="mx-field">Title<input class="mx-input" name="title" maxlength="300" placeholder="Title" /></label>
            <label class="mx-field">Summary<input class="mx-input" name="summary" maxlength="400" /></label>
            <label class="mx-field">Related ref<input class="mx-input" name="related_ref" maxlength="200" placeholder="WO / AD / other" /></label>
            <button class="mx-btn" type="submit">Append history</button>
            <p class="mx-subtitle">History cannot be edited or deleted.</p>
          </form>`
        : `<p class="mx-subtitle">History append requires twin.manage (Operator or Administrator).</p>`
    }
    <p class="mx-subtitle" id="weTwinMsg"></p>
  `;
}

export function renderTwinReliability(session, record, bundle) {
  const rows = bundle?.reliability || [];
  const canManage = sessionCanManageTwins(role(bundle));
  const twinId = record?.id || session.id;
  return `
    ${loadBanner(bundle?.reliabilityLoad, "Reliability")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>Reliability</h3><span class="mx-chip mx-chip-warn">Architecture only</span></div>
      <p class="mx-subtitle">Published snapshots only. Mercury does not invent live MTBUR/MTBF engines or ML forecasts.</p>
      ${
        rows.length
          ? table(
              ["Metric", "Value", "Unit", "Window"],
              rows
                .map(
                  (row) => `<tr>
                    <td>${esc(row.metric_code || "—")}</td>
                    <td>${esc(String(row.metric_value ?? row.value ?? "—"))}</td>
                    <td>${esc(row.unit || "—")}</td>
                    <td>${esc(row.window_label || row.window || "—")}</td>
                  </tr>`
                )
                .join("")
            )
          : empty("No reliability metrics recorded.")
      }
    </article>
    ${
      canManage
        ? `<form id="weTwinReliabilityForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Publish reliability snapshot</strong>
            <input type="hidden" name="twin_id" value="${esc(String(twinId))}" />
            <label class="mx-field">Metric<select class="mx-input" name="metric_code" required>${optionHtml(RELIABILITY_METRICS, "mtbur")}</select></label>
            <label class="mx-field">Value<input class="mx-input" name="metric_value" maxlength="80" /></label>
            <label class="mx-field">Unit<input class="mx-input" name="unit" maxlength="40" placeholder="hours" /></label>
            <label class="mx-field">Window<input class="mx-input" name="window_label" maxlength="80" placeholder="rolling_12m" /></label>
            <button class="mx-btn" type="submit">Create snapshot</button>
          </form>`
        : `<p class="mx-subtitle">Reliability publish requires twin.manage (Operator or Administrator).</p>`
    }
    <p class="mx-subtitle" id="weTwinMsg"></p>
  `;
}

export function renderTwinRelationships(session, record, bundle) {
  const rel = bundle?.relationships;
  const links = twinRelationshipRows(rel);
  const hint = rel && !Array.isArray(rel) ? rel.digital_thread_hint || "" : "";
  return `
    ${loadBanner(bundle?.relationshipsLoad, "Relationships")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>Passport relationships</h3></div>
      <p class="mx-subtitle">Edges come from Universal Data Fabric. Twin UI does not invent graph links.</p>
      ${
        links.length
          ? table(
              ["Relation", "From", "To", "Cardinality"],
              links
                .map(
                  (row) => `<tr>
                    <td>${esc(row.relationship_type || row.relation_type || row.kind || "link")}</td>
                    <td class="mx-mono">${esc(row.from_passport_id || row.target_id || "—")}</td>
                    <td class="mx-mono">${esc(row.to_passport_id || row.related_id || row.id || "—")}</td>
                    <td>${esc(row.cardinality || row.target_type || "—")}</td>
                  </tr>`
                )
                .join("")
            )
          : empty("No fabric relationships for this twin passport.")
      }
      ${hint ? `<p class="mx-subtitle mx-mono">${esc(hint)}</p>` : ""}
      <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">${linkedAssetButton(record)}</div>
    </article>
  `;
}

export function renderHostTwinPanel(session, record, bundle) {
  const twin = bundle?.twin;
  const canManage = sessionCanManageTwins(role(bundle));
  const hostType = session.type;
  const label = session.label || record?.registration || record?.serial_number || session.id;
  const metrics = bundle?.reliability || [];
  return `
    ${loadBanner(bundle?.twinsLoad, "Twin registry")}
    <div class="mx-twin-stage we-twin">
      <div class="mx-twin-hud"><span class="mx-chip">Digital Twin</span><span class="mx-chip mx-chip-ok">Not a 3D model</span><span class="mx-chip">${esc(twin?.lifecycle_state || "unbound")}</span></div>
      <div class="mx-twin-orbit"></div>
      <div class="mx-twin-core">${esc(twin?.display_name || twin?.name || label)}</div>
    </div>
    ${
      twin
        ? `<p class="mx-subtitle" style="margin-top:12px">Bound twin ${esc(twin.twin_uuid || twin.id)} · ${esc(twin.twin_type || "")} · passport ${esc(twin.passport_id || "—")}</p>
           <div class="mx-row" style="flex-wrap:wrap;gap:8px">${twinChip(twin)}
             <button type="button" class="mx-btn mx-btn-ghost" data-we-open="digitalTwin:${esc(String(twin.id))}" data-we-tab="history">History</button>
             <button type="button" class="mx-btn mx-btn-ghost" data-we-open="digitalTwin:${esc(String(twin.id))}" data-we-tab="configuration">Configuration</button>
             <button type="button" class="mx-btn mx-btn-ghost" data-we-open="digitalTwin:${esc(String(twin.id))}" data-we-tab="reliability">Reliability</button>
           </div>
           ${
             metrics.length
               ? table(
                   ["Metric", "Value", "Window"],
                   metrics
                     .slice(0, 8)
                     .map(
                       (row) => `<tr><td>${esc(row.metric_code || "—")}</td><td>${esc(String(row.metric_value ?? "—"))}</td><td>${esc(row.window_label || "—")}</td></tr>`
                     )
                     .join("")
                 )
               : `<p class="mx-subtitle">Reliability snapshots appear on the twin object when published.</p>`
           }`
        : `<p class="mx-subtitle" style="margin-top:12px">No twin linked to this ${esc(hostType)}. Register from this panel or the Digital Twin desk.</p>`
    }
    ${
      !twin && canManage && (hostType === "aircraft" || hostType === "component" || hostType === "tool")
        ? `<form id="weTwinBindForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Register bound twin</strong>
            <input type="hidden" name="host_type" value="${esc(hostType)}" />
            <input type="hidden" name="fabric_entity_id" value="${esc(String(session.id))}" />
            <input type="hidden" name="twin_type" value="${esc(bindTwinType(hostType))}" />
            <input type="hidden" name="fabric_entity_type" value="${esc(bindFabricEntityType(hostType))}" />
            <input type="hidden" name="lifecycle_state" value="${esc(defaultLifecycleForType(bindTwinType(hostType)))}" />
            <label class="mx-field">Display name<input class="mx-input" name="display_name" required maxlength="400" value="${esc(String(label))}" /></label>
            <label class="mx-field">Serial<input class="mx-input" name="serial_number" maxlength="120" value="${esc(String(record?.serial_number || record?.tool_code || ""))}" /></label>
            <label class="mx-field">Part number<input class="mx-input" name="part_number" maxlength="120" value="${esc(String(record?.part_number || ""))}" /></label>
            <button class="mx-btn" type="submit">Create twin + passport</button>
          </form>`
        : ""
    }
    ${!canManage && !twin ? `<p class="mx-subtitle">Twin registration requires twin.manage (Operator or Administrator).</p>` : ""}
    <p class="mx-subtitle" id="weTwinMsg"></p>
  `;
}

function setTwinMessage(text, ok) {
  const node = document.getElementById("weTwinMsg") || document.getElementById("twinOpsMsg");
  if (!node) return;
  node.textContent = text || "";
  node.style.color = ok ? "" : "var(--danger, #c44)";
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

export function bindTwinOpsPanel(active, { onRefresh } = {}) {
  if (!active) return;
  const fail = (result) => {
    const msg = mutationErrorMessage(result);
    setTwinMessage(msg, false);
    toast(msg);
  };

  document.getElementById("weTwinLifecycleForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManageTwins(role(active.bundle))) return fail({ status: 403, error: "twin.manage required" });
    const values = formValues(event.target);
    if (isTerminalLifecycle(values.to_state) && !window.confirm(`Transition ${active.label || values.twin_id} to ${values.to_state}? The twin row is retained.`)) {
      return;
    }
    const result = await runLocked(`twin-life:${values.twin_id}`, () =>
      softMutate(`/twin/twins/${encodeURIComponent(values.twin_id)}/lifecycle`, {
        body: { to_state: values.to_state, summary: values.summary || "", related_ref: values.related_ref || "" },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Lifecycle ${result.data?.lifecycle_state || values.to_state}`);
    await onRefresh?.({ twinId: values.twin_id });
  });

  document.getElementById("weTwinHistoryForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManageTwins(role(active.bundle))) return fail({ status: 403, error: "twin.manage required" });
    const values = formValues(event.target);
    const result = await runLocked(`twin-hist:${values.twin_id}`, () =>
      softMutate(`/twin/twins/${encodeURIComponent(values.twin_id)}/history`, {
        body: {
          history_kind: values.history_kind,
          title: values.title || "",
          summary: values.summary || "",
          related_ref: values.related_ref || "",
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("History appended");
    await onRefresh?.({ twinId: values.twin_id });
  });

  document.getElementById("weTwinConfigForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManageTwins(role(active.bundle))) return fail({ status: 403, error: "twin.manage required" });
    const values = formValues(event.target);
    let configurationJson = values.configuration_json || "{}";
    try {
      JSON.parse(configurationJson);
    } catch {
      return fail({ status: 422, error: "configuration_json must be valid JSON" });
    }
    const result = await runLocked(`twin-cfg:${values.twin_id}`, () =>
      softMutate(`/twin/twins/${encodeURIComponent(values.twin_id)}/configurations`, {
        body: {
          baseline: values.baseline || "current",
          version_label: values.version_label || "",
          configuration_json: configurationJson,
          set_as_current: Boolean(values.set_as_current),
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Configuration ${result.data?.baseline || ""} recorded`);
    await onRefresh?.({ twinId: values.twin_id });
  });

  document.getElementById("weTwinReliabilityForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManageTwins(role(active.bundle))) return fail({ status: 403, error: "twin.manage required" });
    const values = formValues(event.target);
    const result = await runLocked(`twin-rel:${values.twin_id}`, () =>
      softMutate(`/twin/twins/${encodeURIComponent(values.twin_id)}/reliability`, {
        body: {
          metric_code: values.metric_code,
          metric_value: values.metric_value || "",
          unit: values.unit || "",
          window_label: values.window_label || "",
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Reliability ${result.data?.metric_code || ""} published`);
    await onRefresh?.({ twinId: values.twin_id });
  });

  document.getElementById("weTwinBindForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManageTwins(role(active.bundle))) return fail({ status: 403, error: "twin.manage required" });
    const values = formValues(event.target);
    const hostType = values.host_type || active.type;
    const result = await runLocked(`twin-bind:${hostType}:${values.fabric_entity_id}`, () =>
      softMutate("/twin/twins", {
        body: {
          twin_type: values.twin_type || bindTwinType(hostType),
          display_name: String(values.display_name || "").trim(),
          serial_number: values.serial_number || "",
          part_number: values.part_number || "",
          fabric_entity_type: values.fabric_entity_type || bindFabricEntityType(hostType),
          fabric_entity_id: values.fabric_entity_id,
          lifecycle_state: values.lifecycle_state || defaultLifecycleForType(values.twin_type),
          ensure_passport: true,
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Twin registered");
    await onRefresh?.({
      twinId: result.data?.id,
      aircraftId: hostType === "aircraft" ? values.fabric_entity_id : "",
      componentId: hostType === "component" ? values.fabric_entity_id : "",
      toolId: hostType === "tool" ? values.fabric_entity_id : "",
    });
  });
}
