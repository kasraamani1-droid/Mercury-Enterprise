export const el = id => document.getElementById(id);
export const esc = value => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");
export const fmt = value => value ? new Date(value).toLocaleString() : "Unknown time";
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
