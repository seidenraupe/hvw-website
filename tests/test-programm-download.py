#!/usr/bin/env python3
"""Agenda-Programm-PDF: Button, Dateiname, Deploy und Auslieferung."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
agenda = (ROOT / "agenda.html").read_text(encoding="utf-8")
htaccess = (ROOT / ".htaccess").read_text(encoding="utf-8")
vorschau = (ROOT / "deploy/vorschau.htaccess").read_text(encoding="utf-8")
deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
soft = (ROOT / "scripts/build-hostpoint-soft-launch.sh").read_text(encoding="utf-8")
preview = (ROOT / "scripts/build-hostpoint-vorschau.sh").read_text(encoding="utf-8")

if 'data-programm-download' not in agenda:
    raise SystemExit("Agenda braucht den Programm-Download-Button")
if "Alle Anlässe zum Herunterladen oder Ausdrucken" not in agenda:
    raise SystemExit("Download-Button-Text fehlt")
if 'href="/programm/Programm.pdf"' not in agenda:
    raise SystemExit("Button muss auf /programm/Programm.pdf zeigen")
if "js/programm-download.js" not in agenda:
    raise SystemExit("Agenda muss programm-download.js laden")
if not (ROOT / "js/programm-download.js").is_file():
    raise SystemExit("js/programm-download.js fehlt")
if not (ROOT / "programm/Programm.pdf").is_file():
    raise SystemExit("programm/Programm.pdf fehlt")
if not (ROOT / "programm/Programm.json").is_file():
    raise SystemExit("programm/Programm.json fehlt")
if "generate-programm-pdf.py" not in deploy:
    raise SystemExit("Deploy muss das Programm-PDF erzeugen")
if 'copy_dir "${ROOT}/programm"' not in preview:
    raise SystemExit("Vorschau-Build muss programm/ kopieren")
if "programm-download.js" not in soft:
    raise SystemExit("Soft-Launch muss programm-download.js mitliefern")
if "RewriteRule ^programm/ - [G,L]" in htaccess:
    raise SystemExit("Root-.htaccess darf das PDF nicht mit 410 blockieren")
if "RewriteRule ^programm(/|$) - [G,L]" in vorschau:
    raise SystemExit("Vorschau-.htaccess darf /programm nicht mit 410 blockieren")
print("programm download ok")
