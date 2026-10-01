#!/usr/bin/env bash
# Baut die öffentliche Website für Hostpoint (Document Root, ohne /edit/-Zugang).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/deploy/hostpoint-soft-launch"

rm -rf "${OUT}"
mkdir -p "${OUT}"

copy_dir() {
  local src="$1"
  local dest="$2"
  mkdir -p "${dest}"
  cp -a "${src}/." "${dest}/"
}

for page in index.html agenda.html museen.html lindengut.html moersburg.html ueber-uns.html mitmachen.html \
            partner.html sammlung.html zitate.html \
            impressum.html datenschutz.html; do
  cp "${ROOT}/${page}" "${OUT}/${page}"
done

copy_dir "${ROOT}/css" "${OUT}/css"
copy_dir "${ROOT}/fonts" "${OUT}/fonts"
copy_dir "${ROOT}/js" "${OUT}/js"
copy_dir "${ROOT}/images" "${OUT}/images"
mkdir -p "${OUT}/data"
cp "${ROOT}/data/analytics.json" "${OUT}/data/analytics.json"
cp "${ROOT}/data/content-schema.json" "${OUT}/data/content-schema.json"
cp "${ROOT}/data/content-live.json" "${OUT}/data/content-live.seed.json"
mkdir -p "${OUT}/data/uploads"
cp "${ROOT}/data/uploads/.htaccess" "${OUT}/data/uploads/.htaccess"

PUBLIC_PDFS=(
  Statuten.pdf
  Sammlungskonzept.pdf
  Jahresbericht-2025.pdf
  JB_2024_final.pdf
  Programm.pdf
  historische-privat-fuehrungen.pdf
  szenische-fuehrung-berta.pdf
)
mkdir -p "${OUT}/dokumente"
for pdf in "${PUBLIC_PDFS[@]}"; do
  if [[ ! -f "${ROOT}/dokumente/${pdf}" ]]; then
    echo "dokumente/${pdf} fehlt — öffentlicher Deploy wäre unvollständig." >&2
    exit 1
  fi
  cp "${ROOT}/dokumente/${pdf}" "${OUT}/dokumente/${pdf}"
done

copy_dir "${ROOT}/programm" "${OUT}/programm"
copy_dir "${ROOT}/coucou" "${OUT}/coucou"
copy_dir "${ROOT}/mus" "${OUT}/mus"

cp "${ROOT}/.htaccess" "${OUT}/.htaccess"
cp "${ROOT}/robots.txt" "${OUT}/robots.txt"

cat > "${OUT}/UPLOAD.txt" <<'TXT'
Hostpoint — öffentliche Website (Document Root)
===============================================

Stamm-URL:  https://www.hvwinterthur.ch/
Bearbeitung: https://www.hvwinterthur.ch/edit/ (E-Mail-Code, nicht öffentlich)

Bevorzugt: GitHub Action «Deploy via rsync» (siehe README).
TXT

echo "Hostpoint-Stamm-Website erstellt: ${OUT}"
find "${OUT}" -type f | wc -l
