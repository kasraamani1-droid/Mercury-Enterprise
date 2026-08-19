/**
 * Publications / Technical Library operator UI (Workspace Engine + helpers).
 * Uses existing /api/v1/publications and /api/v1/library routes.
 */

import { esc, toast } from "../utils.js";
import { softMutate } from "../ux2/api.js";
import { mutationErrorMessage, runLocked } from "./logistics-ops.js";

export function normalizeRole(role) {
  return String(role || "").trim();
}

export function sessionCanReadPublications(role) {
  const value = normalizeRole(role);
  return value === "Viewer" || value === "Operator" || value === "Reviewer" || value === "Administrator";
}

export function sessionCanManagePublications(role) {
  const value = normalizeRole(role);
  return value === "Operator" || value === "Administrator";
}

export function sessionCanAdminPublications(role) {
  return normalizeRole(role) === "Administrator";
}

export function filterPublications(rows, { q = "", code = "", status = "" } = {}) {
  const query = String(q || "").trim().toLowerCase();
  const pubCode = String(code || "").trim().toLowerCase();
  const st = String(status || "").trim().toLowerCase();
  return (Array.isArray(rows) ? rows : []).filter((row) => {
    if (pubCode && String(row.publication_code || "").toLowerCase() !== pubCode) return false;
    if (st && String(row.status || "").toLowerCase() !== st) return false;
    if (!query) return true;
    const hay = `${row.title || ""} ${row.publication_number || ""} ${row.publication_code || ""} ${row.authority || ""} ${row.current_revision_number || ""} ${row.id || ""}`.toLowerCase();
    return hay.includes(query);
  });
}

export function libraryBrowseQuery(filters = {}) {
  const params = new URLSearchParams();
  if (filters.manufacturerId) params.set("manufacturer_id", filters.manufacturerId);
  if (filters.familyId) params.set("family_id", filters.familyId);
  if (filters.modelId) params.set("aircraft_model_id", filters.modelId);
  if (filters.publicationCode) params.set("publication_code", filters.publicationCode);
  if (filters.ataChapterId) params.set("ata_chapter_id", filters.ataChapterId);
  const qs = params.toString();
  return qs ? `/library/browse?${qs}` : "/library/browse";
}

export function publicationsOpsCacheKeys(session, mutation = {}) {
  const publications = [];
  const aircraft = [];
  const components = [];
  const ads = [];
  const sbs = [];
  const eos = [];
  const push = (list, value) => {
    const id = String(value || "").trim();
    if (id && !list.includes(id)) list.push(id);
  };
  if (session?.type === "publication") push(publications, session.id);
  if (session?.type === "aircraft") push(aircraft, session.id);
  if (session?.type === "component") push(components, session.id);
  push(publications, mutation.publicationId);
  push(aircraft, mutation.aircraftId || session?.record?.aircraft_id);
  push(components, mutation.componentId);
  push(ads, mutation.adId);
  push(sbs, mutation.sbId);
  push(eos, mutation.eoId);
  return { publications, aircraft, components, ads, sbs, eos };
}

function role(bundle) {
  return bundle?.sessionRole || "";
}

function empty(text) {
  return `<div class="mx-empty">${esc(text)}</div>`;
}

function loadBanner(load, label) {
  if (!load || load.ok) return "";
  return `<div class="mx-empty">${esc(label)} unavailable: ${esc(load.error || `HTTP ${load.status || 0}`)}</div>`;
}

function table(headers, body) {
  return `<table class="data-table we-ops-table"><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table>`;
}

export function publicationChip(row) {
  if (!row?.id) return "";
  const label = row.publication_number || row.title || row.id;
  return `<button type="button" class="mx-chip" data-we-open="publication:${esc(String(row.id))}" data-we-label="${esc(label)}">${esc(row.publication_code || "PUB")} ${esc(label)}</button>`;
}

