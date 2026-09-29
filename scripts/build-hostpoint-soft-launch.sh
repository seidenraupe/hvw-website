#!/usr/bin/env bash
# Baut ein schlankes Upload-Paket für Hostpoint (nur Programm-Soft-Launch).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/deploy/hostpoint-soft-launch"

rm -rf "${OUT}"
mkdir -p "${OUT}/css" "${OUT}/js" "${OUT}/images" "${OUT}/data"

# Stamm-URL: Weiterleitung zur bestehenden Vereinswebsite (nicht zum Programm)
cat > "${OUT}/index.html" <<'HTML'
<!DOCTYPE html>
<html lang="de-CH">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Historischer Verein Winterthur</title>
  <link rel="canonical" href="https://www.historischer-verein-winterthur.ch/">
  <meta name="robots" content="noindex,follow">
  <meta http-equiv="refresh" content="0; url=https://www.historischer-verein-winterthur.ch/">
  <script>location.replace('https://www.historischer-verein-winterthur.ch/' + location.search + location.hash);</script>
</head>
<body>
  <p><a href="https://www.historischer-verein-winterthur.ch/">Weiter zur Website des Historischen Vereins Winterthur</a></p>
</body>
</html>
HTML

cp "${ROOT}/.htaccess" "${OUT}/.htaccess"
cp "${ROOT}/robots.txt" "${OUT}/robots.txt"
cp "${ROOT}/impressum.html" "${OUT}/impressum.html"
cp "${ROOT}/datenschutz.html" "${OUT}/datenschutz.html"
if [[ ! -f "${ROOT}/Statuten.pdf" ]]; then
  echo "Statuten.pdf fehlt — Deploy auf Hostpoint wäre unvollständig." >&2
  exit 1
fi
cp "${ROOT}/Statuten.pdf" "${OUT}/Statuten.pdf"
mkdir -p "${OUT}/coucou"
cp "${ROOT}/coucou/index.html" "${OUT}/coucou/index.html"
cp "${ROOT}/coucou/.htaccess" "${OUT}/coucou/.htaccess"
mkdir -p "${OUT}/mus"
cp "${ROOT}/mus/index.html" "${OUT}/mus/index.html"
cp "${ROOT}/mus/.htaccess" "${OUT}/mus/.htaccess"
cp "${ROOT}/css/site.css" "${OUT}/css/site.css"
cp "${ROOT}/js/tailwind-config.js" "${OUT}/js/tailwind-config.js"
cp "${ROOT}/js/analytics.js" "${OUT}/js/analytics.js"
cp "${ROOT}/js/main.js" "${OUT}/js/main.js"
cp "${ROOT}/js/coucou-preview.js" "${OUT}/js/coucou-preview.js"
cp "${ROOT}/data/analytics.json" "${OUT}/data/analytics.json"
cp "${ROOT}/images/hvw-logo.png" "${OUT}/images/hvw-logo.png"
for f in favicon.ico favicon-32.png favicon-192.png apple-touch-icon.png; do
  if [[ -f "${ROOT}/images/${f}" ]]; then
    cp "${ROOT}/images/${f}" "${OUT}/images/${f}"
  fi
done

cat > "${OUT}/UPLOAD.txt" <<'TXT'
Hostpoint Soft-Launch — Upload-Anleitung
========================================

Stamm-URL:  https://www.hvwinterthur.ch/  →  https://www.historischer-verein-winterthur.ch/
Programmseite und Programm-PDF: entfernt (HTTP 410 unter /programm).

1. Im Hostpoint Control Panel den Document Root von www.hvwinterthur.ch öffnen
   (FTP/SFTP oder Dateimanager).
2. Den gesamten Inhalt DIESES Ordners in den Document Root hochladen
   (index.html, .htaccess, robots.txt, css/, js/, data/, images/).
3. Prüfen:
   - https://www.hvwinterthur.ch/         → Weiterleitung zur Vereinswebsite
   - https://www.hvwinterthur.ch/programm → 410, Seite ist entfernt
   - https://www.hvwinterthur.ch/coucou → Coucou-JSON-Kontrolle
   - https://www.hvwinterthur.ch/mus → MuS-JSON-Kontrolle
   - https://www.hvwinterthur.ch/impressum.html
   - https://www.hvwinterthur.ch/datenschutz.html
   - https://www.hvwinterthur.ch/Statuten.pdf
4. Eventfrog: Domain www.hvwinterthur.ch für das Embed freischalten.

Hinweis: Die übrige Prototyp-Website gehört NICHT in diesen Upload.
Bevorzugt: GitHub Action «Deploy via rsync» (siehe README).
TXT

echo "Hostpoint-Paket erstellt: ${OUT}"
find "${OUT}" -type f | sort
