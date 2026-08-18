import { esc } from "../utils.js";
import { getObjectType } from "./types.js";
import { addComment, getComments, getPinnedWidgets } from "./store.js";
import {
  renderAircraftConfigurationPanel,
  renderComponentInstallHistory,
  renderComponentOverview,
} from "./configuration.js";

export function renderShellSkeleton() {
  return `
    <div class="we-shell" id="weShell">
      <header class="we-header" id="weHeader"></header>
      <nav class="we-tabs" id="weTabs" aria-label="Object tabs"></nav>
      <div class="we-body">
        <main class="we-main" id="weMain"></main>
        <aside class="we-rail" id="weRail" aria-label="Workspace rail"></aside>
      </div>
    </div>
  `;
}

export function renderHeader(session, typeDef, record) {
  const label = session.label || typeDef.resolveLabel?.(record) || session.id;
  const status = record?.status || record?.status_code || record?.lifecycle_state || record?.component_status || "open";
  const actions = (typeDef.quickActions || [])
    .map((a) => `<button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-action="${esc(a.id)}">${esc(a.label)}</button>`)
    .join("");
  return `
    <div class="we-header-left">
      <span class="we-type-badge">${esc(typeDef.icon || "•")} ${esc(typeDef.label)}</span>
      <h1 class="we-title">${esc(String(label))}</h1>
      <span class="mx-chip">${esc(String(status))}</span>
      <span class="mx-mono we-id">${esc(session.id)}</span>
    </div>
    <div class="we-header-actions">${actions}
      <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-action="close">Close</button>
    </div>
  `;
}

export function renderTabs(typeDef, activeTab) {
  return (typeDef.tabs || [])
    .map(
      (t) =>
        `<button type="button" class="we-tab${t.id === activeTab ? " active" : ""}" data-we-tab="${esc(t.id)}">${esc(t.label)}</button>`
    )
    .join("");
}

