import { el, esc } from "./utils.js";
import { request } from "./api.js";

function qs(params = {}) {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function getJson(path) {
  return (await request(path)).json();
}

function toast(msg) {
  const t = el("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2800);
}

function renderRows(hostId, rows, empty) {
  const host = el(hostId);
  if (!host) return;
  host.innerHTML = rows.length
    ? rows.join("")
    : `<div class="empty">${esc(empty)}</div>`;
}

export async function refreshLogisticsWorkspace() {
  try {
    const [dash, warehouses, locations, parts, balances, tools, mrs, pos, vendors, shortages] =
      await Promise.all([
        getJson("/logistics/dashboard"),
        getJson("/logistics/warehouses"),
        getJson("/logistics/locations?limit=30"),
        getJson("/logistics/parts?limit=30"),
        getJson("/logistics/stock/balances?limit=40"),
        getJson("/logistics/tools?limit=30"),
        getJson("/logistics/material-requests?limit=20"),
        getJson("/logistics/purchase-orders?limit=20"),
        getJson("/logistics/vendors"),
        getJson("/logistics/shortages"),
      ]);

    const kpi = el("logDashKpis");
    if (kpi) {
      kpi.innerHTML = `
        <article><span>Parts</span><b>${dash.parts ?? 0}</b></article>
        <article><span>Low stock</span><b>${dash.low_stock_parts ?? 0}</b></article>
        <article><span>On hand</span><b>${dash.total_on_hand ?? 0}</b></article>
        <article><span>Reserved</span><b>${dash.total_reserved ?? 0}</b></article>
        <article><span>In repair</span><b>${dash.open_rotable_cycles ?? 0}</b></article>
        <article><span>On order</span><b>${dash.open_purchase_orders ?? 0}</b></article>
        <article><span>Cal due</span><b>${dash.tools_calibration_due_30d ?? 0}</b></article>
        <article><span>Expired</span><b>${dash.expired_lots ?? 0}</b></article>`;
    }

    renderRows(
      "logWarehouses",
      (warehouses || []).map(
        (w) =>
          `<div class="contact-row"><b>${esc(w.code)}</b><span>${esc(w.name)} · ${esc(w.warehouse_type)}</span><em>${esc(w.status)}</em></div>`
      ),
      "No warehouses."
    );

    renderRows(
      "logLocations",
      (locations || []).slice(0, 20).map(
        (l) =>
          `<div class="contact-row"><b>${esc(l.location_code)}</b><span>${esc(l.location_type)}</span><em>${esc(l.status)}</em></div>`
      ),
      "No locations."
    );

    renderRows(
      "logParts",
      (parts || []).map(
        (p) =>
          `<div class="contact-row"><b>${esc(p.oem_part_number)}</b><span>${esc(p.description)} · ${esc(p.part_class)}</span><em>${esc(p.issue_policy || "")}</em></div>`
      ),
      "No parts."
    );

    renderRows(
      "logBalances",
      (balances || []).map(
        (b) =>
          `<div class="contact-row"><b>${esc(b.oem_part_number || b.part_master_id)}</b><span>OH ${esc(String(b.qty_on_hand))} · RSV ${esc(String(b.qty_reserved))} · ${esc(b.condition)}</span><em>${esc(b.location_code || b.location_id || "")}</em></div>`
      ),
      "No balances."
    );

    renderRows(
      "logTools",
      (tools || []).map(
        (t) =>
          `<div class="contact-row"><b>${esc(t.tool_code)}</b><span>${esc(t.description)} · cal ${esc(t.calibration_status)}</span><em>${esc(t.status)}</em></div>`
      ),
      "No tools."
    );

    renderRows(
      "logMaterialRequests",
      (mrs || []).map(
        (m) =>
          `<div class="contact-row"><b>${esc(m.request_number)}</b><span>${esc(m.requested_by)}</span><em>${esc(m.status)}</em></div>`
      ),
      "No material requests."
    );

    renderRows(
      "logPurchaseOrders",
      (pos || []).map(
        (p) =>
          `<div class="contact-row"><b>${esc(p.po_number)}</b><span>${esc(p.currency)} · ${esc(p.vendor_id || "")}</span><em>${esc(p.status)}</em></div>`
      ),
      "No purchase orders."
    );

    renderRows(
      "logVendors",
      (vendors || []).map(
        (v) =>
          `<div class="contact-row"><b>${esc(v.code)}</b><span>${esc(v.name)} · ${esc(v.vendor_type)}</span><em>★ ${esc(String(v.rating))}</em></div>`
      ),
      "No vendors."
    );

    const shortageItems = shortages?.items || shortages?.lines || shortages || [];
    renderRows(
      "logShortages",
      (Array.isArray(shortageItems) ? shortageItems : []).slice(0, 30).map(
        (s) =>
          `<div class="contact-row"><b>${esc(s.part_number || s.oem_part_number || s.status)}</b><span>${esc(s.message || s.description || "")}</span><em>${esc(s.status || "")}</em></div>`
      ),
      "No shortages."
    );
  } catch (error) {
    toast(error.message || "Unable to refresh logistics");
  }
}

export function initializeLogistics() {
  el("logRefresh")?.addEventListener("click", () => refreshLogisticsWorkspace());
  el("logScanBtn")?.addEventListener("click", async () => {
    const value = el("logScanValue")?.value?.trim();
    if (!value) return toast("Enter a scan value");
    try {
      const res = await request("/logistics/scan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value }),
      });
      const body = await res.json();
      const host = el("logScanResult");
      if (host) {
        host.innerHTML = `<div class="contact-row"><b>${esc(body.entity_type || body.matched_type || "hit")}</b><span>${esc(body.oem_part_number || body.tool_code || body.serial_number || body.value || "")}</span><em>${esc(body.identifier_type || "")}</em></div>`;
      }
      toast("Scan resolved");
    } catch (error) {
      toast(error.message || "Scan failed");
    }
  });
}
