#!/usr/bin/env python3
"""Freigabe warnt, wenn Upload-Bilder öffentlich fehlen."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
api = (ROOT / "redaktion/api.php").read_text(encoding="utf-8")
lib = (ROOT / "redaktion/lib.php").read_text(encoding="utf-8")
editor = (ROOT / "js/content-editor.js").read_text(encoding="utf-8")
content = (ROOT / "js/content.js").read_text(encoding="utf-8")

for needle in (
    "publish-check",
    "hvw_collect_public_upload_gaps",
    "hvw_publish_upload_error_message",
    "uploadGaps",
):
    if needle not in api and needle not in lib:
        raise SystemExit(f"Fehlt: {needle}")

if "hvw_sync_field_uploads_to_public($fields);" not in api:
    raise SystemExit("Publish muss Uploads vor dem Schreiben der Live-JSON spiegeln")

if "publish-check" not in editor or "editAvailable" not in editor:
    raise SystemExit("Editor muss publish-check und editAvailable auswerten")

if "20261010-publish-upload" not in content:
    raise SystemExit("Editor-Asset-Version muss für Cache-Bust erhöht sein")

print("ok")
