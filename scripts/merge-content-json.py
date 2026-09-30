#!/usr/bin/env python3
"""Merge Git-Startwerte mit Server-Texten: bestehende Redaktion gewinnt."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def field_map(data: dict[str, Any]) -> dict[str, str]:
    fields = data.get("fields")
    if not isinstance(fields, dict):
        return {}
    return {str(k): "" if v is None else str(v) for k, v in fields.items()}


def schema_ids(schema: dict[str, Any]) -> list[str]:
    fields = schema.get("fields")
    if not isinstance(fields, dict):
        return []
    return [str(k) for k in fields.keys()]


# Bei Deploy: diese Felder aus Git (Seed) erzwingen — z. B. Formatierung der Vorstand-Legende.
GIT_WINS_FIELD_IDS = {
    "ueber-uns.vorstand.caption",
    "ueber-uns.vorstand.note",
    *(f"ueber-uns.vorstand.person{n}" for n in range(1, 10)),
}

# Redaktionell gepflegte Karten: nie per INITIAL_SEED-Reset überschreiben.
EDITORIAL_PREFIXES = ("sammlung.objekt.", "agenda.rueckblick.", "lindengut.", "moersburg.", "partner.")

# Zu wenig Remote-Daten → kein Live-Reset aus Git (verhindert Datenverlust bei fehlendem rsync).
MIN_REMOTE_FIELD_COUNT = 10


def is_editorial_content_field(field_id: str) -> bool:
    return field_id.startswith(EDITORIAL_PREFIXES)


def apply_deploy_overrides(
    live: dict[str, str],
    ids: list[str],
    seed: dict[str, str],
    remote_draft: dict[str, str],
) -> tuple[dict[str, str], dict[str, int]]:
    out = dict(live)
    forced = 0
    for field_id in GIT_WINS_FIELD_IDS:
        if field_id not in ids or field_id not in seed:
            continue
        out[field_id] = seed[field_id]
        forced += 1
    promoted = 0
    for field_id in ids:
        if not is_editorial_content_field(field_id):
            continue
        if out.get(field_id, "").strip():
            continue
        draft_v = remote_draft.get(field_id, "")
        if not draft_v.strip():
            continue
        out[field_id] = draft_v
        promoted += 1
    return out, {"forced_from_git": forced, "promoted_from_draft": promoted}


def merge_live_fields(
    ids: list[str],
    seed: dict[str, str],
    remote: dict[str, str],
    remote_draft: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, int]]:
    """Remote gewinnt, sobald ein Feld dort existiert. Seed nur für neue IDs."""
    out = dict(remote)
    added = 0
    kept = 0
    for field_id in ids:
        if field_id in remote:
            out[field_id] = remote[field_id]
            kept += 1
        else:
            out[field_id] = seed.get(field_id, "")
            added += 1
    remote_draft = remote_draft or {}
    out, override_stats = apply_deploy_overrides(out, ids, seed, remote_draft)
    split_house_hours(out, remote)
    link_moersburg_tours(out)
    ensure_moersburg_member_admission(out)
    return out, {
        "kept": kept,
        "added": added,
        "extra": max(0, len(remote) - kept),
        **override_stats,
    }


def norm_text(value: str) -> str:
    return " ".join(str(value or "").split())


def split_opening_hours(text: str) -> tuple[str, str] | None:
    """Trennt einen Lead, der noch den Block «Öffnungszeiten» enthält."""
    match = re.search(r"(?:^|<br\s*/?>|\n)\s*(Öffnungszeiten\b)", text, flags=re.IGNORECASE)
    if not match:
        return None
    lead = re.sub(r"(?:\s|<br\s*/?>)+$", "", text[: match.start()], flags=re.IGNORECASE).strip()
    hours = text[match.start(1) :].strip()
    if not lead or not hours:
        return None
    return lead, hours


TOUR_PDF_LINKS = (
    ("öffentliche Führungen", "dokumente/szenische-fuehrung-berta.pdf"),
    ("oeffentliche Führungen", "dokumente/szenische-fuehrung-berta.pdf"),
    ("Private Führungen", "dokumente/historische-privat-fuehrungen.pdf"),
)


def link_tour_phrase(html: str, phrase: str, href: str) -> str:
    """Hängt eine PDF-Adresse an eine Formulierung, ohne bestehende Links zu doppeln."""
    words = [re.escape(part) for part in phrase.split()]
    pattern = re.compile(
        r"(<a\b[^>]*>.*?</a>)|(" + r"\s+".join(words) + r")",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        if match.group(1):
            return match.group(1)
        return (
            f'<a href="{href}" target="_blank" rel="noopener noreferrer">{match.group(2)}</a>'
        )

    return pattern.sub(repl, html)


def ensure_moersburg_member_admission(fields: dict[str, str]) -> None:
    """Kultur-Legi statt reduziertem Preis, plus Gratis-Hinweis für Mitglieder."""
    text = fields.get("moersburg.oeffnung", "")
    if not text:
        return
    text = re.sub(
        r"reduziert\s+CHF\s*3(?:\.(?:–|-))?",
        "mit Kultur-Legi CHF 2.50",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    if "HVW-Mitglieder" not in text:
        text, count = re.subn(
            r"(CHF\s*2\.50|CHF\s*3\.(?:–|-))(?!\s*,\s*für\s+HVW-Mitglieder)",
            r"\1, für HVW-Mitglieder gratis",
            text,
            count=1,
        )
        if not count:
            return
    fields["moersburg.oeffnung"] = text


def link_moersburg_tours(fields: dict[str, str]) -> None:
    for field_id in ("moersburg.lead", "moersburg.oeffnung", "moersburg.body"):
        text = fields.get(field_id, "")
        if not text:
            continue
        updated = text
        for phrase, href in TOUR_PDF_LINKS:
            updated = link_tour_phrase(updated, phrase, href)
        fields[field_id] = updated


def split_house_hours(fields: dict[str, str], already_present: dict[str, str]) -> None:
    for key in ("lindengut", "moersburg"):
        hours_id = f"{key}.oeffnung"
        lead_id = f"{key}.lead"
        if hours_id not in fields or lead_id not in fields:
            continue
        if hours_id in already_present:
            continue
        parts = split_opening_hours(fields.get(lead_id, ""))
        if not parts:
            continue
        fields[lead_id], fields[hours_id] = parts


# Neue data-content-Felder vom 30.08.2026: Startwerte, keine Redaktionsarbeit.
# Entwurf nur zurücksetzen, wenn der Text noch dem Seed/Live entspricht
# (inkl. reiner HTML-Leerzeichen). Andere Entwurfsfelder bleiben unangetastet.
INITIAL_SEED_FIELD_IDS = {
    "agenda.intro",
    "agenda.rueckblick.intro",
    "mitmachen.intro",
    "mitmachen.anmeldung.lead",
    "sammlung.intro",
    "zitate.intro",
}


def looks_like_initial_seed(draft_val: str, live_val: str, seed_val: str) -> bool:
    draft_n = norm_text(draft_val)
    return draft_n == "" or draft_n == norm_text(live_val) or draft_n == norm_text(seed_val)


def merge_draft_fields(
    ids: list[str],
    live: dict[str, str],
    remote_draft: dict[str, str],
    seed: dict[str, str] | None = None,
) -> dict[str, str]:
    seed = seed or {}
    out = dict(remote_draft)
    for field_id in ids:
        live_val = live.get(field_id, "")
        if field_id in GIT_WINS_FIELD_IDS:
            out[field_id] = live_val
            continue
        if field_id not in remote_draft:
            out[field_id] = live_val
            continue
        draft_val = remote_draft[field_id]
        if field_id in INITIAL_SEED_FIELD_IDS and looks_like_initial_seed(
            draft_val, live_val, seed.get(field_id, "")
        ):
            out[field_id] = live_val
        else:
            out[field_id] = draft_val
    split_house_hours(out, remote_draft)
    link_moersburg_tours(out)
    return out


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def selftest() -> None:
    ids = ["a", "b", "c"]
    seed = {"a": "seed-a", "b": "seed-b", "c": "seed-c", "gone": "x"}
    remote = {"a": "redaktion-a", "gone": "keep-me"}
    live, stats = merge_live_fields(ids, seed, remote)
    assert live["a"] == "redaktion-a", live
    assert live["b"] == "seed-b", live
    assert live["c"] == "seed-c", live
    assert live["gone"] == "keep-me", live
    assert stats["kept"] == 1 and stats["added"] == 2, stats

    draft = merge_draft_fields(ids, live, {"a": "entwurf-a"})
    assert draft["a"] == "entwurf-a"
    assert draft["b"] == "seed-b"
    assert draft["c"] == "seed-c"

    seed_intro = "Alle Veranstaltungen des Historischen Vereins Winterthur."
    live_intro = seed_intro
    html_intro = "  Alle Veranstaltungen\n          des Historischen Vereins Winterthur.  "
    draft_reset = merge_draft_fields(
        ["agenda.intro", "ueber-uns.intro"],
        {"agenda.intro": live_intro, "ueber-uns.intro": "Vorstand überarbeitet."},
        {
            "agenda.intro": html_intro,
            "ueber-uns.intro": "Vorstand überarbeitet — Entwurf.",
        },
        {"agenda.intro": seed_intro, "ueber-uns.intro": "Alter Startwert."},
    )
    assert draft_reset["agenda.intro"] == live_intro
    assert draft_reset["ueber-uns.intro"] == "Vorstand überarbeitet — Entwurf."
    print("selftest ok")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--seed", type=Path, help="content-live.json aus Git")
    parser.add_argument("--remote-live", type=Path)
    parser.add_argument("--remote-draft", type=Path)
    parser.add_argument("--out-live", type=Path)
    parser.add_argument("--out-draft", type=Path)
    args = parser.parse_args()

    if args.selftest:
        selftest()
        return 0

    if not args.schema or not args.seed or not args.out_live:
        parser.error("--schema, --seed und --out-live sind nötig")

    ids = schema_ids(load_json(args.schema))
    seed_doc = load_json(args.seed)
    remote_live_doc = load_json(args.remote_live)
    remote_draft_doc = load_json(args.remote_draft) if args.remote_draft else {}
    seed_fields = field_map(seed_doc)
    remote_live = field_map(remote_live_doc)
    remote_draft = field_map(remote_draft_doc)

    if len(remote_live) < MIN_REMOTE_FIELD_COUNT:
        print(
            f"content-live merge: Remote zu klein ({len(remote_live)} Felder) — "
            "kein Zurücksetzen aus Git; nur fehlende Felder ergänzen und Overrides.",
            file=sys.stderr,
        )
        live_fields = dict(remote_live)
        added = 0
        for field_id in ids:
            if field_id not in live_fields:
                live_fields[field_id] = seed_fields.get(field_id, "")
                added += 1
        live_fields, override_stats = apply_deploy_overrides(
            live_fields, ids, seed_fields, remote_draft
        )
        split_house_hours(live_fields, remote_live)
        link_moersburg_tours(live_fields)
        stats = {
            "kept": len(remote_live),
            "added": added,
            "extra": 0,
            **override_stats,
        }
    else:
        live_fields, stats = merge_live_fields(
            ids, seed_fields, remote_live, remote_draft
        )

    live_out = dict(remote_live_doc) if remote_live_doc else dict(seed_doc)
    live_out["fields"] = live_fields
    if "updatedAt" not in live_out and seed_doc.get("updatedAt"):
        live_out["updatedAt"] = seed_doc["updatedAt"]
    write_json(args.out_live, live_out)

    if args.out_draft:
        draft_fields = merge_draft_fields(
            ids, live_fields, remote_draft, seed_fields
        )
        draft_out = dict(remote_draft_doc) if remote_draft_doc else {}
        draft_out.setdefault("status", "clean")
        draft_out["fields"] = draft_fields
        write_json(args.out_draft, draft_out)

    print(
        f"content-live merge: {stats['kept']} Felder von der Redaktion behalten, "
        f"{stats['added']} neue aus Git ergänzt, {stats['extra']} zusätzliche Server-Felder belassen, "
        f"{stats.get('forced_from_git', 0)} aus Git erzwungen, "
        f"{stats.get('promoted_from_draft', 0)} aus Entwurf übernommen (Live war leer)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