export function renderLinkedPublication(record, bundle) {
  const id = record?.publication_id;
  if (!id) return `<p class="mx-subtitle">No publication_id on this record. Link at create time from Planning or the library desk.</p>`;
  const hit = (bundle?.publications || []).find((row) => String(row.id) === String(id));
  if (hit) return `<p class="mx-subtitle">Linked publication</p><div class="mx-row" style="flex-wrap:wrap;gap:8px">${publicationChip(hit)}</div>`;
  return `<p class="mx-subtitle">Linked publication</p><button type="button" class="mx-chip" data-we-open="publication:${esc(String(id))}" data-we-label="${esc(String(id))}">Open ${esc(String(id))}</button>`;
}

export function renderPublicationWorkspace(session, record, bundle) {
  const row = record || {};
  const canManage = sessionCanManagePublications(role(bundle));
  const canAdmin = sessionCanAdminPublications(role(bundle));
  const revisions = bundle?.revisions || [];
  const current = revisions.find((rev) => String(rev.id) === String(row.current_revision_id)) || revisions.find((rev) => rev.status === "current");
  const ataChapters = bundle?.ataChapters || [];
  return `
    ${loadBanner(bundle?.recordLoad, "Publication")}
    <article class="mx-card">
      <div class="mx-card-header"><h3>${esc(row.publication_number || session.id)}</h3><span class="mx-chip">${esc(row.status || "—")}</span></div>
      <p class="mx-subtitle">${esc(row.publication_code || "")} · ${esc(row.title || "")} · access ${esc(row.access_classification || "—")}</p>
      <p class="mx-subtitle">${esc(row.description || "")}</p>
      <p class="mx-subtitle">Current revision ${esc(row.current_revision_number || current?.revision_number || "—")} · ATA ${esc(row.ata_chapter_id || "—")} · model ${esc(row.aircraft_model_id || "—")}</p>
      <p class="mx-subtitle">Storage locators only — OEM binaries are not hosted in this catalog.</p>
      <div class="mx-row" style="flex-wrap:wrap;gap:8px;margin-top:8px">
        <button type="button" class="mx-chip" data-ux2-goto="techLibrary">Technical Library</button>
        <button type="button" class="mx-chip" data-ux2-goto="engineering">Engineering</button>
        <button type="button" class="mx-chip" data-ux2-goto="planning">Planning</button>
      </div>
    </article>
    <article class="mx-card" style="margin-top:12px">
      <div class="mx-card-header"><h3>Revisions</h3></div>
      ${
        revisions.length
          ? table(
              ["Revision", "Status", "Effective", "Storage"],
              revisions
                .map(
                  (rev) => `<tr>
                    <td class="mx-mono">${esc(rev.revision_number || rev.id)}</td>
                    <td><span class="mx-chip">${esc(rev.status || "—")}</span></td>
                    <td>${esc(String(rev.effective_date || "—").slice(0, 10))}</td>
                    <td>${esc(rev.storage_kind || "none")}${rev.storage_uri ? ` · ${esc(rev.storage_uri)}` : ""}</td>
                  </tr>`
                )
                .join("")
            )
          : empty("No revisions loaded.")
      }
    </article>
    ${
      canManage
        ? `<form id="wePubRevisionForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Add revision (draft)</strong>
            <input type="hidden" name="publication_id" value="${esc(String(row.id || session.id))}" />
            <label class="mx-field">Revision number<input class="mx-input" name="revision_number" required maxlength="80" /></label>
            <label class="mx-field">Change summary<input class="mx-input" name="change_summary" maxlength="400" /></label>
            <label class="mx-field">Storage kind<select class="mx-input" name="storage_kind"><option value="none">none</option><option value="external_url">external_url</option><option value="object_storage">object_storage</option><option value="future_ingestion">future_ingestion</option></select></label>
            <label class="mx-field">Locator URI<input class="mx-input" name="storage_uri" placeholder="https://…" /></label>
            <button class="mx-btn" type="submit">Create draft revision</button>
          </form>`
        : `<p class="mx-subtitle">Revision create requires publication.manage (Operator or Administrator).</p>`
    }
    ${
      canManage
        ? `<form id="wePubAtaForm" class="mx-card" style="padding:12px;margin-top:12px">
            <strong>Link ATA chapter</strong>
            <input type="hidden" name="publication_id" value="${esc(String(row.id || session.id))}" />
            <label class="mx-field">ATA<select class="mx-input" name="ata_chapter_id" required>
              <option value="">Select ATA</option>
              ${ataChapters.map((ata) => `<option value="${esc(String(ata.id))}">${esc(ata.chapter_number || ata.code || ata.id)} · ${esc(ata.title || ata.name || "")}</option>`).join("")}
            </select></label>
            <button class="mx-btn" type="submit">Link ATA</button>
          </form>`
        : ""
    }
    ${
      canAdmin
        ? `<div class="enterprise-grid" style="margin-top:12px">
            <form id="wePubActivateForm" class="mx-card" style="padding:12px">
              <strong>Activate revision</strong>
              <input type="hidden" name="publication_id" value="${esc(String(row.id || session.id))}" />
              <label class="mx-field">Draft revision<select class="mx-input" name="revision_id" required>
                <option value="">Select draft</option>
                ${revisions
                  .filter((rev) => String(rev.status || "") === "draft")
                  .map((rev) => `<option value="${esc(String(rev.id))}">${esc(rev.revision_number)}</option>`)
                  .join("")}
              </select></label>
              <button class="mx-btn" type="submit">Activate (supersedes current)</button>
            </form>
            <form id="wePubAccessForm" class="mx-card" style="padding:12px">
              <strong>Access classification</strong>
              <input type="hidden" name="publication_id" value="${esc(String(row.id || session.id))}" />
              <label class="mx-field">Class<select class="mx-input" name="access_classification">
                <option value="internal"${row.access_classification === "internal" ? " selected" : ""}>internal</option>
                <option value="restricted"${row.access_classification === "restricted" ? " selected" : ""}>restricted</option>
                <option value="licensed"${row.access_classification === "licensed" ? " selected" : ""}>licensed</option>
                <option value="public"${row.access_classification === "public" ? " selected" : ""}>public</option>
              </select></label>
              <button class="mx-btn" type="submit">Update access</button>
            </form>
            <form id="wePubArchiveForm" class="mx-card" style="padding:12px">
              <strong>Archive</strong>
              <input type="hidden" name="publication_id" value="${esc(String(row.id || session.id))}" />
              <button class="mx-btn" type="submit">Archive publication</button>
            </form>
          </div>`
        : `<p class="mx-subtitle">Archive, access classification, and revision activation require publication.admin (Administrator).</p>`
    }
    <p class="mx-subtitle" id="wePubMsg"></p>
  `;
}

