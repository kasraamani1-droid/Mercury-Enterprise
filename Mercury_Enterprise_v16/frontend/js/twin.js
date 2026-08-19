import { el, esc } from "./utils.js";
import { getSessionStatus } from "./api.js";
import { listify, softGet, softMutate } from "./ux2/api.js";
import { mutationErrorMessage, runLocked } from "./workspace-engine/logistics-ops.js";
import {
  LIFECYCLE_STATES,
  TWIN_TYPES,
  defaultLifecycleForType,
  fabricEntityTypeForTwinType,
  filterTwins,
  sessionCanManageTwins,
  sessionCanReadTwins,
  twinSearchQuery,
} from "./workspace-engine/twin-ops.js";

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
  const node = el("twinStatus");
  if (node) node.textContent = text || "";
}

function empty(text) {
  return `<div class="empty">${esc(text)}</div>`;
}

function optionList(rows, valueKey, labelFn, selected) {
  return (Array.isArray(rows) ? rows : [])
    .map((row) => {
      const id = String(row[valueKey] || row.id || row);
      return `<option value="${esc(id)}"${id === String(selected || "") ? " selected" : ""}>${esc(typeof labelFn === "function" ? labelFn(row) : id)}</option>`;
    })
    .join("");
}

function renderRows(hostId, html, fallback) {
  const host = el(hostId);
  if (!host) return;
  host.innerHTML = html || empty(fallback);
}

function renderDesk({ canManage, aircraft, components, tools }) {
  const host = el("twinOpsDesk");
  if (!host) return;
  if (!canManage) {
    host.innerHTML = `<p class="muted">Twin mutations require twin.manage (Operator or Administrator). Viewer/Reviewer can inspect the registry, passport, history, configuration, and reliability.</p>`;
    return;
  }
  host.innerHTML = `
    <article class="card">
      <h3>Register twin</h3>
      <form data-twin-action="create">
        <select name="twin_type" required>
          <option value="">Twin type</option>
          ${TWIN_TYPES.map((type) => `<option value="${esc(type)}">${esc(type)}</option>`).join("")}
        </select>
        <input name="display_name" required maxlength="400" placeholder="Display name" />
        <input name="serial_number" maxlength="120" placeholder="Serial number" />
        <input name="part_number" maxlength="120" placeholder="Part number" />
        <select name="lifecycle_state">${LIFECYCLE_STATES.map((state) => `<option value="${esc(state)}"${state === "delivered" ? " selected" : ""}>${esc(state)}</option>`).join("")}</select>
        <select name="aircraft_id"><option value="">Bind aircraft (optional)</option>${optionList(aircraft, "id", (row) => row.registration || row.id)}</select>
        <select name="component_id"><option value="">Bind serialized component (optional)</option>${optionList(components, "id", (row) => `${row.serial_number || row.id} · ${row.part_number || ""}`)}</select>
        <select name="tool_id"><option value="">Bind tool (optional)</option>${optionList(tools, "id", (row) => row.tool_code || row.description || row.id)}</select>
        <input name="fabric_entity_id" maxlength="80" placeholder="Or fabric entity id" />
        <label class="muted"><input type="checkbox" name="ensure_passport" checked /> Ensure digital passport</label>
        <button type="submit">Create twin</button>
      </form>
      <p class="muted">Lifecycle vocabularies match /api/v1/twin. Duplicate type+serial+PN returns 409. Reliability is architecture-only.</p>
    </article>
    <p class="muted" id="twinOpsMsg"></p>
  `;
}

