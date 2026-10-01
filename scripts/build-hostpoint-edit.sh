#!/usr/bin/env bash
# Baut den passwortgeschützten Bearbeitungszugang für Hostpoint (/edit/).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/deploy/hostpoint-edit"

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
copy_dir "${ROOT}/data" "${OUT}/data"
mkdir -p "${OUT}/data/uploads"
cp "${ROOT}/data/uploads/.htaccess" "${OUT}/data/uploads/.htaccess"
rm -f "${OUT}/data/uploads/"*.jpg "${OUT}/data/uploads/"*.jpeg \
      "${OUT}/data/uploads/"*.png "${OUT}/data/uploads/"*.webp
cp "${ROOT}/data/content-live.json" "${OUT}/data/content-live.seed.json"
EDIT_PDFS=(
  Statuten.pdf
  Sammlungskonzept.pdf
  Jahresbericht-2025.pdf
  JB_2024_final.pdf
  Programm.pdf
  historische-privat-fuehrungen.pdf
  szenische-fuehrung-berta.pdf
)
mkdir -p "${OUT}/dokumente"
for pdf in "${EDIT_PDFS[@]}"; do
  if [[ ! -f "${ROOT}/dokumente/${pdf}" ]]; then
    echo "dokumente/${pdf} fehlt — /edit/ auf Hostpoint wäre unvollständig." >&2
    exit 1
  fi
  cp "${ROOT}/dokumente/${pdf}" "${OUT}/dokumente/${pdf}"
done
copy_dir "${ROOT}/programm" "${OUT}/programm"
copy_dir "${ROOT}/coucou" "${OUT}/coucou"
copy_dir "${ROOT}/mus" "${OUT}/mus"
copy_dir "${ROOT}/zugang" "${OUT}/zugang"

mkdir -p "${OUT}/redaktion/storage"
cp "${ROOT}/redaktion/api.php" "${OUT}/redaktion/api.php"
cp "${ROOT}/redaktion/index.php" "${OUT}/redaktion/index.php"
cp "${ROOT}/redaktion/zugang.php" "${OUT}/redaktion/zugang.php"
cp "${ROOT}/redaktion/lib.php" "${OUT}/redaktion/lib.php"
cp "${ROOT}/redaktion/.htaccess" "${OUT}/redaktion/.htaccess"
cp "${ROOT}/redaktion/storage/.htaccess" "${OUT}/redaktion/storage/.htaccess"
cp "${ROOT}/redaktion/config.local.example.php" "${OUT}/redaktion/config.local.example.php"
cp "${ROOT}/redaktion/config.mail.example.php" "${OUT}/redaktion/config.mail.example.php"

cp "${ROOT}/deploy/edit.htaccess" "${OUT}/.htaccess"
cp "${ROOT}/deploy/edit.robots.txt" "${OUT}/robots.txt"

rm -f "${OUT}/redaktion/config.local.php"
rm -f "${OUT}/redaktion/config.mail.php"
rm -f "${OUT}/redaktion/storage/content-draft.json"
rm -f "${OUT}/redaktion/storage/access-emails.json"
rm -f "${OUT}/redaktion/storage/otp.json"
rm -f "${OUT}/redaktion/storage/zugang-secret.txt"

cat > "${OUT}/UPLOAD.txt" <<'TXT'
Hostpoint Bearbeitungszugang — /edit/
=====================================

URL:  https://www.hvwinterthur.ch/edit/
Zugang: zugelassene E-Mail-Adresse + Code per Mail
Redaktion: https://www.hvwinterthur.ch/edit/redaktion/
E-Mail-Liste: https://www.hvwinterthur.ch/edit/redaktion/zugang.php (Rolle Freigabe)

Alte URL /vorschau/ leitet per 301 auf /edit/ um (kein Ordner /vorschau/ mehr).

SMTP: GitHub-Secrets MAIL_SMTP_*. Start-Adressen im Code (Giger, Huggenberg, Jöhri).

Bevorzugt: GitHub Action «Deploy via rsync» (siehe README).
TXT

echo "Hostpoint-/edit/-Paket erstellt: ${OUT}"
find "${OUT}" -type f | wc -l
