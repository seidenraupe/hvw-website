#!/usr/bin/env python3
"""Import interview statements + portraits from historymatters.ch into data/stimmen.json."""
from __future__ import annotations

import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://historymatters.ch/interviews-2-2-2/"
OUT_JSON = ROOT / "data" / "stimmen.json"
IMG_DIR = ROOT / "images" / "stimmen"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0
        self._skip = {"script", "style", "noscript"}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip:
            self.skip += 1
        if tag == "br" and not self.skip:
            self.parts.append("\n")
        if tag in ("p", "h1", "h2", "h3", "h4", "li", "div") and not self.skip:
            self.parts.append("\n")
        if tag == "img" and not self.skip:
            data = dict(attrs)
            src = data.get("src") or data.get("data-src") or ""
            if (
                src
                and "wp-content/uploads" in src
                and re.search(r"/20\d{2}/", src)
                and not any(x in src for x in ("hvw_", "museumschaffen", "cropped-H", "dynamic_avia", "/H.png"))
            ):
                self.parts.append(f"\n<<<IMG:{src}>>>\n")

    def handle_endtag(self, tag):
        if tag in self._skip and self.skip:
            self.skip -= 1
        if tag in ("p", "h1", "h2", "h3", "h4", "li") and not self.skip:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def slugify(name: str) -> str:
    slug = (
        name.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    return re.sub(r"[^a-z0-9]+", "-", slug).strip("-")


def download(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 HVW-prototype"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        return data if len(data) >= 500 else None
    except Exception as exc:  # noqa: BLE001
        print(f"fail {url}: {exc}")
        return None


def main() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    html = download(SOURCE_URL)
    if not html:
        raise SystemExit(f"Could not fetch {SOURCE_URL}")
    parser = TextExtractor()
    parser.feed(html.decode("utf-8", errors="ignore"))
    text = re.sub(r"[ \t]+", " ", "".join(parser.parts))
    text = re.sub(r"\n{3,}", "\n\n", text)

    start = text.find("<<<IMG:")
    end_candidates = [
        text.find("\nRömerstrasse"),
        text.find("Instagram History Matters"),
        text.find("gestaltung claudia"),
    ]
    end = min(c for c in end_candidates if c != -1)
    body = text[start:end]
    chunks = re.split(r"<<<IMG:(https://[^>]+?)>>>", body)

    people = []
    q_re = re.compile(
        r"(?:History Matters – )?Warum ist Geschichte für Winterthur wichtig\?"
        r"|Was bedeutet Geschichte für Sie persönlich\?"
        r"|Was wünschen Sie dem Historischen Verein(?: für die nächsten 150 Jahre| Winterthur)\?"
    )

    for i in range(1, len(chunks), 2):
        img_url = chunks[i].strip()
        content = chunks[i + 1].strip() if i + 1 < len(chunks) else ""
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        if not lines:
            continue
        header = lines[0].replace("Caspar HIrschi", "Caspar Hirschi")
        if "," in header:
            name, role = header.split(",", 1)
            name, role = name.strip(), role.strip()
        else:
            name, role = header.strip(), ""

        joined = "\n".join(lines[1:])
        parts = q_re.split(joined)
        questions = q_re.findall(joined)
        statements = []
        for question, answer in zip(questions, parts[1:]):
            qn = question.replace("History Matters – ", "")
            ans = re.sub(r"\s+", " ", answer).strip()
            ans = re.sub(r"\s+zurück$", "", ans)
            ans = ans.replace("am wichtigsten Geschichte kann", "am wichtigsten: Geschichte kann")
            if ans:
                statements.append({"question": qn, "text": ans})

        slug = slugify(name)
        local_name = ""
        match = re.match(r"(.+?)(-\d+x\d+)?(\.[a-zA-Z]+)$", img_url)
        if match:
            stem, ext = match.group(1), match.group(3)
            candidates = [f"{stem}-300x300{ext}", f"{stem}{ext}", img_url]
        else:
            candidates = [img_url]

        for url in dict.fromkeys(candidates):
            blob = download(url)
            if not blob:
                continue
            ext = Path(url.split("?")[0]).suffix.lower() or ".jpg"
            local_name = f"{slug}{ext}"
            (IMG_DIR / local_name).write_bytes(blob)
            print(f"OK {name}: {local_name}")
            break

        people.append(
            {
                "id": slug,
                "name": name,
                "role": role,
                "image": f"images/stimmen/{local_name}" if local_name else "images/placeholder-quote.svg",
                "statements": statements,
                "featuredQuote": statements[0]["text"] if statements else "",
            }
        )

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"source": SOURCE_URL, "people": people}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(people)} people to {OUT_JSON}")


if __name__ == "__main__":
    main()
