import { el, esc } from "./utils.js";
import { getSessionStatus } from "./api.js";
import { listify, softGet, softMutate } from "./ux2/api.js";
import { mutationErrorMessage, runLocked } from "./workspace-engine/logistics-ops.js";
import {
  filterPublications,
  libraryBrowseQuery,
  sessionCanAdminPublications,
  sessionCanManagePublications,
  sessionCanReadPublications,
} from "./workspace-engine/publications-ops.js";

let lastRole = "";
let refreshGeneration = 0;
let browseState = { manufacturerId: "", familyId: "", modelId: "", publicationCode: "", ataChapterId: "" };

function toast(msg) {
  const t = el("toast");
  if (!t) return;
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2800);
}

function setStatus(text) {
  const node = el("libStatus");
  if (node) node.textContent = text || "";
}

function empty(text) {
  return `<div class="empty">${esc(text)}</div>`;
}

function rowOpen(type, id, label, inner) {
  return `<div class="contact-row we-row-open" data-we-open="${esc(type)}:${esc(String(id))}" data-we-label="${esc(label || id)}">${inner}</div>`;
}

function renderRows(hostId, html, fallback) {
  const host = el(hostId);
  if (!host) return;
  host.innerHTML = html || empty(fallback);
}

function optionList(rows, valueKey, labelFn, selected) {
  return (Array.isArray(rows) ? rows : [])
    .map((row) => {
      const id = String(row[valueKey] || row.id || "");
      return `<option value="${esc(id)}"${id === String(selected || "") ? " selected" : ""}>${esc(labelFn(row))}</option>`;
    })
    .join("");
}

function renderDesk({ canManage, types, manufacturers, models, ata }) {
  const host = el("libOpsDesk");
  if (!host) return;
  if (!canManage) {
    host.innerHTML = `<p class="muted">Publication mutations require publication.manage (Operator or Administrator). Viewer/Reviewer can browse and search. Archive/activate/access require publication.admin.</p>`;
    return;
  }
  host.innerHTML = `
    <article class="card">
      <h3>Register publication</h3>
      <form data-lib-action="create">
        <select name="publication_type_code" required>
          <option value="">Type code</option>
          ${optionList(types, "code", (row) => `${row.code} · ${row.name || row.category || ""}`)}
        </select>
        <input name="publication_number" required maxlength="120" placeholder="Publication number" />
        <input name="title" required maxlength="300" placeholder="Title" />
        <select name="manufacturer_id"><option value="">Manufacturer (optional)</option>${optionList(manufacturers, "id", (row) => row.name || row.code || row.id)}</select>
        <select name="aircraft_model_id"><option value="">Model (optional)</option>${optionList(models, "id", (row) => row.name || row.code || row.id)}</select>
        <select name="ata_chapter_id"><option value="">ATA (optional)</option>${optionList(ata, "id", (row) => `${row.chapter_number || row.code || row.id} · ${row.title || row.name || ""}`)}</select>
        <input name="authority" maxlength="120" placeholder="Authority" />
        <select name="access_classification"><option value="internal">internal</option><option value="restricted">restricted</option><option value="licensed">licensed</option><option value="public">public</option></select>
        <input name="revision_number" placeholder="Initial revision (optional)" />
        <select name="storage_kind"><option value="none">storage none</option><option value="external_url">external_url</option></select>
        <input name="storage_uri" placeholder="Locator URI" />
        <button type="submit">Create publication</button>
      </form>
      <p class="muted">Metadata and locators only. Duplicate revision numbers return 409.</p>
    </article>
    <p class="muted" id="libOpsMsg"></p>
  `;
}

