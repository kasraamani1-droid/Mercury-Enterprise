export const el = id => document.getElementById(id);
export const esc = value => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");
export const fmt = value => value ? new Date(value).toLocaleString() : "Unknown time";

/** Download a string or JSON-serializable payload as a browser file. */
export function download(name, data, type = "application/json") {
  const payload = typeof data === "string" ? data : JSON.stringify(data, null, 2);
  const blob = new Blob([payload], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function toast(message) {
  const node = el("toast");
  node.textContent = message;
  node.classList.add("show");
  window.setTimeout(() => node.classList.remove("show"), 2200);
}
export function confidenceAverage(items) {
  const values = items.map(x => Number(x.confidence)).filter(Number.isFinite);
  return values.length ? Math.round(values.reduce((a,b)=>a+b,0)/values.length) : null;
}
