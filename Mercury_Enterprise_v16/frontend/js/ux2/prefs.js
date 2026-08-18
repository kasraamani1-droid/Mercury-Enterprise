function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function writeJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
}

const FAV_KEY = "mercury.ux2.favorites";
const PIN_KEY = "mercury.ux2.pins";
const RECENT_KEY = "mercury.ux2.recent";
const TABS_KEY = "mercury.ux2.tabs";

export function getFavorites() {
  return readJson(FAV_KEY, []);
}

export function toggleFavorite(id) {
  const set = new Set(getFavorites());
  if (set.has(id)) set.delete(id);
  else set.add(id);
  const next = [...set];
  writeJson(FAV_KEY, next);
  return next;
}

export function getPins() {
  return readJson(PIN_KEY, []);
}

export function togglePin(id) {
  const set = new Set(getPins());
  if (set.has(id)) set.delete(id);
  else set.add(id);
  const next = [...set];
  writeJson(PIN_KEY, next);
  return next;
}

export function pushRecent(id) {
  const list = getRecent().filter((x) => x !== id);
  list.unshift(id);
  writeJson(RECENT_KEY, list.slice(0, 12));
  return list;
}

export function getRecent() {
  return readJson(RECENT_KEY, []);
}

export function getOpenTabs() {
  return readJson(TABS_KEY, ["home"]);
}

export function setOpenTabs(tabs) {
  writeJson(TABS_KEY, tabs);
  return tabs;
}
