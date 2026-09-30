#!/usr/bin/env python
"""
Eventfrog → home-events.json (Titelseite)
========================================

Eigener Hostpoint-Cron — unabhängig von GitHub und vom Coucou-/MuS-Export.
Attraktionen (Öffnungszeiten) werden wie im Coucou-Export weggelassen.

Schreibt die nächsten 3 Anlässe aller HVW-Org-IDs nach:
    https://www.hvwinterthur.ch/home-events.json
    https://www.hvwinterthur.ch/data/home-events.json
    und eine Kopie unter /edit/data/ für den Bearbeitungszugang.

Hostpoint-Cron (täglich, z.B. 03:10):
    cd /home/zozuhosa/cronjobs && /usr/local/bin/python eventfrog_to_home.py >/dev/null 2>&1
"""

from __future__ import print_function

import requests

from eventfrog_to_coucou import (
    API_KEY_ENV_NAME,
    API_KEY_FILE,
    build_home_events_payload,
    filter_attraction_events,
    get_all_events,
    get_locations,
    load_api_key,
    resolve_httpdocs_dir,
    resolve_org_ids,
    write_home_events_files,
)


def main():
    httpdocs_dir = resolve_httpdocs_dir()
    org_ids = resolve_org_ids()
    api_key = load_api_key()
    if not api_key:
        print(
            "Fehler: Eventfrog API-Key fehlt.\n"
            "  - Umgebungsvariable {0} setzen, oder\n"
            "  - Datei '{1}' anlegen (Vorlage: eventfrog_api_key.example).\n"
            "Niemals den Key in httpdocs/ oder ins Git-Repo legen.".format(
                API_KEY_ENV_NAME, API_KEY_FILE
            )
        )
        return

    print(
        "Rufe Events von Eventfrog ab (Titelseite, Org-IDs: {0}) ...".format(
            ", ".join(org_ids)
        )
    )
    try:
        events = get_all_events(org_ids, api_key)
    except requests.exceptions.RequestException as exc:
        print("Netzwerkfehler: {0}".format(exc))
        return
    except RuntimeError as exc:
        print(exc)
        return

    print("{0} Event(s) von der API. Filtere Attraktionen/Öffnungszeiten ...".format(len(events)))
    events, skipped_attractions = filter_attraction_events(events)
    if skipped_attractions:
        print(
            "{0} Attraktion(en)/Öffnungszeit(en) entfernt, {1} Veranstaltung(en) bleiben.".format(
                skipped_attractions, len(events)
            )
        )
    print("{0} Veranstaltung(en). Lade Locations ...".format(len(events)))

    all_location_ids = set()
    for event in events:
        for loc_id in event.get("locationIds") or []:
            all_location_ids.add(loc_id)

    try:
        locations_by_id = get_locations(api_key, all_location_ids)
    except (requests.exceptions.RequestException, RuntimeError) as exc:
        print(
            "Warnung: Locations konnten nicht geladen werden ({0}). "
            "Adressfelder werden übersprungen.".format(exc)
        )
        locations_by_id = {}

    try:
        payload = build_home_events_payload(events, locations_by_id)
        written = write_home_events_files(httpdocs_dir, payload)
        print(
            "{0} kommende Event(s) für die Titelseite gespeichert in: {1}.".format(
                len(payload.get("events", [])),
                ", ".join("'{0}'".format(path) for path in written),
            )
        )
    except Exception as exc:
        print(
            "Fehler: home-events.json konnte nicht geschrieben werden "
            "({0}: {1}).".format(type(exc).__name__, exc)
        )


if __name__ == "__main__":
    main()
