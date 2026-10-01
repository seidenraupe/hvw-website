#!/usr/bin/env python3
"""Go-Live-Vorbereitung: /vorschau/ → /edit/ mit gleichen Funktionen."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
htaccess = (ROOT / ".htaccess").read_text(encoding="utf-8")
edit_ht = (ROOT / "deploy/edit.htaccess").read_text(encoding="utf-8")
deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
build = (ROOT / "scripts/build-hostpoint-edit.sh").read_text(encoding="utf-8")
robots = (ROOT / "robots.txt").read_text(encoding="utf-8")

if not (ROOT / "deploy/edit.htaccess").is_file():
    raise SystemExit("deploy/edit.htaccess fehlt")
if (ROOT / "deploy/vorschau.htaccess").exists():
    raise SystemExit("deploy/vorschau.htaccess darf nicht mehr existieren")
if (ROOT / "scripts/build-hostpoint-vorschau.sh").exists():
    raise SystemExit("build-hostpoint-vorschau.sh wurde durch build-hostpoint-edit.sh ersetzt")

if "RewriteBase /edit/" not in edit_ht:
    raise SystemExit("edit.htaccess braucht RewriteBase /edit/")
if "RewriteRule ^vorschau/?$ /edit/" not in htaccess:
    raise SystemExit("Root-.htaccess muss /vorschau/ nach /edit/ weiterleiten")
if 'exclude \'edit/\'' not in deploy:
    raise SystemExit("Soft-Launch-Deploy muss edit/ ausschliessen")
if "deploy/hostpoint-edit/" not in deploy or "target}edit/" not in deploy:
    raise SystemExit("Deploy muss nach /edit/ rsyncen")
if "exclude 'vorschau/'" not in deploy:
    raise SystemExit("Soft-Launch-Deploy muss vorschau/ als Server-Backup ausschliessen")
if "restore-edit-from-vorschau.sh" not in deploy:
    raise SystemExit("Deploy muss Redaktionsdaten aus /vorschau/ nach /edit/ kopieren")
if "rm -rf '${target}vorschau'" in deploy:
    raise SystemExit("Deploy darf /vorschau/ auf dem Server nicht löschen (Daten-Backup)")
if "hostpoint-edit" not in build:
    raise SystemExit("Edit-Build-Skript fehlt Ziel hostpoint-edit")
if "Disallow: /edit/" not in robots:
    raise SystemExit("robots.txt muss /edit/ sperren")

print("edit-path ok")
