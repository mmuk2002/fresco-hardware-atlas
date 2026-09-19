/* Hardware Atlas: a local, source-grounded review client. No build step. */
"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const state = {
    documents: [], documentId: null, result: null, extracted: false,
    setId: null, draft: null, drafts: new Map(), page: 1, zoom: 1,
    loadToken: 0, imageToken: 0, extracting: new Set(), saving: false,
    highlightedComponent: null, toastTimer: null,
  };
  const fields = ["qty", "description", "catalog_number", "mfr", "finish", "notes"];
  const fieldNames = {qty: "Quantity", description: "Description", catalog_number: "Catalog number", mfr: "Manufacturer", finish: "Finish", notes: "Notes"};
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  };
  const draftKey = (documentId = state.documentId, setId = state.setId) => `${documentId}:${setId}`;
  const originalSet = () => state.result?.sets.find((item) => item.id === state.setId);
  const hasDrafts = (documentId) => [...state.drafts.keys()].some((key) => key.startsWith(`${documentId}:`));
  const plural = (count, noun) => `${count} ${noun}${count === 1 ? "" : "s"}`;
  const pagesFor = (item) => [...new Set((item?.locations || []).map((location) => location.page))].sort((a, b) => a - b);
  const needsInspection = (item) => item.confidence < 0.8 || item.warnings?.length > 0 || item.components.some((component) =>
    component.warnings?.length > 0 || component.qty === null || Object.values(component.confidence || {}).some((score) => score < 0.8));

  async function request(path, options = {}) {
    let response;
    try { response = await fetch(path, options); }
    catch { throw new Error("Cannot reach the local server. Check that it is running, then try again."); }
    if (!response.ok) {
      let detail;
      try {
        const body = await response.json();
        detail = Array.isArray(body.detail) ? body.detail.map((entry) => `${entry.loc?.join(" / ") || "Field"}: ${entry.msg}`).join("; ") : body.detail;
      } catch { /* The server may have returned a non-JSON error page. */ }
      const error = new Error(detail || `Request failed (${response.status}). Please try again.`);
      error.status = response.status;
      throw error;
    }
    return response.json();
  }

  function notice(message, error = false) {
    const container = $("notice");
    container.replaceChildren(element("span", "", message));
    container.className = `notice${error ? " error" : ""}`;
    const close = element("button", "", "×");
    close.type = "button";
    close.setAttribute("aria-label", "Dismiss notification");
    close.addEventListener("click", () => { container.hidden = true; });
    container.append(close);
    container.hidden = false;
  }

  function toast(message) {
    clearTimeout(state.toastTimer);
    $("toast").textContent = message;
    $("toast").hidden = false;
    state.toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4500);
  }

  function showView(view) {
    ["empty-state", "loading-state", "workspace"].forEach((id) => { $(id).hidden = id !== view; });
  }

  async function refreshLibrary() {
    state.documents = await request("/api/documents");
    renderLibrary();
  }

  function renderLibrary() {
    const query = $("document-search").value.trim().toLowerCase();
    const documents = state.documents.filter((item) => `${item.name} ${item.project || ""}`.toLowerCase().includes(query));
    $("library-count").textContent = state.documents.length;
    $("document-list").replaceChildren();
    if (!documents.length) {
      $("document-list").append(element("p", "list-message", query ? "No matching documents." : "Your specification library starts here."));
    }
    documents.forEach((item) => {
      const button = element("button", `document-item${item.id === state.documentId ? " active" : ""}`);
      button.type = "button";
      button.title = item.name;
      button.setAttribute("aria-current", item.id === state.documentId ? "true" : "false");
      const title = element("span", "document-item-title");
      const icon = element("span", "document-icon", "PDF");
      icon.setAttribute("aria-hidden", "true");
      title.append(icon, element("span", "document-name", item.project || item.name.replace(/\.pdf$/i, "")));
      const meta = element("span", "document-meta");
      meta.append(element("i", `status-dot${item.status === "uploaded" ? " amber" : ""}`));
      const status = state.extracting.has(item.id) ? "Extracting…" : item.status === "uploaded" ? "Ready to extract" : plural(item.set_count, "set");
      meta.append(element("span", "", `${status} · ${item.page_count} pp${hasDrafts(item.id) ? " · unsaved" : ""}`));
      button.append(title, meta);
      button.addEventListener("click", () => openDocument(item.id));
      $("document-list").append(button);
    });
  }

  async function openDocument(id) {
    if (id === state.documentId && state.result) return;
    const token = ++state.loadToken;
    state.documentId = id;
    state.result = null;
    state.draft = null;
    state.setId = null;
    $("notice").hidden = true;
    $("set-search").value = "";
    $("set-filter").value = "all";
    renderLibrary();
    showView("loading-state");
    try {
      let result;
      let extracted = true;
      try { result = await request(`/api/documents/${encodeURIComponent(id)}`); }
      catch (error) {
        const metadata = state.documents.find((item) => item.id === id);
        if (error.status !== 404 || !metadata || metadata.status !== "uploaded") throw error;
        extracted = false;
        result = {...metadata, sets: [], warnings: []};
      }
      if (token !== state.loadToken) return;
      state.result = result;
      state.extracted = extracted;
      renderDocument();
      if (hasDrafts(id)) toast("Your unsaved corrections are still available in this document.");
    } catch (error) {
      if (token !== state.loadToken) return;
      showView("empty-state");
      notice(error.message, true);
    }
  }

  function renderDocument() {
    if (!state.result) return;
    const result = state.result;
    showView("workspace");
    $("document-title").textContent = result.project || result.name.replace(/\.pdf$/i, "");
    $("document-subtitle").textContent = `${result.project ? `${result.name} · ` : ""}${plural(result.page_count, "PDF page")} · ${state.extracted ? "Review against original source pages" : "Ready for local extraction"}`;
    $("stat-sets").textContent = result.sets.length;
    $("stat-components").textContent = result.sets.reduce((total, item) => total + item.components.length, 0);
    $("stat-pages").textContent = new Set(result.sets.flatMap((item) => pagesFor(item))).size;
    $("stat-review").textContent = result.sets.filter(needsInspection).length;
    $("document-warnings").hidden = !result.warnings?.length;
    $("document-warning-list").replaceChildren(...(result.warnings || []).map((warning) => element("li", "", warning)));
    for (const format of ["json", "csv"]) {
      $( `export-${format}`).href = `/api/documents/${encodeURIComponent(state.documentId)}/export?format=${format}`;
    }
    updateActions();
    renderSetList();
    if (!state.setId || !result.sets.some((item) => item.id === state.setId)) selectSet(result.sets[0]?.id || null);
  }

  function updateActions() {
    const extracting = state.extracting.has(state.documentId);
    $("extract-button").disabled = extracting || hasDrafts(state.documentId) || state.saving;
    $("extract-button").textContent = extracting ? "Extracting…" : state.extracted ? "Re-extract" : "Extract sets";
    $("extract-button").title = hasDrafts(state.documentId) ? "Save or discard this document's drafts before extracting again." : "Run local extraction; saved corrections are kept separately.";
    $("export-button").disabled = !state.extracted;
    const dirty = state.drafts.has(draftKey());
    $("save-button").disabled = !dirty || state.saving;
    $("reset-button").disabled = !dirty || state.saving;
    $("save-button").textContent = state.saving ? "Saving…" : "Save corrections";
    const status = state.saving ? "Saving corrections…" : dirty ? "Unsaved changes" : state.draft?.corrected ? "Corrections saved" : "No unsaved changes";
    $("save-state").className = `save-state${dirty ? " dirty" : ""}`;
    $("save-state").replaceChildren(element("i"), document.createTextNode(status));
  }

  function visibleSets() {
    if (!state.result) return [];
    const query = $("set-search").value.trim().toLowerCase();
    const filter = $("set-filter").value;
    return state.result.sets.filter((item) => {
      const searchable = [item.set_number, item.description, ...item.components.flatMap((component) => fields.map((field) => component[field]))].join(" ").toLowerCase();
      return (!query || searchable.includes(query)) && (filter !== "attention" || needsInspection(item)) && (filter !== "not_used" || item.status === "not_used");
    });
  }

  function renderSetList() {
    const sets = visibleSets();
    $("set-list").replaceChildren();
    $("set-result-count").textContent = `${sets.length} of ${state.result?.sets.length || 0}`;
    sets.forEach((item) => {
      const button = element("button", `set-item${state.setId === item.id ? " active" : ""}`);
      button.type = "button";
      button.dataset.setId = item.id;
      button.setAttribute("aria-pressed", String(state.setId === item.id));
      const top = element("span", "set-item-top", `Set ${item.set_number}`);
      if (needsInspection(item)) {
        const indicator = element("i");
        indicator.title = "Contains fields to inspect";
        top.append(indicator);
      }
      const description = element("div", "set-item-description", item.description || (item.status === "not_used" ? "Not used" : "Hardware schedule"));
      description.title = item.description || "";
      const pages = pagesFor(item);
      const dirty = state.drafts.has(draftKey(state.documentId, item.id));
      button.append(top, description, element("div", "set-item-meta", `${item.status === "not_used" ? "Not used" : plural(item.components.length, "item")} · ${dirty ? "Unsaved" : pages.length ? `p. ${pages[0]}${pages.length > 1 ? "+" : ""}` : "No location"}`));
      button.addEventListener("click", () => selectSet(item.id));
      $("set-list").append(button);
    });
    $("no-sets").hidden = sets.length > 0;
    $("no-sets-message").textContent = state.result?.sets.length ? "No sets match these filters. Clear the search or choose All sets." : state.extracted ? "The extractor found no hardware sets. Check the document extraction notes; a scanned PDF may need OCR." : "Select Extract sets to identify this document's hardware schedules.";
    if (!sets.length && state.result?.sets.length) {
      $("review-layout").hidden = true;
    } else if (sets.length && state.setId) {
      $("review-layout").hidden = false;
    }
  }

  function filterSets() {
    renderSetList();
    const sets = visibleSets();
    if (sets.length && !sets.some((item) => item.id === state.setId)) selectSet(sets[0].id);
  }

  function selectSet(id) {
    if (!id) {
      state.setId = null;
      state.draft = null;
      $("review-layout").hidden = true;
      return;
    }
    const item = state.result?.sets.find((entry) => entry.id === id);
    if (!item) return;
    state.setId = id;
    state.draft = state.drafts.get(draftKey()) || clone(item);
    state.highlightedComponent = null;
    $("review-layout").hidden = false;
    renderSetList();
    renderEditor();
    state.page = pagesFor(state.draft)[0] || 1;
    state.zoom = 1;
    renderPageOptions();
    loadPage();
    updateActions();
  }

  function renderEditor() {
    const item = state.draft;
    $("edit-set-number").value = item.set_number;
    $("edit-set-description").value = item.description || "";
    $("edit-set-status").value = item.status;
    $("confidence-badge").textContent = `${item.corrected ? "Corrected · " : ""}Heuristic ${Math.round(item.confidence * 100)}%`;
    $("confidence-badge").classList.toggle("low", needsInspection(item));
    $("set-warnings").hidden = !item.warnings?.length;
    $("set-warnings").replaceChildren(...(item.warnings || []).map((warning) => element("p", "", warning)));
    const notes = $("set-notes-content");
    notes.replaceChildren();
    for (const note of item.notes || []) notes.append(element("p", "", note));
    const raw = item.raw_text || item.components.map((component) => component.raw_text).filter(Boolean).join("\n");
    if (raw) notes.append(element("pre", "", raw));
    $("set-notes").hidden = !notes.childNodes.length;
    renderComponents();
  }

  function renderComponents() {
    $("component-rows").replaceChildren();
    $("component-count").textContent = state.draft.components.length;
    $("no-components").hidden = state.draft.components.length > 0;
    document.querySelector(".component-table-wrap").hidden = state.draft.components.length === 0;
    state.draft.components.forEach((component, index) => {
      const row = element("tr");
      fields.forEach((field) => {
        const score = component.confidence?.[field];
        const cell = element("td", typeof score === "number" && score < 0.8 ? "low-confidence" : "");
        const input = element(field === "description" || field === "notes" ? "textarea" : "input");
        input.value = component[field] ?? "";
        input.dataset.field = field;
        input.dataset.componentId = component.id;
        input.setAttribute("aria-label", `${fieldNames[field]}, component ${index + 1}`);
        if (input.tagName === "TEXTAREA") input.rows = 2;
        else input.type = "text";
        if (field === "qty") input.inputMode = "decimal";
        input.placeholder = field === "qty" ? "—" : "";
        input.title = `${fieldNames[field]}${typeof score === "number" ? ` · heuristic confidence ${Math.round(score * 100)}%` : " · no confidence score"}${component.warnings?.length ? `\n${component.warnings.join("\n")}` : ""}`;
        input.addEventListener("input", () => {
          const value = input.value;
          if (field === "qty") {
            const trimmed = value.trim();
            component.qty = !trimmed ? null : /^\d+(?:\.\d+)?$/.test(trimmed) && Number.isFinite(Number(trimmed)) ? Number(trimmed) : trimmed;
          } else component[field] = field === "description" ? value : value || null;
          markChanged();
        });
        input.addEventListener("focus", () => highlightComponent(component, false));
        cell.append(input);
        row.append(cell);
      });
      const actions = element("div", "row-actions");
      const locate = element("button", "evidence-button", "◎");
      locate.type = "button";
      locate.title = "Show this component in the source";
      locate.setAttribute("aria-label", `Show source for component ${index + 1}`);
      locate.disabled = !component.locations?.length;
      locate.addEventListener("click", () => highlightComponent(component, true));
      const remove = element("button", "", "×");
      remove.type = "button";
      remove.title = "Remove component";
      remove.setAttribute("aria-label", `Remove component ${index + 1}`);
      remove.addEventListener("click", () => {
        state.draft.components.splice(index, 1);
        markChanged();
        renderComponents();
        state.highlightedComponent = null;
        renderOverlays();
      });
      actions.append(locate, remove);
      const actionCell = element("td");
      actionCell.append(actions);
      row.append(actionCell);
      $("component-rows").append(row);
      if (component.catalog_resolution) {
        const resolution = component.catalog_resolution;
        const details = [resolution.description, resolution.catalog_number, resolution.mfr, resolution.finish, resolution.notes].filter(Boolean);
        const resolutionRow = element("tr", "code-resolution-row");
        const resolutionCell = element("td");
        resolutionCell.colSpan = fields.length + 1;
        const page = resolution.location?.page ? ` · source p. ${resolution.location.page}` : "";
        resolutionCell.textContent = `Resolved code ${resolution.code}: ${details.join(" · ")}${page}`;
        resolutionCell.title = `Explicit same-page lookup · ${Math.round((resolution.confidence || 0) * 100)}% heuristic confidence`;
        resolutionRow.append(resolutionCell);
        $("component-rows").append(resolutionRow);
      }
    });
  }

  function markChanged() {
    if (JSON.stringify(state.draft) === JSON.stringify(originalSet())) state.drafts.delete(draftKey());
    else state.drafts.set(draftKey(), state.draft);
    updateActions();
    renderLibrary();
    renderSetList();
  }

  async function saveCorrections() {
    if (!state.draft || state.saving || !state.drafts.has(draftKey())) return;
    if (!state.draft.set_number.trim()) {
      notice("Enter a set number before saving corrections.", true);
      $("edit-set-number").focus();
      return;
    }
    const documentId = state.documentId;
    const setId = state.setId;
    const key = draftKey();
    const submitted = clone(state.draft);
    state.saving = true;
    updateActions();
    try {
      const saved = await request(`/api/documents/${encodeURIComponent(documentId)}/sets/${encodeURIComponent(setId)}`, {
        method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(submitted),
      });
      // A save must not silently overwrite edits made while its request was in flight.
      const latest = state.drafts.get(key);
      const editedWhileSaving = latest && JSON.stringify(latest) !== JSON.stringify(submitted);
      if (!editedWhileSaving) state.drafts.delete(key);
      if (state.documentId === documentId && state.result) {
        const index = state.result.sets.findIndex((item) => item.id === setId);
        if (index >= 0) state.result.sets[index] = saved;
        if (state.setId === setId && !editedWhileSaving) {
          state.draft = clone(saved);
          renderEditor();
        }
        renderDocument();
      }
      toast(editedWhileSaving ? "Corrections saved. Your newer edits remain unsaved." : `Set ${saved.set_number}: corrections saved.`);
      await refreshLibrary();
    } catch (error) { notice(error.message, true); }
    finally { state.saving = false; updateActions(); }
  }

  function renderPageOptions() {
    const pages = pagesFor(state.draft);
    const options = [];
    for (let page = 1; page <= state.result.page_count; page++) {
      const label = pages.includes(page) ? `${page} · ${page === pages[0] ? "selected set" : "continued"}` : String(page);
      const option = element("option", "", label);
      option.value = page;
      options.push(option);
    }
    $("page-select").replaceChildren(...options);
    $("page-select").value = state.page;
    updatePageNavigation();
  }

  function updatePageNavigation() {
    $("previous-page").disabled = state.page <= 1;
    $("next-page").disabled = state.page >= (state.result?.page_count || 1);
  }

  function changePage(page) {
    if (!state.result || page < 1 || page > state.result.page_count) return;
    state.page = page;
    $("page-select").value = page;
    state.highlightedComponent = null;
    loadPage();
  }

  function loadPage() {
    if (!state.result || !state.draft) return;
    const token = ++state.imageToken;
    const image = $("source-image");
    $("source-error").hidden = true;
    $("page-stage").hidden = false;
    $("source-viewport").classList.add("loading");
    applyZoom();
    renderOverlays();
    updatePageNavigation();
    image.onload = () => {
      if (token !== state.imageToken) return;
      $("source-viewport").classList.remove("loading");
      renderOverlays();
      scrollToEvidence();
    };
    image.onerror = () => {
      if (token !== state.imageToken) return;
      $("source-viewport").classList.remove("loading");
      $("page-stage").hidden = true;
      $("source-error").textContent = "This source page could not be loaded. Check that the original PDF is still available, then select the page again.";
      $("source-error").hidden = false;
    };
    image.alt = `${state.result.name}, PDF page ${state.page}. Highlighted regions identify the selected hardware set.`;
    image.src = `/api/documents/${encodeURIComponent(state.documentId)}/pages/${state.page}.png`;
  }

  function renderOverlays() {
    const container = $("source-overlays");
    container.replaceChildren();
    if (!state.draft) return;
    const locations = (state.draft.locations || []).filter((location) => location.page === state.page);
    const box = (location, component = false) => {
      const [left, top, right, bottom] = location.bbox;
      if (!location.page_width || !location.page_height) return;
      const overlay = element("div", `bbox-overlay${component ? " component-highlight" : ""}`);
      Object.assign(overlay.style, {left: `${left / location.page_width * 100}%`, top: `${top / location.page_height * 100}%`, width: `${(right - left) / location.page_width * 100}%`, height: `${(bottom - top) / location.page_height * 100}%`});
      if (!component) overlay.append(element("span", "", `SET ${state.draft.set_number}`));
      container.append(overlay);
    };
    locations.forEach((location) => box(location));
    const component = state.draft.components.find((item) => item.id === state.highlightedComponent);
    (component?.locations || []).filter((location) => location.page === state.page).forEach((location) => box(location, true));
    const location = locations[0];
    const lineLabel = location?.line_start ? ` · lines ${location.line_start}–${location.line_end || location.line_start}` : "";
    $("source-location").textContent = `PDF p. ${state.page} of ${state.result.page_count}${locations.length ? lineLabel : " · no set region on this page"}`;
  }

  function scrollToEvidence() {
    const target = $("source-overlays").querySelector(".component-highlight") || $("source-overlays").querySelector(".bbox-overlay");
    const viewport = $("source-viewport");
    viewport.scrollTop = target ? Math.max(0, target.offsetTop - 45) : 0;
    viewport.scrollLeft = 0;
  }

  function highlightComponent(component, scroll) {
    state.highlightedComponent = component.id;
    const location = component.locations?.[0];
    if (location && location.page !== state.page) {
      state.page = location.page;
      $("page-select").value = state.page;
      loadPage();
    } else {
      renderOverlays();
      if (scroll) scrollToEvidence();
    }
    if (scroll) document.querySelector(".source-panel").scrollIntoView({behavior: "smooth", block: "nearest"});
  }

  function applyZoom() {
    $("page-stage").style.width = `${state.zoom * 100}%`;
    $("zoom-value").textContent = state.zoom === 1 ? "Fit" : `${Math.round(state.zoom * 100)}%`;
    $("zoom-out").disabled = state.zoom <= 1;
    $("zoom-in").disabled = state.zoom >= 3;
  }

  async function extractDocument(id = state.documentId) {
    if (!id || state.extracting.has(id)) return;
    if (hasDrafts(id)) { notice("Save or discard this document's unsaved corrections before extracting again."); return; }
    state.extracting.add(id);
    renderLibrary();
    updateActions();
    if (state.documentId === id) notice("Extracting hardware sets locally. Large specification books may take a few minutes; you can browse another document while this runs.");
    try {
      const result = await request(`/api/documents/${encodeURIComponent(id)}/extract`, {
        method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({ocr: $("use-ocr").checked}),
      });
      if (state.documentId === id) {
        ++state.loadToken;
        state.result = result;
        state.extracted = true;
        state.setId = null;
        $("notice").hidden = true;
        renderDocument();
      }
      toast(`Extraction complete: ${plural(result.sets.length, "hardware set")}.`);
      await refreshLibrary();
    } catch (error) { notice(error.message, true); }
    finally { state.extracting.delete(id); renderLibrary(); updateActions(); }
  }

  async function uploadDocument(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) { notice("Choose a PDF specification document.", true); return; }
    $("file-upload").disabled = true;
    $("upload-label").classList.add("busy");
    $("upload-status").textContent = "Importing PDF into the local library…";
    try {
      const form = new FormData();
      form.append("file", file);
      const metadata = await request("/api/documents", {method: "POST", body: form});
      await refreshLibrary();
      await openDocument(metadata.id);
      if (metadata.status === "uploaded") {
        $("upload-status").textContent = "PDF imported · extracting hardware sets…";
        await extractDocument(metadata.id);
      } else toast("This PDF is already in your library. Opened the saved extraction.");
    } catch (error) { notice(error.message, true); }
    finally {
      $("file-upload").disabled = false;
      $("file-upload").value = "";
      $("upload-label").classList.remove("busy");
      $("upload-status").textContent = "PDF documents · processed locally";
    }
  }

  $("document-search").addEventListener("input", renderLibrary);
  $("set-search").addEventListener("input", filterSets);
  $("set-filter").addEventListener("change", filterSets);
  $("edit-set-number").addEventListener("input", (event) => { state.draft.set_number = event.target.value; markChanged(); renderOverlays(); });
  $("edit-set-description").addEventListener("input", (event) => { state.draft.description = event.target.value || null; markChanged(); });
  $("edit-set-status").addEventListener("change", (event) => { state.draft.status = event.target.value; markChanged(); });
  $("add-component").addEventListener("click", () => {
    state.draft.components.push({id: crypto.randomUUID().replaceAll("-", ""), qty: null, description: "", catalog_number: null, mfr: null, finish: null, notes: null, confidence: {}, locations: [], raw_text: "", warnings: []});
    markChanged();
    renderComponents();
    $("component-rows").lastElementChild.querySelector('[data-field="description"]').focus();
  });
  $("save-button").addEventListener("click", saveCorrections);
  $("reset-button").addEventListener("click", () => {
    state.drafts.delete(draftKey());
    state.draft = clone(originalSet());
    renderEditor();
    renderOverlays();
    renderLibrary();
    renderSetList();
    updateActions();
    toast("Unsaved changes discarded for this set.");
  });
  $("page-select").addEventListener("change", (event) => changePage(Number(event.target.value)));
  $("previous-page").addEventListener("click", () => changePage(state.page - 1));
  $("next-page").addEventListener("click", () => changePage(state.page + 1));
  $("zoom-in").addEventListener("click", () => { state.zoom = Math.min(3, state.zoom + 0.25); applyZoom(); });
  $("zoom-out").addEventListener("click", () => { state.zoom = Math.max(1, state.zoom - 0.25); applyZoom(); });
  $("zoom-reset").addEventListener("click", () => { state.zoom = 1; applyZoom(); scrollToEvidence(); });
  $("extract-button").addEventListener("click", () => extractDocument());
  $("file-upload").addEventListener("change", (event) => uploadDocument(event.target.files[0]));
  document.querySelectorAll('label[for="file-upload"]').forEach((label) => {
    label.tabIndex = 0;
    label.setAttribute("role", "button");
    label.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") { event.preventDefault(); $("file-upload").click(); }
    });
  });
  $("export-button").addEventListener("click", () => {
    $("export-options").hidden = !$("export-options").hidden;
    $("export-button").setAttribute("aria-expanded", String(!$("export-options").hidden));
  });
  for (const format of ["json", "csv"]) $( `export-${format}`).addEventListener("click", (event) => {
    if (hasDrafts(state.documentId)) {
      event.preventDefault();
      notice("This document has unsaved corrections. Save or discard them before exporting so the download matches your review.");
    }
    $("export-options").hidden = true;
    $("export-button").setAttribute("aria-expanded", "false");
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".export-menu")) {
      $("export-options").hidden = true;
      $("export-button").setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); saveCorrections(); }
    if (event.key === "Escape") { $("export-options").hidden = true; $("export-button").setAttribute("aria-expanded", "false"); }
  });
  window.addEventListener("beforeunload", (event) => {
    if (state.drafts.size) { event.preventDefault(); event.returnValue = ""; }
  });

  async function initialize() {
    try {
      await refreshLibrary();
      if (state.documents.length) await openDocument(state.documents[0].id);
      else showView("empty-state");
    } catch (error) {
      showView("empty-state");
      $("document-list").replaceChildren(element("p", "list-message", "Library unavailable. Reload after starting the local server."));
      notice(error.message, true);
    }
  }
  initialize();
})();
