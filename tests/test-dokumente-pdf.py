#!/usr/bin/env python3
"""Alle Website-PDFs liegen unter dokumente/; Links und Deploy kopieren dorthin."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOK = ROOT / "dokumente"
EXPECTED = {
    "Statuten.pdf",
    "Sammlungskonzept.pdf",
    "Jahresbericht-2025.pdf",
    "JB_2024_final.pdf",
    "Programm.pdf",
    "historische-privat-fuehrungen.pdf",
    "szenische-fuehrung-berta.pdf",
}

found = {p.name for p in DOK.glob("*.pdf")}
if found != EXPECTED:
    raise SystemExit(f"dokumente/*.pdf: erwartet {sorted(EXPECTED)}, gefunden {sorted(found)}")

for name in ("Statuten.pdf", "Sammlungskonzept.pdf", "Jahresbericht-2025.pdf", "JB_2024_final.pdf"):
    if (ROOT / name).exists():
        raise SystemExit(f"{name} darf nicht mehr im Repo-Root liegen")
if (ROOT / "programm" / "Programm.pdf").exists():
    raise SystemExit("programm/Programm.pdf wurde nach dokumente/ verschoben")

agenda = (ROOT / "agenda.html").read_text(encoding="utf-8")
if 'href="dokumente/Programm.pdf"' not in agenda:
    raise SystemExit("Agenda muss dokumente/Programm.pdf verlinken")

ueber = (ROOT / "ueber-uns.html").read_text(encoding="utf-8")
for part in ("dokumente/Statuten.pdf", "dokumente/Jahresbericht-2025.pdf", "dokumente/JB_2024_final.pdf"):
    if part not in ueber:
        raise SystemExit(f"ueber-uns.html fehlt Link {part}")

htaccess = (ROOT / ".htaccess").read_text(encoding="utf-8")
for rule in (
    "RewriteRule ^Statuten\\.pdf$ /dokumente/Statuten.pdf",
    "RewriteRule ^programm/Programm\\.pdf$ /dokumente/Programm.pdf",
):
    if rule not in htaccess:
        raise SystemExit(f".htaccess fehlt Weiterleitung: {rule}")

build = (ROOT / "scripts/build-hostpoint-edit.sh").read_text(encoding="utf-8")
if "dokumente/${pdf}" not in build:
    raise SystemExit("Vorschau-Build kopiert dokumente/ nicht einheitlich")

print("dokumente-pdf ok")