export function renderMainTab(session, typeDef, record, bundle, tabId) {
  const label = session.label || typeDef.resolveLabel?.(record) || session.id;
  if (session.type === "component" && tabId === "overview") {
    return renderComponentOverview(session, record, bundle);
  }
  if (session.type === "component" && (tabId === "installHistory" || tabId === "history")) {
    return renderComponentInstallHistory(bundle);
  }
  if (session.type === "aircraft" && (tabId === "configuration" || tabId === "components")) {
    const dueHtml =
      tabId === "components" && bundle.due?.length
        ? `<article class="mx-card" style="margin-top:16px">
            <div class="mx-card-header"><h3>Due / findings</h3></div>
            <p class="mx-subtitle">Planning due items remain available while the aircraft stays in focus.</p>
            <div class="mx-stack" style="margin-top:12px">${bundle.due.slice(0, 6).map((d) => dueChip(d)).join("")}</div>
          </article>`
        : tabId === "components"
          ? `<article class="mx-card" style="margin-top:16px"><div class="mx-card-header"><h3>Due / findings</h3></div><div class="mx-empty">No due items for this aircraft context.</div></article>`
          : "";
    return renderAircraftConfigurationPanel(session, bundle, { dueHtml });
  }
  if (tabId === "overview") {
    return `
      <div class="mx-grid mx-grid-3" style="margin-bottom:16px">
        <article class="mx-kpi"><div class="mx-label">Object</div><div class="mx-kpi-value" style="font-size:18px">${esc(String(label))}</div></article>
        <article class="mx-kpi"><div class="mx-label">Type</div><div class="mx-kpi-value" style="font-size:18px">${esc(typeDef.label)}</div></article>
        <article class="mx-kpi"><div class="mx-label">Status</div><div class="mx-kpi-value" style="font-size:18px">${esc(String(record?.status || "—"))}</div></article>
      </div>
      <article class="mx-card">
        <div class="mx-card-header"><h3>Summary</h3></div>
        <pre class="we-json">${esc(JSON.stringify(pickSummary(record), null, 2))}</pre>
      </article>
      ${relatedStrip(bundle)}
    `;
  }
  if (tabId === "digitalTwin") {
    const twin = bundle.twin;
    return `
      <div class="mx-twin-stage we-twin">
        <div class="mx-twin-hud"><span class="mx-chip">Digital Twin</span><span class="mx-chip mx-chip-ok">Architecture viz</span></div>
        <div class="mx-twin-orbit"></div>
        <div class="mx-twin-core">${esc(twin?.name || label)}</div>
      </div>
      <p class="mx-subtitle" style="margin-top:12px">${twin ? `Bound twin ${esc(twin.twin_uuid || twin.id)}` : "No twin linked yet — open Digital Twin workspace to register."}</p>
      ${twin ? `<button type="button" class="mx-btn mx-btn-ghost" data-we-open="digitalTwin:${esc(twin.id)}">Open twin object</button>` : ""}
    `;
  }
  if (tabId === "workOrders" || tabId === "tasks") {
    const rows = (bundle.workOrders || bundle.jobCards || []).slice(0, 30);
    if (!rows.length) return empty("No related work items.");
    return table(
      ["ID", "Status", "Detail"],
      rows
        .map((r) => {
          const id = r.id || r.work_order_id || r.job_card_id || "";
          return `<tr class="we-row-open" data-we-open="workOrder:${esc(String(id))}">
            <td class="mx-mono">${esc(String(id))}</td>
            <td><span class="mx-chip">${esc(r.status || "—")}</span></td>
            <td>${esc(r.description || r.title || r.aircraft_id || "—")}</td>
          </tr>`;
        })
        .join("")
    );
  }
  if (tabId === "history" || tabId === "logbook") {
    return timelineHtml(bundle.timeline || []);
  }
  if (tabId === "pricing" && session.type === "marketplaceListing") {
    const pricing = bundle.pricing;
    if (!pricing) return empty("No pricing payload for this listing.");
    return `
      <article class="mx-card">
        <div class="mx-card-header"><h3>Pricing</h3><span class="mx-chip">Readiness</span></div>
        <pre class="we-json">${esc(JSON.stringify(pricing, null, 2))}</pre>
        <p class="mx-subtitle">Payments are out of RC scope — use Add to cart / Request quote actions.</p>
      </article>`;
  }
  if (tabId === "configuration" && session.type === "digitalTwin") {
    const rows = bundle.configurations || [];
    if (!rows.length) return empty("No configuration snapshots for this twin.");
    return table(
      ["Revision", "Status", "Effective", "Notes"],
      rows
        .map(
          (c) => `<tr>
            <td class="mx-mono">${esc(String(c.revision || c.version || c.id || "—"))}</td>
            <td><span class="mx-chip">${esc(c.status || "—")}</span></td>
            <td>${esc(c.effective_at || c.created_at || "—")}</td>
            <td>${esc(c.notes || c.summary || "—")}</td>
          </tr>`
        )
        .join("")
    );
  }
  if (tabId === "reliability") {
    const rows = bundle.reliability || [];
    if (!rows.length) {
      return `<article class="mx-card"><div class="mx-card-header"><h3>Reliability</h3><span class="mx-chip mx-chip-warn">Architecture only</span></div>
        <p class="mx-subtitle">No reliability metrics recorded. Mercury does not invent ML forecasts — metrics appear when published via Twin APIs.</p></article>`;
    }
    return table(
      ["Metric", "Value", "Window", "Notes"],
      rows
        .map(
          (r) => `<tr>
            <td>${esc(r.metric_code || r.name || r.id || "—")}</td>
            <td>${esc(String(r.value ?? r.metric_value ?? "—"))}</td>
            <td>${esc(r.window || r.period || "—")}</td>
            <td>${esc(r.notes || r.summary || "—")}</td>
          </tr>`
        )
        .join("")
    );
  }
  if (tabId === "relationships") {
    const rel = bundle.relationships;
    if (!rel) return empty("No relationship graph for this twin.");
    const links = Array.isArray(rel) ? rel : listifyRelationships(rel);
    if (!links.length) return empty("No linked entities.");
    return table(
      ["Relation", "Target", "Type"],
      links
        .map(
          (r) => `<tr>
            <td>${esc(r.relation_type || r.kind || "link")}</td>
            <td class="mx-mono">${esc(r.target_id || r.related_id || r.id || "—")}</td>
            <td>${esc(r.target_type || r.entity_type || "—")}</td>
          </tr>`
        )
        .join("")
    );
  }
  if (tabId === "passport") {
    return `
      <article class="mx-card">
        <div class="mx-card-header"><h3>Digital Passport</h3><span class="mx-chip mx-chip-ok">Not a 3D model</span></div>
        <p class="mx-subtitle">Passport metadata for ${esc(String(label))}.</p>
        <pre class="we-json">${esc(JSON.stringify(pickSummary(record), null, 2))}</pre>
      </article>`;
  }
  if (tabId === "aiAssistant") {
    return `
      <article class="mx-card">
        <div class="mx-card-header"><h3>AI Assistant</h3><span class="mx-chip mx-chip-warn">Advisory only</span></div>
        <p class="mx-subtitle">Ask about ${esc(String(label))}. Answers are decision-support only — humans remain in control.</p>
        <div class="we-ai-thread" id="weAiThread"><div class="mx-empty">Ask a question in the AI rail panel.</div></div>
      </article>
    `;
  }
  if (tabId === "documents" || tabId === "attachments") {
    return empty("Attachments panel is on the rail. Document bindings use platform file metadata.");
  }
  if (tabId === "marketplace") {
    return `
      <article class="mx-card">
        <h3>Marketplace context</h3>
        <p class="mx-subtitle">Find parts and services related to this ${esc(typeDef.label.toLowerCase())}.</p>
        <button type="button" class="mx-btn" data-ux2-goto="marketplace">Open Marketplace area</button>
      </article>
    `;
  }
  if (tabId === "configuration" || tabId === "components" || tabId === "maintenance" || tabId === "sb" || tabId === "ad") {
    return `
      <article class="mx-card">
        <div class="mx-card-header"><h3>${esc(tabLabel(typeDef, tabId))}</h3></div>
        <p class="mx-subtitle">Context tab for <strong>${esc(String(label))}</strong>. Domain boards remain available via area navigation; this tab keeps the object in focus.</p>
        ${bundle.due?.length ? `<div class="mx-stack" style="margin-top:12px">${bundle.due.slice(0, 6).map((d) => dueChip(d)).join("")}</div>` : ""}
        ${bundle.configurations?.length ? `<pre class="we-json">${esc(JSON.stringify(bundle.configurations.slice(0, 3), null, 2))}</pre>` : ""}
      </article>
    `;
  }
  return `
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(tabLabel(typeDef, tabId))}</h3></div>
      <p class="mx-subtitle">Object-centric view for ${esc(typeDef.label)} · ${esc(String(label))}.</p>
      <pre class="we-json">${esc(JSON.stringify(pickSummary(record), null, 2))}</pre>
    </article>
  `;
}

