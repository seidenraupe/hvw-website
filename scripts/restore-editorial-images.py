#!/usr/bin/env python3
"""Stellt Redaktions-Bildpfade wieder her (Live leer, Entwurf oder Upload-Ordner)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

EDITORIAL_IMAGE_RE = re.compile(
    r"^(agenda\.rueckblick\.([1-6])\.image|"
    r"sammlung\.objekt\.([1-6])\.image|"
    r"(lindengut|moersburg)\.bild\.([1-3])\.image|"
    r"partner\.([1-9]|1[0-9]|20)\.image)$"
)

UPLOAD_FILE_RE = re.compile(
    r"^(rueckblick|sammlung|lindengut|moersburg|partnerbild|partnerlogo)-"
    r"([1-9]|1[0-9]|20)-[a-z0-9]+\.(?:jpe?g|png|webp)$",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def field_map(doc: dict[str, Any]) -> dict[str, str]:
    fields = doc.get("fields")
    if not isinstance(fields, dict):
        return {}
    return {str(k): "" if v is None else str(v) for k, v in fields.items()}


def slot_key(field_id: str) -> str | None:
    m = EDITORIAL_IMAGE_RE.match(field_id)
    if not m:
        return None
    if m.group(2):
        return f"rueckblick-{m.group(2)}"
    if m.group(3):
        return f"sammlung-{m.group(3)}"
    if m.group(4) and m.group(5):
        return f"{m.group(4)}-{m.group(5)}"
    if m.group(6):
        return f"partnerbild-{m.group(6)}"
    return None


def index_uploads(upload_dirs: list[Path]) -> dict[str, Path]:
    """Neueste Datei pro Slot (prefix-N)."""
    best: dict[str, tuple[float, Path]] = {}
    for root in upload_dirs:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if not path.is_file():
                continue
            m = UPLOAD_FILE_RE.match(path.name)
            if not m:
                continue
            key = f"{m.group(1).lower()}-{m.group(2)}"
            if key.startswith("partnerlogo"):
                key = f"partnerbild-{m.group(2)}"
            mtime = path.stat().st_mtime
            prev = best.get(key)
            if prev is None or mtime >= prev[0]:
                best[key] = (mtime, path)
    return {k: v[1] for k, v in best.items()}


def restore_fields(
    live: dict[str, str],
    draft: dict[str, str],
    uploads: dict[str, Path],
) -> tuple[dict[str, str], dict[str, int]]:
    out = dict(live)
    stats = {"from_draft": 0, "from_disk": 0, "already_ok": 0, "still_empty": 0}
    for field_id, live_val in list(out.items()):
        if not field_id.endswith(".image"):
            continue
        if live_val.strip():
            stats["already_ok"] += 1
            continue
        draft_val = draft.get(field_id, "").strip()
        if draft_val:
            out[field_id] = draft_val
            stats["from_draft"] += 1
            continue
        key = slot_key(field_id)
        if key and key in uploads:
            out[field_id] = f"data/uploads/{uploads[key].name}"
            stats["from_disk"] += 1
            continue
        stats["still_empty"] += 1
    return out, stats


def write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def selftest() -> None:
    live = {"sammlung.objekt.1.image": "", "agenda.rueckblick.1.image": ""}
    draft = {"sammlung.objekt.1.image": "data/uploads/sammlung-1-deadbeef.jpg"}
    uploads = {"sammlung-2": Path("sammlung-2-beefdead.jpg")}
    out, stats = restore_fields(live, draft, uploads)
    assert out["sammlung.objekt.1.image"] == draft["sammlung.objekt.1.image"]
    assert stats["from_draft"] == 1
    print("selftest ok")


def main() -> int:
    if "--selftest" in sys.argv:
        selftest()
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--live", type=Path, required=True)
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--upload-dir", type=Path, action="append", default=[])
    parser.add_argument("--out-live", type=Path, required=True)
    parser.add_argument("--out-draft", type=Path)
    args = parser.parse_args()

    live_doc = load_json(args.live)
    draft_doc = load_json(args.draft) if args.draft else {}
    live_fields = field_map(live_doc)
    draft_fields = field_map(draft_doc)
    uploads = index_uploads(args.upload_dir)

    restored, stats = restore_fields(live_fields, draft_fields, uploads)
    live_out = dict(live_doc)
    live_out["fields"] = restored
    write_json(args.out_live, live_out)

    if args.out_draft:
        draft_out = dict(draft_doc) if draft_doc else {"status": "draft", "fields": {}}
        draft_fields_out = dict(field_map(draft_out))
        for field_id, val in restored.items():
            if field_id.endswith(".image") and val.strip():
                draft_fields_out[field_id] = val
        draft_out["fields"] = draft_fields_out
        write_json(args.out_draft, draft_out)

    print(
        "restore-editorial-images: "
        f"{stats['from_draft']} aus Entwurf, "
        f"{stats['from_disk']} aus Upload-Ordner, "
        f"{stats['already_ok']} unverändert, "
        f"{stats['still_empty']} weiterhin leer."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
