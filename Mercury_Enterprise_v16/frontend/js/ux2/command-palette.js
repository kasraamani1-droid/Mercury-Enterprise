import { allWorkspaces, getSimWorkspacesVisible, SHORTCUT_ACTIONS } from "./registry.js";
import { uxFetchPlatformSearch } from "./api.js";
import { listObjectTypes, searchObjects } from "../workspace-engine/index.js";
import { esc } from "../utils.js";

let overlay = null;
let activeIndex = 0;
let items = [];
let onNavigate = null;
let onOpenObject = null;

function buildOverlay() {
  if (overlay) return overlay;
  overlay = document.createElement("div");
  overlay.id = "ux2CommandPalette";
  overlay.className = "ux2-palette-overlay hidden";
  overlay.innerHTML = `
    <div class="ux2-palette" role="dialog" aria-modal="true" aria-label="Command palette">
      <input id="ux2PaletteInput" type="search" placeholder="Open object, jump area, or run command… (e.g. aircraft C-GABC)" autocomplete="off" />
      <div id="ux2PaletteList" class="ux2-palette-list"></div>
      <div class="ux2-palette-hint">↑↓ navigate · Enter open · Esc close · ${SHORTCUT_ACTIONS.map((s) => s.keys + " " + s.label).slice(0, 2).join(" · ")}</div>
    </div>
  `;
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closePalette();
  });
  document.body.appendChild(overlay);
  const input = overlay.querySelector("#ux2PaletteInput");
  input.addEventListener("input", () => refreshList(input.value));
  input.addEventListener("keydown", onInputKey);
  return overlay;
}

function onInputKey(e) {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    activeIndex = Math.min(activeIndex + 1, items.length - 1);
    paintActive();
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    activeIndex = Math.max(activeIndex - 1, 0);
    paintActive();
  } else if (e.key === "Enter") {
    e.preventDefault();
    runItem(items[activeIndex]);
  } else if (e.key === "Escape") {
    e.preventDefault();
    closePalette();
  }
}

function paintActive() {
  const nodes = overlay.querySelectorAll(".ux2-palette-item");
  nodes.forEach((n, i) => n.classList.toggle("active", i === activeIndex));
  nodes[activeIndex]?.scrollIntoView({ block: "nearest" });
}

function parseTypedOpen(query) {
  const raw = String(query || "").trim();
  const m = raw.match(/^(aircraft|engine|apu|workorder|work\s*order|twin|digitaltwin|organization|org|component|listing|supplier|project|engineer|planner|technician|qa|inspection|finding)\s+(.+)$/i);
  if (!m) return null;
  let type = m[1].toLowerCase().replace(/\s+/g, "");
  const map = {
    workorder: "workOrder",
    twin: "digitalTwin",
    digitaltwin: "digitalTwin",
    org: "organization",
    listing: "marketplaceListing",
  };
  type = map[type] || type;
  return { type, id: m[2].trim() };
}

