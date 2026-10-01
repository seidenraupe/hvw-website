#!/usr/bin/env bash
# Hostpoint: fehlendes content-live.json finden oder anlegen, Bildpfade reparieren.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

host="${1:?host}"
user="${2:?user}"
target="${3:?target}"
keyfile="${4:?keyfile}"

case "$target" in */) ;; *) target="${target}/" ;; esac

ssh_cmd() {
  ssh -i "$keyfile" -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no "${user}@${host}" "$@"
}

rsync_from() {
  local remote_path="$1"
  local local_path="$2"
  rsync -avz \
    -e "ssh -i ${keyfile} -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no" \
    "${user}@${host}:${remote_path}" \
    "${local_path}" 2>/dev/null || return 1
}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "Server-Inventar (content-live + Uploads)…"
ssh_cmd "find '${target}' \\( -name 'content-live.json' -o -path '*/data/uploads/*.jpg' -o -path '*/data/uploads/*.jpeg' -o -path '*/data/uploads/*.png' -o -path '*/data/uploads/*.webp' \\) 2>/dev/null | sort" \
  | tee "${work}/inventory.txt" || true

live_local="${work}/live.json"
draft_local="${work}/draft.json"
touch "${draft_local}"

candidates=(
  "${target}edit/data/content-live.json"
  "${target}data/content-live.json"
  "${target}vorschau/data/content-live.json"
  "${target}edit/data/content-live.seed.json"
  "${target}data/content-live.seed.json"
)

for remote in "${candidates[@]}"; do
  if rsync_from "${remote}" "${live_local}" && [ -s "${live_local}" ]; then
    echo "Live-JSON übernommen von: ${remote}"
    break
  fi
done

if [ ! -s "${live_local}" ]; then
  echo "::warning::Kein content-live auf dem Server — Git-Seed als Basis."
  cp "${ROOT}/data/content-live.json" "${live_local}"
fi

draft_candidates=(
  "${target}edit/redaktion/storage/content-draft.json"
  "${target}vorschau/redaktion/storage/content-draft.json"
)
for remote in "${draft_candidates[@]}"; do
  if rsync_from "${remote}" "${draft_local}" && [ -s "${draft_local}" ]; then
    echo "Entwurf übernommen von: ${remote}"
    break
  fi
done

mkdir -p "${work}/uploads-collected"
while IFS= read -r abs; do
  [ -z "$abs" ] || continue
  case "$abs" in
    *.jpg|*.jpeg|*.png|*.webp)
      base=$(basename "$abs")
      rsync_from "$abs" "${work}/uploads-collected/${base}" || true
      ;;
  esac
done < "${work}/inventory.txt"

for sub in uploads-edit uploads-root uploads-vorschau; do
  mkdir -p "${work}/${sub}"
  rsync_from "${target}edit/data/uploads/" "${work}/${sub}/" || true
  rsync_from "${target}data/uploads/" "${work}/uploads-root/" || true
  rsync_from "${target}vorschau/data/uploads/" "${work}/uploads-vorschau/" || true
done

python3 "${ROOT}/scripts/merge-content-json.py" \
  --schema "${ROOT}/data/content-schema.json" \
  --seed "${ROOT}/data/content-live.json" \
  --remote-live "${live_local}" \
  --remote-draft "${draft_local}" \
  --out-live "${work}/merged-live.json" \
  --out-draft "${work}/merged-draft.json" || cp "${live_local}" "${work}/merged-live.json"

python3 "${ROOT}/scripts/restore-editorial-images.py" \
  --live "${work}/merged-live.json" \
  --draft "${work}/merged-draft.json" \
  --upload-dir "${work}/uploads-collected" \
  --upload-dir "${work}/uploads-edit" \
  --upload-dir "${work}/uploads-root" \
  --upload-dir "${work}/uploads-vorschau" \
  --out-live "${work}/final-live.json" \
  --out-draft "${work}/final-draft.json"

ssh_cmd "mkdir -p '${target}edit/data' '${target}data' '${target}edit/data/uploads' '${target}data/uploads' '${target}edit/redaktion/storage'"

rsync -avz \
  -e "ssh -i ${keyfile} -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no" \
  "${work}/final-live.json" \
  "${user}@${host}:${target}edit/data/content-live.json"
rsync -avz \
  -e "ssh -i ${keyfile} -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no" \
  "${work}/final-live.json" \
  "${user}@${host}:${target}data/content-live.json"
rsync -avz \
  -e "ssh -i ${keyfile} -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no" \
  "${work}/final-draft.json" \
  "${user}@${host}:${target}edit/redaktion/storage/content-draft.json"

if compgen -G "${work}/uploads-collected/*" > /dev/null; then
  rsync -avz \
    -e "ssh -i ${keyfile} -p 22 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no" \
    "${work}/uploads-collected/" \
    "${user}@${host}:${target}edit/data/uploads/"
fi

ssh_cmd "rsync -a '${target}edit/data/uploads/' '${target}data/uploads/' 2>/dev/null || true"

echo "Bootstrap abgeschlossen."
