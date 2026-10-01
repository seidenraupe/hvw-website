#!/usr/bin/env bash
# Vollständiges Backup des Hostpoint-Document-Roots (öffentliche Site + /edit/ + /vorschau/ + data/ …).
# Optional: ~/cronjobs/ und Git-Quellcode als Ergänzung.
set -euo pipefail

host="${1:?host}"
user="${2:?user}"
target="${3:?target}"
keyfile="${4:?keyfile}"
out_root="${5:?output directory}"

case "$target" in */) ;; *) target="${target}/" ;; esac

stamp="$(date -u +%Y-%m-%dT%H%M%SZ)"
backup_dir="${out_root%/}/hostpoint-backup-${stamp}"
site_dir="${backup_dir}/hvwinterthur.ch"
mkdir -p "${site_dir}"

ssh_cmd() {
  ssh -i "$keyfile" -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no "${user}@${host}" "$@"
}

rsync_from() {
  rsync -avz \
    -e "ssh -i ${keyfile} -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no" \
    "$@"
}

echo "Hostpoint-Backup → ${backup_dir}"
echo "Quelle: ${user}@${host}:${target}"

rsync_from "${user}@${host}:${target}" "${site_dir}/"

if [ "${BACKUP_INCLUDE_CRONJOBS:-1}" = "1" ]; then
  cron_local="${backup_dir}/cronjobs-hostpoint"
  mkdir -p "${cron_local}"
  if rsync_from "${user}@${host}:~/cronjobs/" "${cron_local}/" 2>/dev/null; then
    echo "cronjobs/ gesichert."
  else
    echo "::warning::~/cronjobs/ konnte nicht gelesen werden (optional)."
    rmdir "${cron_local}" 2>/dev/null || true
  fi
fi

if [ -n "${BACKUP_GIT_ARCHIVE:-}" ] && [ -f "${BACKUP_GIT_ARCHIVE}" ]; then
  mkdir -p "${backup_dir}/github-quellcode"
  cp "${BACKUP_GIT_ARCHIVE}" "${backup_dir}/github-quellcode/"
  echo "Git-Archiv angehängt: $(basename "${BACKUP_GIT_ARCHIVE}")"
fi

{
  echo "Hostpoint-Vollbackup"
  echo "Erstellt (UTC): ${stamp}"
  echo "Quelle: ${user}@${host}:${target}"
  echo "Ordnerstruktur: hvwinterthur.ch/ = Document Root 1:1"
  echo ""
  echo "Dateien unter hvwinterthur.ch/:"
  find "${site_dir}" -type f | wc -l
  echo "Bytes unter hvwinterthur.ch/:"
  du -sb "${site_dir}" | awk '{print $1}'
} > "${backup_dir}/BACKUP-INFO.txt"

( cd "${backup_dir}" && find . -type f ! -path './BACKUP-INFO.txt' | sort ) > "${backup_dir}/manifest-dateien.txt"

archive="${out_root%/}/hostpoint-backup-${stamp}.tar.gz"
tar -C "${out_root%/}" -czf "${archive}" "hostpoint-backup-${stamp}"
echo "Archiv: ${archive} ($(du -h "${archive}" | awk '{print $1}'))"
echo "${archive}"