export async function refreshTechLibraryWorkspace() {
  const generation = ++refreshGeneration;
  setStatus("Loading library…");
  const session = await getSessionStatus().catch(() => null);
  lastRole = session?.role || "";
  if (!sessionCanReadPublications(lastRole) && session?.role) {
    setStatus("Publication read is not granted for this session.");
  }

  const browsePath = libraryBrowseQuery(browseState);
  const q = el("libSearch")?.value || "";
  const code = el("libCodeFilter")?.value || "";
  const status = el("libStatusFilter")?.value || "";
  const [
    pubs,
    types,
    browse,
    search,
    manufacturers,
    models,
    ata,
    ads,
    sbs,
    eos,
  ] = await Promise.all([
    softGet("/publications?limit=80"),
    softGet("/publications/types"),
    softGet(browsePath),
    q ? softGet(`/library/search?q=${encodeURIComponent(q)}&limit=40`) : Promise.resolve({ ok: true, data: [] }),
    softGet("/fleet/manufacturers"),
    softGet("/fleet/models"),
    softGet("/components/ata-chapters"),
    softGet("/planning/ads?limit=20"),
    softGet("/planning/service-bulletins?limit=20"),
    softGet("/planning/engineering-orders?limit=20"),
  ]);
  if (generation !== refreshGeneration) return;

  const failed = [pubs, browse].filter((res) => !res.ok);
  setStatus(failed.length ? `Partial load: ${failed.map((res) => res.error || `HTTP ${res.status}`).join("; ")}` : "Live technical library.");

  const typeRows = listify(types.data);
  const pubRows = filterPublications(listify(pubs.data), { q, code, status });
  const searchRows = listify(search.data);
  const browseNodes = listify(browse.data?.nodes);
  const browseTrail = listify(browse.data?.path);
  const mfrRows = listify(manufacturers.data);
  const modelRows = listify(models.data);
  const ataRows = listify(ata.data);

  const codeEl = el("libCodeFilter");
  if (codeEl && codeEl.options.length <= 1) {
    const codes = [...new Set(typeRows.map((row) => row.code).filter(Boolean))];
    codeEl.innerHTML = `<option value="">All types</option>` + codes.map((item) => `<option value="${esc(item)}">${esc(item)}</option>`).join("");
  }

  renderDesk({
    canManage: sessionCanManagePublications(lastRole),
    types: typeRows,
    manufacturers: mfrRows,
    models: modelRows,
    ata: ataRows,
  });

  const kpi = el("libDashKpis");
  if (kpi) {
    kpi.innerHTML = `
      <article><span>Publications</span><b>${esc(String(listify(pubs.data).length))}</b></article>
      <article><span>Types</span><b>${esc(String(typeRows.length))}</b></article>
      <article><span>Browse nodes</span><b>${esc(String(browseNodes.length))}</b></article>
      <article><span>Admin</span><b>${sessionCanAdminPublications(lastRole) ? "yes" : "no"}</b></article>`;
  }

  renderRows(
    "libBrowse",
    `<p class="muted">Path: ${esc(browseTrail.join(" / ") || "library")}</p>
     ${browseState.manufacturerId ? `<button type="button" class="ghost small" data-lib-browse-reset="1">Reset browse</button>` : ""}
     ${browseNodes
       .map(
         (node) =>
           `<div class="contact-row"><b>${esc(node.label || node.id)}</b><span>${esc(node.node_type)} · ${esc(String(node.count ?? 0))}</span>
             <button type="button" class="ghost small" data-lib-browse="${esc(node.node_type)}" data-lib-id="${esc(String(node.id))}">Open</button></div>`
       )
       .join("")}`,
    browse.ok ? "No browse nodes." : browse.error || "Browse unavailable"
  );

  renderRows(
    "libPublications",
    pubRows
      .slice(0, 50)
      .map((row) =>
        rowOpen(
          "publication",
          row.id,
          row.publication_number || row.title || row.id,
          `<b>${esc(row.publication_code)}</b><span>${esc(row.publication_number)} · ${esc(row.title)}</span><em>${esc(row.current_revision_number || "—")} · ${esc(row.status)}</em>`
        )
      )
      .join(""),
    pubs.ok ? "No publications." : pubs.error || "Publications unavailable"
  );

  renderRows(
    "libSearchResults",
    (q ? searchRows : [])
      .map((row) =>
        rowOpen(
          "publication",
          row.id,
          row.publication_number || row.title,
          `<b>${esc(row.publication_code)}</b><span>${esc(row.title)}</span><em>${esc(row.status)}</em>`
        )
      )
      .join(""),
    q ? (search.ok ? "No search hits." : search.error || "Search unavailable") : "Enter a search term and apply filters."
  );

  const directiveRows = (kind, type, numberKey) =>
    listify(kind.data)
      .map((row) => {
        const pub = row.publication_id
          ? `<button type="button" class="ghost small" data-we-open="publication:${esc(String(row.publication_id))}">Publication</button>`
          : "";
        return `<div class="contact-row"><b>${esc(row[numberKey] || row.id)}</b><span>${esc(row.title || "")}</span>
          <div><button type="button" class="ghost small" data-we-open="${esc(type)}:${esc(String(row.id))}" data-we-label="${esc(row[numberKey] || row.id)}">Open</button> ${pub}</div></div>`;
      })
      .join("");
  renderRows("libAds", directiveRows(ads, "airworthinessDirective", "ad_number"), ads.ok ? "No ADs." : ads.error || "ADs unavailable");
  renderRows("libSbs", directiveRows(sbs, "serviceBulletin", "sb_number"), sbs.ok ? "No SBs." : sbs.error || "SBs unavailable");
  renderRows("libEos", directiveRows(eos, "engineeringOrder", "eo_number"), eos.ok ? "No EOs." : eos.error || "EOs unavailable");
}

