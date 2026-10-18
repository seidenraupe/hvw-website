#!/usr/bin/env python3
"""Agenda-Programm-PDF: Button, Dateiname, Deploy und Auslieferung."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
agenda = (ROOT / "agenda.html").read_text(encoding="utf-8")
htaccess = (ROOT / ".htaccess").read_text(encoding="utf-8")
vorschau = (ROOT / "deploy/edit.htaccess").read_text(encoding="utf-8")
deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
deploy_cron = (ROOT / ".github/workflows/deploy-cronjobs.yml").read_text(
    encoding="utf-8"
)
cron_readme = (ROOT / "cronjobs/README.md").read_text(encoding="utf-8")
preview = (ROOT / "scripts/build-hostpoint-edit.sh").read_text(encoding="utf-8")

if "Alle Anlässe zum Herunterladen oder Ausdrucken" not in agenda:
    raise SystemExit("Download-Button-Text fehlt")
if 'href="dokumente/Programm.pdf"' not in agenda:
    raise SystemExit("Button muss auf dokumente/Programm.pdf zeigen")
if "download=" in agenda.split('href="dokumente/Programm.pdf"', 1)[-1].split("</a>", 1)[0]:
    raise SystemExit("Programm-PDF darf kein download-Attribut haben (wie Statuten im Viewer öffnen)")
if "data-programm-download" in agenda:
    raise SystemExit("Programm-Link darf download nicht per JS erzwingen")
if "js/programm-download.js" in agenda:
    raise SystemExit("Agenda darf programm-download.js nicht mehr laden")
if not (ROOT / "dokumente/Programm.pdf").is_file():
    raise SystemExit("dokumente/Programm.pdf fehlt")
if not (ROOT / "programm/Programm.json").is_file():
    raise SystemExit("programm/Programm.json fehlt")
if "generate-programm-pdf.py" not in deploy:
    raise SystemExit("Deploy muss das Programm-PDF erzeugen")
if "eventfrog_to_programm_pdf.py" not in deploy_cron:
    raise SystemExit("deploy-cronjobs muss Programm-PDF-Cron testen")
if "eventfrog_to_programm_pdf.py" not in cron_readme:
    raise SystemExit("cronjobs/README muss Programm-PDF-Cron dokumentieren")
if not (ROOT / "cronjobs/eventfrog_to_programm_pdf.py").is_file():
    raise SystemExit("cronjobs/eventfrog_to_programm_pdf.py fehlt")
if 'copy_dir "${ROOT}/programm"' not in preview:
    raise SystemExit("Vorschau-Build muss programm/ kopieren")
if "RewriteRule ^programm/ - [G,L]" in htaccess:
    raise SystemExit("Root-.htaccess darf das PDF nicht mit 410 blockieren")
if "RewriteRule ^programm(/|$) - [G,L]" in vorschau:
    raise SystemExit("Vorschau-.htaccess darf /programm nicht mit 410 blockieren")
print("programm download ok")