function listifyRelationships(rel) {
  if (!rel || typeof rel !== "object") return [];
  if (Array.isArray(rel.links)) return rel.links;
  if (Array.isArray(rel.relationships)) return rel.relationships;
  if (Array.isArray(rel.items)) return rel.items;
  return Object.entries(rel)
    .filter(([, v]) => v && typeof v === "object")
    .map(([k, v]) => ({ relation_type: k, ...(typeof v === "object" ? v : { target_id: String(v) }) }));
}

export function renderRail(session, typeDef, record, bundle) {
  const key = session.key;
  const widgets = getPinnedWidgets(key);
  const comments = getComments(key);
  const widgetHtml = widgets
    .map((w) => {
      if (w === "status") return `<div class="we-widget"><div class="mx-label">Status</div><strong>${esc(String(record?.status || "—"))}</strong></div>`;
      if (w === "due") return `<div class="we-widget"><div class="mx-label">Due items</div><strong>${esc(String(bundle.due?.length ?? 0))}</strong></div>`;
      if (w === "owner") return `<div class="we-widget"><div class="mx-label">Owner</div><strong>${esc(String(record?.operator_name || record?.owner || "—"))}</strong></div>`;
      return `<div class="we-widget"><div class="mx-label">${esc(w)}</div><strong>—</strong></div>`;
    })
    .join("");

  return `
    <section class="we-rail-block">
      <div class="mx-label">Pinned widgets</div>
      <div class="we-widget-row">${widgetHtml}</div>
    </section>
    <section class="we-rail-block">
      <div class="mx-label">Timeline</div>
      ${timelineHtml(bundle.timeline || [])}
    </section>
    <section class="we-rail-block">
      <div class="mx-label">Recent activity</div>
      <div class="mx-subtitle">${esc(typeDef.label)} session · local + API events</div>
    </section>
    <section class="we-rail-block">
      <div class="mx-label">Attachments</div>
      <div class="mx-empty" style="padding:12px">Drop / link via File Service (metadata).</div>
      <button type="button" class="mx-btn mx-btn-ghost mx-btn-sm" data-we-action="attach">Add attachment ref</button>
    </section>
    <section class="we-rail-block">
      <div class="mx-label">Comments</div>
      <div id="weComments" class="we-comments">${comments.map((c) => `<div class="we-comment"><strong>${esc(c.author)}</strong><span class="mx-timeline-meta">${esc(c.at)}</span><div>${esc(c.text)}</div></div>`).join("") || '<div class="mx-empty" style="padding:8px">No comments</div>'}</div>
      <form id="weCommentForm" class="we-comment-form">
        <input class="mx-input" id="weCommentInput" placeholder="Add a comment…" required />
        <button class="mx-btn mx-btn-sm" type="submit">Post</button>
      </form>
    </section>
    <section class="we-rail-block">
      <div class="mx-label">Notifications</div>
      <div class="mx-subtitle">Object-scoped alerts appear here when subscribed.</div>
    </section>
    <section class="we-rail-block">
      <div class="mx-label">Search in object</div>
      <input class="mx-input" id="weObjectSearch" placeholder="Filter tabs & related…" />
    </section>
    <section class="we-rail-block we-ai-panel">
      <div class="mx-label">AI Panel</div>
      <textarea class="mx-textarea" id="weAiInput" rows="3" placeholder="Ask about this object…"></textarea>
      <button type="button" class="mx-btn mx-btn-sm" id="weAiAsk">Ask (advisory)</button>
      <div id="weAiRailOut" class="mx-subtitle" style="margin-top:8px"></div>
    </section>
  `;
}

