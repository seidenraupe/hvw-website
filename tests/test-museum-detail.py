#!/usr/bin/env python3
"""Lindengut und Mörsburg: eigene Seiten, Texte und drei Bild-Uploads."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
schema = json.loads((ROOT / "data/content-schema.json").read_text(encoding="utf-8"))
live = json.loads((ROOT / "data/content-live.json").read_text(encoding="utf-8"))
museen = (ROOT / "museen.html").read_text(encoding="utf-8")
lib = (ROOT / "redaktion/lib.php").read_text(encoding="utf-8")
build = (ROOT / "scripts/build-hostpoint-vorschau.sh").read_text(encoding="utf-8")

if "winterthur.com" in museen or "moersburg-winterthur.ch" in museen:
    raise SystemExit("Museumsseite darf nicht mehr auf externe Haus-Websites verlinken")
if 'href="lindengut.html"' not in museen or 'href="moersburg.html"' not in museen:
    raise SystemExit("Museumsseite muss auf die Detailseiten verlinken")

for key, filename in (("lindengut", "lindengut.html"), ("moersburg", "moersburg.html")):
    html = (ROOT / filename).read_text(encoding="utf-8")
    for part in ("kicker", "title", "lead", "oeffnung", "body"):
        field = f"{key}.{part}"
        if field not in schema["fields"] or field not in live["fields"]:
            raise SystemExit(f"Feld fehlt: {field}")
        if f'data-content="{field}"' not in html:
            raise SystemExit(f"{filename} fehlt {field}")
    if schema["fields"][f"{key}.lead"]["max"] != 1000:
        raise SystemExit(f"{key}.lead muss 1000 Zeichen erlauben")
    if schema["fields"][f"{key}.oeffnung"]["max"] != 600:
        raise SystemExit(f"{key}.oeffnung muss 600 Zeichen erlauben")
    if schema["fields"][f"{key}.body"]["max"] != 4000:
        raise SystemExit(f"{key}.body muss 4000 Zeichen erlauben")
    if html.find(f'id="{key}-bilder"') > html.find(f'id="{key}-text"'):
        raise SystemExit(f"{filename}: Bilder müssen vor dem Erklärungstext stehen")
    if "google.com/maps/search/" not in html or ">Google Maps</a>" not in html:
        raise SystemExit(f"{filename}: Google-Maps-Button fehlt")
    if html.find(f'data-content="{key}.oeffnung"') > html.find(">Google Maps</a>"):
        raise SystemExit(f"{filename}: Maps-Button muss unter der Öffnungszeiten-Box stehen")
    if key == "lindengut":
        tour = "https://www.jantofilm.ch/panotour/MuseumLindengut/index.html"
        if tour not in html or ">360-Grad-Tour</a>" not in html:
            raise SystemExit("Lindengut: Button 360-Grad-Tour fehlt")
        if html.find('data-content="lindengut.lead"') > html.find(">360-Grad-Tour</a>"):
            raise SystemExit("360-Grad-Tour muss unter der linken Textbox stehen")
        spiel = "https://360games.ch/lindengut/"
        if spiel not in html or ">Online-Spiel in der Villa Lindengut</a>" not in html:
            raise SystemExit("Lindengut: Button Online-Spiel fehlt")
        if "Lieblings-Kinderspielzeug von NR Dr. Eduard Sulzer-Ziegler" not in html:
            raise SystemExit("Lindengut: Erklärung zum Online-Spiel fehlt")
        if html.find('data-content="lindengut.body"') > html.find(">Online-Spiel in der Villa Lindengut</a>"):
            raise SystemExit("Online-Spiel muss unter dem Erklärungstext stehen")
    if "lg:grid-cols-2" not in html:
        raise SystemExit(f"{filename}: Lead und Öffnungszeiten müssen nebeneinander stehen")
    if 'class="hvw-explain mt-6 text-lg leading-relaxed"' not in html:
        raise SystemExit(f"{filename}: Erklärungstext muss die Klasse hvw-explain tragen")
    if f'data-content="{key}.body"' in html and "max-w-3xl" in html.split(f'data-content="{key}.body"')[0].split("<div")[-1]:
        raise SystemExit(f"{filename}: Erklärungstext darf nicht auf max-w-3xl begrenzt sein")
    for n in range(1, 4):
        image = f"{key}.bild.{n}.image"
        caption = f"{key}.bild.{n}.caption"
        if schema["fields"][image].get("type") != "image":
            raise SystemExit(f"{image} ist kein Bildfeld")
        if f'data-content-image="{image}"' not in html:
            raise SystemExit(f"{filename} fehlt {image}")
        if f'data-content="{caption}"' not in html:
            raise SystemExit(f"{filename} fehlt {caption}")
        block = html.split(f'data-content="{caption}"', 1)[0]
        lead = block[-280:]
        if 'class="hvw-bild-caption"' not in lead or 'class="hvw-bild-caption__label">Legende</span>' not in lead:
            raise SystemExit(f"{filename}: {caption} braucht eine Legende-Beschriftung für den Edit-Modus")
        if 'data-content="' in lead.split('class="hvw-bild-caption"', 1)[-1]:
            raise SystemExit(f"{filename}: Legende darf nicht im bearbeitbaren Text von {caption} stehen")
        if "hvw-image-tools" not in html:
            raise SystemExit(f"{filename} braucht Upload-Buttons")
    if "lightbox.js" not in html or "content.js" not in html:
        raise SystemExit(f"{filename} muss Lightbox und Redaktion laden")

if "lindengut" not in lib or "moersburg" not in lib:
    raise SystemExit("lib.php muss Lindengut- und Mörsburg-Uploads erlauben")
if "lindengut.html" not in build or "moersburg.html" not in build:
    raise SystemExit("Vorschau-Build muss die Detailseiten enthalten")

site_css = (ROOT / "css/site.css").read_text(encoding="utf-8")
editor_css = (ROOT / "css/content-editor.css").read_text(encoding="utf-8")
if ".hvw-bild-caption__label" not in site_css or "display: none" not in site_css.split(".hvw-bild-caption__label", 1)[1][:80]:
    raise SystemExit("Legende-Beschriftung muss auf der öffentlichen Seite ausgeblendet sein")
if "body.hvw-editing .hvw-bild-caption__label" not in editor_css:
    raise SystemExit("Legende-Beschriftung muss im Edit-Modus sichtbar sein")
if "body.hvw-editing .hvw-bild-caption [data-content]" not in editor_css:
    raise SystemExit("Bildlegende braucht im Edit-Modus eine klickbare Mindesthöhe")

print("museum detail pages ok")
