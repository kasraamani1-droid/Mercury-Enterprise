import { NAV_SECTIONS, WORKSPACE_IDS, workspaceById } from "./registry.js";
import { getFavorites, getOpenTabs, getPins, getRecent, pushRecent, setOpenTabs, toggleFavorite, togglePin } from "./prefs.js";
import { closePalette, initCommandPalette, isPaletteOpen, openPalette } from "./command-palette.js";
import { initTheme, toggleTheme } from "./theme.js";
import { refreshUxWorkspace } from "./workspaces.js";
import {
  focusSession,
  getOpenObjectSessions,
  getPinnedObjects,
  getRecentObjects,
  initializeWorkspaceEngine,
  openObject,
} from "../workspace-engine/index.js";
import { getObjectType } from "../workspace-engine/types.js";

let navigateImpl = null;
let openTabs = [];
let activeId = "home";
let weApi = null;

function $(id) {
  return document.getElementById(id);
}

function renderSidebar() {
  const root = $("ux2SidebarNav");
  if (!root) return;
  const pins = new Set(getPins());
  const favs = new Set(getFavorites());
  root.innerHTML = NAV_SECTIONS.map((section) => {
    const items = section.items
      .map((item) => {
        const pinned = pins.has(item.id);
        const fav = favs.has(item.id);
        return `<button type="button" class="ux2-nav-item${activeId === item.id ? " active" : ""}" data-workspace="${item.id}" title="${item.label}">
          <span class="mx-icon">${item.icon}</span>
          <span class="label">${item.label}${fav ? " *" : ""}${item.simulated ? ' <span class="mx-chip mx-chip-warn" style="font-size:10px;padding:1px 6px">SIM</span>' : ""}</span>
          <span class="pin${pinned ? " on" : ""}" data-pin="${item.id}" title="Pin">${pinned ? "●" : "○"}</span>
        </button>`;
      })
      .join("");
    return `<div class="ux2-nav-section"><div class="ux2-nav-section-label">${section.label}</div>${items}</div>`;
  }).join("");

  const recentObjects = getRecentObjects().slice(0, 6);
  const pinnedObjects = getPinnedObjects().slice(0, 6);
  const objectBlock = (title, list) => {
    if (!list.length) return "";
    return `<div class="we-recents"><div class="we-recents-title">${title}</div>${list
      .map((o) => {
        const t = getObjectType(o.type);
        return `<button type="button" class="ux2-nav-item" data-we-open="${o.key}" data-we-label="${o.label || o.id}">
          <span class="mx-icon">${t?.icon || "◉"}</span>
          <span class="label">${o.label || o.id}</span>
        </button>`;
      })
      .join("")}</div>`;
  };
  root.insertAdjacentHTML("beforeend", objectBlock("Pinned objects", pinnedObjects) + objectBlock("Recent objects", recentObjects));

  root.querySelectorAll("[data-workspace]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      if (e.target?.dataset?.pin) {
        e.stopPropagation();
        togglePin(e.target.dataset.pin);
        renderSidebar();
        return;
      }
      navigate(btn.dataset.workspace);
    });
  });
}

