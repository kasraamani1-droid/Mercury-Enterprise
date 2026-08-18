const SESSIONS_KEY = "mercury.we.sessions";
const ACTIVE_KEY = "mercury.we.active";
const RECENT_OBJECTS_KEY = "mercury.we.recentObjects";
const PINNED_OBJECTS_KEY = "mercury.we.pinnedObjects";
const WIDGETS_KEY = "mercury.we.widgets";
const COMMENTS_KEY = "mercury.we.comments";

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
}

export function getSessions() {
  return read(SESSIONS_KEY, []);
}

export function saveSessions(sessions) {
  write(SESSIONS_KEY, sessions.slice(0, 12));
  return sessions;
}

export function getActiveSessionKey() {
  try {
    return localStorage.getItem(ACTIVE_KEY) || "";
  } catch {
    return "";
  }
}

export function setActiveSessionKey(key) {
  try {
    if (key) localStorage.setItem(ACTIVE_KEY, key);
    else localStorage.removeItem(ACTIVE_KEY);
  } catch {
    /* ignore */
  }
}

export function pushRecentObject(entry) {
  const list = getRecentObjects().filter((x) => x.key !== entry.key);
  list.unshift(entry);
  write(RECENT_OBJECTS_KEY, list.slice(0, 20));
  return list;
}

export function getRecentObjects() {
  return read(RECENT_OBJECTS_KEY, []);
}

export function getPinnedObjects() {
  return read(PINNED_OBJECTS_KEY, []);
}

export function togglePinnedObject(entry) {
  const list = getPinnedObjects();
  const idx = list.findIndex((x) => x.key === entry.key);
  if (idx >= 0) list.splice(idx, 1);
  else list.unshift(entry);
  write(PINNED_OBJECTS_KEY, list.slice(0, 20));
  return list;
}

export function getPinnedWidgets(sessionKey) {
  const all = read(WIDGETS_KEY, {});
  return all[sessionKey] || ["status", "due", "owner"];
}

export function setPinnedWidgets(sessionKey, widgets) {
  const all = read(WIDGETS_KEY, {});
  all[sessionKey] = widgets;
  write(WIDGETS_KEY, all);
}

export function getComments(sessionKey) {
  const all = read(COMMENTS_KEY, {});
  return all[sessionKey] || [];
}

export function addComment(sessionKey, text, author = "operator") {
  const all = read(COMMENTS_KEY, {});
  const list = all[sessionKey] || [];
  list.unshift({
    id: `c-${Date.now()}`,
    text,
    author,
    at: new Date().toISOString(),
  });
  all[sessionKey] = list.slice(0, 50);
  write(COMMENTS_KEY, all);
  return all[sessionKey];
}
