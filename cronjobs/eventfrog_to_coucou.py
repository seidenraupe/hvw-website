"""
Eventfrog API -> Coucou-Export (und Guidle-Kopie)
================================================

Was macht dieses Skript?
    1. Ruft über die Eventfrog Public API v1 alle Events der angegebenen
       Organisationen ab (inkl. Paginierung).
    2. Lädt zusätzlich die Rubriken (Kategorien) und die Veranstaltungsorte
       (Locations), die von den Events referenziert werden.
    3. Baut daraus für jedes Event ein JSON-Objekt exakt nach dem Feld-Schema
       der Coucou-Schnittstelle (siehe "Schnittstelle Kulturmagazin Coucou",
       Version 1.4).
    4. Speichert das Ergebnis als Liste von Event-Objekten im öffentlichen
       Webroot (Standard: coucou_export.json). Nach dem Coucou-Export wird
       dieselbe Datei als guidle_export.json dupliziert. Dateiname und Org-IDs
       sind per Umgebungsvariable steuerbar (siehe unten) – z.B. mus_export.json
       nur für Museum Schaffen (OrgID 5116588); dann keine Guidle-Kopie.
    Die Titelseite (home-events.json) läuft als eigener Cron:
       eventfrog_to_home.py — nicht über dieses Skript.

Voraussetzungen:
    pip install -r requirements.txt   # bzw. pip install --user requests

Bitte vor dem Start unten bei DEFAULT_ORG_IDS die Organisations-IDs prüfen.

API-Key (geheim – nie ins Git-Repo):
    1. Umgebungsvariable EVENTFROG_API_KEY, oder
    2. Datei 'eventfrog_api_key' im gleichen Ordner wie dieses Skript
       (nur der Key, eine Zeile; Vorlage: eventfrog_api_key.example).
    Die Key-Datei liegt bewusst in .../cronjobs/ – nicht im Webroot.

Pfad-Hinweis:
    Skript typischerweise in ~/cronjobs/ (Hostpoint) bzw. .../cronjobs/ (Plesk).
    Webroot wird so ermittelt (erste passende Variante):
      1. Umgebungsvariable HVW_HTTPDOCS_DIR
      2. ../www/hvwinterthur.ch  (Hostpoint)
      3. ../httpdocs             (Plesk / Kreativ Media)

Umgebungsvariablen (optional):
    HVW_ORG_IDS          Kommagetrennte Eventfrog-Org-IDs (Default: alle HVW)
    HVW_EXPORT_FILENAME  Dateiname im Webroot (Default: coucou_export.json)
    HVW_HTTPDOCS_DIR     Expliziter Webroot

Beschreibung in beiden Exporten (coucou_export.json und mus_export.json):
    description       Kurzbeschreibung (shortDescription)
    description_long  Lange Eventbeschreibung als Klartext
    description_html  Lange Eventbeschreibung als HTML

Öffentliche URLs (Beispiele):
    https://www.hvwinterthur.ch/coucou_export.json
    https://www.hvwinterthur.ch/guidle_export.json
    https://www.hvwinterthur.ch/mus_export.json
    https://www.hvwinterthur.ch/home-events.json
    https://www.hvwinterthur.ch/data/home-events.json

Bekannte Einschränkungen (siehe Kommentare weiter unten im Code):
    - "category" wird über den Rubrik-NAMEN auf die Coucou-Kategorie-IDs
      gemappt (Best-Effort, bitte kurz stichprobenartig prüfen/anpassen).
    - "location_id" (Coucous eigene interne Orts-ID) kann nicht automatisch
      ermittelt werden. Stattdessen werden die Adressfelder
      (location_name/_street/_zip/_city/_website) befüllt - das ist laut
      Coucou-Doku die zulässige Alternative.
    - "weekdays", "fee_options" und "attachments" liefert die Eventfrog
      Public API in diesem Schema nicht und bleiben daher leer.
    - Eventfrog-Attraktionen (Öffnungszeiten, z.B. Museum täglich) werden
      vor dem Export entfernt. Nur Veranstaltungen bleiben im JSON.
"""

