#!/usr/bin/env python3
"""Sammlung: Button öffnet das Sammlungskonzept, PDF trägt das HVW-Logo."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
html = (ROOT / "sammlung.html").read_text(encoding="utf-8")
if 'href="dokumente/Sammlungskonzept.pdf"' not in html:
    raise SystemExit("Button-Link auf dokumente/Sammlungskonzept.pdf fehlt")
if "Kulturerbe-Portal" in html or "www.zh.ch" in html or "Digitaler Katalog" in html:
    raise SystemExit("Kulturerbe-Link oder Katalog-Erklärung ist noch auf der Seite")
if html.count('href="dokumente/Sammlungskonzept.pdf"') != 1:
    raise SystemExit("Es soll genau eine Box zum Sammlungskonzept geben")

pdf = (ROOT / "dokumente/Sammlungskonzept.pdf").read_bytes()
if b"/Subtype/Image" not in pdf and b"/Subtype /Image" not in pdf:
    raise SystemExit("PDF enthält kein Logo-Bild")

build = (ROOT / "scripts/build-hostpoint-vorschau.sh").read_text(encoding="utf-8")
if "dokumente/${pdf}" not in build and "dokumente/" not in build:
    raise SystemExit("Vorschau-Build kopiert dokumente/ nicht")
print("sammlungskonzept ok")
