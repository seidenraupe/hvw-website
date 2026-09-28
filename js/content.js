/**
 * Texte aus data/content-live.json in [data-content]-Felder schreiben.
 * Wenn jemand angemeldet ist, wird der Redaktions-Editor nachgeladen.
 */
(function () {
  const LIVE_URL = "data/content-live.json";
  const API = "redaktion/api.php";

  function safeRichHref(raw) {
    let value = String(raw || "").replace(/[\u0000-\u001F\u007F]/g, "").replace(/\s+/g, "");
    if (!value || value.length > 500) return "";
    if (/^(javascript|data|vbscript):/i.test(value) || value.indexOf("\\") >= 0 || value.slice(0, 2) === "//") {
      return "";
    }
    if (value.charAt(0) === "#") {
      return /^#[A-Za-z0-9_-]+$/.test(value) ? value : "";
    }
    if (/^[a-z][a-z0-9+.-]*:/i.test(value)) {
      try {
        const url = new URL(value);
        if ((url.protocol !== "http:" && url.protocol !== "https:") || url.username || url.password) return "";
        if (!url.hostname || url.hostname.indexOf(".") < 0) return "";
        return url.href;
      } catch (_err) {
        return "";
      }
    }
    if (value.indexOf("..") >= 0 || value.indexOf(":") >= 0) return "";
    if (!/^(?:\.\/|\/)?[A-Za-z0-9][A-Za-z0-9._~/-]*(?:\?[A-Za-z0-9._~%=&+-]*)?(?:#[A-Za-z0-9_-]+)?$/.test(value)) {
      return "";
    }
    return value;
  }

  function unwrapNode(el) {
    const parent = el.parentNode;
    if (!parent) return;
    while (el.firstChild) parent.insertBefore(el.firstChild, el);
    el.remove();
  }

  function renameTag(el, tag) {
    const next = document.createElement(tag);
    while (el.firstChild) next.appendChild(el.firstChild);
    el.replaceWith(next);
    return next;
  }

  function sanitizeRich(html) {
    const allowed = { STRONG: true, EM: true, U: true, BR: true, A: true };
    const drop = { SCRIPT: true, STYLE: true, IFRAME: true, OBJECT: true, EMBED: true };
    const wrap = document.createElement("div");
    wrap.innerHTML = String(html || "");
    const walk = (node) => {
      let child = node.firstChild;
      while (child) {
        const next = child.nextSibling;
        if (child.nodeType === Node.TEXT_NODE) {
          child = next;
          continue;
        }
        if (child.nodeType !== Node.ELEMENT_NODE) {
          child.remove();
          child = next;
          continue;
        }
        if (drop[child.tagName]) {
          child.remove();
          child = next;
          continue;
        }
        let el = child;
        if (el.tagName === "B") el = renameTag(el, "strong");
        else if (el.tagName === "I") el = renameTag(el, "em");
        if (el.tagName === "SPAN" || el.tagName === "FONT") {
          const style = (el.getAttribute("style") || "").toLowerCase();
          const wraps = [];
          if (/text-decoration(?:-line)?\s*:[^;]*underline/.test(style)) wraps.push("u");
          if (/font-style\s*:\s*italic/.test(style)) wraps.push("em");
          if (/font-weight\s*:\s*(bold|bolder|[6-9]00)/.test(style)) wraps.push("strong");
          if (wraps.length) {
            const inner = document.createElement(wraps[0]);
            while (el.firstChild) inner.appendChild(el.firstChild);
            let current = inner;
            wraps.slice(1).forEach((tag) => {
              const outer = document.createElement(tag);
              outer.appendChild(current);
              current = outer;
            });
            el.appendChild(current);
          }
          const marker = document.createTextNode("");
          el.parentNode.insertBefore(marker, el);
          unwrapNode(el);
          child = marker.nextSibling;
          marker.remove();
          continue;
        }
        if (!allowed[el.tagName]) {
          walk(el);
          const marker = document.createTextNode("");
          el.parentNode.insertBefore(marker, el);
          unwrapNode(el);
          child = marker.nextSibling;
          marker.remove();
          continue;
        }
        if (el.tagName === "A") {
          const href = safeRichHref(el.getAttribute("href"));
          const nested = el.parentElement && el.parentElement.closest("a");
          while (el.attributes.length) el.removeAttribute(el.attributes[0].name);
          if (!href || nested) {
            walk(el);
            const marker = document.createTextNode("");
            el.parentNode.insertBefore(marker, el);
            unwrapNode(el);
            child = marker.nextSibling;
            marker.remove();
            continue;
          }
          el.setAttribute("href", href);
          if (/^https?:\/\//i.test(href) || /\.pdf(?:$|[?#])/i.test(href)) {
            el.setAttribute("target", "_blank");
            el.setAttribute("rel", "noopener noreferrer");
          }
          walk(el);
          child = el.nextSibling;
          continue;
        }
        while (el.attributes.length) el.removeAttribute(el.attributes[0].name);
        if (el.tagName !== "BR") walk(el);
        child = el.nextSibling;
      }
    };
    walk(wrap);
    let cleaned = wrap.innerHTML;
    cleaned = cleaned.replace(/^(?:\s|<br\s*\/?>)+/i, "");
    cleaned = cleaned.replace(/(?:\s|<br\s*\/?>)+$/i, "");
    return cleaned.trim();
  }

  function canonicalRich(html) {
    return sanitizeRich(html).replace(/\s+/g, " ").trim();
  }

  function applyImageFields(fields) {
    if (!fields) return;
    document.querySelectorAll("[data-content-image]").forEach((el) => {
      const id = el.getAttribute("data-content-image");
      if (!id || !Object.prototype.hasOwnProperty.call(fields, id)) return;
      const fallback = el.getAttribute("data-content-image-fallback") || "";
      const raw = String(fields[id] || "").trim();
      const src = raw || fallback;
      const img = el.querySelector("img");
      if (img && src) {
        if (img.getAttribute("src") !== src) img.setAttribute("src", src);
      }
      el.classList.toggle("has-photo", Boolean(raw));
    });
  }

  function sanitizeUrl(value) {
    const text = String(value || "").replace(/\s+/g, "").trim();
    if (!/^https:\/\//i.test(text)) return "";
    try {
      const url = new URL(text);
      if (url.protocol !== "https:" || url.username || url.password) return "";
      if (!url.hostname || url.hostname.indexOf(".") < 0) return "";
      return url.origin + url.pathname + url.search;
    } catch (_err) {
      return "";
    }
  }

  function applyFields(fields) {
    if (!fields) return;
    document.querySelectorAll("[data-content]").forEach((el) => {
      const id = el.getAttribute("data-content");
      if (!Object.prototype.hasOwnProperty.call(fields, id)) return;
      const rich = el.getAttribute("data-content-rich") === "1";
      const value = fields[id];
      if (rich) el.innerHTML = sanitizeRich(value);
      else el.textContent = String(value || "").replace(/\s+/g, " ").trim();
      if (el.hasAttribute("data-content-href")) {
        const href = sanitizeUrl(el.textContent);
        if (href) el.setAttribute("href", href);
      }
    });
    applyImageFields(fields);
    if (typeof window.hvwSortRueckblick === "function") window.hvwSortRueckblick();
  }

  async function loadLive() {
    try {
      const res = await fetch(LIVE_URL, { cache: "no-cache" });
      if (!res.ok) return;
      const data = await res.json();
      applyFields(data.fields || {});
    } catch (err) {
      console.warn("Live-Texte nicht geladen:", err);
    }
  }

  async function maybeEditor() {
    try {
      const res = await fetch(API + "?action=me", { credentials: "same-origin", cache: "no-store" });
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.user) {
        loadEditor();
        return;
      }
      showLoginInvite();
    } catch (_err) {
      /* PHP-Redaktion nicht erreichbar (z. B. reiner Datei-Server) */
    }
  }

  const EDITOR_ASSET_V = "20260928-freigabe";

  function loadEditor() {
    if (!document.querySelector('link[href*="css/content-editor.css"]')) {
      const css = document.createElement("link");
      css.rel = "stylesheet";
      css.href = "css/content-editor.css?v=" + EDITOR_ASSET_V;
      document.head.appendChild(css);
    }
    if (!document.querySelector('script[src*="js/content-editor.js"]')) {
      const script = document.createElement("script");
      script.src = "js/content-editor.js?v=" + EDITOR_ASSET_V;
      document.body.appendChild(script);
    }
  }

  function showLoginInvite() {
    if (document.getElementById("hvw-login-invite")) return;
    const page = (location.pathname.split("/").pop() || "index.html");
    const next = "../" + (page.includes(".") ? page : "index.html");
    const bar = document.createElement("div");
    bar.id = "hvw-login-invite";
    bar.setAttribute("role", "region");
    bar.setAttribute("aria-label", "Änderungsmodus");
    bar.style.background = "#146b54";
    bar.style.color = "#fff";
    bar.style.borderBottom = "3px solid #c9a227";
    bar.innerHTML =
      "<p><strong>Änderungsmodus</strong> — Texte bearbeiten oder freigeben?</p>" +
      "<a href=\"redaktion/index.php?next=" +
      encodeURIComponent(next) +
      "\">Anmelden</a>";
    document.body.appendChild(bar);
    document.body.classList.add("hvw-has-login-invite");
  }

  window.hvwApplyContent = applyFields;
  window.hvwSanitizeRich = sanitizeRich;
  window.hvwCanonicalRich = canonicalRich;
  window.hvwSafeRichHref = safeRichHref;
  window.hvwSanitizeUrl = sanitizeUrl;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      loadLive().then(maybeEditor);
    });
  } else {
    loadLive().then(maybeEditor);
  }
})();