import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------
# Konfiguration - bitte anpassen
# ---------------------------------------------------------------------
# Default: alle HVW-Organisationen (Coucou-Export).
# Override: HVW_ORG_IDS=5116588 (Museum Schaffen → mus_export.json)
DEFAULT_ORG_IDS = ["4936116", "5116588", "5137433"]
ORG_IDS = DEFAULT_ORG_IDS  # Abwärtskompatibilität

DEFAULT_EXPORT_FILENAME = "coucou_export.json"
GUIDLE_EXPORT_FILENAME = "guidle_export.json"

# API-Key wird NICHT im Quellcode gespeichert (siehe load_api_key()).
API_KEY_ENV_NAME = "EVENTFROG_API_KEY"

BASE_URL = "https://api.eventfrog.net"

# Bevorzugte Sprache für mehrsprachige Felder (title, description, ...)
# Eventfrog liefert diese Felder als Objekt, z.B. {"de": "...", "en": "...", "fr": "..."}
PREFERRED_LANGUAGES = ["de", "de_CH", "en", "fr", "it"]

# Best-Effort-Zuordnung: Eventfrog-Rubrikname (klein geschrieben, Teilstring-Suche)
# -> Coucou category-ID gemäss Schnittstellen-Dokumentation
RUBRIC_NAME_TO_COUCOU_CATEGORY = [
    ("konzert", 69),
    ("party", 70),
    ("film", 11),
    ("literatur", 14),
    ("theater", 71),
    ("tanz", 72),
    ("ausstellung", 13),
    ("vernissage", 217),
    ("kinder", 213),
    ("führung", 280),
    ("fuehrung", 280),
    ("vortrag", 281),
]
# Fallback-Kategorie, falls kein Rubrikname zugeordnet werden kann
DEFAULT_COUCOU_CATEGORY = 15  # "Diverses"

# Titelseite hvwinterthur.ch: kompakter Auszug der nächsten Events
HVW_HOME_EVENT_LIMIT = 3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def resolve_org_ids():
    """Org-IDs aus HVW_ORG_IDS (kommagetrennt) oder DEFAULT_ORG_IDS."""
    raw = os.environ.get("HVW_ORG_IDS", "").strip()
    if not raw:
        return list(DEFAULT_ORG_IDS)
    ids = [part.strip() for part in raw.split(",") if part.strip()]
    return ids or list(DEFAULT_ORG_IDS)


def resolve_httpdocs_dir():
    """Öffentlicher Webroot für Export-JSON / home-events.json."""
    env_dir = os.environ.get("HVW_HTTPDOCS_DIR", "").strip()
    if env_dir:
        return os.path.abspath(env_dir)

    candidates = [
        # Hostpoint: /home/<user>/cronjobs -> /home/<user>/www/hvwinterthur.ch
        os.path.normpath(os.path.join(SCRIPT_DIR, "..", "www", "hvwinterthur.ch")),
        # Plesk / Kreativ Media: .../cronjobs -> .../httpdocs
        os.path.normpath(os.path.join(SCRIPT_DIR, "..", "httpdocs")),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]


def resolve_export_path(httpdocs_dir):
    """Zielpfad der Export-JSON (Basename via HVW_EXPORT_FILENAME)."""
    name = os.environ.get("HVW_EXPORT_FILENAME", DEFAULT_EXPORT_FILENAME).strip()
    if not name:
        name = DEFAULT_EXPORT_FILENAME
    # Keine Pfadtraversal: nur Dateiname im Webroot
    name = os.path.basename(name)
    return os.path.join(httpdocs_dir, name)


def copy_guidle_export(export_path):
    """Nach coucou_export.json eine identische guidle_export.json ablegen.

    mus_export.json (Museum Schaffen) wird nicht kopiert.
    """
    if os.path.basename(export_path) != DEFAULT_EXPORT_FILENAME:
        return None
    dest = os.path.join(os.path.dirname(export_path), GUIDLE_EXPORT_FILENAME)
    shutil.copy2(export_path, dest)
    return dest