function renderTabs() {
  const bar = $("ux2TabBar");
  if (!bar) return;
  openTabs = getOpenTabs().filter((id) => WORKSPACE_IDS.includes(id));
  if (!openTabs.includes(activeId) && WORKSPACE_IDS.includes(activeId)) openTabs.push(activeId);
  openTabs = [...new Set(openTabs)].slice(0, 8);
  setOpenTabs(openTabs);

  const objectSessions = getOpenObjectSessions().slice(0, 6);
  const areaHtml = openTabs
    .map((id) => {
      const meta = workspaceById(id);
      return `<button type="button" class="ux2-tab${id === activeId && !isObjectHash() ? " active" : ""}" data-tab="${id}">
        ${meta?.icon || "•"} ${meta?.label || id}
        <span class="close" data-close="${id}" title="Close">×</span>
      </button>`;
    })
    .join("");

  const objectHtml = objectSessions
    .map((s) => {
      const t = getObjectType(s.type);
      const active = location.hash.includes(`/object/${s.type}/`);
      return `<button type="button" class="ux2-tab we-object-tab${active ? " active" : ""}" data-object-key="${s.key}">
        ${t?.icon || "◉"} ${s.label || s.id}
        <span class="close" data-close-object="${s.key}" title="Close">×</span>
      </button>`;
    })
    .join("");

  bar.innerHTML = areaHtml + objectHtml;

  bar.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const closeId = e.target?.dataset?.close;
      if (closeId) {
        e.stopPropagation();
        openTabs = openTabs.filter((x) => x !== closeId);
        if (!openTabs.length) openTabs = ["home"];
        setOpenTabs(openTabs);
        if (activeId === closeId) navigate(openTabs[openTabs.length - 1]);
        else renderTabs();
        return;
      }
      navigate(btn.dataset.tab);
    });
  });

  bar.querySelectorAll("[data-object-key]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const closeKey = e.target?.dataset?.closeObject;
      if (closeKey) {
        e.stopPropagation();
        weApi?.closeObject?.(closeKey);
        renderTabs();
        renderSidebar();
        return;
      }
      focusSession(btn.dataset.objectKey);
      activeId = "context";
      renderTabs();
      renderSidebar();
    });
  });
}

function isObjectHash() {
  return /^#\/?object\//.test(location.hash || "");
}

function syncLegacyNav(id) {
  document.querySelectorAll(".product-tab").forEach((b) => {
    b.classList.toggle("active", b.dataset.workspace === id);
  });
}

export function navigate(rawId, _ctx = {}) {
  if (String(rawId).startsWith("cmd:")) {
    const cmd = String(rawId).slice(4);
    if (cmd === "theme") toggleTheme();
    if (cmd === "sidebar") toggleSidebar();
    if (cmd === "notifications") $("notificationButton")?.click();
    return;
  }
  const id = WORKSPACE_IDS.includes(rawId) ? rawId : "home";
  activeId = id;
  pushRecent(id);
  openTabs = getOpenTabs();
  if (!openTabs.includes(id)) openTabs.push(id);
  setOpenTabs(openTabs);

  WORKSPACE_IDS.forEach((ws) => {
    const node = $(`${ws}Workspace`);
    if (!node) return;
    const on = ws === id;
    node.classList.toggle("hidden", !on);
    node.classList.toggle("active", on);
  });

  syncLegacyNav(id);
  renderSidebar();
  renderTabs();
  document.body.classList.remove("ux2-nav-open");

  if (navigateImpl) navigateImpl(id);
  refreshUxWorkspace(id).catch(() => {});

  if (id === "context") {
    const sessions = getOpenObjectSessions();
    if (sessions[0] && !isObjectHash()) {
      focusSession(sessions[0].key);
      return;
    }
    ensureContextEmpty();
  }

  try {
    if (id !== "context") history.replaceState({ workspace: id }, "", `#/${id}`);
  } catch {
    /* ignore */
  }
}

function ensureContextEmpty() {
  const host = $("contextWorkspace");
  if (!host) return;
  if (!getOpenObjectSessions().length) {
    host.innerHTML = `<div class="ux2-page-header"><div><div class="mx-label">Workspace Engine</div><h1>No object open</h1><p>Open an aircraft, work order, twin, or other object from lists or the command palette (<kbd>Ctrl K</kbd> then <code>aircraft C-GABC</code>).</p></div>
      <button type="button" class="mx-btn" id="weDemoOpen">Open demo aircraft context</button></div>`;
    host.querySelector("#weDemoOpen")?.addEventListener("click", () => {
      openObject("aircraft", "ac-c-gmea", { label: "C-GMEA" });
    });
  }
}

function toggleSidebar() {
  $("ux2App")?.classList.toggle("sidebar-collapsed");
  document.body.classList.toggle("ux2-nav-open");
}

