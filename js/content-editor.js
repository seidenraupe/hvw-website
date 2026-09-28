/**
 * On-Page-Redaktion: Entwurf speichern, Vorschau, Freigabe.
 * Erlaubt: fett / kursiv / unterstrichen und Links (interne Seiten oder http/https). Kein Layout.
 */
(function () {
  const API = "redaktion/api.php";
  let session = null;
  let schema = {};
  let draftFields = {};
  let liveFields = {};
  let view = "draft";
  let dirty = false;
  let activeEl = null;
  let reviewIndex = 0;
  const REVIEW_KEY = "hvw-review-id";
  const ACCEPTED_KEY = "hvw-review-accepted";
  let acceptedIds = loadAccepted();
  let savedRange = null;
  let linkDialogOpen = false;

  const $ = (sel, root) => (root || document).querySelector(sel);

  function isFreigabe() {
    return session && session.role === "freigabe";
  }

  function loadAccepted() {
    try {
      const raw = sessionStorage.getItem(ACCEPTED_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(arr) ? arr : []);
    } catch (_e) {
      return new Set();
    }
  }

  function persistAccepted() {
    sessionStorage.setItem(ACCEPTED_KEY, JSON.stringify([...acceptedIds]));
  }

  function currentPageName() {
    const parts = (location.pathname || "").split("/").filter(Boolean);
    let name = parts[parts.length - 1] || "index.html";
    if (!name.includes(".")) name = "index.html";
    return name;
  }

  function pageHref(page) {
    return page || "index.html";
  }

  function normText(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function sameText(a, b) {
    return normText(a) === normText(b);
  }

  function canonicalValue(id, value) {
    const meta = fieldMeta(id);
    const text = String(value || "");
    if (meta.type === "image") return text.trim();
    if (meta.rich && window.hvwCanonicalRich) return window.hvwCanonicalRich(text);
    return normText(text);
  }

  function sameField(id, a, b) {
    return canonicalValue(id, a) === canonicalValue(id, b);
  }

  function draftViewFields() {
    return Object.assign({}, liveFields, draftFields);
  }

  function currentFields() {
    return Object.assign({}, liveFields, draftFields, view === "draft" ? collectFields() : {});
  }

  function allChanges() {
    const current = currentFields();
    const list = [];
    Object.keys(schema).forEach((id) => {
      if (!sameField(id, current[id], liveFields[id])) {
        list.push({
          id,
          label: fieldMeta(id).label,
          page: fieldMeta(id).page || "index.html",
          live: String(liveFields[id] || ""),
          draft: String(current[id] || ""),
        });
      }
    });
    return list;
  }

  function fieldEl(id) {
    const safe = String(id).replace(/"/g, "");
    return (
      document.querySelector('[data-content="' + safe + '"]') ||
      document.querySelector('[data-content-image="' + safe + '"]')
    );
  }

  function isImageField(id) {
    const meta = fieldMeta(id);
    return meta.type === "image";
  }

  function imageFieldValue(el) {
    const img = el.querySelector("img");
    const fallback = el.getAttribute("data-content-image-fallback") || "";
    const src = img ? img.getAttribute("src") || "" : "";
    return src && src !== fallback ? src : "";
  }

  function clip(html, max) {
    const text = strip(html).replace(/\s+/g, " ").trim();
    if (text.length <= max) return text;
    return text.slice(0, max - 1) + "…";
  }

  function csrfHeaders() {
    return {
      "Content-Type": "application/json",
      "X-CSRF-Token": session && session.csrf ? session.csrf : "",
    };
  }

  async function api(action, options) {
    const opts = options || {};
    const url = API + "?action=" + encodeURIComponent(action);
    const res = await fetch(url, Object.assign({ credentials: "same-origin", cache: "no-store" }, opts));
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || "Die Anfrage ist fehlgeschlagen.");
    }
    return data;
  }

  function plainLen(html) {
    const d = document.createElement("div");
    d.innerHTML = html || "";
    return (d.textContent || "").replace(/\s+/g, " ").trim().length;
  }

  function fieldValue(el) {
    const rich = el.getAttribute("data-content-rich") === "1";
    const raw = rich ? window.hvwSanitizeRich(el.innerHTML) : el.textContent || "";
    return normText(raw);
  }

  function collectFields() {
    const out = {};
    document.querySelectorAll("[data-content]").forEach((el) => {
      out[el.getAttribute("data-content")] = fieldValue(el);
    });
    document.querySelectorAll("[data-content-image]").forEach((el) => {
      out[el.getAttribute("data-content-image")] = imageFieldValue(el);
    });
    return out;
  }

  function markFieldState(el, id, currentValue) {
    const editing = view === "draft";
    const changed = editing && !sameField(id, currentValue, liveFields[id]);
    const accepted = changed && acceptedIds.has(id);
    el.classList.toggle("hvw-changed", changed && !accepted);
    el.classList.toggle("hvw-accepted", accepted);
    if (accepted) {
      el.setAttribute("title", "Angenommen — wird mit «Live schalten» öffentlich");
      el.setAttribute("data-change-hint", "Angenommen");
    } else if (changed) {
      el.setAttribute("title", "Geändert — noch nicht öffentlich, wartet auf Freigabe");
      el.setAttribute("data-change-hint", "Geändert — zur Freigabe");
    } else {
      el.removeAttribute("title");
      el.removeAttribute("data-change-hint");
      acceptedIds.delete(id);
    }
  }

  function markChangedFields() {
    document.querySelectorAll("[data-content]").forEach((el) => {
      const id = el.getAttribute("data-content");
      markFieldState(el, id, fieldValue(el));
    });
    document.querySelectorAll("[data-content-image]").forEach((el) => {
      const id = el.getAttribute("data-content-image");
      markFieldState(el, id, imageFieldValue(el));
    });
    persistAccepted();
    updateReviewDock();
  }

  function setView(mode) {
    view = mode;
    applyCurrent();
    updateBar();
  }

  function applyCurrent() {
    const fields = view === "live" ? liveFields : draftViewFields();
    window.hvwApplyContent(fields);
    document.body.classList.toggle("hvw-editing", view === "draft");
    document.querySelectorAll("[data-content]").forEach((el) => {
      const canEdit = view === "draft";
      el.contentEditable = canEdit ? "true" : "false";
      el.classList.toggle("hvw-editable", canEdit);
      el.spellcheck = true;
    });
    document.querySelectorAll("[data-content-image]").forEach((el) => {
      el.classList.toggle("hvw-image-editable", view === "draft");
    });
    markChangedFields();
    if (view !== "draft") closeLinkDialog();
    updateFormatState();
  }

  function fieldMeta(id) {
    return schema[id] || { label: id, max: 400, rich: false, multiline: true, type: "text" };
  }

  function updateCounter() {
    const box = $("#hvw-counter");
    if (!box || !activeEl) {
      if (box) box.textContent = "";
      return;
    }
    const id = activeEl.getAttribute("data-content");
    const meta = fieldMeta(id);
    const len = plainLen(activeEl.getAttribute("data-content-rich") === "1" ? activeEl.innerHTML : activeEl.textContent);
    box.textContent = meta.label + " · " + len + " / " + meta.max + " Zeichen";
    box.classList.toggle("is-over", len > meta.max);
    updateFormatState();
  }

  function markDirty() {
    dirty = true;
    markChangedFields();
    updateBar();
  }

  function updateBar() {
    const bar = $("#hvw-editor-bar");
    if (!bar) return;
    const changes = diffCount();
    $("#hvw-role-label").textContent = session.name + " (" + (session.role === "freigabe" ? "Freigabe" : "Redaktion") + ")";
    $("#hvw-status").textContent =
      view === "live"
        ? "Sie sehen die Live-Seite"
        : changes
          ? "Entwurf · " + changes + " Änderung" + (changes === 1 ? "" : "en") + (dirty ? " (nicht gespeichert)" : "")
          : dirty
            ? "Entwurf · nicht gespeichert"
            : "Entwurf · identisch mit Live";
    const legend = $("#hvw-legend");
    if (legend) legend.hidden = view !== "draft" || changes === 0;
    const diffBtn = $("#hvw-btn-diff");
    if (diffBtn) diffBtn.classList.toggle("is-attention", view === "draft" && changes > 0);
    $("#hvw-btn-draft").hidden = view === "draft";
    $("#hvw-btn-live").hidden = view === "live";
    $("#hvw-btn-save").disabled = view !== "draft";
    const pub = $("#hvw-btn-publish");
    if (pub) {
      pub.hidden = !isFreigabe();
      pub.disabled = view !== "draft" || dirty || changes === 0;
    }
    const zugang = $("#hvw-btn-zugang");
    if (zugang) zugang.hidden = !isFreigabe();
    updateReviewDock();
  }

  function diffCount() {
    return allChanges().length;
  }

  function syncReviewIndex(changes) {
    if (!changes.length) {
      reviewIndex = 0;
      return;
    }
    if (reviewIndex >= changes.length) reviewIndex = changes.length - 1;
    if (reviewIndex < 0) reviewIndex = 0;
  }

  function highlightCurrent(id) {
    document.querySelectorAll("[data-content].hvw-review-current").forEach((el) => {
      el.classList.remove("hvw-review-current");
    });
    const el = fieldEl(id);
    if (!el) return null;
    el.classList.add("hvw-review-current");
    return el;
  }

  function goToChange(index, opts) {
    const options = opts || {};
    if (view !== "draft") setView("draft");
    const changes = allChanges();
    if (!changes.length) {
      updateReviewDock();
      return;
    }
    reviewIndex = ((index % changes.length) + changes.length) % changes.length;
    const item = changes[reviewIndex];
    sessionStorage.setItem(REVIEW_KEY, item.id);
    if (!options.stay && item.page && item.page !== currentPageName()) {
      location.href = pageHref(item.page);
      return;
    }
    const el = highlightCurrent(item.id);
    if (el) {
      el.scrollIntoView({ behavior: options.instant ? "auto" : "smooth", block: "center" });
      if (options.focus) {
        el.focus({ preventScroll: true });
        activeEl = el;
        updateCounter();
      }
    }
    updateReviewDock();
  }

  function goRelative(step) {
    const changes = allChanges();
    if (!changes.length) return;
    syncReviewIndex(changes);
    goToChange(reviewIndex + step);
  }

  function goToNextOpen() {
    const changes = allChanges();
    if (!changes.length) {
      updateReviewDock();
      return;
    }
    const start = reviewIndex;
    for (let i = 1; i <= changes.length; i += 1) {
      const next = changes[(start + i) % changes.length];
      if (!acceptedIds.has(next.id)) {
        goToChange((start + i) % changes.length);
        return;
      }
    }
    updateReviewDock();
  }

  function acceptCurrent() {
    const changes = allChanges();
    if (!changes.length) return;
    syncReviewIndex(changes);
    acceptedIds.add(changes[reviewIndex].id);
    persistAccepted();
    markChangedFields();
    toast("Änderung angenommen.");
    goToNextOpen();
  }

  function editCurrent() {
    const changes = allChanges();
    if (!changes.length) return;
    syncReviewIndex(changes);
    const id = changes[reviewIndex].id;
    acceptedIds.delete(id);
    persistAccepted();
    goToChange(reviewIndex, { focus: true });
  }

  function revertCurrent() {
    const changes = allChanges();
    if (!changes.length) return;
    syncReviewIndex(changes);
    const item = changes[reviewIndex];
    if (!confirm("Diese Änderung rückgängig machen und den Live-Stand wiederherstellen?")) return;
    draftFields[item.id] = liveFields[item.id] || "";
    acceptedIds.delete(item.id);
    persistAccepted();
    const el = fieldEl(item.id);
    if (el) window.hvwApplyContent({ [item.id]: draftFields[item.id] });
    markDirty();
    saveDraft(true).catch(() => {});
    toast("Änderung rückgängig gemacht.");
    const left = allChanges();
    if (left.length) goToChange(Math.min(reviewIndex, left.length - 1), { stay: true });
    else updateReviewDock();
  }

  function updateReviewDock() {
    const dock = $("#hvw-review-dock");
    if (!dock) return;
    const changes = view === "draft" ? allChanges() : [];
    const show = isFreigabe() && view === "draft" && changes.length > 0;
    dock.hidden = !show;
    document.body.classList.toggle("hvw-has-review", show);
    if (!show) {
      document.querySelectorAll(".hvw-review-current").forEach((el) => el.classList.remove("hvw-review-current"));
      return;
    }
    syncReviewIndex(changes);
    const item = changes[reviewIndex];
    const open = changes.filter((c) => !acceptedIds.has(c.id)).length;
    $("#hvw-review-pos").textContent = reviewIndex + 1 + " / " + changes.length;
    $("#hvw-review-label").textContent = item.label;
    $("#hvw-review-open").textContent =
      open === 0
        ? "Alle angenommen — jetzt live schalten"
        : open + " noch offen";
    if (isImageField(item.id)) {
      $("#hvw-review-old").textContent = item.live ? "hochgeladenes Bild" : "Platzhalter";
      $("#hvw-review-new").textContent = item.draft ? "hochgeladenes Bild" : "Platzhalter";
    } else {
      $("#hvw-review-old").textContent = clip(item.live, 140) || "—";
      $("#hvw-review-new").textContent = clip(item.draft, 140) || "—";
    }
    const otherPage = item.page && item.page !== currentPageName();
    $("#hvw-review-page").textContent = otherPage ? "andere Seite — «Zur Stelle» wechseln" : "";
    $("#hvw-btn-accept").disabled = otherPage || acceptedIds.has(item.id);
    $("#hvw-btn-edit").disabled = otherPage;
    $("#hvw-btn-revert").disabled = otherPage;
    if (!otherPage) highlightCurrent(item.id);
  }

  function resumeReview() {
    if (!isFreigabe()) return;
    const changes = allChanges();
    if (!changes.length) return;
    const wanted = sessionStorage.getItem(REVIEW_KEY);
    if (wanted) {
      const found = changes.findIndex((c) => c.id === wanted);
      if (found >= 0) {
        goToChange(found, { instant: true, stay: true });
        return;
      }
    }
    const onPage = changes.findIndex((c) => (c.page || "index.html") === currentPageName());
    if (onPage >= 0) goToChange(onPage, { instant: true, stay: true });
    else {
      reviewIndex = 0;
      updateReviewDock();
    }
  }

  function richActive() {
    return !!(activeEl && view === "draft" && activeEl.getAttribute("data-content-rich") === "1");
  }

  function captureRange() {
    const sel = window.getSelection();
    if (!sel || !sel.rangeCount || !activeEl) return;
    const range = sel.getRangeAt(0);
    if (!activeEl.contains(range.commonAncestorContainer)) return;
    savedRange = range.cloneRange();
  }

  function restoreRange() {
    if (!activeEl || !savedRange) return false;
    activeEl.focus();
    const sel = window.getSelection();
    if (!sel) return false;
    sel.removeAllRanges();
    sel.addRange(savedRange);
    return true;
  }

  function linkFromRange(range) {
    if (!range || !activeEl) return null;
    let node = range.commonAncestorContainer;
    if (node.nodeType === Node.TEXT_NODE) node = node.parentNode;
    while (node && node !== activeEl) {
      if (node.nodeName === "A") return node;
      node = node.parentNode;
    }
    return null;
  }

  function unwrapElement(el) {
    const parent = el.parentNode;
    if (!parent) return;
    while (el.firstChild) parent.insertBefore(el.firstChild, el);
    el.remove();
  }

  function normalizeFormatting(root) {
    if (!root) return;
    root.querySelectorAll("b").forEach((el) => {
      const next = document.createElement("strong");
      while (el.firstChild) next.appendChild(el.firstChild);
      el.replaceWith(next);
    });
    root.querySelectorAll("i").forEach((el) => {
      const next = document.createElement("em");
      while (el.firstChild) next.appendChild(el.firstChild);
      el.replaceWith(next);
    });
    [...root.querySelectorAll("span, font")].forEach((el) => {
      if (typeof window.hvwSanitizeRich !== "function") return;
      const holder = document.createElement("div");
      holder.innerHTML = window.hvwSanitizeRich(el.outerHTML);
      el.replaceWith(...holder.childNodes);
    });
  }

  function updateFormatState() {
    const on = richActive();
    [
      ["hvw-btn-b", "bold"],
      ["hvw-btn-i", "italic"],
      ["hvw-btn-u", "underline"],
    ].forEach(([id, cmd]) => {
      const btn = $("#" + id);
      if (!btn) return;
      btn.disabled = !on;
      let active = false;
      if (on) {
        try {
          active = document.queryCommandState(cmd);
        } catch (_err) {
          active = false;
        }
      }
      btn.classList.toggle("is-on", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
    const linkBtn = $("#hvw-btn-link");
    if (!linkBtn) return;
    linkBtn.disabled = !on;
    let inLink = false;
    if (on) {
      const sel = window.getSelection();
      if (sel && sel.rangeCount && activeEl.contains(sel.anchorNode)) {
        inLink = !!linkFromRange(sel.getRangeAt(0));
      }
    }
    linkBtn.classList.toggle("is-on", inLink);
    linkBtn.setAttribute("aria-pressed", inLink ? "true" : "false");
  }

  function openLinkDialog() {
    if (!richActive()) return;
    captureRange();
    const existing = savedRange ? linkFromRange(savedRange) : null;
    const input = $("#hvw-link-url");
    input.value = existing ? existing.getAttribute("href") || "" : "";
    linkDialogOpen = true;
    $("#hvw-link-pop").hidden = false;
    input.focus();
    input.select();
  }

  function closeLinkDialog() {
    linkDialogOpen = false;
    const pop = $("#hvw-link-pop");
    if (pop) pop.hidden = true;
  }

  function applyInlineLink(href) {
    if (!restoreRange()) {
      toast("Bitte zuerst den Text im Feld markieren.", true);
      return false;
    }
    const sel = window.getSelection();
    const range = sel && sel.rangeCount ? sel.getRangeAt(0) : null;
    if (!range || !activeEl.contains(range.commonAncestorContainer)) {
      toast("Bitte zuerst den Text im Feld markieren.", true);
      return false;
    }
    const existing = linkFromRange(range);
    if (existing) {
      existing.setAttribute("href", href);
      if (/^https?:\/\//i.test(href)) {
        existing.setAttribute("target", "_blank");
        existing.setAttribute("rel", "noopener noreferrer");
      } else {
        existing.removeAttribute("target");
        existing.removeAttribute("rel");
      }
    } else if (range.collapsed) {
      toast("Bitte den Text markieren, der zum Link werden soll.", true);
      return false;
    } else {
      const anchor = document.createElement("a");
      anchor.setAttribute("href", href);
      if (/^https?:\/\//i.test(href)) {
        anchor.setAttribute("target", "_blank");
        anchor.setAttribute("rel", "noopener noreferrer");
      }
      try {
        range.surroundContents(anchor);
      } catch (_err) {
        anchor.appendChild(range.extractContents());
        range.insertNode(anchor);
      }
    }
    if (typeof window.hvwSanitizeRich === "function") {
      activeEl.innerHTML = window.hvwSanitizeRich(activeEl.innerHTML);
    }
    return true;
  }

  function commitLink() {
    const href = window.hvwSafeRichHref ? window.hvwSafeRichHref($("#hvw-link-url").value) : "";
    if (!href) {
      toast("Adresse nicht erlaubt. Zum Beispiel agenda.html oder https://…", true);
      return;
    }
    if (!applyInlineLink(href)) return;
    closeLinkDialog();
    markDirty();
    updateCounter();
  }

  function removeLink() {
    if (!restoreRange()) {
      toast("Kein Link an dieser Stelle.", true);
      return;
    }
    const sel = window.getSelection();
    const range = sel && sel.rangeCount ? sel.getRangeAt(0) : savedRange;
    const existing = linkFromRange(range);
    if (!existing) {
      toast("Kein Link an dieser Stelle.", true);
      return;
    }
    unwrapElement(existing);
    closeLinkDialog();
    markDirty();
    updateCounter();
  }

  function exec(cmd) {
    if (!richActive()) return;
    activeEl.focus();
    document.execCommand(cmd, false, null);
    normalizeFormatting(activeEl);
    markDirty();
    updateCounter();
  }

  function onKey(e) {
    if (!activeEl) return;
    const meta = fieldMeta(activeEl.getAttribute("data-content"));
    if (e.key === "Enter" && !meta.multiline) {
      e.preventDefault();
      return;
    }
    if (e.key === "Enter" && meta.multiline && !e.shiftKey) {
      e.preventDefault();
      document.execCommand("insertLineBreak");
      markDirty();
    }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      saveDraft();
    }
    if ((e.metaKey || e.ctrlKey) && "biu".includes(e.key.toLowerCase())) {
      if (activeEl.getAttribute("data-content-rich") !== "1") e.preventDefault();
    }
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      if (activeEl.getAttribute("data-content-rich") === "1") {
        e.preventDefault();
        openLinkDialog();
      }
    }
  }

  function onPaste(e) {
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData("text/plain") || "";
    document.execCommand("insertText", false, text.replace(/\r/g, ""));
    markDirty();
  }

  async function saveDraft(quiet) {
    const fields = Object.assign({}, liveFields, draftFields, collectFields());
    try {
      const data = await api("save", { method: "POST", headers: csrfHeaders(), body: JSON.stringify({ fields }) });
      draftFields = fields;
      dirty = false;
      if (!quiet) toast("Entwurf gespeichert. Noch nicht öffentlich.");
      updateBar();
      return data;
    } catch (err) {
      toast(err.message, true);
      throw err;
    }
  }

  async function publish() {
    if (dirty) await saveDraft();
    if (!confirm("Entwurf jetzt öffentlich schalten?")) return;
    try {
      await api("publish", { method: "POST", headers: csrfHeaders(), body: "{}" });
      liveFields = Object.assign({}, draftFields);
      acceptedIds = new Set();
      persistAccepted();
      sessionStorage.removeItem(REVIEW_KEY);
      markChangedFields();
      toast("Freigegeben — die Änderungen sind live.");
      updateBar();
    } catch (err) {
      toast(err.message, true);
    }
  }

  async function discard() {
    if (!confirm("Entwurf verwerfen und die Live-Texte wiederherstellen?")) return;
    try {
      await api("discard", { method: "POST", headers: csrfHeaders(), body: "{}" });
      draftFields = Object.assign({}, liveFields);
      dirty = false;
      acceptedIds = new Set();
      persistAccepted();
      sessionStorage.removeItem(REVIEW_KEY);
      applyCurrent();
      toast("Entwurf verworfen.");
      updateBar();
    } catch (err) {
      toast(err.message, true);
    }
  }

  function showDiff() {
    const rows = allChanges().map((item) => {
      const oldText = isImageField(item.id)
        ? item.live
          ? "hochgeladenes Bild"
          : "Platzhalter"
        : strip(item.live);
      const newText = isImageField(item.id)
        ? item.draft
          ? "hochgeladenes Bild"
          : "Platzhalter"
        : strip(item.draft);
      return (
        "<article class=\"hvw-diff-item\" data-jump=\"" +
        escapeHtml(item.id) +
        "\"><h3>" +
        escapeHtml(item.label) +
        "</h3><p class=\"hvw-diff-old\">" +
        escapeHtml(oldText) +
        "</p><p class=\"hvw-diff-new\">" +
        escapeHtml(newText) +
        "</p><p><button type=\"button\" class=\"hvw-diff-jump\" data-jump-id=\"" +
        escapeHtml(item.id) +
        "\">Zur Stelle</button></p></article>"
      );
    });
    $("#hvw-diff-body").innerHTML = rows.length
      ? rows.join("")
      : "<p>Keine Unterschiede zum Live-Stand.</p>";
    $("#hvw-diff").hidden = false;
  }

  function strip(html) {
    const d = document.createElement("div");
    d.innerHTML = html;
    return d.textContent || "";
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function toast(msg, isError) {
    const el = $("#hvw-toast");
    el.textContent = msg;
    el.classList.toggle("is-error", !!isError);
    el.hidden = false;
    clearTimeout(toast.t);
    toast.t = setTimeout(() => {
      el.hidden = true;
    }, 4000);
  }

  function mountBar() {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <div id="hvw-editor-bar" role="region" aria-label="Redaktion">
        <div class="hvw-editor-bar__main">
          <span id="hvw-role-label"></span>
          <span id="hvw-status"></span>
          <span id="hvw-legend" hidden><span class="hvw-legend-swatch" aria-hidden="true"></span> Orange = geändert, noch nicht live</span>
          <span id="hvw-counter"></span>
        </div>
        <div class="hvw-editor-bar__tools" id="hvw-editor-tools">
          <button type="button" id="hvw-btn-b" title="Fett" aria-pressed="false"><strong>F</strong></button>
          <button type="button" id="hvw-btn-i" title="Kursiv" aria-pressed="false"><em>K</em></button>
          <button type="button" id="hvw-btn-u" title="Unterstrichen" aria-pressed="false"><u>U</u></button>
          <button type="button" id="hvw-btn-link" title="Link setzen" aria-pressed="false">Link</button>
          <div id="hvw-link-pop" hidden>
            <label for="hvw-link-url">Adresse</label>
            <input id="hvw-link-url" type="text" inputmode="url" autocomplete="off" spellcheck="false" placeholder="agenda.html oder https://…">
            <button type="button" id="hvw-link-apply">Setzen</button>
            <button type="button" id="hvw-link-remove">Entfernen</button>
            <button type="button" id="hvw-link-cancel">Abbrechen</button>
          </div>
        </div>
        <div class="hvw-editor-bar__actions">
          <button type="button" id="hvw-btn-live">Live ansehen</button>
          <button type="button" id="hvw-btn-draft">Entwurf ansehen</button>
          <button type="button" id="hvw-btn-diff">Änderungen</button>
          <button type="button" id="hvw-btn-save">Entwurf speichern</button>
          <button type="button" id="hvw-btn-discard">Verwerfen</button>
          <button type="button" id="hvw-btn-publish" hidden>Live schalten</button>
          <a id="hvw-btn-zugang" hidden href="redaktion/zugang.php">E-Mail-Zugang</a>
          <button type="button" id="hvw-btn-logout">Abmelden</button>
        </div>
      </div>
      <div id="hvw-review-dock" hidden>
        <div class="hvw-review-dock__nav">
          <button type="button" id="hvw-btn-prev" title="Vorherige Änderung">← Vorherige</button>
          <span id="hvw-review-pos">0 / 0</span>
          <button type="button" id="hvw-btn-next" title="Nächste Änderung">Nächste →</button>
        </div>
        <div class="hvw-review-dock__meta">
          <strong id="hvw-review-label"></strong>
          <span id="hvw-review-page"></span>
          <span id="hvw-review-open"></span>
        </div>
        <div class="hvw-review-dock__compare">
          <p><span>Live</span> <span id="hvw-review-old"></span></p>
          <p><span>Entwurf</span> <span id="hvw-review-new"></span></p>
        </div>
        <div class="hvw-review-dock__actions">
          <button type="button" id="hvw-btn-goto">Zur Stelle</button>
          <button type="button" id="hvw-btn-accept">Annehmen</button>
          <button type="button" id="hvw-btn-edit">Ändern</button>
          <button type="button" id="hvw-btn-revert">Rückgängig</button>
        </div>
      </div>
      <div id="hvw-toast" hidden></div>
      <div id="hvw-diff" hidden>
        <div class="hvw-diff-panel">
          <div class="hvw-diff-head">
            <h2>Änderungen im Entwurf</h2>
            <button type="button" id="hvw-diff-close">Schliessen</button>
          </div>
          <div id="hvw-diff-body"></div>
        </div>
      </div>`;
    document.body.appendChild(wrap);
    document.body.classList.add("hvw-has-editor");

    $("#hvw-editor-tools").addEventListener("mousedown", (e) => {
      if (e.target.closest("#hvw-link-pop")) return;
      e.preventDefault();
    });
    $("#hvw-btn-b").addEventListener("click", () => exec("bold"));
    $("#hvw-btn-i").addEventListener("click", () => exec("italic"));
    $("#hvw-btn-u").addEventListener("click", () => exec("underline"));
    $("#hvw-btn-link").addEventListener("click", () => openLinkDialog());
    $("#hvw-link-apply").addEventListener("click", () => commitLink());
    $("#hvw-link-remove").addEventListener("click", () => removeLink());
    $("#hvw-link-cancel").addEventListener("click", () => closeLinkDialog());
    $("#hvw-link-url").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        commitLink();
      } else if (e.key === "Escape") {
        e.preventDefault();
        closeLinkDialog();
      }
    });
    document.addEventListener("selectionchange", () => updateFormatState());
    $("#hvw-btn-save").addEventListener("click", () => saveDraft().catch(() => {}));
    $("#hvw-btn-publish").addEventListener("click", () => publish());
    $("#hvw-btn-discard").addEventListener("click", () => discard());
    $("#hvw-btn-live").addEventListener("click", () => {
      if (dirty && !confirm("Ungespeicherte Änderungen bleiben im Formular. Trotzdem Live ansehen?")) return;
      setView("live");
    });
    $("#hvw-btn-draft").addEventListener("click", () => setView("draft"));
    $("#hvw-btn-diff").addEventListener("click", showDiff);
    $("#hvw-diff-close").addEventListener("click", () => {
      $("#hvw-diff").hidden = true;
    });
    $("#hvw-diff-body").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-jump-id]");
      if (!btn) return;
      const id = btn.getAttribute("data-jump-id");
      $("#hvw-diff").hidden = true;
      const changes = allChanges();
      const idx = changes.findIndex((c) => c.id === id);
      if (idx >= 0) goToChange(idx, { focus: true });
    });
    $("#hvw-btn-prev").addEventListener("click", () => goRelative(-1));
    $("#hvw-btn-next").addEventListener("click", () => goRelative(1));
    $("#hvw-btn-goto").addEventListener("click", () => goToChange(reviewIndex, { focus: true }));
    $("#hvw-btn-accept").addEventListener("click", acceptCurrent);
    $("#hvw-btn-edit").addEventListener("click", editCurrent);
    $("#hvw-btn-revert").addEventListener("click", revertCurrent);
    document.addEventListener("keydown", (e) => {
      if (!isFreigabe() || view !== "draft") return;
      if (e.altKey && e.key === "ArrowRight") {
        e.preventDefault();
        goRelative(1);
      }
      if (e.altKey && e.key === "ArrowLeft") {
        e.preventDefault();
        goRelative(-1);
      }
    });
    $("#hvw-btn-logout").addEventListener("click", async () => {
      try {
        await api("logout", { method: "POST", headers: csrfHeaders(), body: "{}" });
      } catch (_e) {}
      location.reload();
    });
  }

  function ensureImageControls(el) {
    if (el.querySelector(".hvw-image-tools")) return;
    const tools = document.createElement("div");
    tools.className = "hvw-image-tools";
    tools.innerHTML =
      '<label class="hvw-image-upload">Bild hochladen<input type="file" accept="image/jpeg,image/png,image/webp" hidden></label>' +
      '<button type="button" class="hvw-image-clear">Platzhalter</button>';
    el.appendChild(tools);
  }

  function bindImageTools() {
    if (document.documentElement.dataset.hvwImageTools === "1") return;
    document.documentElement.dataset.hvwImageTools = "1";
    document.addEventListener("change", (e) => {
      const input = e.target;
      if (!input || input.type !== "file") return;
      if (!input.closest(".hvw-image-tools")) return;
      const el = input.closest("[data-content-image]");
      const file = input.files && input.files[0];
      input.value = "";
      if (el && file) uploadImage(el, file);
    });
    document.addEventListener("click", (e) => {
      const clear = e.target.closest && e.target.closest(".hvw-image-clear");
      if (!clear) return;
      const el = clear.closest("[data-content-image]");
      if (!el || view !== "draft") return;
      e.preventDefault();
      e.stopPropagation();
      const id = el.getAttribute("data-content-image");
      const fallback = el.getAttribute("data-content-image-fallback") || "";
      const img = el.querySelector("img");
      if (img) img.setAttribute("src", fallback);
      el.classList.remove("has-photo");
      draftFields[id] = "";
      acceptedIds.delete(id);
      persistAccepted();
      markDirty();
    });
  }

  async function uploadImage(el, file) {
    const id = el.getAttribute("data-content-image");
    if (!id) return;
    if (!/image\/(jpeg|png|webp)/i.test(file.type)) {
      toast("Bitte ein JPG-, PNG- oder WebP-Bild wählen.", true);
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      toast("Das Bild darf höchstens 8 MB haben.", true);
      return;
    }
    const body = new FormData();
    body.append("field", id);
    body.append("file", file);
    try {
      const data = await api("upload-image", {
        method: "POST",
        headers: { "X-CSRF-Token": session && session.csrf ? session.csrf : "" },
        body,
      });
      draftFields = Object.assign({}, draftFields, { [id]: data.url });
      window.hvwApplyContent({ [id]: data.url });
      acceptedIds.delete(id);
      persistAccepted();
      dirty = false;
      markChangedFields();
      updateBar();
      toast("Bild im Entwurf gespeichert. Noch nicht öffentlich.");
    } catch (err) {
      toast(err.message, true);
    }
  }

  function bindFields() {
    document.querySelectorAll("[data-content]").forEach((el) => {
      el.addEventListener("focus", () => {
        activeEl = el;
        updateCounter();
      });
      el.addEventListener("input", () => {
        if (el.getAttribute("data-content-rich") === "1") normalizeFormatting(el);
        if (el.hasAttribute("data-content-href") && window.hvwSanitizeUrl) {
          const href = window.hvwSanitizeUrl(el.textContent || "");
          if (href) el.setAttribute("href", href);
        }
        const id = el.getAttribute("data-content");
        if (acceptedIds.has(id)) {
          acceptedIds.delete(id);
          persistAccepted();
        }
        markDirty();
        updateCounter();
      });
      el.addEventListener("keydown", onKey);
      el.addEventListener("paste", onPaste);
      el.addEventListener("blur", () => {
        if (linkDialogOpen) return;
        if (el.getAttribute("data-content-rich") === "1") {
          el.innerHTML = window.hvwSanitizeRich(el.innerHTML);
        }
        markChangedFields();
        const fieldId = el.getAttribute("data-content") || "";
        if (fieldId.endsWith(".kicker") && typeof window.hvwSortRueckblick === "function") {
          window.hvwSortRueckblick();
        }
      });
      el.addEventListener("click", (e) => {
        if (view !== "draft") return;
        e.stopPropagation();
      });
    });
    bindImageTools();
    document.querySelectorAll("[data-content-image]").forEach((el) => {
      ensureImageControls(el);
    });
    document.addEventListener(
      "click",
      (e) => {
        if (view !== "draft") return;
        const field = e.target.closest && e.target.closest("[data-content]");
        if (!field) return;
        const link = e.target.closest("a");
        if (link && (link === field || field.contains(link))) e.preventDefault();
      },
      true
    );
  }

  async function boot() {
    try {
      const meRes = await fetch(API + "?action=me", { credentials: "same-origin", cache: "no-store" });
      const me = await meRes.json();
      if (!me.user) return;
      session = me.user;
      const sch = await (await fetch(API + "?action=schema", { credentials: "same-origin" })).json();
      schema = sch.fields || {};
      const live = await (await fetch("data/content-live.json", { cache: "no-cache" })).json();
      liveFields = live.fields || {};
      const draftRes = await fetch(API + "?action=content&source=draft", {
        credentials: "same-origin",
        cache: "no-store",
      });
      const draft = await draftRes.json();
      draftFields = draft.fields || Object.assign({}, liveFields);
      mountBar();
      bindFields();
      setView("draft");
      resumeReview();
    } catch (err) {
      console.warn("Redaktion nicht gestartet:", err);
    }
  }

  boot();
})();
