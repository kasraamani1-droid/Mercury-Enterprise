const THEME_KEY = "mercury.ux2.theme";

export function getStoredTheme() {
  try {
    return localStorage.getItem(THEME_KEY) || "dark";
  } catch {
    return "dark";
  }
}

export function applyTheme(theme) {
  const next = theme === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* ignore */
  }
  return next;
}

export function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || getStoredTheme();
  return applyTheme(current === "light" ? "dark" : "light");
}

export function initTheme() {
  return applyTheme(getStoredTheme());
}
