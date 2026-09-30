#!/usr/bin/env python3
"""Jede öffentliche Seite hat vollständige Open-Graph-Daten."""
from pathlib import Path
import re

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://www.hvwinterthur.ch"

REQUIRED = (
    "og:type",
    "og:locale",
    "og:site_name",
    "og:title",
    "og:description",
    "og:url",
    "og:image",
    "og:image:width",
    "og:image:height",
    "og:image:alt",
)

PAGES = [
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
    "impressum.html",
    "datenschutz.html",
    "coucou/index.html",
    "mus/index.html",
]

SOFT_LAUNCH = [
    "deploy/hostpoint-soft-launch/impressum.html",
    "deploy/hostpoint-soft-launch/datenschutz.html",
    "deploy/hostpoint-soft-launch/coucou/index.html",
    "deploy/hostpoint-soft-launch/mus/index.html",
]


def meta_map(html: str) -> dict[str, str]:
    found = {}
    for match in re.finditer(
        r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"',
        html,
    ):
        found[match.group(1)] = match.group(2)
    return found


def canonical(html: str) -> str:
    match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    if not match:
        raise SystemExit("canonical fehlt")
    return match.group(1)


def check(rel: str) -> None:
    path = ROOT / rel
    html = path.read_text(encoding="utf-8")
    tags = meta_map(html)
    for key in REQUIRED:
        if not tags.get(key, "").strip():
            raise SystemExit(f"{rel}: {key} fehlt oder ist leer")
    if tags["og:type"] != "website":
        raise SystemExit(f"{rel}: og:type muss website sein")
    if tags["og:locale"] != "de_CH":
        raise SystemExit(f"{rel}: og:locale muss de_CH sein")
    if tags["og:site_name"] != "Historischer Verein Winterthur":
        raise SystemExit(f"{rel}: og:site_name stimmt nicht")
    if tags.get("twitter:card") != "summary_large_image":
        raise SystemExit(f"{rel}: twitter:card fehlt")
    url = canonical(html)
    if tags["og:url"] != url:
        raise SystemExit(f"{rel}: og:url weicht von canonical ab ({tags['og:url']} != {url})")
    if not url.startswith(SITE):
        raise SystemExit(f"{rel}: canonical zeigt nicht auf {SITE}")
    image = tags["og:image"]
    if not image.startswith(f"{SITE}/images/"):
        raise SystemExit(f"{rel}: og:image ist keine absolute Bild-URL ({image})")
    image_path = ROOT / image.removeprefix(SITE + "/")
    if not image_path.is_file():
        raise SystemExit(f"{rel}: Bilddatei fehlt ({image_path})")
    width = int(tags["og:image:width"])
    height = int(tags["og:image:height"])
    if Image is not None:
        with Image.open(image_path) as im:
            actual = im.size
        if (width, height) != actual:
            raise SystemExit(f"{rel}: Bildmasse {width}x{height}, Datei ist {actual[0]}x{actual[1]}")
    if '"' in tags["og:description"] or "<" in tags["og:description"]:
        raise SystemExit(f"{rel}: og:description enthält ungültige Zeichen")


for page in PAGES + SOFT_LAUNCH:
    check(page)

redirect = (ROOT / "deploy/hostpoint-soft-launch/index.html").read_text(encoding="utf-8")
if "og:title" in redirect:
    raise SystemExit("Soft-Launch-Startseite ist nur eine Weiterleitung und braucht keine Open-Graph-Daten")

print("open graph ok")
