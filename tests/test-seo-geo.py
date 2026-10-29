#!/usr/bin/env python3
"""SEO & GEO: sitemap.xml, robots.txt, Redirects und JSON-LD auf allen Hauptseiten."""
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://www.hvwinterthur.ch"

sitemap_path = ROOT / "sitemap.xml"
if not sitemap_path.is_file():
    raise SystemExit("sitemap.xml fehlt")

tree = ET.parse(sitemap_path)
ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
locs = [el.text.strip() for el in tree.findall(".//sm:url/sm:loc", ns) if el.text]
expected_urls = [
    f"{SITE}/",
    f"{SITE}/agenda.html",
    f"{SITE}/museen.html",
    f"{SITE}/lindengut.html",
    f"{SITE}/moersburg.html",
    f"{SITE}/sammlung.html",
    f"{SITE}/partner.html",
    f"{SITE}/ueber-uns.html",
    f"{SITE}/mitmachen.html",
    f"{SITE}/zitate.html",
    f"{SITE}/impressum.html",
    f"{SITE}/datenschutz.html",
]
for url in expected_urls:
    if url not in locs:
        raise SystemExit(f"sitemap.xml fehlt URL: {url}")

robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
if f"Sitemap: {SITE}/sitemap.xml" not in robots:
    raise SystemExit("robots.txt muss Sitemap referenzieren")

htaccess = (ROOT / ".htaccess").read_text(encoding="utf-8")
if "RewriteCond %{HTTP_HOST} ^hvwinterthur\\.ch$ [NC]" not in htaccess:
    raise SystemExit(".htaccess muss non-www auf www weiterleiten")
if "RewriteRule ^index\\.html$ https://www.hvwinterthur.ch/ [L,R=301]" not in htaccess:
    raise SystemExit(".htaccess muss /index.html auf / weiterleiten")

soft_build = (ROOT / "scripts/build-hostpoint-soft-launch.sh").read_text(encoding="utf-8")
if 'cp "${ROOT}/sitemap.xml" "${OUT}/sitemap.xml"' not in soft_build:
    raise SystemExit("build-hostpoint-soft-launch.sh muss sitemap.xml kopieren")

JSONLD_PAGES = [
    "index.html",
    "agenda.html",
    "museen.html",
    "lindengut.html",
    "moersburg.html",
    "sammlung.html",
    "partner.html",
    "ueber-uns.html",
    "mitmachen.html",
    "zitate.html",
]

for page in JSONLD_PAGES:
    html = (ROOT / page).read_text(encoding="utf-8")
    blocks = re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>',
        html,
        re.DOTALL,
    )
    if not blocks:
        raise SystemExit(f"{page}: JSON-LD fehlt")
    for block in blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{page}: ungültiges JSON-LD ({exc})") from exc
        if data.get("@context") != "https://schema.org":
            raise SystemExit(f"{page}: @context muss https://schema.org sein")

lindengut = (ROOT / "lindengut.html").read_text(encoding="utf-8")
if '"Römerstrasse 8"' not in lindengut or '"GeoCoordinates"' not in lindengut:
    raise SystemExit("lindengut.html braucht vollständige Adresse + GeoCoordinates im JSON-LD")

moersburg = (ROOT / "moersburg.html").read_text(encoding="utf-8")
if '"Mörsburgstrasse 30"' not in moersburg or '"GeoCoordinates"' not in moersburg:
    raise SystemExit("moersburg.html braucht vollständige Adresse + GeoCoordinates im JSON-LD")

mitmachen = (ROOT / "mitmachen.html").read_text(encoding="utf-8")
if '"OfferCatalog"' not in mitmachen or '"priceCurrency": "CHF"' not in mitmachen:
    raise SystemExit("mitmachen.html braucht OfferCatalog für Mitgliedschaften im JSON-LD")

print("seo-geo ok")
