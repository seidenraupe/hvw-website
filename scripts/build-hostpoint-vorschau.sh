#!/usr/bin/env bash
# Baut die passwortgeschützte Vorschau der ganzen Website für Hostpoint (/vorschau/).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${ROOT}/deploy/hostpoint-vorschau"

rm -rf "${OUT}"
mkdir -p "${OUT}"

copy_dir() {
  local src="$1"
  local dest="$2"
  mkdir -p "${dest}"
  cp -a "${src}/." "${dest}/"
}

for page in index.html agenda.html museen.html lindengut.html moersburg.html ueber-uns.html mitmachen.html \
            partner.html sammlung.html zitate.html programm.html \
            impressum.html datenschutz.html; do
  cp "${ROOT}/${page}" "${OUT}/${page}"
done

copy_dir "${ROOT}/css" "${OUT}/css"
copy_dir "${ROOT}/js" "${OUT}/js"
copy_dir "${ROOT}/images" "${OUT}/images"
copy_dir "${ROOT}/data" "${OUT}/data"
mkdir -p "${OUT}/data/uploads"
rm -f "${OUT}/data/uploads/"*.jpg "${OUT}/data/uploads/"*.jpeg \
      "${OUT}/data/uploads/"*.png "${OUT}/data/uploads/"*.webp
cp "${ROOT}/data/content-live.json" "${OUT}/data/content-live.seed.json"
if [[ ! -f "${ROOT}/Statuten.pdf" ]]; then
  echo "Statuten.pdf fehlt — Vorschau auf Hostpoint wäre unvollständig." >&2
  exit 1
fi
cp "${ROOT}/Statuten.pdf" "${OUT}/Statuten.pdf"
if [[ ! -f "${ROOT}/Sammlungskonzept.pdf" ]]; then
  echo "Sammlungskonzept.pdf fehlt — Vorschau auf Hostpoint wäre unvollständig." >&2
  exit 1
fi
cp "${ROOT}/Sammlungskonzept.pdf" "${OUT}/Sammlungskonzept.pdf"
for pdf in historische-privat-fuehrungen.pdf szenische-fuehrung-berta.pdf; do
  if [[ ! -f "${ROOT}/dokumente/${pdf}" ]]; then
    echo "dokumente/${pdf} fehlt — Vorschau auf Hostpoint wäre unvollständig." >&2
    exit 1
  fi
done
mkdir -p "${OUT}/dokumente"
cp "${ROOT}/dokumente/historische-privat-fuehrungen.pdf" "${OUT}/dokumente/historische-privat-fuehrungen.pdf"
cp "${ROOT}/dokumente/szenische-fuehrung-berta.pdf" "${OUT}/dokumente/szenische-fuehrung-berta.pdf"
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

cp "${ROOT}/deploy/vorschau.htaccess" "${OUT}/.htaccess"
cp "${ROOT}/deploy/vorschau.robots.txt" "${OUT}/robots.txt"

rm -f "${OUT}/redaktion/config.local.php"
rm -f "${OUT}/redaktion/config.mail.php"
rm -f "${OUT}/redaktion/storage/content-draft.json"
rm -f "${OUT}/redaktion/storage/access-emails.json"
rm -f "${OUT}/redaktion/storage/otp.json"
rm -f "${OUT}/redaktion/storage/zugang-secret.txt"

cat > "${OUT}/UPLOAD.txt" <<'TXT'
Hostpoint interne Vorschau — /vorschau/
======================================

URL:  https://www.hvwinterthur.ch/vorschau/
Zugang: zugelassene E-Mail-Adresse + Code per Mail
Redaktion: https://www.hvwinterthur.ch/vorschau/redaktion/
E-Mail-Liste: https://www.hvwinterthur.ch/vorschau/redaktion/zugang.php (Rolle Freigabe)

SMTP: GitHub-Secrets MAIL_SMTP_*. Start-Adressen im Code (Giger, Huggenberg, Jöhri).

Bevorzugt: GitHub Action «Deploy via rsync» (siehe README).
TXT

echo "Hostpoint-Vorschau erstellt: ${OUT}"
find "${OUT}" -type f | wc -l
