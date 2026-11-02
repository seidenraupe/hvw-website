#!/usr/bin/env python3
"""Vorstand ohne Gruppenfoto; Namen fett; kein Platzhalter-Hinweis."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "ueber-uns.html").read_text(encoding="utf-8")
live = json.loads((ROOT / "data/content-live.json").read_text(encoding="utf-8"))

if "placeholder-vorstand" in html:
    raise SystemExit("Vorstand-Platzhalterbild muss fehlen")
if "ueber-uns.vorstand.note" in html:
    raise SystemExit("Hinweis unter dem Vorstand muss entfernt sein")
if 'src="images/vorstand.jpg"' not in html:
    raise SystemExit("Vorstandsfoto images/vorstand.jpg fehlt im HTML")
jpg = ROOT / "images/vorstand.jpg"
if not jpg.is_file():
    raise SystemExit("images/vorstand.jpg fehlt")
if jpg.stat().st_size > 400_000:
    raise SystemExit("vorstand.jpg soll web-tauglich komprimiert sein (< 400 KB)")
vorstand_pos = html.find('id="vorstand-heading"')
photo_pos = html.find('images/vorstand.jpg')
list_pos = html.find("ueber-uns.vorstand.person1")
if not (vorstand_pos < photo_pos < list_pos):
    raise SystemExit("Vorstandsfoto muss vor der Namensliste stehen")
if 'event-card__media aspect-[3/2]" data-lightbox' not in html:
    raise SystemExit("Vorstandsfoto braucht aspect-Ratio am Media-Container")
if "<strong>Rita Borner</strong>" not in html:
    raise SystemExit("Rita Borner muss fett im HTML stehen")
if "nicht im Bild" not in live["fields"]["ueber-uns.vorstand.person9"]:
    raise SystemExit("person9 braucht Hinweis «nicht im Bild» in live.json")
if live["fields"]["ueber-uns.vorstand.note"] != "":
    raise SystemExit("note muss leer sein")
for n in range(1, 10):
    key = f"ueber-uns.vorstand.person{n}"
    val = live["fields"].get(key, "")
    if "<strong>" not in val or "</strong>" not in val:
        raise SystemExit(f"{key} braucht fetten Namen in live.json")
    if val.strip().startswith("<br"):
        raise SystemExit(f"{key} darf nicht mit br beginnen")

merge = (ROOT / "scripts/merge-content-json.py").read_text(encoding="utf-8")
if "GIT_WINS_FIELD_IDS" not in merge:
    raise SystemExit("Deploy-Merge muss Vorstand aus Git erzwingen können")

if html.find('id="jahresbericht-heading"') == -1:
    raise SystemExit("Jahresbericht-Sektion fehlt")
if not (
    html.find('id="kontakt-heading"')
    < html.find('id="jahresbericht-heading"')
    < html.find('id="vorstand-heading"')
):
    raise SystemExit("Jahresbericht muss vor dem Vorstand stehen")
if 'href="dokumente/Jahresbericht-2025.pdf"' not in html or "Jahresbericht 2025" not in html:
    raise SystemExit("PDF-Download für Jahresbericht 2025 fehlt")
if 'href="dokumente/JB_2024_final.pdf"' not in html or "Jahresbericht 2024" not in html:
    raise SystemExit("PDF-Download für Jahresbericht 2024 fehlt")
if 'download="Jahresbericht-2025.pdf"' in html or 'download="Jahresbericht-2024.pdf"' in html:
    raise SystemExit("Jahresberichte müssen wie Statuten im PDF-Viewer öffnen")
if 'id="ueber-uns-statuten"' not in html:
    raise SystemExit("Statuten-Link oben auf Über uns fehlt")
statuten_start = html.rfind("<a ", 0, html.find('id="ueber-uns-statuten"'))
statuten_link = html[statuten_start : html.find("</a>", html.find('id="ueber-uns-statuten"'))]
if 'href="dokumente/Statuten.pdf"' not in statuten_link:
    raise SystemExit("Statuten-Link oben auf Über uns fehlt")
if not (
    html.find("<h1")
    < html.find('id="ueber-uns-statuten"')
    < html.find('id="kontakt-heading"')
):
    raise SystemExit("Statuten müssen oben rechts neben dem Intro stehen")
if "Jahresbericht-2025.pdf" not in (ROOT / "scripts/build-hostpoint-edit.sh").read_text(encoding="utf-8"):
    raise SystemExit("Vorschau-Build kopiert Jahresbericht-2025.pdf nicht")
if "JB_2024_final.pdf" not in (ROOT / "scripts/build-hostpoint-edit.sh").read_text(encoding="utf-8"):
    raise SystemExit("Vorschau-Build kopiert JB_2024_final.pdf nicht")
pdf = ROOT / "dokumente/Jahresbericht-2025.pdf"
if not pdf.is_file() or not pdf.read_bytes().startswith(b"%PDF"):
    raise SystemExit("dokumente/Jahresbericht-2025.pdf fehlt")
pdf24 = ROOT / "dokumente/JB_2024_final.pdf"
if not pdf24.is_file() or not pdf24.read_bytes().startswith(b"%PDF"):
    raise SystemExit("dokumente/JB_2024_final.pdf fehlt")

print("ueber uns vorstand ok")
