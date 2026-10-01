/**
 * Setzt den PDF-Dateinamen auf «Programm HVW MM.JJJJ bis MM.JJJJ.pdf».
 */
(function () {
  document.querySelectorAll("a[data-programm-download]").forEach(function (link) {
    const href = link.getAttribute("href") || "";
    const jsonUrl = href.replace(/\.pdf(\?.*)?$/i, ".json");
    if (!jsonUrl || jsonUrl === href) return;
    fetch(jsonUrl, { cache: "no-cache" })
      .then(function (res) {
        return res.ok ? res.json() : null;
      })
      .then(function (meta) {
        if (meta && typeof meta.downloadName === "string" && meta.downloadName) {
          link.setAttribute("download", meta.downloadName);
        }
      })
      .catch(function () {
        /* Dateiname bleibt der Fallback im HTML */
      });
  });
})();
