#!/usr/bin/env python3
"""Tailwind liegt als gebautes CSS im Repo, nicht mehr als CDN-Skript."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "css/tailwind.css").read_text(encoding="utf-8")

SOURCES = list(ROOT.glob("*.html"))
for folder in ("coucou", "mus", "redaktion", "zugang", "js"):
    base = ROOT / folder
    SOURCES.extend(base.rglob("*.html"))
    SOURCES.extend(base.rglob("*.php"))
    SOURCES.extend(base.rglob("*.js"))

blob = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in SOURCES)
if "cdn.tailwindcss.com" in blob or "tailwind-config.js" in blob:
    raise SystemExit("Tailwind-CDN oder tailwind-config.js ist noch referenziert")
build = (ROOT / "scripts/build-hostpoint-soft-launch.sh").read_text(encoding="utf-8")
if "tailwind-config.js" in build or "css/tailwind.css" not in build:
    raise SystemExit("Soft-Launch-Build muss css/tailwind.css kopieren")
if ".max-w-site{" not in CSS or ".bg-hvw-ink{" not in CSS or ".text-base{" not in CSS:
    raise SystemExit("css/tailwind.css enthält die HVW-Utilities nicht")
if (ROOT / "js/tailwind-config.js").exists():
    raise SystemExit("js/tailwind-config.js gehört nicht mehr ins Repo")

CLASS_ATTR = re.compile(r"""class\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.S)
TOGGLE = re.compile(r"""classList\.(?:add|remove|toggle)\(\s*["']([^"']+)["']""")


def looks_like_utility(token: str) -> bool:
    if any(char in token for char in ":/[]"):
        return True
    prefixes = (
        "bg-", "text-", "font-", "border", "rounded", "px-", "py-", "pt-", "pb-",
        "pl-", "pr-", "mx-", "my-", "mt-", "mb-", "ml-", "mr-", "min-", "max-",
        "flex", "grid", "col-", "gap-", "space-", "items-", "justify-", "self-",
        "overflow-", "object-", "aspect-", "top-", "bottom-", "left-", "right-",
        "sr-", "inline", "list-", "underline", "no-underline", "decoration-",
        "uppercase", "italic", "antialiased", "tracking-", "leading-", "transition",
        "duration-", "outline-", "shadow", "order-", "shrink", "grow", "basis-",
        "scroll-", "whitespace-", "opacity-", "ring-", "cursor-", "pointer-events-",
        "place-", "columns-", "backdrop-",
    )
    exact = {
        "flex", "grid", "hidden", "block", "inline", "table", "underline", "italic",
        "uppercase", "antialiased", "sr-only", "static", "fixed", "sticky", "relative",
        "absolute", "container", "contents", "truncate", "filter", "blur",
        "p-2", "p-5", "p-6", "w-auto", "w-full", "h-12", "h-full", "z-40", "z-50",
    }
    if token in exact:
        return True
    if len(token) >= 2 and token[0] in "pmwhz" and token[1] == "-" and token[2:3].isdigit():
        return True
    return token.startswith(prefixes)


def escape_token(token: str) -> str:
    return "".join("\\" + char if char in "!:/[]#.%," else char for char in token)


missing = []
seen = set()
for match in list(CLASS_ATTR.finditer(blob)) + list(TOGGLE.finditer(blob)):
    raw = next(group for group in match.groups() if group)
    for token in raw.split():
        if token in seen or not looks_like_utility(token):
            seen.add(token)
            continue
        seen.add(token)
        if "." + escape_token(token) not in CSS:
            missing.append(token)

if missing:
    raise SystemExit("Klassen fehlen in css/tailwind.css: " + ", ".join(sorted(set(missing))))

print(f"tailwind static ok ({len(seen)} klassen)")
