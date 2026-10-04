#!/usr/bin/env python3
"""Agenda-Rückblick: Bild-Upload, Cover-Crop, optionale Schema-Felder."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
agenda = (ROOT / "agenda.html").read_text(encoding="utf-8")
schema = json.loads((ROOT / "data/content-schema.json").read_text(encoding="utf-8"))
live = json.loads((ROOT / "data/content-live.json").read_text(encoding="utf-8"))
css = (ROOT / "css/site.css").read_text(encoding="utf-8")
editor_js = (ROOT / "js/content-editor.js").read_text(encoding="utf-8")
content_js = (ROOT / "js/content.js").read_text(encoding="utf-8")
api = (ROOT / "redaktion/api.php").read_text(encoding="utf-8")
lib = (ROOT / "redaktion/lib.php").read_text(encoding="utf-8")
deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
merge = (ROOT / "scripts/merge-content-json.py").read_text(encoding="utf-8")

for n in range(1, 7):
    field = f"agenda.rueckblick.{n}.image"
    if field not in schema["fields"]:
        raise SystemExit(f"Schema fehlt {field}")
    if schema["fields"][field].get("type") != "image":
        raise SystemExit(f"{field} ist kein image-Feld")
    if schema["fields"][field].get("optional") is not True:
        raise SystemExit(f"{field} muss optional sein")
    if field not in live["fields"]:
        raise SystemExit(f"Live fehlt {field}")
    body = f"agenda.rueckblick.{n}.body"
    if schema["fields"][body].get("max") != 600:
        raise SystemExit(f"{body} muss 600 Zeichen erlauben")
    if f'data-content-image="{field}"' not in agenda:
        raise SystemExit(f"agenda.html fehlt {field}")

if "object-fit: cover" not in css or "object-position: center" not in css:
    raise SystemExit("Kartenbild muss formatfüllend und zentriert beschnitten werden")
if ".event-card__media.has-photo .event-card__watermark" not in css:
    raise SystemExit("Wasserzeichen nach Upload ausblenden fehlt")
if "body.hvw-editing [data-content-image] .hvw-image-tools" not in css:
    raise SystemExit("Upload-Buttons müssen im Redaktionsmodus über dem Bild liegen")

if agenda.count("hvw-image-tools") < 6:
    raise SystemExit("agenda.html muss die Upload-Buttons in allen 6 Karten enthalten")
if 'js/content.js?v=' not in agenda:
    raise SystemExit("agenda.html muss content.js cache-frei laden")

if 'data-content-image' not in content_js or "applyImageFields" not in content_js:
    raise SystemExit("content.js wendet Bildfelder nicht an")
if "upload-image" not in editor_js or "hvw-image-upload" not in editor_js:
    raise SystemExit("Editor hat keinen Bild-Upload")
if "bindImageTools" not in editor_js:
    raise SystemExit("Editor muss Upload-Buttons per Delegation binden")
if 'content-editor.js?v=' not in content_js:
    raise SystemExit("Editor-Skript muss cache-frei geladen werden")
if "imagecopyresampled" not in api or "targetW = 1200" not in api or "targetH = 900" not in api:
    raise SystemExit("API schneidet nicht zentriert auf 4:3 / 1200×900")
if "hvw_sanitize_image_path" not in lib or "hvw_is_optional_field" not in lib:
    raise SystemExit("lib.php fehlt Bild-Sanitisierung")
if "data/uploads/*.jpg" not in deploy:
    raise SystemExit("Deploy darf hochgeladene Bilder nicht löschen")
if "agenda.rueckblick." not in merge:
    raise SystemExit("Merge muss Agenda-Rückblick als Redaktionsfelder kennen")

htaccess = ROOT / "data/uploads/.htaccess"
if not htaccess.is_file():
    raise SystemExit("data/uploads/.htaccess fehlt")
if "Require all denied" not in htaccess.read_text(encoding="utf-8"):
    raise SystemExit("Upload-Ordner muss PHP verbieten")

serve = (ROOT / "zugang/serve.php").read_text(encoding="utf-8")
if "Cache-Control: no-store" not in serve:
    raise SystemExit("Vorschau-HTML darf nicht aus dem Browser-Cache kommen")
vorschau_ht = (ROOT / "deploy/edit.htaccess").read_text(encoding="utf-8")
if "Cache-Control" not in vorschau_ht:
    raise SystemExit("edit.htaccess muss JS/CSS ohne Cache ausliefern")

print("agenda image upload ok")