def home_events_output_paths(httpdocs_dir):
    """Ziele für den Titelseiten-Auszug (öffentlich + /edit/)."""
    return [
        os.path.join(httpdocs_dir, "home-events.json"),
        os.path.join(httpdocs_dir, "data", "home-events.json"),
        os.path.join(httpdocs_dir, "edit", "data", "home-events.json"),
    ]


def write_home_events_files(httpdocs_dir, payload):
    """Schreibt den Titelseiten-Auszug an die öffentlichen Hostpoint-Pfade."""
    written = []
    for home_output_path in home_events_output_paths(httpdocs_dir):
        directory = os.path.dirname(home_output_path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        with open(home_output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        written.append(home_output_path)
    return written


def pick_event_image(event):
    """Bild-URL aus dem Eventfrog-Event, sonst leer."""
    emblem = event.get("emblemToShow")
    if isinstance(emblem, dict):
        url = emblem.get("url") or ""
        if str(url).startswith("http"):
            return url.split("?")[0]
    image = event.get("image")
    if isinstance(image, dict):
        url = image.get("url") or ""
        if str(url).startswith("http"):
            return url.split("?")[0]
    if isinstance(image, str) and image.startswith("http"):
        return image.split("?")[0]
    for key in ("imageUrl", "imageURL", "flyerUrl", "thumbnailUrl"):
        url = event.get(key) or ""
        if isinstance(url, str) and url.startswith("http"):
            return url.split("?")[0]
    return ""


def fetch_og_image(event_url):
    """og:image der Eventseite, falls die API kein Bild liefert."""
    if not event_url or not str(event_url).startswith("http"):
        return ""
    try:
        response = requests.get(
            event_url,
            timeout=20,
            headers={"User-Agent": "HVW-home-events/1.0"},
        )
        if response.status_code != 200:
            return ""
        html = response.text
        match = re.search(
            r'property=["\']og:image["\']\s+content=["\']([^"\']+)',
            html,
            re.I,
        )
        if not match:
            match = re.search(
                r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
                html,
                re.I,
            )
        url = (match.group(1).strip() if match else "")
        if url.startswith("http"):
            return url.split("?")[0]
    except requests.exceptions.RequestException:
        return ""
    return ""


# Geheimer Key-File neben dem Skript (ausserhalb vom Webroot, nicht im Git)
API_KEY_FILE = os.path.join(SCRIPT_DIR, "eventfrog_api_key")


def load_api_key():
    """Lädt den Eventfrog API-Key aus Env oder lokaler Datei.

    Reihenfolge:
      1. Umgebungsvariable EVENTFROG_API_KEY
      2. Datei eventfrog_api_key im Skriptordner (eine Zeile Key, oder
         KEY=value / EVENTFROG_API_KEY=value)

    Gibt None zurück, wenn nichts gefunden wurde.
    """
    env_key = os.environ.get(API_KEY_ENV_NAME, "").strip()
    if env_key:
        return env_key

    try:
        with open(API_KEY_FILE, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    name, value = line.split("=", 1)
                    name = name.strip()
                    value = value.strip().strip('"').strip("'")
                    if name in (API_KEY_ENV_NAME, "API_KEY") and value:
                        return value
                    continue
                return line
    except OSError:
        pass

    return None


# ---------------------------------------------------------------------
# Hilfsfunktionen: API-Zugriff
# ---------------------------------------------------------------------
def api_get(path, params, timeout=60, retries=3):
    """Führt einen GET-Request gegen die Eventfrog API aus.

    Werte, die Listen sind, werden von 'requests' automatisch als
    mehrfacher Query-Parameter gesendet (z.B. orgId=1&orgId=2).

    Bei Timeout/5xx wird begrenzt erneut versucht (Hosting-Cron oft
    langsamer / Gateway-504).
    """
    url = f"{BASE_URL}{path}"
    headers = {"Accept": "application/json"}
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url, params=params, headers=headers, timeout=timeout
            )
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < retries:
                continue
            raise

        if response.status_code == 200:
            return response.json()

        # 408/429/5xx: Retry lohnt sich oft (z.B. Gateway 504 stream timeout)
        if response.status_code in (408, 429, 500, 502, 503, 504) and attempt < retries:
            last_error = RuntimeError(
                f"Fehler beim Abruf von {path}: HTTP {response.status_code}\n"
                f"Antwort: {response.text}"
            )
            continue

        raise RuntimeError(
            f"Fehler beim Abruf von {path}: HTTP {response.status_code}\n"
            f"Antwort: {response.text}"
        )

    raise RuntimeError(f"Fehler beim Abruf von {path}: {last_error}")


def get_all_events(org_ids, api_key):
    """Holt ALLE Events der angegebenen Organisationen (mit Paginierung)."""
    all_events = []
    page = 1
    per_page = 1000

    while True:
        data = api_get("/public/v1/events", {
            "apiKey": api_key,
            "orgId": org_ids,      # Liste -> mehrere orgId=...-Parameter
            "page": page,
            "perPage": per_page,
        })
        events = data.get("events", [])
        all_events.extend(events)

        total = data.get("totalNumberOfResources", len(all_events))
        if len(all_events) >= total or not events:
            break
        page += 1

    return all_events


# Eventfrog unterscheidet Veranstaltung (type=default) und Attraktion
# (type=attractionOriginal / attractionInstance). Attraktionen haben
# Öffnungszeiten; die Public API liefert daraus oft einen Eintrag pro Tag.
# Coucou/MuS/Guidle sollen nur Veranstaltungen enthalten.
ATTRACTION_TYPE_VALUES = frozenset(
    (
        "attraction",
        "attractionoriginal",
        "attractioninstance",
        "attraktion",
    )
)

# Bekannte Museums-Öffnungszeiten, falls die Public API kein type-Feld liefert.
EXCLUDED_ATTRACTION_TITLES = frozenset(
    (
        "erinnerungstank haldengut",
    )
)

# Serie gilt als explodierte Öffnungszeit (nicht als Vortragsreihe):
# gleicher Titel an vielen Tagen und an mehreren Wochentagen, auch Sa/So.
# Eine wöchentliche Reihe trifft nur einen Wochentag und bleibt deshalb drin.
OPENING_HOURS_MIN_DATES = 5
OPENING_HOURS_MIN_WEEKDAYS = 4


def normalize_event_title(event):
    """Titel klein, zusammengeschoben – für Vergleich und Filterlisten."""
    if not isinstance(event, dict):
        return ""
    title = event.get("title")
    if isinstance(title, dict):
        title = pick_lang(title)
    if not title:
        return ""
    return re.sub(r"\s+", " ", str(title).strip().lower())


def _normalize_event_type(value):
    if value is None:
        return ""
    return re.sub(r"[\s_-]+", "", str(value).strip().lower())


def _event_begin_date(event):
    """Kalendertag des Event-Starts oder None."""
    if not isinstance(event, dict):
        return None
    begin = event.get("begin")
    dt = _parse_iso(begin) if begin else None
    if dt is not None:
        return dt.date() if hasattr(dt, "date") else dt

    raw = event.get("date") or ""
    text = str(raw).strip()[:10]
    if len(text) == 10 and text[4] in "-/" and text[7] in "-/":
        try:
            return datetime.strptime(text.replace("/", "-"), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    return None


def is_attraction_event(event):
    """True, wenn das Eventfrog-Objekt eine Attraktion / Öffnungszeit ist.

    Organizer-API-Felder (type, attractionId) werden mitgelesen, auch wenn
    die Public-API-Doku sie nicht auflistet. Zusätzlich: bekannte Titel.
    """
    if not isinstance(event, dict):
        return False

    event_type = _normalize_event_type(
        event.get("type") or event.get("eventType")
    )
    if event_type in ATTRACTION_TYPE_VALUES:
        return True

    attraction_id = event.get("attractionId")
    if attraction_id not in (None, "", 0, "0"):
        return True
    if event.get("attraction") is True or event.get("isAttraction") is True:
        return True

    url = str(event.get("url") or "").lower()
    if any(
        part in url
        for part in ("/attraktionen/", "/attractions/", "/attraction/")
    ):
        return True

    title = normalize_event_title(event)
    return any(excluded in title for excluded in EXCLUDED_ATTRACTION_TITLES if excluded)


def opening_hours_attraction_titles(events):
    """Titel, die wie täglich explodierte Museums-Öffnungszeiten aussehen.

    Eine echte Veranstaltungsreihe (Käfele, Vortrag, Führung) hat wenige
    Termine oder nur einen Wochentag. Ausstellungen mit täglicher Öffnung
    stehen oft Mittwoch bis Sonntag zur gleichen Uhrzeit im Kalender.
    """
    buckets = defaultdict(lambda: {"dates": set(), "weekdays": set()})
    for event in events or []:
        title = normalize_event_title(event)
        if not title:
            continue
        day = _event_begin_date(event)
        if day is None:
            continue
        time_start = ""
        if event.get("begin"):
            time_start = iso_to_time_str(event.get("begin")) or ""
        elif event.get("time_start"):
            time_start = str(event.get("time_start") or "")
        key = (title, time_start)
        buckets[key]["dates"].add(day)
        buckets[key]["weekdays"].add(day.weekday())

    titles = set(EXCLUDED_ATTRACTION_TITLES)
    for (title, _time), info in buckets.items():
        dates = info["dates"]
        if len(dates) < OPENING_HOURS_MIN_DATES:
            continue
        if len(info["weekdays"]) < OPENING_HOURS_MIN_WEEKDAYS:
            continue
        titles.add(title)
    return titles


def filter_attraction_events(events):
    """Entfernt Attraktionen/Öffnungszeiten, behält Veranstaltungen.

    Gibt (veranstaltungen, anzahl_entfernt) zurück.
    """
    excluded_titles = opening_hours_attraction_titles(events)
    kept = []
    skipped = 0
    for event in events or []:
        title = normalize_event_title(event)
        if is_attraction_event(event) or title in excluded_titles:
            skipped += 1
            continue
        kept.append(event)
    return kept, skipped


def get_rubrics(api_key):
    """Holt alle Event-Rubriken (Kategorien) und gibt ein Dict
    rubricId -> Rubrik-Objekt zurück."""
    data = api_get("/public/v1/rubrics", {"apiKey": api_key})
    return {r["id"]: r for r in data.get("rubrics", [])}


def get_locations(api_key, location_ids):
    """Holt Location-Details für Location-IDs.

    Zuerst in kleinen Batches, bei Fehler einzeln mit Retry – damit ein
    Gateway-Timeout nicht alle Adressfelder verwirft.
    """
    location_ids = [lid for lid in location_ids if lid]
    locations_by_id = {}
    if not location_ids:
        return locations_by_id

    def _store(data):
        for loc in data.get("locations", []):
            locations_by_id[loc["id"]] = loc

    # Kleine Batches sind auf shared Hosting zuverlässiger als 100er-Pakete
    batch_size = 10
    failed_ids = []

    for i in range(0, len(location_ids), batch_size):
        batch = location_ids[i:i + batch_size]
        try:
            data = api_get(
                "/public/v1/locations",
                {"apiKey": api_key, "id": batch},
                timeout=90,
                retries=3,
            )
            _store(data)
        except (requests.exceptions.RequestException, RuntimeError):
            failed_ids.extend(batch)

    # Einzelabruf als Fallback für fehlgeschlagene Batches
    for loc_id in failed_ids:
        try:
            data = api_get(
                "/public/v1/locations",
                {"apiKey": api_key, "id": [loc_id]},
                timeout=90,
                retries=3,
            )
            _store(data)
        except (requests.exceptions.RequestException, RuntimeError) as exc:
            print(
                f"Warnung: Location {loc_id} konnte nicht geladen werden ({exc})."
            )

    return locations_by_id


# ---------------------------------------------------------------------
# Hilfsfunktionen: Datenaufbereitung
# ---------------------------------------------------------------------
def pick_lang(value):
    """Wählt aus einem mehrsprachigen Eventfrog-Feld (Dict wie
    {'de': '...', 'en': '...'}) den bevorzugten Sprachwert aus.
    Gibt None zurück, wenn kein Text vorhanden ist."""
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for lang in PREFERRED_LANGUAGES:
            text = value.get(lang)
            if text:
                return text
        # Fallback: irgendeinen vorhandenen, nicht-leeren Wert nehmen
        for text in value.values():
            if text:
                return text
    return None


def strip_html(html_text):
    """Entfernt HTML-Tags aus einem String (einfache Variante,
    für Coucou 'description' als Freitext)."""
    if not html_text:
        return None
    text = re.sub(r"<[^>]+>", "", html_text)
    return re.sub(r"\s+", " ", text).strip() or None


def _split_iso_offset(iso_string):
    """Zerlegt einen ISO-String in (rumpf, offset) für Parser-Fallbacks.

    offset ist z.B. '+02:00', '+0200', 'Z' oder ''.
    """
    s = str(iso_string).strip()
    if not s:
        return "", ""

    if s.endswith(("Z", "z")):
        return s[:-1], "Z"

    m = re.search(r"([+-]\d{2}:?\d{2})$", s)
    if m:
        return s[:m.start()], m.group(1)
    return s, ""


def _parse_iso(iso_string):
    """Parst ein ISO-8601-Datum/Zeit robust für ältere Hosting-Pythons.

    Wichtig:
    - datetime.fromisoformat gibt es erst ab Python 3.7 und versteht 'Z'
      erst ab 3.11
    - strptime %z versteht auf alten Pythons oft nur +0200 (ohne ':')
    - Bei Parse-Fehlern: None statt Exception (Cron soll nicht sterben)
    """
    if not iso_string:
        return None

    raw = str(iso_string).strip()
    if not raw:
        return None

    body, offset = _split_iso_offset(raw)

    # Varianten für fromisoformat (mag +02:00) und strptime (mag oft +0200)
    if offset in ("Z", "z"):
        offset_colon = "+00:00"
        offset_compact = "+0000"
    elif offset and ":" in offset:
        offset_colon = offset
        offset_compact = offset.replace(":", "")
    elif offset:
        offset_colon = offset[:3] + ":" + offset[3:]
        offset_compact = offset
    else:
        offset_colon = ""
        offset_compact = ""

    candidates = []
    if offset_colon:
        candidates.append(body + offset_colon)
    candidates.append(raw)
    if body and body not in candidates:
        candidates.append(body)

    # 1) fromisoformat, falls vorhanden – AttributeError auf Python < 3.7 abfangen
    fromisoformat = getattr(datetime, "fromisoformat", None)
    if fromisoformat is not None:
        for candidate in candidates:
            try:
                return fromisoformat(candidate)
            except (ValueError, TypeError):
                continue

    # 2) strptime-Fallbacks (auch Python 3.6)
    strptime_candidates = []
    if offset_compact:
        strptime_candidates.append(body + offset_compact)
    strptime_candidates.append(body)

    for candidate in strptime_candidates:
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            # %z nur verwenden, wenn der Candidate auch einen Offset hat
            if "%z" in fmt and not re.search(r"[+-]\d{4}$", candidate):
                continue
            try:
                return datetime.strptime(candidate, fmt)
            except (ValueError, TypeError):
                continue

    return None


def iso_to_date_str(iso_string):
    """Wandelt ein ISO-8601-Datum/Zeit (z.B. '2024-07-15T19:00:00+02:00')
    in das Coucou-Format 'YYYY/MM/DD' um."""
    try:
        dt = _parse_iso(iso_string)
        if dt:
            return dt.strftime("%Y/%m/%d")
    except Exception:
        # Absolute Absicherung für den Cron: nie wegen eines Datums crashen
        pass

    # Letzter Fallback: YYYY-MM-DD aus den ersten 10 Zeichen ziehen
    s = str(iso_string or "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[0:4] + "/" + s[5:7] + "/" + s[8:10]
    return None


def iso_to_time_str(iso_string):
    """Wandelt ein ISO-8601-Datum/Zeit in das Coucou-Zeitformat 'HH:mm' um."""
    try:
        dt = _parse_iso(iso_string)
        if dt:
            return dt.strftime("%H:%M")
    except Exception:
        pass
    return None


def map_rubric_to_category(rubric_id, rubrics_by_id):
    """Mappt eine Eventfrog rubricId auf eine Coucou category-ID,
    basierend auf dem (deutschen) Rubrik-Namen. Best-Effort - siehe
    Hinweis am Dateianfang."""
    rubric = rubrics_by_id.get(rubric_id)
    rubric_name = pick_lang(rubric.get("title")) if rubric else None

    if rubric_name:
        name_lower = rubric_name.lower()
        for keyword, coucou_id in RUBRIC_NAME_TO_COUCOU_CATEGORY:
            if keyword in name_lower:
                return coucou_id

    return DEFAULT_COUCOU_CATEGORY


def build_coucou_event(event, rubrics_by_id, locations_by_id):
    """Baut aus einem Eventfrog-Event-Objekt ein Dict im Coucou-Schema.

    Kurz- und Langbeschreibung werden beide gesetzt (coucou_export und
    mus_export identisch):
      description       – Kurzbeschreibung (Coucou-Feld, shortDescription)
      description_long  – Eventbeschreibung als Klartext
      description_html  – Eventbeschreibung als HTML
    """
    begin = event.get("begin")
    end = event.get("end")

    emblem = event.get("emblemToShow")
    image_url = emblem.get("url") if isinstance(emblem, dict) else None

    short_description = pick_lang(event.get("shortDescription"))
    description_html = pick_lang(event.get("descriptionAsHTML"))
    description_long = strip_html(description_html) if description_html else None

    # Coucou-Feld "description": Kurzbeschreibung (Fallback: Langtext)
    description = short_description or description_long

    coucou_event = {
        "reference": event.get("id"),
        "title": pick_lang(event.get("title")),
        "description": description,
        "image": image_url,
        "url": event.get("url"),
        "date": iso_to_date_str(begin),
        "time_start": iso_to_time_str(begin),
        "time_end": iso_to_time_str(end),
        "fee": event.get("lowestTicketPrice"),
        "presale": event.get("presaleLink"),
        "category": map_rubric_to_category(event.get("rubricId"), rubrics_by_id),
    }

    if description_long:
        coucou_event["description_long"] = description_long
    if description_html:
        coucou_event["description_html"] = description_html

    # date_end nur setzen, wenn Start- und Enddatum tatsächlich unterschiedlich sind
    date_begin = iso_to_date_str(begin)
    date_end = iso_to_date_str(end)
    if date_end and date_end != date_begin:
        coucou_event["date_end"] = date_end

    # Location: erste referenzierte Location verwenden (falls vorhanden)
    location_ids = event.get("locationIds") or []
    location = None
    if location_ids and isinstance(location_ids, list):
        location = locations_by_id.get(location_ids[0])
    if location:
        coucou_event["location_name"] = pick_lang(location.get("title"))
        coucou_event["location_street"] = location.get("addressLine")
        coucou_event["location_zip"] = location.get("zip")
        coucou_event["location_city"] = location.get("city")
        coucou_event["location_website"] = location.get("websiteUrl")

    # Nicht verfügbare Felder (siehe Hinweis am Dateianfang):
    # "weekdays", "fee_options", "attachments" -> von Eventfrog nicht geliefert

    # Leere/None-Werte entfernen, damit der Export sauber bleibt
    return {k: v for k, v in coucou_event.items() if v not in (None, "", [])}


def select_upcoming_events(events, limit=HVW_HOME_EVENT_LIMIT):
    """Wählt die nächsten kommenden Events (ab heute), chronologisch sortiert."""
    today = datetime.now().strftime("%Y-%m-%d")
    upcoming = []

    for event in events:
        if event.get("cancelled"):
            continue
        begin = event.get("begin") or ""
        date_part = str(begin)[:10]
        if len(date_part) == 10 and date_part >= today:
            upcoming.append(event)

    upcoming.sort(key=lambda e: e.get("begin") or "")
    return upcoming[:limit]


def build_home_event(event, locations_by_id):
    """Kompaktes Event-Objekt für die HVW-Titelseite (#home-events-preview).

    Schema angelehnt an fetch-events.mjs / data/home-events.json:
    id, title, begin, url, organizerName, location.
    """
    location_label = ""
    location_ids = event.get("locationIds") or []
    if location_ids and isinstance(location_ids, list):
        location = locations_by_id.get(location_ids[0])
        if location:
            parts = [
                pick_lang(location.get("title")),
                location.get("city"),
            ]
            location_label = ", ".join([p for p in parts if p])

    if not location_label:
        location_label = event.get("organizerName") or ""

    return {
        "id": str(event.get("id") or ""),
        "title": pick_lang(event.get("title")) or "",
        "begin": event.get("begin") or "",
        "url": event.get("url") or "",
        "organizerName": event.get("organizerName") or "",
        "location": location_label,
        "image": pick_event_image(event),
    }


def build_home_events_payload(events, locations_by_id, limit=HVW_HOME_EVENT_LIMIT):
    """Payload für home-events.json: { generatedAt, events: [...] }."""
    next_events = select_upcoming_events(events, limit=limit)
    items = []
    for event in next_events:
        item = build_home_event(event, locations_by_id)
        if not item.get("image") and item.get("url"):
            item["image"] = fetch_og_image(item["url"])
        items.append(item)
    return {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "eventfrog-hostpoint-cron",
        "events": items,
    }


# ---------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------
def main():
    org_ids = resolve_org_ids()
    httpdocs_dir = resolve_httpdocs_dir()
    export_path = resolve_export_path(httpdocs_dir)

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
        "Rufe Events von Eventfrog ab (Org-IDs: {0}) ...".format(
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
    print("{0} Veranstaltung(en). Lade Rubriken und Locations ...".format(len(events)))

    try:
        rubrics_by_id = get_rubrics(api_key)
    except (requests.exceptions.RequestException, RuntimeError) as exc:
        print(
            "Warnung: Rubriken konnten nicht geladen werden ({0}). "
            "Kategorie-Zuordnung wird übersprungen.".format(exc)
        )
        rubrics_by_id = {}

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
    else:
        if all_location_ids and not locations_by_id:
            print(
                "Warnung: Keine Locations geladen – Adressfelder werden übersprungen."
            )
        elif locations_by_id:
            print(
                "{0}/{1} Location(s) geladen.".format(
                    len(locations_by_id), len(all_location_ids)
                )
            )

    # In Coucou-Format umwandeln – pro Event absichern, damit ein
    # einzelnes Problem den gesamten Cron-Export nicht killt.
    coucou_events = []
    for event in events:
        try:
            coucou_events.append(
                build_coucou_event(event, rubrics_by_id, locations_by_id)
            )
        except Exception as exc:
            print(
                "Warnung: Event {0} übersprungen ({1}: {2}).".format(
                    event.get("id"), type(exc).__name__, exc
                )
            )

    # Öffentlichen Webroot sicherstellen
    try:
        if not os.path.isdir(httpdocs_dir):
            os.makedirs(httpdocs_dir)
    except OSError as exc:
        print(
            "Fehler: Webroot '{0}' nicht schreibbar ({1}).".format(
                httpdocs_dir, exc
            )
        )
        return

    # Export als JSON-Array, wie von Coucou verlangt: [ {event-object}, .. ]
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(coucou_events, f, ensure_ascii=False, indent=2)

    print(
        "\n{0} Event(s) im Coucou-Format gespeichert in '{1}'.".format(
            len(coucou_events), export_path
        )
    )
    try:
        guidle_path = copy_guidle_export(export_path)
        if guidle_path:
            print("Kopie für Guidle gespeichert in '{0}'.".format(guidle_path))
    except OSError as exc:
        print(
            "Warnung: guidle_export.json konnte nicht geschrieben werden ({0}).".format(
                exc
            )
        )
    print("Bitte insbesondere die 'category'-Zuordnung stichprobenartig prüfen.")


if __name__ == "__main__":
    main()