async function refreshList(query) {
  const q = String(query || "").trim().toLowerCase();
  const typed = parseTypedOpen(query);

  const workspaces = allWorkspaces()
    .filter((w) => {
      if (!getSimWorkspacesVisible() && w.simulated) return false;
      if (!q) return true;
      return `${w.label} ${w.keywords} ${w.section}`.toLowerCase().includes(q);
    })
    .slice(0, 8)
    .map((w) => ({
      type: "workspace",
      id: w.id,
      label: w.label,
      meta: w.section,
      icon: w.icon,
    }));

  const typeHints = listObjectTypes()
    .filter((t) => !q || t.label.toLowerCase().includes(q) || t.type.includes(q))
    .slice(0, 6)
    .map((t) => ({
      type: "hint",
      id: t.type,
      label: `Open ${t.label}…`,
      meta: `Type: ${t.type} <id>`,
      icon: t.icon,
    }));

  const commands = [
    { type: "command", id: "theme", label: "Toggle light / dark theme", meta: "Appearance", icon: "◐" },
    { type: "command", id: "sidebar", label: "Toggle sidebar", meta: "Layout", icon: "☰" },
    { type: "command", id: "notifications", label: "Open notifications", meta: "System", icon: "N" },
  ].filter((c) => !q || c.label.toLowerCase().includes(q));

  items = [];
  if (typed) {
    items.push({
      type: "object",
      objectType: typed.type,
      id: typed.id,
      label: `Open ${typed.type} ${typed.id}`,
      meta: "Workspace Engine",
      icon: "◉",
    });
  }
  items.push(...workspaces, ...commands);
  if (!typed && q.length < 2) items.push(...typeHints);

  if (q.length >= 2) {
    const [search, objects] = await Promise.all([uxFetchPlatformSearch(q), searchObjects(q)]);
    objects.slice(0, 8).forEach((obj) => {
      items.push({
        type: "object",
        objectType: obj.type,
        id: obj.id,
        label: obj.label,
        meta: obj.meta || obj.type,
        icon: "◉",
      });
    });
    if (search.ok && search.data) {
      const hits = Array.isArray(search.data.hits)
        ? search.data.hits
        : Array.isArray(search.data)
          ? search.data
          : [];
      hits.slice(0, 6).forEach((hit) => {
        items.push({
          type: "search",
          id: hit.id || hit.entity_id || hit.document_id || "",
          label: hit.title || hit.name || hit.summary || "Search hit",
          meta: hit.entity_type || hit.kind || "Search",
          icon: "⌕",
          payload: hit,
        });
      });
    }
  }

  activeIndex = 0;
  const list = overlay.querySelector("#ux2PaletteList");
  if (!items.length) {
    list.innerHTML = `<div class="mx-empty">No matches.</div>`;
    return;
  }
  list.innerHTML = items
    .map(
      (item, i) => `
    <button type="button" class="ux2-palette-item${i === 0 ? " active" : ""}" data-index="${i}">
      <span class="mx-icon">${esc(item.icon || "•")}</span>
      <span>${esc(item.label)}</span>
      <small>${esc(item.meta || "")}</small>
    </button>
  `
    )
    .join("");
  list.querySelectorAll(".ux2-palette-item").forEach((btn) => {
    btn.addEventListener("click", () => runItem(items[Number(btn.dataset.index)]));
  });
}

function runItem(item) {
  if (!item) return;
  closePalette();
  if (item.type === "workspace" && onNavigate) onNavigate(item.id);
  if (item.type === "command" && onNavigate) onNavigate(`cmd:${item.id}`);
  if (item.type === "object" && onOpenObject) onOpenObject(item.objectType, item.id, { label: item.label });
  if (item.type === "hint" && onNavigate) {
    openPalette();
    const input = overlay?.querySelector("#ux2PaletteInput");
    if (input) {
      input.value = `${item.id} `;
      input.focus();
      refreshList(input.value);
    }
  }
  if (item.type === "search") {
    const kind = String(item.meta || "").toLowerCase();
    if (onOpenObject && item.id) {
      if (kind.includes("aircraft")) onOpenObject("aircraft", item.id);
      else if (kind.includes("twin")) onOpenObject("digitalTwin", item.id);
      else if (onNavigate) onNavigate("context");
    } else if (onNavigate) onNavigate("home");
  }
}

export function openPalette() {
  buildOverlay();
  overlay.classList.remove("hidden");
  const input = overlay.querySelector("#ux2PaletteInput");
  input.value = "";
  refreshList("");
  setTimeout(() => input.focus(), 0);
}

export function closePalette() {
  if (!overlay) return;
  overlay.classList.add("hidden");
}

export function isPaletteOpen() {
  return Boolean(overlay && !overlay.classList.contains("hidden"));
}

export function initCommandPalette(handlers) {
  onNavigate = handlers.navigate;
  onOpenObject = handlers.openObject || null;
  buildOverlay();
}