function bindShortcuts() {
  document.addEventListener("keydown", (e) => {
    const meta = e.metaKey || e.ctrlKey;
    const tag = (e.target && e.target.tagName) || "";
    const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || e.target?.isContentEditable;

    if (meta && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (isPaletteOpen()) closePalette();
      else openPalette();
      return;
    }
    if (meta && e.key === "/") {
      e.preventDefault();
      openPalette();
      return;
    }
    if (meta && e.shiftKey && e.key.toLowerCase() === "l") {
      e.preventDefault();
      toggleTheme();
      return;
    }
    if (meta && e.shiftKey && e.key.toLowerCase() === "n") {
      e.preventDefault();
      $("notificationButton")?.click();
      return;
    }
    if (!typing && e.key === "[" && !meta) {
      e.preventDefault();
      toggleSidebar();
      return;
    }
    if (!typing && e.key.toLowerCase() === "g" && !meta) {
      window.__ux2PendingG = true;
      setTimeout(() => {
        window.__ux2PendingG = false;
      }, 800);
      return;
    }
    if (!typing && window.__ux2PendingG) {
      const map = {
        h: "home",
        x: "context",
        c: "command",
        a: "aircraft",
        f: "fleet",
        p: "planning",
        w: "workOrders",
        m: "maintenance",
        l: "logbook",
        e: "engineering",
        i: "inventory",
        o: "logistics",
        k: "marketplace",
        t: "assetTwin",
        u: "authority",
        n: "organization",
        q: "ai",
        d: "admin",
        v: "developer",
      };
      const target = map[e.key.toLowerCase()];
      if (target) {
        e.preventDefault();
        window.__ux2PendingG = false;
        navigate(target);
      }
    }
    if (e.key === "Escape" && isPaletteOpen()) closePalette();
  });
}

function bindChrome() {
  $("ux2SearchTrigger")?.addEventListener("click", () => openPalette());
  $("ux2ThemeToggle")?.addEventListener("click", () => toggleTheme());
  $("ux2SidebarToggle")?.addEventListener("click", () => toggleSidebar());
  $("ux2FavToggle")?.addEventListener("click", () => {
    toggleFavorite(activeId);
    renderSidebar();
  });
  document.addEventListener("click", (e) => {
    const goto = e.target?.closest?.("[data-ux2-goto]");
    if (goto) {
      e.preventDefault();
      navigate(goto.getAttribute("data-ux2-goto"));
    }
  });
}

export function initializeUx2(options = {}) {
  navigateImpl = options.onNavigate || null;
  document.body.classList.add("ux2");
  initTheme();

  weApi = initializeWorkspaceEngine({
    onAreaNavigate: (id) => {
      activeId = id;
      WORKSPACE_IDS.forEach((ws) => {
        const node = $(`${ws}Workspace`);
        if (!node) return;
        const on = ws === id;
        node.classList.toggle("hidden", !on);
        node.classList.toggle("active", on);
      });
      if (navigateImpl) navigateImpl(id);
      renderSidebar();
      renderTabs();
    },
    onSessionsChanged: () => {
      renderTabs();
      renderSidebar();
    },
  });

  initCommandPalette({
    navigate,
    openObject: (type, id, opts) => openObject(type, id, opts),
  });
  bindChrome();
  bindShortcuts();
  renderSidebar();

  const hash = (location.hash || "").replace(/^#\/?/, "");
  if (hash.startsWith("object/")) {
    // engine initializer already opens from hash
    activeId = "context";
    renderTabs();
    renderSidebar();
  } else {
    const initial = WORKSPACE_IDS.includes(hash) ? hash : options.initial || "home";
    navigate(initial);
  }

  return { navigate, openObject, weApi };
}

export function getActiveWorkspace() {
  return activeId;
}

export function getRecentWorkspaces() {
  return getRecent();
}

export { openObject };
