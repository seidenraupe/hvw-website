/**
 * Coucou-Export prüfen: aktuelles /coucou_export.json tabellarisch,
 * Eventbilder mit Overlay (Dateiformat + Pixelgrösse).
 */
(function () {
  function resolveJsonUrl() {
    if (window.HVW_EXPORT_JSON) return String(window.HVW_EXPORT_JSON);
    const fromBody = document.body && document.body.getAttribute("data-export-json");
    if (fromBody) return fromBody;
    const path = (location.pathname || "").replace(/\/+$/, "") || "/";
    if (path === "/mus" || path.endsWith("/mus")) return "/mus_export.json";
    return "/coucou_export.json";
  }
  const HIDDEN_IN_EXTRA = new Set([
    "image",
    "title",
    "date",
    "time_start",
    "time_end",
    "location_name",
    "location_street",
    "location_zip",
    "location_city",
    "description",
    "description_long",
    "category",
  ]);

  const $ = (id) => document.getElementById(id);

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function clip(text, max) {
    const value = String(text || "").replace(/\s+/g, " ").trim();
    if (value.length <= max) return value;
    return value.slice(0, max - 1) + "…";
  }

  function formatFromUrl(src) {
    if (!src) return "";
    try {
      const path = new URL(src, location.href).pathname;
      const match = path.match(/\.([a-z0-9]+)$/i);
      if (!match) return "";
      const ext = match[1].toLowerCase();
      if (ext === "jpeg") return "JPG";
      if (ext === "tif" || ext === "tiff") return "TIFF";
      return ext.toUpperCase();
    } catch (_err) {
      return "";
    }
  }

  function loadImageSize(src) {
    return new Promise((resolve) => {
      if (!src) {
        resolve({ width: 0, height: 0, ok: false });
        return;
      }
      const img = new Image();
      img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight, ok: true });
      img.onerror = () => resolve({ width: 0, height: 0, ok: false });
      img.src = src;
    });
  }

  function overlayInfoText(format, size) {
    const parts = [];
    parts.push(format || "Format unbekannt");
    if (size && size.ok) {
      parts.push(size.width + " × " + size.height + " px");
    } else if (size && !size.ok) {
      parts.push("Pixelgrösse nicht lesbar");
    } else {
      parts.push("Pixelgrösse wird gelesen…");
    }
    return parts.join(" · ");
  }

  function extraFields(event) {
    const extras = [];
    Object.keys(event).forEach((key) => {
      if (HIDDEN_IN_EXTRA.has(key)) return;
      const value = event[key];
      if (value == null || value === "") return;
      extras.push(
        "<p><span>" +
          escapeHtml(key) +
          "</span> " +
          escapeHtml(clip(typeof value === "string" ? value : JSON.stringify(value), 180)) +
          "</p>"
      );
    });
    return extras.length ? extras.join("") : "<p class=\"text-hvw-mute\">—</p>";
  }

  function formatCategory(value) {
    if (value == null || value === "") return "—";
    if (Array.isArray(value)) {
      const parts = value.filter((item) => item != null && item !== "");
      return parts.length ? parts.join(", ") : "—";
    }
    return String(value);
  }

  function locationCell(event) {
    const parts = [event.location_name, event.location_street, [event.location_zip, event.location_city].filter(Boolean).join(" ")]
      .map((part) => String(part || "").trim())
      .filter(Boolean);
    return parts.length ? escapeHtml(parts.join(", ")) : "—";
  }

  function renderRows(events) {
    const body = $("coucou-rows");
    if (!events.length) {
      body.innerHTML = '<tr><td colspan="9" class="p-6 text-hvw-mute">Keine Events im Export.</td></tr>';
      return;
    }
    body.innerHTML = events
      .map((event) => {
        const image = String(event.image || "");
        const format = formatFromUrl(image);
        const title = event.title || "Ohne Titel";
        const thumb = image
          ? '<button type="button" class="coucou-thumb" data-coucou-image="' +
            escapeHtml(image) +
            '" data-coucou-title="' +
            escapeHtml(title) +
            '" aria-label="Eventbild vergrössern: ' +
            escapeHtml(title) +
            '"><img src="' +
            escapeHtml(image) +
            '" alt="" width="240" height="180" loading="lazy"><span class="coucou-thumb__hint">Format &amp; Pixel</span></button>'
          : '<span class="text-hvw-mute">kein Bild</span>';
        const time = [event.time_start, event.time_end].filter(Boolean).join("–") || "—";
        const date = event.date_end && event.date_end !== event.date
          ? escapeHtml(event.date) + " – " + escapeHtml(event.date_end)
          : escapeHtml(event.date || "—");
        return (
          "<tr>" +
          "<td>" +
          thumb +
          (format ? '<p class="coucou-ext">' + escapeHtml(format) + "</p>" : "") +
          "</td>" +
          "<td><strong>" +
          escapeHtml(title) +
          "</strong></td>" +
          "<td>" +
          date +
          "</td>" +
          "<td>" +
          escapeHtml(time) +
          "</td>" +
          "<td>" +
          locationCell(event) +
          "</td>" +
          "<td>" +
          escapeHtml(formatCategory(event.category)) +
          "</td>" +
          "<td>" +
          escapeHtml(clip(event.description, 140) || "—") +
          "</td>" +
          "<td>" +
          escapeHtml(clip(event.description_long, 160) || "—") +
          "</td>" +
          "<td class=\"coucou-extra\">" +
          extraFields(event) +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
  }

  function bindOverlay() {
    const overlay = $("coucou-overlay");
    const imageEl = $("coucou-overlay-image");
    const infoEl = $("coucou-overlay-info");
    const titleEl = $("coucou-overlay-title");
    const urlEl = $("coucou-overlay-url");
    let lastFocus = null;

    function close() {
      overlay.hidden = true;
      imageEl.removeAttribute("src");
      document.body.classList.remove("coucou-overlay-open");
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }

    async function open(src, title, trigger) {
      lastFocus = trigger || document.activeElement;
      overlay.hidden = false;
      document.body.classList.add("coucou-overlay-open");
      titleEl.textContent = title || "";
      urlEl.textContent = src;
      imageEl.alt = title || "Eventbild";
      imageEl.src = src;
      const format = formatFromUrl(src);
      infoEl.textContent = overlayInfoText(format, null);
      const size = await loadImageSize(src);
      if (overlay.hidden) return;
      infoEl.textContent = overlayInfoText(format, size);
      overlay.querySelector(".coucou-overlay__close").focus();
    }

    document.addEventListener("click", (event) => {
      const thumb = event.target.closest("[data-coucou-image]");
      if (thumb) {
        event.preventDefault();
        open(thumb.getAttribute("data-coucou-image"), thumb.getAttribute("data-coucou-title"), thumb);
        return;
      }
      if (event.target.closest("[data-coucou-close]")) {
        close();
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !overlay.hidden) {
        event.preventDefault();
        close();
      }
    });
  }

  function formatStamp(headerValue) {
    if (!headerValue) return "";
    const date = new Date(headerValue);
    if (Number.isNaN(date.getTime())) return headerValue;
    return date.toLocaleString("de-CH", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Europe/Zurich",
    });
  }

  async function boot() {
    const JSON_URL = resolveJsonUrl();
    const meta = $("coucou-meta");
    const status = $("coucou-status");
    bindOverlay();
    try {
      const res = await fetch(JSON_URL, { cache: "no-store" });
      if (!res.ok) {
        throw new Error("HTTP " + res.status);
      }
      const data = await res.json();
      const events = Array.isArray(data) ? data : [];
      const modified = formatStamp(res.headers.get("Last-Modified"));
      let loadedPath = JSON_URL;
      try {
        loadedPath = new URL(res.url || JSON_URL, location.href).pathname;
      } catch (_err) {}
      meta.innerHTML =
        "Geladen: <code>" +
        escapeHtml(loadedPath) +
        "</code> · <strong>" +
        events.length +
        " Events</strong>" +
        (modified ? " · Stand Hostpoint: " + escapeHtml(modified) : "") +
        ' · <a href="' +
        escapeHtml(JSON_URL) +
        '" class="underline underline-offset-2">JSON öffnen</a>';
      status.textContent = "Bild anklicken: Overlay mit Dateiformat und Pixelgrösse.";
      renderRows(events);
    } catch (err) {
      meta.textContent = "Export konnte nicht geladen werden.";
      status.textContent =
        "Die Datei " +
        JSON_URL +
        " fehlt lokal oder ist nicht erreichbar. Auf Hostpoint schreibt sie der nächtliche Cron.";
      $("coucou-rows").innerHTML =
        '<tr><td colspan="9" class="p-6 text-hvw-mute">' +
        escapeHtml(err.message || "unbekannter Fehler") +
        "</td></tr>";
    }
  }

  window.hvwCoucouFormatFromUrl = formatFromUrl;
  window.hvwCoucouOverlayInfo = overlayInfoText;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
