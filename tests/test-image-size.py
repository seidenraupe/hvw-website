#!/usr/bin/env python3
"""Website-Fotos bleiben unter einer üblichen Kantenlänge."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MAX_EDGE = 2000
SKIP = {"favicon.ico", "favicon-32.png", "favicon-192.png", "apple-touch-icon.png"}

for path in (ROOT / "images").rglob("*"):
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png"} or path.name in SKIP:
        continue
    with Image.open(path) as image:
        width, height = image.size
    if max(width, height) > MAX_EDGE:
        raise SystemExit(f"{path.relative_to(ROOT)} ist {width}x{height}, länger als {MAX_EDGE}px")

for name in ("sammlung-titelbild.jpg", "sammlung-ausstellung.jpg"):
    size = (ROOT / "images" / name).stat().st_size
    if size > 600_000:
        raise SystemExit(f"{name} ist {size} Bytes, grösser als für die Website nötig")

print("image size ok")