export function renderAircraftPublications(session, bundle) {
  const rows = bundle?.publications || [];
  return `
    ${loadBanner(bundle?.publicationsLoad, "Aircraft publications")}
    <p class="mx-subtitle">Publications for this aircraft’s model via GET /publications/by-aircraft/{id}.</p>
    ${
      rows.length
        ? table(
            ["Code", "Number", "Title", "Rev", "Status"],
            rows
              .slice(0, 40)
              .map(
                (row) => `<tr class="we-row-open" data-we-open="publication:${esc(String(row.id))}" data-we-label="${esc(row.publication_number || row.title || row.id)}">
                  <td class="mx-mono">${esc(row.publication_code || "—")}</td>
                  <td class="mx-mono">${esc(row.publication_number || "—")}</td>
                  <td>${esc(row.title || "—")}</td>
                  <td>${esc(row.current_revision_number || "—")}</td>
                  <td><span class="mx-chip">${esc(row.status || "—")}</span></td>
                </tr>`
              )
              .join("")
          )
        : empty("No publications for this aircraft model.")
    }
  `;
}

export function renderComponentPublications(session, bundle) {
  const payload = bundle?.componentPublications;
  const rows = payload?.publications || [];
  return `
    ${loadBanner(bundle?.componentPublicationsLoad, "Component publications")}
    <p class="mx-subtitle">CMM/ATA applicability via GET /publications/by-component/{id}.</p>
    ${
      rows.length
        ? table(
            ["Code", "Number", "Title", "Status"],
            rows
              .map(
                (row) => `<tr class="we-row-open" data-we-open="publication:${esc(String(row.id))}" data-we-label="${esc(row.publication_number || row.title || row.id)}">
                  <td class="mx-mono">${esc(row.publication_code || "—")}</td>
                  <td class="mx-mono">${esc(row.publication_number || "—")}</td>
                  <td>${esc(row.title || "—")}</td>
                  <td><span class="mx-chip">${esc(row.status || "—")}</span></td>
                </tr>`
              )
              .join("")
          )
        : empty("No publications linked to this component catalog/ATA.")
    }
  `;
}