async function handleDeskSubmit(form) {
  const values = Object.fromEntries(new FormData(form).entries());
  const msg = el("libOpsMsg");
  const fail = (result) => {
    const text = mutationErrorMessage(result);
    if (msg) msg.textContent = text;
    toast(text);
  };
  const body = {
    publication_type_code: values.publication_type_code,
    publication_number: values.publication_number,
    title: String(values.title || "").trim(),
    access_classification: values.access_classification || "internal",
    authority: values.authority || "",
    storage: { kind: values.storage_kind || "none", uri: values.storage_uri || "" },
  };
  if (values.manufacturer_id) body.manufacturer_id = values.manufacturer_id;
  if (values.aircraft_model_id) body.aircraft_model_id = values.aircraft_model_id;
  if (values.ata_chapter_id) body.ata_chapter_id = values.ata_chapter_id;
  if (values.revision_number) {
    body.revision_number = values.revision_number;
    body.activate_revision = true;
  }
  const result = await runLocked(`lib-create:${body.publication_number}`, () => softMutate("/publications", { body }));
  if (!result) return;
  if (!result.ok) return fail(result);
  if (msg) msg.textContent = `Created ${result.data?.publication_number || ""}`;
  toast("Publication created");
  await refreshTechLibraryWorkspace();
}

function applyBrowseNode(nodeType, id) {
  if (nodeType === "manufacturer") {
    browseState = { manufacturerId: id, familyId: "", modelId: "", publicationCode: "", ataChapterId: "" };
  } else if (nodeType === "aircraft_family") {
    browseState = { ...browseState, familyId: id, modelId: "", publicationCode: "", ataChapterId: "" };
  } else if (nodeType === "aircraft_model") {
    browseState = { ...browseState, modelId: id, publicationCode: "", ataChapterId: "" };
  } else if (nodeType === "publication_type") {
    browseState = { ...browseState, publicationCode: id, ataChapterId: "" };
  } else if (nodeType === "ata_chapter") {
    browseState = { ...browseState, ataChapterId: id };
  }
  refreshTechLibraryWorkspace();
}

export function initializeLibrary() {
  el("libRefresh")?.addEventListener("click", () => refreshTechLibraryWorkspace());
  el("libApplyFilters")?.addEventListener("click", () => refreshTechLibraryWorkspace());
  el("libSearch")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") refreshTechLibraryWorkspace();
  });
  el("techLibraryWorkspace")?.addEventListener("submit", (event) => {
    const form = event.target?.closest?.("[data-lib-action]");
    if (!form) return;
    event.preventDefault();
    handleDeskSubmit(form);
  });
  el("techLibraryWorkspace")?.addEventListener("click", (event) => {
    const reset = event.target?.closest?.("[data-lib-browse-reset]");
    if (reset) {
      browseState = { manufacturerId: "", familyId: "", modelId: "", publicationCode: "", ataChapterId: "" };
      refreshTechLibraryWorkspace();
      return;
    }
    const btn = event.target?.closest?.("[data-lib-browse]");
    if (!btn) return;
    applyBrowseNode(btn.getAttribute("data-lib-browse"), btn.getAttribute("data-lib-id"));
  });
}
