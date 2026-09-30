#!/usr/bin/env python3
"""Outfit kommt lokal von @fontsource, nicht von Google Fonts."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

PAGES = [
    ("index.html", "css/fonts.css"),
    ("agenda.html", "css/fonts.css"),
    ("museen.html", "css/fonts.css"),
    ("lindengut.html", "css/fonts.css"),
    ("moersburg.html", "css/fonts.css"),
    ("sammlung.html", "css/fonts.css"),
    ("partner.html", "css/fonts.css"),
    ("ueber-uns.html", "css/fonts.css"),
    ("mitmachen.html", "css/fonts.css"),
    ("zitate.html", "css/fonts.css"),
    ("impressum.html", "css/fonts.css"),
    ("datenschutz.html", "css/fonts.css"),
    ("coucou/index.html", "../css/fonts.css"),
    ("mus/index.html", "../css/fonts.css"),
    ("redaktion/index.php", "../css/fonts.css"),
    ("redaktion/zugang.php", "../css/fonts.css"),
    ("deploy/hostpoint-soft-launch/impressum.html", "css/fonts.css"),
    ("deploy/hostpoint-soft-launch/datenschutz.html", "css/fonts.css"),
    ("deploy/hostpoint-soft-launch/coucou/index.html", "../css/fonts.css"),
    ("deploy/hostpoint-soft-launch/mus/index.html", "../css/fonts.css"),
]

SCAN = [
    *ROOT.glob("*.html"),
    *ROOT.glob("*/*.html"),
    *ROOT.glob("*/*.php"),
    *ROOT.glob("*/*/*.html"),
    *ROOT.glob("*/*/*.php"),
    ROOT / "css/fonts.css",
    ROOT / "css/site.css",
    ROOT / "zugang/serve.php",
]

GOOGLE = ("fonts.googleapis.com", "fonts.gstatic.com")
WEIGHTS = (400, 500, 600, 700)
SUBSETS = ("latin", "latin-ext")


def fail(msg: str) -> None:
    raise SystemExit(msg)


for path in SCAN:
    if not path.is_file() or "node_modules" in path.parts:
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    for needle in GOOGLE:
        if needle in text:
            fail(f"{path.relative_to(ROOT)} verweist noch auf {needle}")

for rel, href in PAGES:
    html = (ROOT / rel).read_text(encoding="utf-8")
    if f'href="{href}"' not in html:
        fail(f"{rel} bindet {href} nicht ein")

serve = (ROOT / "zugang/serve.php").read_text(encoding="utf-8")
if "css/fonts.css" not in serve:
    fail("zugang/serve.php bindet die lokale Schrift nicht ein")

css = (ROOT / "css/fonts.css").read_text(encoding="utf-8")
for subset in SUBSETS:
    for weight in WEIGHTS:
        name = f"outfit-{subset}-{weight}-normal.woff2"
        if name not in css:
            fail(f"css/fonts.css nennt {name} nicht")
        if not (ROOT / "fonts/outfit" / name).is_file():
            fail(f"fonts/outfit/{name} fehlt")
if css.count("@font-face") != 8:
    fail("css/fonts.css braucht acht Schnitte")
if 'font-family: "Outfit"' not in css:
    fail("Schriftfamilie Outfit fehlt")

for rel in ("datenschutz.html", "deploy/hostpoint-soft-launch/datenschutz.html"):
    text = (ROOT / rel).read_text(encoding="utf-8")
    if "Google Fonts" in text or "Schriftarten von Google" in text:
        fail(f"{rel} erwähnt Google Fonts noch")

soft = (ROOT / "scripts/build-hostpoint-soft-launch.sh").read_text(encoding="utf-8")
if "css/fonts.css" not in soft or "fonts/outfit" not in soft:
    fail("Soft-Launch kopiert die lokalen Schriften nicht")
preview = (ROOT / "scripts/build-hostpoint-edit.sh").read_text(encoding="utf-8")
if 'copy_dir "${ROOT}/fonts"' not in preview:
    fail("Vorschau kopiert fonts/ nicht")

urls = re.findall(r'url\("([^"]+)"\)', css)
for url in urls:
    target = (ROOT / "css" / url).resolve()
    if not target.is_file():
        fail(f"Schrift-URL zeigt ins Leere: {url}")

print("local fonts ok")