function setPubMessage(text, ok) {
  const node = document.getElementById("wePubMsg") || document.getElementById("libOpsMsg");
  if (!node) return;
  node.textContent = text || "";
  node.style.color = ok ? "" : "var(--danger, #c44)";
}

function formValues(form) {
  return Object.fromEntries(new FormData(form).entries());
}

export function bindPublicationsOpsPanel(active, { onRefresh } = {}) {
  if (!active) return;
  const fail = (result) => {
    const msg = mutationErrorMessage(result);
    setPubMessage(msg, false);
    toast(msg);
  };

  document.getElementById("wePubRevisionForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanManagePublications(role(active.bundle))) return fail({ status: 403, error: "publication.manage required" });
    const values = formValues(event.target);
    const result = await runLocked(`pub-rev:${values.publication_id}`, () =>
      softMutate(`/publications/${encodeURIComponent(values.publication_id)}/revisions`, {
        body: {
          revision_number: values.revision_number,
          change_summary: values.change_summary || "",
          activate: false,
          storage: { kind: values.storage_kind || "none", uri: values.storage_uri || "" },
        },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast(`Revision ${result.data?.revision_number || ""} created`);
    await onRefresh?.({ publicationId: values.publication_id });
  });

  document.getElementById("wePubAtaForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const result = await runLocked(`pub-ata:${values.publication_id}`, () =>
      softMutate(`/publications/${encodeURIComponent(values.publication_id)}/ata/${encodeURIComponent(values.ata_chapter_id)}`, { method: "POST" })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("ATA linked");
    await onRefresh?.({ publicationId: values.publication_id });
  });

  document.getElementById("wePubActivateForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!sessionCanAdminPublications(role(active.bundle))) return fail({ status: 403, error: "publication.admin required" });
    const values = formValues(event.target);
    if (!window.confirm("Activate this revision? The current revision will be superseded.")) return;
    const result = await runLocked(`pub-act:${values.revision_id}`, () =>
      softMutate(
        `/publications/${encodeURIComponent(values.publication_id)}/revisions/${encodeURIComponent(values.revision_id)}/activate`,
        { method: "POST" }
      )
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Revision activated");
    await onRefresh?.({ publicationId: values.publication_id });
  });

  document.getElementById("wePubAccessForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    const result = await runLocked(`pub-access:${values.publication_id}`, () =>
      softMutate(`/publications/${encodeURIComponent(values.publication_id)}/access-classification`, {
        method: "POST",
        body: { access_classification: values.access_classification },
      })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Access classification updated");
    await onRefresh?.({ publicationId: values.publication_id });
  });

  document.getElementById("wePubArchiveForm")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = formValues(event.target);
    if (!window.confirm("Archive this publication?")) return;
    const result = await runLocked(`pub-arch:${values.publication_id}`, () =>
      softMutate(`/publications/${encodeURIComponent(values.publication_id)}/archive`, { method: "POST" })
    );
    if (!result) return;
    if (!result.ok) return fail(result);
    toast("Publication archived");
    await onRefresh?.({ publicationId: values.publication_id });
  });
}
