#!/usr/bin/env python3
"""Agenda: zusätzliche Rückblick-Karten im Edit-Modus, ohne bestehende Inhalte."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
agenda = (ROOT / "agenda.html").read_text(encoding="utf-8")
content = (ROOT / "js/content.js").read_text(encoding="utf-8")
editor = (ROOT / "js/content-editor.js").read_text(encoding="utf-8")
lib = (ROOT / "redaktion/lib.php").read_text(encoding="utf-8")
live = (ROOT / "data/content-live.json").read_text(encoding="utf-8")

if 'data-rueckblick-add' not in agenda:
    raise SystemExit("agenda.html braucht den Button «Vergangene Veranstaltung hinzufügen»")
if "Vergangene Veranstaltung hinzufügen" not in agenda:
    raise SystemExit("Button-Beschriftung fehlt")
for n in range(1, 7):
    if f'data-rueckblick-slot="{n}"' not in agenda:
        raise SystemExit(f"Bestehende Karte {n} braucht data-rueckblick-slot")

if "hvwEnsureRueckblickCards" not in content or "hvwNextRueckblickSlot" not in content:
    raise SystemExit("content.js muss Rückblick-Karten dynamisch erzeugen")
if "RUECKBLICK_MAX = 48" not in content:
    raise SystemExit("Maximal 48 Rückblick-Karten")
if "addRueckblickCard" not in editor:
    raise SystemExit("Editor braucht addRueckblickCard")
if "keepEmpty: view === \"draft\"" not in editor:
    raise SystemExit("Im Entwurf bleiben leere neue Karten sichtbar")

if "function hvw_rueckblick_max" not in lib:
    raise SystemExit("lib.php muss zusätzliche Rückblick-Slots erlauben")
if "hvw_extend_schema_from_fields" not in lib:
    raise SystemExit("Schema muss neue Rückblick-Felder aus Live/Entwurf ergänzen")

# Bestehende Live-Inhalte der ersten sechs Karten dürfen nicht verloren gehen
for n in range(1, 7):
    key = f'"agenda.rueckblick.{n}.title"'
    if key not in live:
        raise SystemExit(f"Live-Inhalt {key} fehlt")

print("rueckblick add ok")
