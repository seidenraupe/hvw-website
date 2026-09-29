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
    "https://schlosskyburg.ch/",
    "https://www.uhrenmuseumwinterthur.ch/",
    "https://muenzkabinett.winterthur.ch/",
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
    "https://winterthur.heimatschutz.ch/",
    "https://stadt.winterthur.ch/organisation/verwaltung-departemente/bau-und-mobilitaet/amt-fuer-staedtebau/stadtplanung/denkmalpflege",
    "https://stadt.winterthur.ch/organisation/verwaltung-departemente/stadtkanzlei/stadtarchiv",
    "https://bibliotheken.winterthur.ch/programm/sammlung-winterthur",
    "https://www.zh.ch/de/sport-kultur/kultur/kulturerbe/archaeologie.html",
    "https://www.zh.ch/de/sport-kultur/kultur/kulturerbe/denkmalpflege.html?search=denkmalpflege",
    "https://www.zh.ch/de/sport-kultur/swisslos-fonds/gemeinnuetziger-fonds.html",
]
for url in urls:
    if url not in page:
        raise SystemExit(f"Link fehlt: {url}")
if "publikationen.html" in page:
    raise SystemExit("Partnerseite verlinkt noch Publikationen")
if "partner-slot--logo" in page or ">Logo<" in page:
    raise SystemExit("Logo-Spalte ist noch auf der Partnerseite")
if 'data-content-image="partner.14.image"' not in page or 'data-content-href="1"' not in page:
    raise SystemExit("Bildfeld oder Linkfeld fehlt")
if page.find("IG Geschichtsstadt Winterthur") > page.find("Schloss Hegi"):
    raise SystemExit("Geschichtsstadt steht nicht zuoberst")
if not (page.find("IG Geschichtsstadt Winterthur") < page.find("Gasthaus Schlosshalde") < page.find("Schloss Hegi")):
    raise SystemExit("Schlosshalde muss an zweiter Stelle stehen")
heroes = [
    "hero-geschichtsstadt.jpg",
    "hero-schlosshalde.jpg",
    "hero-1.jpg",
    "hero-14.jpg",
]
for filename in heroes:
    if filename not in page or not (ROOT / "images/partner" / filename).is_file():
        raise SystemExit(f"Hero fehlt: {filename}")
if page.count('class="partner-slot partner-slot--photo') != 20:
    raise SystemExit("Nicht jede Partnerzeile hat genau ein Bild")
if not (
    page.find("Frauenstadtrundgang Winterthur")
    < page.find("Museum Schloss Kyburg")
    < page.find("Uhrenmuseum Winterthur")
    < page.find("Münzkabinett Winterthur")
    < page.find("Winterthur-Glossar")
):
    raise SystemExit("Neue Partner müssen nach Frauenstadtrundgang und vor dem Glossar stehen")
for filename in ("hero-17.jpg", "hero-18.jpg", "hero-19.jpg", "hero-20.jpg"):
    if filename not in page or not (ROOT / "images/partner" / filename).is_file():
        raise SystemExit(f"Hero fehlt: {filename}")
if "Heimatschutz Winterthur" not in page:
    raise SystemExit("Heimatschutz fehlt")
if page.find("Heimatschutz Winterthur") < page.find("Netzwerk Kulturerbe Schweiz"):
    raise SystemExit("Heimatschutz muss am Ende der Bildliste stehen")
if not (
    page.find("</table>")
    < page.find('id="netzwerk-stadt-heading"')
    < page.find('id="netzwerk-kanton-heading"')
    < page.find("</main>")
):
    raise SystemExit("Stadt- und Kantonsblock müssen unter der Liste stehen")
if page.find("<h1") > -1 and "Netzwerk" not in page[page.find("<h1"): page.find("</h1>") + 6]:
    raise SystemExit("Seitentitel muss Netzwerk heissen")

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
    if ">Partner<" in block:
        raise SystemExit(f"{html.name}: Navigation heisst noch Partner")
    if ">Netzwerk<" not in block:
        raise SystemExit(f"{html.name}: Navigation braucht den Eintrag Netzwerk")

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
