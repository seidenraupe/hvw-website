#!/usr/bin/env python3
"""Deploy-Merge: Redaktion behalten, Vorstand aus Git, Entwurf rettet leere Live-Felder."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "merge_content", ROOT / "scripts/merge-content-json.py"
)
merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge)

ids = [
    "ueber-uns.vorstand.person1",
    "sammlung.objekt.1.image",
    "sammlung.objekt.1.title",
    "agenda.rueckblick.1.image",
]
seed = {
    "ueber-uns.vorstand.person1": "<strong>Git</strong> — Vorstand",
    "sammlung.objekt.1.image": "",
    "sammlung.objekt.1.title": "Seed-Titel",
    "agenda.rueckblick.1.image": "",
}
remote = {
    "ueber-uns.vorstand.person1": "Christian — ohne strong",
    "sammlung.objekt.1.image": "",
    "sammlung.objekt.1.title": "Redaktions-Titel",
    "agenda.rueckblick.1.image": "",
}
draft = {
    "sammlung.objekt.1.image": "data/uploads/sammlung-1-deadbeef.jpg",
    "agenda.rueckblick.1.image": "data/uploads/rueckblick-1-deadbeef.jpg",
}

live, stats = merge.merge_live_fields(ids, seed, remote, draft)
if live["ueber-uns.vorstand.person1"] != seed["ueber-uns.vorstand.person1"]:
    raise SystemExit("Vorstand muss aus Git kommen")
if live["sammlung.objekt.1.title"] != "Redaktions-Titel":
    raise SystemExit("Sammlungstitel muss vom Server bleiben")
if live["sammlung.objekt.1.image"] != draft["sammlung.objekt.1.image"]:
    raise SystemExit("Leeres Live-Bild muss aus Entwurf übernommen werden")
if live["agenda.rueckblick.1.image"] != draft["agenda.rueckblick.1.image"]:
    raise SystemExit("Agenda-Bild muss aus Entwurf übernommen werden")
if stats.get("promoted_from_draft", 0) < 2:
    raise SystemExit("promote_from_draft Zähler fehlt")

draft_out = merge.merge_draft_fields(
    ids,
    live,
    {
        "sammlung.objekt.1.title": "Entwurf-Titel",
        "sammlung.objekt.1.image": draft["sammlung.objekt.1.image"],
    },
    seed,
)
if draft_out["sammlung.objekt.1.title"] != "Entwurf-Titel":
    raise SystemExit("Redaktions-Entwurf darf nicht auf Seed zurückgesetzt werden")

parts = merge.split_opening_hours(
    "Die Villa steht im Park.<br>Öffnungszeiten<br>Di: 14–17 Uhr"
)
if not parts or not parts[0].startswith("Die Villa") or not parts[1].startswith("Öffnungszeiten"):
    raise SystemExit(f"Öffnungszeiten werden nicht abgetrennt: {parts}")

split_ids = ["lindengut.lead", "lindengut.oeffnung"]
split_seed = {
    "lindengut.lead": "Kurzer Lead.",
    "lindengut.oeffnung": "Öffnungszeiten<br>Sa: 14–17 Uhr",
}
split_remote = {
    "lindengut.lead": "Die Villa steht im Park.<br>Öffnungszeiten<br>Di: 14–17 Uhr",
}
split_live, _stats = merge.merge_live_fields(split_ids, split_seed, split_remote, {})
if "Öffnungszeiten" in split_live["lindengut.lead"]:
    raise SystemExit("Live-Lead behält den Öffnungszeiten-Block")
if not split_live["lindengut.oeffnung"].startswith("Öffnungszeiten"):
    raise SystemExit("Live-Öffnungszeiten fehlen nach der Trennung")
split_draft = merge.merge_draft_fields(
    split_ids,
    split_live,
    {"lindengut.lead": "Entwurf zur Villa.<br><br>Öffnungszeiten<br>So: 10–12 Uhr"},
    split_seed,
)
if split_draft["lindengut.lead"] != "Entwurf zur Villa.":
    raise SystemExit(f"Entwurf-Lead nicht getrennt: {split_draft['lindengut.lead']}")
if "So: 10–12 Uhr" not in split_draft["lindengut.oeffnung"]:
    raise SystemExit("Entwurf-Öffnungszeiten nicht übernommen")

member_price = (
    "<strong>Eintrittspreise:</strong><br>CHF 5.–, reduziert CHF 3.– für Mitglieder "
    "des Historischen Vereins Winterthur mit Ausweis kostenlos"
)
member_live, _member_stats = merge.merge_live_fields(
    ["lindengut.oeffnung"],
    {},
    {"lindengut.oeffnung": member_price},
    {},
)
member_text = member_live["lindengut.oeffnung"]
if "CHF 3.–<br>für Mitglieder" not in member_text:
    raise SystemExit(f"Mitgliederhinweis nicht umbrochen: {member_text}")
if member_text.count("für Mitglieder") != 1 or member_text.count("<br>für Mitglieder") != 1:
    raise SystemExit(f"Mitgliederhinweis mehrfach: {member_text}")
if "<strong>Eintrittspreise:</strong>" not in member_text:
    raise SystemExit("Eintrittspreise-Zeile darf nicht verschwinden")
member_again, _member_again = merge.merge_live_fields(
    ["lindengut.oeffnung"],
    {},
    {"lindengut.oeffnung": member_text},
    {},
)
if member_again["lindengut.oeffnung"] != member_text:
    raise SystemExit("Umbruch wird beim zweiten Merge verdoppelt")
member_draft = merge.merge_draft_fields(
    ["lindengut.oeffnung"],
    {"lindengut.oeffnung": member_text},
    {"lindengut.oeffnung": member_price},
    {},
)
if "CHF 3.–<br>für Mitglieder" not in member_draft["lindengut.oeffnung"]:
    raise SystemExit("Entwurf behält den Mitgliederhinweis in der Preiszeile")

src = (ROOT / "scripts/merge-content-json.py").read_text(encoding="utf-8")
if "sammlung.objekt.1.image" in merge.INITIAL_SEED_FIELD_IDS:
    raise SystemExit("Sammlung darf nicht in INITIAL_SEED_FIELD_IDS stehen")

tour_ids = ["moersburg.oeffnung", "moersburg.lead"]
tour_seed = {
    "moersburg.oeffnung": "Öffnungszeiten<br>Mi–Sa: 14–17 Uhr",
    "moersburg.lead": "Ritterburg.",
}
tour_remote = {
    "moersburg.oeffnung": (
        "Regelmässige öffentliche Führungen gemäss <a href=\"agenda.html\">Programm</a>."
        "<br>Private Führungen nach Absprache."
    ),
    "moersburg.lead": "Ritterburg am Stadtrand.",
}
tour_live, _tour_stats = merge.merge_live_fields(tour_ids, tour_seed, tour_remote, {})
opening = tour_live["moersburg.oeffnung"]
if '<a href="dokumente/szenische-fuehrung-berta.pdf" target="_blank" rel="noopener noreferrer">öffentliche Führungen</a>' not in opening:
    raise SystemExit(f"öffentliche Führungen nicht verlinkt: {opening}")
if '<a href="dokumente/historische-privat-fuehrungen.pdf" target="_blank" rel="noopener noreferrer">Private Führungen</a>' not in opening:
    raise SystemExit(f"Private Führungen nicht verlinkt: {opening}")
if opening.count("<a ") != 3 or '<a href="agenda.html">Programm</a>' not in opening:
    raise SystemExit(f"bestehender Programmlink verändert: {opening}")
if tour_live["moersburg.lead"] != "Ritterburg am Stadtrand.":
    raise SystemExit("Lead ohne die Formulierungen darf sich nicht ändern")
again, _again_stats = merge.merge_live_fields(tour_ids, tour_seed, {"moersburg.oeffnung": opening, "moersburg.lead": tour_live["moersburg.lead"]}, {})
if again["moersburg.oeffnung"] != opening:
    raise SystemExit("Führungs-Links werden beim zweiten Merge doppelt gesetzt")
for pdf in ("historische-privat-fuehrungen.pdf", "szenische-fuehrung-berta.pdf"):
    path = ROOT / "dokumente" / pdf
    if not path.is_file() or path.read_bytes()[:5] != b"%PDF-":
        raise SystemExit(f"PDF fehlt: {path}")
build = (ROOT / "scripts/build-hostpoint-vorschau.sh").read_text(encoding="utf-8")
if "VORSCHAU_PDFS" not in build or "historische-privat-fuehrungen.pdf" not in build:
    raise SystemExit("Vorschau-Build muss dokumente/ inkl. Führungs-PDFs kopieren")

hours_remote = {
    "moersburg.oeffnung": (
        "<strong>Öffnungszeiten</strong><br>1. Mai bis 31. Oktober<br>"
        "So und Feiertage: 13–17 Uhr<br><br><strong>Eintrittspreise</strong><br>"
        "CHF 5.–, reduziert CHF 3.–"
    ),
    "moersburg.lead": "Ritterburg.",
}
hours_live, _hours_stats = merge.merge_live_fields(
    tour_ids, tour_seed, hours_remote, {}
)
hours = hours_live["moersburg.oeffnung"]
if "1. Mai bis 31. Oktober" not in hours or "So und Feiertage: 13–17 Uhr" not in hours:
    raise SystemExit(f"Öffnungszeiten dürfen nicht verschwinden: {hours}")
if "reduziert CHF 3" in hours:
    raise SystemExit(f"reduzierter Preis bleibt stehen: {hours}")
if "mit Kultur-Legi CHF 2.50, für HVW-Mitglieder gratis" not in hours:
    raise SystemExit(f"Kultur-Legi oder Mitglieder-Hinweis fehlt: {hours}")
again_hours, _ = merge.merge_live_fields(
    tour_ids, tour_seed, {"moersburg.oeffnung": hours, "moersburg.lead": "Ritterburg."}, {}
)
if again_hours["moersburg.oeffnung"].count("HVW-Mitglieder") != 1:
    raise SystemExit("Mitglieder-Hinweis wird doppelt gesetzt")
old_partner = (
    "Die Plattform dokumentiert erhaltene Industrieanlagen in einem nationalen Online-Inventar. "
    "Getragen wird sie von der SGTI; ein Projektteam in Winterthur arbeitet mit den kantonalen Denkmalpflegen."
)
partner_live, _partner_stats = merge.merge_live_fields(
    ["partner.6.body"],
    {},
    {"partner.6.body": old_partner},
    {},
)
partner_text = partner_live["partner.6.body"]
if "dokumentiert historisch relevante, erhaltene Industrieanlagen" not in partner_text:
    raise SystemExit(f"Industriekultur-Anlagen nicht ergänzt: {partner_text}")
if "fotografiert und beschreibt Objekte in Absprache mit den kantonalen Denkmalpflegen" not in partner_text:
    raise SystemExit(f"Industriekultur-Aufnahme nicht ergänzt: {partner_text}")
if "arbeitet mit" in partner_text:
    raise SystemExit(f"alte Formulierung bleibt: {partner_text}")
partner_again, _partner_again = merge.merge_live_fields(
    ["partner.6.body"],
    {},
    {"partner.6.body": partner_text},
    {},
)
if partner_again["partner.6.body"] != partner_text:
    raise SystemExit("Industriekultur-Text wird beim zweiten Merge verdoppelt")

print("content merge ok")
