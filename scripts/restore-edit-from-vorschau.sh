#!/usr/bin/env bash
# Redaktionsdaten von /vorschau/ nach /edit/ (+ öffentliche data/), /vorschau/ unangetastet lassen.
# Einmalig bzw. nur mit FORCE — Marker liegt ausserhalb des /edit/-rsync (--delete).
set -euo pipefail

host="${1:?host}"
user="${2:?user}"
target="${3:?target}"
keyfile="${4:?keyfile}"

case "$target" in */) ;; *) target="${target}/" ;; esac

ssh_cmd() {
  ssh -i "$keyfile" -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no "${user}@${host}" "$@"
}

v="${target}vorschau/"
e="${target}edit/"
marker="${target}data/.vorschau-restore-done"
legacy_marker="${e}.synced-from-vorschau-backup"

marker_exists() {
  ssh_cmd "test -f '${marker}' || test -f '${legacy_marker}'"
}

if [ "${FORCE_RESTORE_FROM_VORSCHAU:-0}" != "1" ]; then
  if marker_exists; then
    echo "Vorschau→Edit-Restore bereits erledigt (${marker}). FORCE_RESTORE_FROM_VORSCHAU=1 zum erneuten Kopieren."
    exit 0
  fi
fi

if ! ssh_cmd "test -f '${v}data/content-live.json'"; then
  echo "::warning::Kein ${v}data/content-live.json — Restore aus /vorschau/ übersprungen."
  exit 0
fi

# Edit-Stand neuer als eingefrorenes /vorschau/-Backup → nicht überschreiben (z. B. nach Redaktion heute).
if [ "${FORCE_RESTORE_FROM_VORSCHAU:-0}" != "1" ]; then
  newer=$(
    ssh_cmd "python3 - <<'PY'
import json
from pathlib import Path

def ts(path: str) -> str:
    try:
        d = json.loads(Path(path).read_text(encoding='utf-8'))
        return str(d.get('updatedAt') or '')
    except Exception:
        return ''

edit = ts('${e}data/content-live.json')
vorschau = ts('${v}data/content-live.json')
if edit and vorschau and edit > vorschau:
    print('edit_newer')
elif edit and not vorschau:
    print('edit_only')
else:
    print('ok')
PY"
  ) || newer="ok"
  case "$newer" in
    edit_newer|edit_only)
      echo "Edit/content-live.json ist neuer als /vorschau/-Backup — kein Überschreiben (${newer})."
      ssh_cmd "mkdir -p '${target}data' && date -u +%Y-%m-%dT%H:%M:%SZ > '${marker}'"
      exit 0
      ;;
  esac
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

ssh_cmd "mkdir -p '${target}data' && date -u +%Y-%m-%dT%H:%M:%SZ > '${marker}'"
ssh_cmd "rm -f '${legacy_marker}' 2>/dev/null || true"
echo "Restore aus /vorschau/ abgeschlossen. Marker: ${marker}"