function tabLabel(typeDef, tabId) {
  return typeDef.tabs.find((t) => t.id === tabId)?.label || tabId;
}

function pickSummary(record) {
  if (!record || typeof record !== "object") return {};
  const keys = [
    "id",
    "registration",
    "tail_number",
    "name",
    "status",
    "model_id",
    "model_name",
    "operator_name",
    "serial_number",
    "part_number",
    "twin_uuid",
    "lifecycle_state",
    "description",
    "title",
    "defect_number",
    "aircraft_id",
    "sku",
    "code",
    "note",
  ];
  const out = {};
  keys.forEach((k) => {
    if (record[k] != null) out[k] = record[k];
  });
  return Object.keys(out).length ? out : record;
}

function table(headers, body) {
  return `<div class="mx-table-wrap"><table class="mx-table"><thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function empty(msg) {
  return `<div class="mx-empty">${esc(msg)}</div>`;
}

function timelineHtml(items) {
  if (!items.length) return empty("No timeline events.");
  return `<div class="mx-timeline">${items
    .slice(0, 12)
    .map(
      (i) => `<div class="mx-timeline-item"><div><strong>${esc(String(i.title || "Event"))}</strong>
      <div class="mx-subtitle">${esc(String(i.detail || ""))}</div>
      <div class="mx-timeline-meta">${esc(String(i.at || ""))}</div></div></div>`
    )
    .join("")}</div>`;
}

function dueOpenTarget(item) {
  const source = String(item?.source_type || "").toLowerCase();
  const id = item?.source_id || item?.id;
  if (!id) return null;
  // Due-list mixes checks / AD / SB / EO / deferred defects. Only types that
  // already exist in the Workspace Engine catalog get data-we-open (same
  // contract as related work-order chips). Others stay informational.
  if (source === "deferred_defect") {
    return { key: `finding:${id}`, label: item.title || item.defect_number || String(id) };
  }
  return null;
}

function dueChip(item) {
  const text = item.task_code || item.title || item.id || "Due";
  const open = dueOpenTarget(item);
  if (open) {
    return `<button type="button" class="mx-chip" data-we-open="${esc(open.key)}" data-we-label="${esc(open.label)}">${esc(String(text))}</button>`;
  }
  return `<div class="mx-chip">${esc(String(text))}</div>`;
}

function relatedStrip(bundle) {
  const wos = bundle.workOrders || [];
  if (!wos.length) return "";
  return `<article class="mx-card" style="margin-top:16px"><div class="mx-card-header"><h3>Related work orders</h3></div>
    <div class="mx-row" style="flex-wrap:wrap">${wos
      .slice(0, 8)
      .map((w) => `<button type="button" class="mx-chip" data-we-open="workOrder:${esc(String(w.id))}">${esc(String(w.id))}</button>`)
      .join("")}</div></article>`;
}

export function bindCommentForm(sessionKey, onChange) {
  const form = document.getElementById("weCommentForm");
  if (!form) return;
  form.onsubmit = (e) => {
    e.preventDefault();
    const input = document.getElementById("weCommentInput");
    const text = input?.value?.trim();
    if (!text) return;
    addComment(sessionKey, text);
    input.value = "";
    onChange?.();
  };
}

export function bindAiPanel(session, record) {
  const btn = document.getElementById("weAiAsk");
  if (!btn) return;
  btn.onclick = () => {
    const q = document.getElementById("weAiInput")?.value?.trim() || "";
    const out = document.getElementById("weAiRailOut");
    const thread = document.getElementById("weAiThread");
    const typeDef = getObjectType(session.type);
    const label = session.label || record?.registration || session.id;
    const answer = q
      ? `Advisory: For ${typeDef?.label || session.type} ${label}, review ${q} against maintenance program, open findings, and human procedures. No autonomous action taken.`
      : "Enter a question.";
    if (out) out.textContent = answer;
    if (thread) thread.innerHTML = `<div class="we-ai-msg"><strong>You</strong><div>${esc(q)}</div></div><div class="we-ai-msg"><strong>Mercury AI</strong><div>${esc(answer)}</div></div>`;
  };
}
