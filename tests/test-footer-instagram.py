#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
URL = "https://www.instagram.com/hvwinterthur/"
pages = list(ROOT.glob("*.html")) + [ROOT / "coucou/index.html", ROOT / "mus/index.html"]
missing = []
for path in pages:
    html = path.read_text(encoding="utf-8")
    if "<footer" not in html:
        continue
    if URL not in html or "@hvwinterthur" not in html or "Instagram" not in html:
        missing.append(path.name)
    if 'class="hvw-ig' not in html or "<svg" not in html.split("hvw-ig", 1)[-1][:800]:
        missing.append(path.name + " (Logo)")
if missing:
    raise SystemExit("Instagram-Footer fehlt auf: " + ", ".join(missing))
index = (ROOT / "index.html").read_text(encoding="utf-8")
if URL not in index.split('"sameAs"')[1].split("]")[0]:
    raise SystemExit("sameAs in index.html muss Instagram enthalten")
print("footer instagram ok")