export async function refreshAssetTwinWorkspace() {
  const generation = ++refreshGeneration;
  setStatus("Loading twins…");
  const session = await getSessionStatus().catch(() => null);
  lastRole = session?.role || "";
  if (!sessionCanReadTwins(lastRole) && session?.role) {
    setStatus("Twin read is not granted for this session.");
  }

  const q = el("twinSearch")?.value || "";
  const twinType = el("twinTypeFilter")?.value || "";
  const lifecycle = el("twinLifecycleFilter")?.value || "";
  const listPath = twinType ? `/twin/twins?twin_type=${encodeURIComponent(twinType)}&limit=100` : "/twin/twins?limit=100";
  const [
    overview,
    twins,
    search,
    aircraft,
    components,
    tools,
  ] = await Promise.all([
    softGet("/twin/overview"),
    softGet(listPath),
    q ? softGet(twinSearchQuery({ q, twinType })) : Promise.resolve({ ok: true, data: { items: [] } }),
    softGet("/fleet/aircraft?limit=100"),
    softGet("/components/serialized"),
    softGet("/logistics/tools?limit=80"),
  ]);
  if (generation !== refreshGeneration) return;

  const failed = [overview, twins].filter((res) => !res.ok);
  setStatus(failed.length ? `Partial load: ${failed.map((res) => res.error || `HTTP ${res.status}`).join("; ")}` : "Live digital twin registry.");

  const typeEl = el("twinTypeFilter");
  if (typeEl && typeEl.options.length <= 1) {
    typeEl.innerHTML = `<option value="">All types</option>` + TWIN_TYPES.map((type) => `<option value="${esc(type)}">${esc(type)}</option>`).join("");
    if (twinType) typeEl.value = twinType;
  }
  const lifeEl = el("twinLifecycleFilter");
  if (lifeEl && lifeEl.options.length <= 1) {
    lifeEl.innerHTML = `<option value="">All lifecycle</option>` + LIFECYCLE_STATES.map((state) => `<option value="${esc(state)}">${esc(state)}</option>`).join("");
    if (lifecycle) lifeEl.value = lifecycle;
  }

  const twinRows = filterTwins(listify(twins.data), { q, twinType: "", lifecycle });
  const first = twinRows[0];
  const ov = overview.ok ? overview.data : {};
  const searchHits = listify(search.data?.items || search.data);

  renderDesk({
    canManage: sessionCanManageTwins(lastRole),
    aircraft: listify(aircraft.data),
    components: listify(components.data),
    tools: listify(tools.data),
  });

  const kpi = el("twinDashKpis");
  if (kpi) {
    kpi.innerHTML = overview.ok
      ? `<article><span>Twins</span><b>${esc(String(ov.twins ?? twinRows.length))}</b></article>
         <article><span>History</span><b>${esc(String(ov.history_entries ?? 0))}</b></article>
         <article><span>Configurations</span><b>${esc(String(ov.configurations ?? 0))}</b></article>
         <article><span>Reliability</span><b>${esc(String(ov.reliability_snapshots ?? 0))}</b></article>`
      : `<article><span>Overview</span><b>${esc(overview.error || "unavailable")}</b></article>`;
  }

  const stage = el("assetTwinStage");
  if (stage) {
    stage.innerHTML = `<div class="mx-twin-stage">
      <div class="mx-twin-hud"><span class="mx-chip">Digital Twin</span><span class="mx-chip mx-chip-ok">Not a 3D model</span><span class="mx-chip">Lifecycle registry</span></div>
      <div class="mx-twin-orbit"></div>
      <div class="mx-twin-core">${esc(first?.display_name || first?.name || first?.twin_uuid || "Asset Twin")}</div>
      <div class="mx-twin-node" style="left:12%;top:28%">Passport</div>
      <div class="mx-twin-node" style="right:14%;top:34%">Config</div>
      <div class="mx-twin-node" style="left:18%;bottom:22%">History</div>
      <div class="mx-twin-node" style="right:16%;bottom:26%">Reliability</div>
    </div>
    <p class="muted">${esc(ov.disclaimer || "Passports never disappear; history is immutable. Reliability metrics are architecture readiness only.")}</p>`;
  }

  const listHost = el("assetTwinList");
  if (listHost) {
    listHost.innerHTML = twinRows.length
      ? `<table class="data-table"><thead><tr><th>Name</th><th>UUID</th><th>Type</th><th>Lifecycle</th><th>Entity</th></tr></thead><tbody>${twinRows
          .map((row) => {
            const label = row.display_name || row.name || row.twin_uuid || row.id;
            return `<tr class="we-row-open" data-we-open="digitalTwin:${esc(String(row.id || ""))}" data-we-label="${esc(label)}">
              <td>${esc(label)}</td>
              <td class="mx-mono">${esc(row.twin_uuid || row.id || "")}</td>
              <td>${esc(row.twin_type || "—")}</td>
              <td><span class="mx-chip">${esc(row.lifecycle_state || row.status || "—")}</span></td>
              <td>${esc([row.fabric_entity_type, row.fabric_entity_id].filter(Boolean).join(" · ") || "—")}</td>
            </tr>`;
          })
          .join("")}</tbody></table>`
      : empty(twins.ok ? "No twins registered." : twins.error || "Twin API unavailable");
  }

  renderRows(
    "twinSearchResults",
    searchHits
      .map((hit) => {
        const id = hit.twin_id || hit.id;
        return `<div class="contact-row we-row-open" data-we-open="digitalTwin:${esc(String(id))}" data-we-label="${esc(hit.title || hit.twin_uuid || id)}">
          <b>${esc(hit.title || hit.twin_uuid || id)}</b>
          <span>${esc(hit.twin_type || "")} · ${esc(hit.serial_number || "")} · ${esc(hit.summary || "")}</span>
        </div>`;
      })
      .join(""),
    q ? (search.ok ? "No search hits." : search.error || "Search unavailable") : "Enter a search term and apply filters."
  );
}

