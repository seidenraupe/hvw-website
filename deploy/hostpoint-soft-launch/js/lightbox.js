/**
 * Vollbild für Kartenbilder (Sammlung, Agenda-Rückblick).
 * Nur Live, nicht im Redaktionsmodus. Platzhalter werden nicht geöffnet.
 */
(function () {
  const PLACEHOLDER = /placeholder/i;

  function isEditing() {
    return document.body.classList.contains("hvw-editing");
  }

  function ensureLightbox() {
    let root = document.getElementById("hvw-lightbox");
    if (root) return root;
    root = document.createElement("div");
    root.id = "hvw-lightbox";
    root.className = "hvw-lightbox";
    root.setAttribute("hidden", "");
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", "Bild in Grossansicht");
    root.innerHTML =
      '<button type="button" class="hvw-lightbox__backdrop" aria-label="Schliessen"></button>' +
      '<figure class="hvw-lightbox__figure">' +
      '<button type="button" class="hvw-lightbox__close">Schliessen</button>' +
      '<img alt="">' +
      "</figure>";
    document.body.appendChild(root);
    root.addEventListener("click", (e) => {
      if (e.target === root || e.target.classList.contains("hvw-lightbox__backdrop") || e.target.classList.contains("hvw-lightbox__close")) {
        closeLightbox();
      }
    });
    return root;
  }

  function openLightbox(src, alt) {
    const root = ensureLightbox();
    const img = root.querySelector("img");
    img.src = src;
    img.alt = alt || "";
    root.removeAttribute("hidden");
    document.body.classList.add("hvw-lightbox-open");
    const closeBtn = root.querySelector(".hvw-lightbox__close");
    if (closeBtn) closeBtn.focus();
  }

  function closeLightbox() {
    const root = document.getElementById("hvw-lightbox");
    if (!root || root.hasAttribute("hidden")) return;
    root.setAttribute("hidden", "");
    document.body.classList.remove("hvw-lightbox-open");
    const img = root.querySelector("img");
    if (img) img.removeAttribute("src");
  }

  document.addEventListener("click", (e) => {
    if (isEditing()) return;
    if (e.target.closest(".hvw-image-tools")) return;
    const media = e.target.closest("[data-lightbox]");
    if (!media) return;
    const img = media.querySelector("img");
    const src = img ? img.getAttribute("src") || "" : "";
    if (!src || PLACEHOLDER.test(src)) return;
    e.preventDefault();
    openLightbox(src, img.getAttribute("alt") || "");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeLightbox();
  });
})();
