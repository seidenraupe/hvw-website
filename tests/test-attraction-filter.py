#!/usr/bin/env python3
"""Eventfrog-Attraktionen (Öffnungszeiten) gehören nicht ins Coucou/MuS-JSON."""
import os
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

fake_requests = types.ModuleType("requests")
fake_requests.exceptions = types.SimpleNamespace(RequestException=Exception)
sys.modules.setdefault("requests", fake_requests)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cronjobs"))
from eventfrog_to_coucou import (  # noqa: E402
    EXCLUDED_ATTRACTION_TITLES,
    filter_attraction_events,
    is_attraction_event,
    normalize_event_title,
    opening_hours_attraction_titles,
)


def _event(title, begin, **extra):
    payload = {
        "id": extra.pop("id", "1"),
        "title": {"de": title} if not isinstance(title, dict) else title,
        "begin": begin,
        "end": extra.pop("end", begin),
        "url": extra.pop("url", "https://eventfrog.ch/de/p/kultur/event-1.html"),
    }
    payload.update(extra)
    return payload


def _weekdays(start, count, hour=10, minute=0):
    """count Werktage ab start (Wochenenden überspringen)."""
    day = start
    dates = []
    while len(dates) < count:
        if day.weekday() < 5:
            dates.append(
                day.replace(hour=hour, minute=minute, second=0).strftime(
                    "%Y-%m-%dT%H:%M:%S+02:00"
                )
            )
        day += timedelta(days=1)
    return dates


def main():
    if is_attraction_event(
        _event("Käfele", "2026-09-25T14:00:00+02:00", type="default")
    ):
        raise SystemExit("default Veranstaltung darf keine Attraktion sein")

    if not is_attraction_event(
        _event(
            "Ausstellung",
            "2026-09-02T10:00:00+02:00",
            type="attractionInstance",
        )
    ):
        raise SystemExit("attractionInstance muss erkannt werden")

    if not is_attraction_event(
        _event(
            "Ausstellung Original",
            "2026-09-01T10:00:00+02:00",
            type="attractionOriginal",
        )
    ):
        raise SystemExit("attractionOriginal muss erkannt werden")

    if not is_attraction_event(
        _event("Ausstellung", "2026-09-02T10:00:00+02:00", attractionId="99")
    ):
        raise SystemExit("attractionId muss als Attraktion gelten")

    if not is_attraction_event(
        _event("Erinnerungstank Haldengut", "2026-09-02T10:00:00+02:00")
    ):
        raise SystemExit("bekannter Öffnungszeiten-Titel muss rausfallen")

    if not is_attraction_event(
        _event(
            "Ausstellung: Erinnerungstank Haldengut",
            "2026-09-25T10:00:00+02:00",
        )
    ):
        raise SystemExit("Ausstellung-Präfix vor Erinnerungstank muss rausfallen")

    if is_attraction_event(
        _event(
            "Käfele mit der Kuratorin der Ausstellung",
            "2026-09-25T14:00:00+02:00",
        )
    ):
        raise SystemExit("Käfele ist eine Veranstaltung, keine Öffnungszeit")

    if normalize_event_title(
        {"title": {"de": "  Erinnerungstank   Haldengut "}}
    ) not in EXCLUDED_ATTRACTION_TITLES:
        raise SystemExit("Titel-Normalisierung für Erinnerungstank fehlgeschlagen")

    weekly = [
        _event(
            "Winterthurer Vorträge",
            (datetime(2026, 9, 2, 19, 0) + timedelta(days=7 * i)).strftime(
                "%Y-%m-%dT%H:%M:%S+02:00"
            ),
        )
        for i in range(12)
    ]
    weekly_titles = opening_hours_attraction_titles(weekly)
    if "winterthurer vorträge" in weekly_titles:
        raise SystemExit("wöchentliche Vortragsreihe darf nicht als Öffnungszeit gelten")

    opening = [
        _event("Neue Ausstellung", begin)
        for begin in _weekdays(datetime(2026, 9, 1), 8)
    ]
    opening_titles = opening_hours_attraction_titles(opening)
    if "neue ausstellung" not in opening_titles:
        raise SystemExit("Werktags-Öffnungszeiten müssen als Attraktion erkannt werden")

    def _open_days(start, count, weekdays, hour=10):
        day = start
        dates = []
        while len(dates) < count:
            if day.weekday() in weekdays:
                dates.append(
                    day.replace(hour=hour, minute=0, second=0).strftime(
                        "%Y-%m-%dT%H:%M:%S+02:00"
                    )
                )
            day += timedelta(days=1)
        return dates

    museum = [
        _event("Ausstellung: Neue Schau", begin)
        for begin in _open_days(datetime(2026, 9, 25), 15, {2, 3, 4, 5, 6})
    ]
    museum_titles = opening_hours_attraction_titles(museum)
    if "ausstellung: neue schau" not in museum_titles:
        raise SystemExit("Mi–So-Öffnungszeiten müssen als Attraktion erkannt werden")

    mixed = (
        [
            _event(
                "Erinnerungstank Haldengut",
                begin,
                type="attractionInstance",
                attractionId="42",
            )
            for begin in _weekdays(datetime(2026, 9, 2), 12)
        ]
        + [
            _event(
                "Kuratorinnenführung – Wir (ver)zapfen Geschichte",
                "2026-09-03T19:00:00+02:00",
                type="default",
            ),
            _event(
                "Käfele mit der Kuratorin der Ausstellung",
                "2026-09-25T14:00:00+02:00",
                type="default",
            ),
            _event("AfterWorkKultur", "2026-09-25T18:00:00+02:00", type="default"),
            _event("PiMS - Pubquiz im Museum!", "2026-09-24T19:00:00+02:00"),
            _event("Winterthur's wilde 80er", "2026-11-04T19:00:00+02:00"),
        ]
    )
    kept, skipped = filter_attraction_events(mixed)
    kept_titles = [normalize_event_title(event) for event in kept]
    if skipped != 12:
        raise SystemExit("erwartete 12 entfernte Attraktionen, got {0}".format(skipped))
    if len(kept) != 5:
        raise SystemExit("erwartete 5 Veranstaltungen, got {0}: {1}".format(len(kept), kept_titles))
    if any("erinnerungstank" in title for title in kept_titles):
        raise SystemExit("Erinnerungstank darf nicht im Export bleiben")

    # Coucou-Records (title/date/time_start) wie im Live-JSON
    coucou_shaped = [
        {
            "title": "Erinnerungstank Haldengut",
            "date": "2026/09/{0:02d}".format(day),
            "time_start": "10:00",
            "time_end": "17:00",
        }
        for day in (2, 3, 4, 5, 6, 9, 10, 11)
    ] + [
        {
            "title": "Käfele mit der Kuratorin der Ausstellung",
            "date": "2026/09/25",
            "time_start": "14:00",
        }
    ]
    kept_coucou, skipped_coucou = filter_attraction_events(coucou_shaped)
    if skipped_coucou != 8 or len(kept_coucou) != 1:
        raise SystemExit(
            "Coucou-Records: expected 8/1, got {0}/{1}".format(
                skipped_coucou, len(kept_coucou)
            )
        )

    pdf_source = (
        Path(__file__).resolve().parents[1] / "scripts" / "generate-programm-pdf.py"
    ).read_text(encoding="utf-8")
    if "filter_attraction_events" not in pdf_source:
        raise SystemExit("Programm-PDF filtert Öffnungszeiten nicht")

    print("attraction filter ok")


if __name__ == "__main__":
    main()