async function handleDeskSubmit(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  const msg = el("twinOpsMsg");
  const fail = (result) => {
    const text = mutationErrorMessage(result);
    if (msg) msg.textContent = text;
    toast(text);
  };
  const twinType = values.twin_type;
  if (!twinType) return fail({ status: 422, error: "twin_type required" });
  const displayName = String(values.display_name || "").trim();
  if (!displayName) return fail({ status: 422, error: "display_name required" });

  let fabricEntityType = "";
  let fabricEntityId = String(values.fabric_entity_id || "").trim();
  if (values.aircraft_id) {
    fabricEntityType = "aircraft";
    fabricEntityId = values.aircraft_id;
  } else if (values.component_id) {
    fabricEntityType = "serialized_component";
    fabricEntityId = values.component_id;
  } else if (values.tool_id) {
    fabricEntityType = "tool";
    fabricEntityId = values.tool_id;
  } else if (fabricEntityId) {
    fabricEntityType = fabricEntityTypeForTwinType(twinType);
  }

  const body = {
    twin_type: twinType,
    display_name: displayName,
    serial_number: values.serial_number || "",
    part_number: values.part_number || "",
    lifecycle_state: values.lifecycle_state || defaultLifecycleForType(twinType),
    ensure_passport: Boolean(values.ensure_passport),
  };
  if (fabricEntityType) body.fabric_entity_type = fabricEntityType;
  if (fabricEntityId) body.fabric_entity_id = fabricEntityId;

  const result = await runLocked(`desk-twin:${twinType}:${displayName}`, () => softMutate("/twin/twins", { body }));
  if (!result) return;
  if (!result.ok) return fail(result);
  if (msg) msg.textContent = `Twin ${result.data?.twin_uuid || result.data?.id || ""} created`;
  toast("Twin registered");
  await refreshAssetTwinWorkspace();
}

export function initializeTwin() {
  el("twinRefresh")?.addEventListener("click", () => refreshAssetTwinWorkspace());
  el("twinApplyFilters")?.addEventListener("click", () => refreshAssetTwinWorkspace());
  el("twinSearch")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") refreshAssetTwinWorkspace();
  });
  el("assetTwinWorkspace")?.addEventListener("submit", (event) => {
    const form = event.target?.closest?.("[data-twin-action]");
    if (!form) return;
    event.preventDefault();
    handleDeskSubmit(form);
  });
}
