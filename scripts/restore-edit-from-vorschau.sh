#!/usr/bin/env bash
# Redaktionsdaten von /vorschau/ nach /edit/ (+ öffentliche data/), /vorschau/ unangetastet lassen.
set -euo pipefail

host="${1:?host}"
user="${2:?user}"
target="${3:?target}"
keyfile="${4:?keyfile}"

case "$target" in */) ;; *) target="${target}/" ;; esac

ssh_cmd() {
  ssh -i "$keyfile" -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no "${user}@${host}" "$@"
}

v="${target}vorschau"
e="${target}edit"
marker="${e}.synced-from-vorschau-backup"

if [ "${FORCE_RESTORE_FROM_VORSCHAU:-0}" != "1" ]; then
  if ssh_cmd "test -f '${marker}'"; then
    echo "Edit wurde bereits aus /vorschau/ befüllt (${marker}). FORCE_RESTORE_FROM_VORSCHAU=1 zum erneuten Kopieren."
    exit 0
  fi
fi

if ! ssh_cmd "test -f '${v}data/content-live.json'"; then
  echo "::warning::Kein ${v}data/content-live.json — Restore aus /vorschau/ übersprungen."
  exit 0
fi

echo "Redaktions-Backup /vorschau/ → /edit/ (Ordner /vorschau/ bleibt unverändert)…"
ssh_cmd "mkdir -p '${e}data/uploads' '${e}redaktion/storage' '${target}data/uploads'"

ssh_cmd "cp -f '${v}data/content-live.json' '${e}data/content-live.json'"
ssh_cmd "cp -f '${v}data/content-live.json' '${target}data/content-live.json'"

if ssh_cmd "test -f '${v}redaktion/storage/content-draft.json'"; then
  ssh_cmd "cp -f '${v}redaktion/storage/content-draft.json' '${e}redaktion/storage/content-draft.json'"
fi

if ssh_cmd "test -d '${v}data/uploads'"; then
  ssh_cmd "rsync -a '${v}data/uploads/' '${e}data/uploads/'"
  ssh_cmd "rsync -a '${e}data/uploads/' '${target}data/uploads/'"
fi

ssh_cmd "date -u +%Y-%m-%dT%H:%M:%SZ > '${marker}'"
echo "Restore aus /vorschau/ abgeschlossen. Marker: ${marker}"
