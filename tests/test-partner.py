#!/usr/bin/env python3
"""Publikationen-Seite ist weg, Partner/Netzwerk verlinkt die Organisationen."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "publikationen.html").exists():
    raise SystemExit("publikationen.html muss gelöscht sein")

page = (ROOT / "partner.html").read_text(encoding="utf-8")
urls = [
    "https://www.geschichtsstadt-winterthur.ch/",
    "https://www.moersburg-winterthur.ch/site/",
    "https://schlosshegi.ch/",
    "https://frauenrundgang.ch/",
    "https://www.winterthur-glossar.ch/",
    "https://bilddatenbank.winterthur.ch/ims_publisher/",
    "https://industriekultur-winterthur.ch/site/",
    "https://industriekultur.ch/",
    "https://sgti.ch/site/",
    "https://dampfzentrum.ch/",
    "https://reismuehle-hegi.ch/",
    "https://www.kehrseite-winterthur.ch/",
    "https://www.skkg.ch/",
    "https://dorfmuseum-wülflingen.ch/",
    "https://www.museums.ch/",
    "https://netzwerk-kulturerbe.ch/",
]
for url in urls:
    if url not in page:
        raise SystemExit(f"Link fehlt: {url}")
if "publikationen.html" in page:
    raise SystemExit("Partnerseite verlinkt noch Publikationen")
if 'data-content-image="partner.14.logo"' not in page or 'data-content-href="1"' not in page:
    raise SystemExit("Logo-Upload oder Linkfeld fehlt")
if page.find("IG Geschichtsstadt Winterthur") > page.find("Schloss Hegi"):
    raise SystemExit("Geschichtsstadt steht nicht zuoberst")
if not (page.find("IG Geschichtsstadt Winterthur") < page.find("Gasthaus Schlosshalde") < page.find("Schloss Hegi")):
    raise SystemExit("Schlosshalde muss an zweiter Stelle stehen")
if "bild-geschichtsstadt.jpg" not in page or "logo-geschichtsstadt.png" not in page:
    raise SystemExit("Teaser oder Logo der Geschichtsstadt fehlt")
if "bild-schlosshalde.jpg" not in page or "logo-schlosshalde.png" not in page:
    raise SystemExit("Teaser oder Logo der Schlosshalde fehlt")
for filename in ("logo-schlosshalde.png", "bild-schlosshalde.jpg"):
    if not (ROOT / "images/partner" / filename).is_file():
        raise SystemExit(f"Bilddatei fehlt: {filename}")

for html in ROOT.glob("*.html"):
    if html.name == "programm.html":
        continue
    text = html.read_text(encoding="utf-8")
    if "publikationen.html" in text:
        raise SystemExit(f"{html.name} verlinkt noch Publikationen")
    if 'href="partner.html"' not in text:
        raise SystemExit(f"{html.name} hat keinen Partner-Link")
    nav = re.search(r'aria-label="Hauptnavigation">(.*?)</nav>', text, re.S)
    if not nav:
        raise SystemExit(f"{html.name} hat keine Hauptnavigation")
    block = nav.group(1)
    if block.find('href="sammlung.html"') > block.find('href="partner.html"'):
        raise SystemExit(f"{html.name}: Partner steht noch vor Sammlung")

schema = json.loads((ROOT / "data/content-schema.json").read_text(encoding="utf-8"))
live = json.loads((ROOT / "data/content-live.json").read_text(encoding="utf-8"))
if "publikationen.intro" in schema["fields"] or "publikationen.intro" in live["fields"]:
    raise SystemExit("publikationen.intro ist noch im Inhalt")
if schema["fields"]["partner.7.url"]["type"] != "url":
    raise SystemExit("Partner-Link ist kein URL-Feld")
if "partner." not in (ROOT / "scripts/merge-content-json.py").read_text(encoding="utf-8"):
    raise SystemExit("Merge behandelt Partner-Felder nicht als Redaktion")
if "partner.html" not in (ROOT / "scripts/build-hostpoint-vorschau.sh").read_text(encoding="utf-8"):
    raise SystemExit("Vorschau-Build kopiert partner.html nicht")
print("partner page ok")
