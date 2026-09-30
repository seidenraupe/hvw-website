#!/usr/bin/env python3
"""Stamm-URL: keine Weiterleitung zur alten Vereinsdomain, volles Root-Paket."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
htaccess = (ROOT / ".htaccess").read_text(encoding="utf-8")
build = (ROOT / "scripts/build-hostpoint-soft-launch.sh").read_text(encoding="utf-8")
index = (ROOT / "index.html").read_text(encoding="utf-8")
robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")

if "https://www.historischer-verein-winterthur.ch" in htaccess:
    raise SystemExit("Root-.htaccess darf nicht zur alten Domain weiterleiten")
if "historischer-verein-winterthur" in htaccess and "www.hvwinterthur.ch%{REQUEST_URI}" not in htaccess:
    raise SystemExit("Legacy-Host in .htaccess muss per 301 auf www.hvwinterthur.ch zeigen")
if "historischer-verein-winterthur.ch" in build:
    raise SystemExit("Root-Build darf keine Redirect-index.html erzeugen")
if 'content="noindex,nofollow"' in index:
    raise SystemExit("index.html soll indexierbar sein")
if "index.html agenda.html" not in build:
    raise SystemExit("Root-Build muss alle öffentlichen HTML-Seiten kopieren")
if "Disallow: /edit/" not in robots:
    raise SystemExit("robots.txt muss /edit/ sperren")
for line in robots.splitlines():
    if line.strip() == "Disallow: /":
        raise SystemExit("robots.txt darf die Stamm-URL nicht pauschal sperren")
if "target}data/content-live.json" not in deploy:
    raise SystemExit("Deploy muss content-live.json auf die Stamm-URL syncen")

print("golive-root ok")
