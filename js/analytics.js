/**
 * Google Analytics 4 (gtag.js) — optionaler Loader für Seiten ohne Inline-Tag.
 *
 * Die Website-Seiten enthalten den Google-Tag inline im <head>.
 * Diese Datei überspringt das erneute Laden, wenn gtag bereits
 * konfiguriert ist, und kann auf weiteren Seiten data/analytics.json nutzen.
 */
(function initAnalytics() {
  const CONFIG_URL = '/data/analytics.json';

  function isValidMeasurementId(id) {
    return typeof id === 'string' && /^G-[A-Z0-9]+$/i.test(id.trim());
  }

  function alreadyConfigured() {
    if (typeof window.gtag === 'function' && Array.isArray(window.dataLayer)) {
      return window.dataLayer.some(
        (entry) =>
          Array.isArray(entry) &&
          entry[0] === 'config' &&
          typeof entry[1] === 'string' &&
          entry[1].indexOf('G-') === 0
      );
    }
    return false;
  }

  function loadGtag(measurementId) {
    const id = measurementId.trim();
    window.dataLayer = window.dataLayer || [];
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };

    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
    document.head.appendChild(script);

    window.gtag('js', new Date());
    window.gtag('config', id);
  }

  if (alreadyConfigured()) {
    return;
  }

  fetch(CONFIG_URL, { cache: 'no-cache' })
    .then((res) => (res.ok ? res.json() : null))
    .then((config) => {
      if (!config || !isValidMeasurementId(config.measurementId)) {
        return;
      }
      if (alreadyConfigured()) {
        return;
      }
      loadGtag(config.measurementId);
    })
    .catch(() => {
      /* Analytics optional */
    });
})();
