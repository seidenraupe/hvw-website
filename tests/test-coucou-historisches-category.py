#!/usr/bin/env python3
"""Coucou-Export: jede Veranstaltung erhält Kategorie Historisches (308)."""
import os
import sys
import types

ROOT = os.path.join(os.path.dirname(__file__), "..")
fake_requests = types.ModuleType("requests")
fake_requests.exceptions = types.SimpleNamespace(RequestException=Exception)
sys.modules["requests"] = fake_requests
sys.path.insert(0, os.path.join(ROOT, "cronjobs"))

from eventfrog_to_coucou import (  # noqa: E402
    COUCOU_CATEGORY_HISTORISCHES,
    COUCOU_LOCATION_WEBSITE,
    coucou_event_categories,
    build_coucou_event,
)

if COUCOU_CATEGORY_HISTORISCHES != 308:
    raise SystemExit("Historisches muss Coucou-ID 308 sein")

rubrics = {
    "r-fuehrung": {"title": {"de": "Führungen & Vorträge"}},
    "r-histor": {"title": {"de": "Historisches Programm"}},
}

cats = coucou_event_categories("r-fuehrung", rubrics)
if cats != [280, 308]:
    raise SystemExit("Führung erwartet [280, 308], got {0}".format(cats))

cats_hist = coucou_event_categories("r-histor", rubrics)
if cats_hist != [308]:
    raise SystemExit("Historische Rubrik darf 308 nicht doppeln: {0}".format(cats_hist))

event = {
    "id": "evt-1",
    "title": {"de": "Test-Führung"},
    "rubricId": "r-fuehrung",
    "begin": "2026-11-01T14:00:00+02:00",
    "end": "2026-11-01T16:00:00+02:00",
    "url": "https://eventfrog.ch/de/p/test.html",
}
built = build_coucou_event(event, rubrics, {})
if built.get("category") != [280, 308]:
    raise SystemExit("build_coucou_event category mismatch: {0}".format(built.get("category")))
if built.get("location_website") != COUCOU_LOCATION_WEBSITE:
    raise SystemExit("location_website muss HVW-Agenda sein: {0}".format(built.get("location_website")))

event_with_loc = {
    **event,
    "locationIds": ["loc-1"],
}
locations = {
    "loc-1": {
        "id": "loc-1",
        "title": {"de": "Museum Schaffen"},
        "websiteUrl": "https://www.museumschaffen.ch/",
    },
}
built_loc = build_coucou_event(event_with_loc, rubrics, locations)
if built_loc.get("location_website") != COUCOU_LOCATION_WEBSITE:
    raise SystemExit("location_website darf nicht Eventfrog websiteUrl sein")

coucou_js = open(os.path.join(ROOT, "js/coucou-preview.js"), encoding="utf-8").read()
if "formatCategory" not in coucou_js or "Array.isArray" not in coucou_js:
    raise SystemExit("coucou-preview.js muss Kategorie-Arrays anzeigen")

print("coucou historisches category ok")
