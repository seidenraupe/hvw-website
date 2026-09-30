#!/usr/bin/env python3
"""
Programm-PDF aus Eventfrog (alle HVW-Org-IDs)
=============================================

A4-Hochformat mit:
  - Kompakter Kopf (Logo, Titel, drei Museumsfotos)
  - Alle Anlässe ab Druckdatum (kein Halbjahres-Schnitt)
  - Monatszeile: Druckmonat bis letzte Veranstaltung
  - Teaser-Bild, Kalenderblatt, Titel, Kurztext, Ort

Org-IDs (Default): 4936116, 5116588, 5137433

API-Key:
  EVENTFROG_API_KEY oder Datei cronjobs/eventfrog_api_key

Usage:
  EVENTFROG_API_KEY=... python3 scripts/generate-programm-pdf.py
  python3 scripts/generate-programm-pdf.py -o programm/Programm.pdf
"""

from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timezone

import requests
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    Flowable,
    HRFlowable,
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "cronjobs"))
from eventfrog_to_coucou import filter_attraction_events  # noqa: E402
DEFAULT_OUTPUT = os.path.join(ROOT_DIR, "programm", "Programm.pdf")
DEFAULT_LOGO = os.path.join(ROOT_DIR, "images", "hvw-logo.png")
DEFAULT_ORG_IDS = ["4936116", "5116588", "5137433"]
MUSEUM_PHOTOS = [
    (
        os.path.join(ROOT_DIR, "images", "museen", "museum-schaffen.jpg"),
        "Museum Schaffen",
    ),
    (
        os.path.join(ROOT_DIR, "images", "museen", "museum-lindengut.jpg"),
        "Museum Lindengut",
    ),
    (
        os.path.join(ROOT_DIR, "images", "museen", "schloss-moersburg.jpg"),
        "Schloss Mörsburg",
    ),
]
API_BASE = "https://api.eventfrog.net"
API_KEY_ENV = "EVENTFROG_API_KEY"
PREFERRED_LANGUAGES = ["de", "de_CH", "en", "fr", "it"]

HVW_INK = colors.HexColor("#1a1a1a")
HVW_MUTE = colors.HexColor("#4a4a4a")
HVW_FOG = colors.HexColor("#f3f3f3")
HVW_ACCENT = colors.HexColor("#c8102e")
HVW_LINE = colors.HexColor("#1a1a1a")

WEEKDAYS_DE = [
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
]
WEEKDAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS_DE = [
    "",
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]
MONTHS_SHORT = [
    "",
    "JAN",
    "FEB",
    "MÄR",
    "APR",
    "MAI",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OKT",
    "NOV",
    "DEZ",
]


def pick_lang(value):
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for lang in PREFERRED_LANGUAGES:
            text = value.get(lang)
            if text:
                return text
        for text in value.values():
            if text:
                return text
    return None


def strip_html(html_text):
    if not html_text:
        return None
    text = re.sub(r"<[^>]+>", " ", html_text)
    return re.sub(r"\s+", " ", text).strip() or None


def escape_xml(text):
    if not text:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def load_api_key():
    env_key = os.environ.get(API_KEY_ENV, "").strip()
    if env_key:
        return env_key
    candidates = [
        os.path.join(ROOT_DIR, "cronjobs", "eventfrog_api_key"),
        os.path.join(SCRIPT_DIR, "eventfrog_api_key"),
    ]
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        name, value = line.split("=", 1)
                        if name.strip() in (API_KEY_ENV, "API_KEY") and value.strip():
                            return value.strip().strip('"').strip("'")
                        continue
                    return line
        except OSError:
            continue
    return None


def api_get(path, params, api_key, timeout=60):
    url = "{0}{1}".format(API_BASE, path)
    query = dict(params)
    query["apiKey"] = api_key
    response = requests.get(url, params=query, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(
            "Eventfrog API {0}: HTTP {1}\n{2}".format(
                path, response.status_code, response.text[:500]
            )
        )
    return response.json()


def get_all_events(org_ids, api_key, date_from=None):
    all_events = []
    page = 1
    per_page = 100
    while True:
        params = {"orgId": org_ids, "page": page, "perPage": per_page}
        if date_from:
            params["from"] = date_from
        data = api_get("/public/v1/events", params, api_key)
        events = data.get("events", [])
        all_events.extend(events)
        total = data.get("totalNumberOfResources", len(all_events))
        if len(all_events) >= total or not events:
            break
        page += 1
    return all_events


def get_locations(api_key, location_ids):
    location_ids = [lid for lid in location_ids if lid]
    by_id = {}
    if not location_ids:
        return by_id
    batch_size = 20
    for i in range(0, len(location_ids), batch_size):
        batch = location_ids[i : i + batch_size]
        data = api_get("/public/v1/locations", {"id": batch}, api_key)
        for loc in data.get("locations", []):
            by_id[loc["id"]] = loc
    return by_id


def parse_iso(iso_string):
    if not iso_string:
        return None
    raw = str(iso_string).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            candidate = raw.replace("+02:00", "+0200").replace("+01:00", "+0100")
            return datetime.strptime(candidate, fmt)
        except Exception:
            continue
    return None


def month_name(d):
    return MONTHS_DE[d.month].upper()


def format_period_label(print_on, last_event_on):
    """Monatszeile: Druckdatum bis letzte sichtbare Veranstaltung."""
    if last_event_on < print_on:
        last_event_on = print_on
    if print_on.year == last_event_on.year and print_on.month == last_event_on.month:
        return month_name(print_on)
    if print_on.year == last_event_on.year:
        return "{0} BIS {1}".format(month_name(print_on), month_name(last_event_on))
    return "{0} {1} BIS {2} {3}".format(
        month_name(print_on),
        print_on.year,
        month_name(last_event_on),
        last_event_on.year,
    )


def program_year_label(print_on, last_event_on):
    if last_event_on.year == print_on.year:
        return str(print_on.year)
    return "{0}/{1}".format(print_on.year, str(last_event_on.year)[2:])


def download_basename(print_on, last_event_on):
    """Dateiname ohne Pfad-Slash: «Programm HVW MM.JJJJ bis MM.JJJJ».

    Schrägstriche (08/2026) würden im Browser-Download nur «2026.pdf» speichern.
    """
    if last_event_on < print_on:
        last_event_on = print_on
    return "Programm HVW {0:02d}.{1} bis {2:02d}.{3}".format(
        print_on.month,
        print_on.year,
        last_event_on.month,
        last_event_on.year,
    )


def last_event_date(events, fallback):
    latest = fallback
    for event in events:
        begin_dt = parse_iso(event.get("begin"))
        if begin_dt and begin_dt.date() > latest:
            latest = begin_dt.date()
    return latest


def select_upcoming_events(events, today=None):
    """Alle nicht abgesagten Anlässe ab Druckdatum, ohne Halbjahres-Schnitt."""
    today = today or date.today()
    selected = []
    for event in events:
        if event.get("cancelled"):
            continue
        begin_dt = parse_iso(event.get("begin"))
        if not begin_dt:
            continue
        if begin_dt.date() >= today:
            selected.append(event)
    selected.sort(key=lambda e: e.get("begin") or "")
    return selected


def format_location(location):
    if not location:
        return ""
    title = pick_lang(location.get("title"))
    street = location.get("addressLine") or ""
    zip_code = location.get("zip") or ""
    city = location.get("city") or ""
    addr = ", ".join(
        [p for p in [street, "{0} {1}".format(zip_code, city).strip()] if p]
    )
    if title and addr:
        return "{0}, {1}".format(title, addr)
    return title or addr


def pick_image_url(event):
    emblem = event.get("emblemToShow")
    if isinstance(emblem, dict) and emblem.get("url"):
        return emblem["url"]
    for key in ("image", "flyer"):
        val = event.get(key)
        if isinstance(val, dict) and val.get("url"):
            return val["url"]
        if isinstance(val, str) and val.startswith("http"):
            return val
    return None


def download_image_as_jpeg(url, cache_dir, max_edge=900):
    """Lädt Teaser (auch WebP) und speichert als JPEG für ReportLab."""
    if not url:
        return None
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    out_path = os.path.join(cache_dir, "{0}.jpg".format(digest))
    if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
        return out_path
    try:
        response = requests.get(
            url,
            timeout=45,
            headers={"User-Agent": "HVW-programm-pdf/1.0"},
        )
        response.raise_for_status()
        im = PILImage.open(io.BytesIO(response.content))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        elif im.mode == "L":
            im = im.convert("RGB")
        try:
            resample = PILImage.Resampling.LANCZOS
        except AttributeError:
            resample = PILImage.LANCZOS
        im.thumbnail((max_edge, max_edge), resample)
        im.save(out_path, "JPEG", quality=85, optimize=True)
        return out_path
    except Exception as exc:
        print("Warnung: Bild nicht ladbar ({0}): {1}".format(url[:80], exc))
        return None


class CalendarLeaf(Flowable):
    """Kalenderblatt mit Monat, Tag, Wochentag und Uhrzeit."""

    def __init__(self, begin_dt, end_dt=None, width=28 * mm, height=36 * mm):
        Flowable.__init__(self)
        self.begin_dt = begin_dt
        self.end_dt = end_dt
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        w, h = self.width, self.height
        header_h = 7.5 * mm
        # Blatt-Schatten
        c.setFillColor(colors.Color(0, 0, 0, alpha=0.08))
        c.rect(1.2, -1.2, w, h, fill=1, stroke=0)
        # Blattkörper
        c.setFillColor(colors.white)
        c.setStrokeColor(HVW_INK)
        c.setLineWidth(1)
        c.roundRect(0, 0, w, h, 2.5, fill=1, stroke=1)
        # Monatskopf (Akzent)
        c.setFillColor(HVW_ACCENT)
        c.rect(0, h - header_h, w, header_h, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8)
        month = MONTHS_SHORT[self.begin_dt.month] if self.begin_dt else "—"
        c.drawCentredString(w / 2, h - header_h + 2.4 * mm, month)
        # Binderinge / Kalenderperforation
        c.setFillColor(colors.white)
        for x in (w * 0.28, w * 0.72):
            c.circle(x, h - 1.4 * mm, 1.3, fill=1, stroke=0)
            c.setStrokeColor(HVW_INK)
            c.setLineWidth(0.6)
            c.circle(x, h - 1.4 * mm, 1.3, fill=0, stroke=1)
            c.setFillColor(colors.white)
        # Tageszahl
        c.setFillColor(HVW_INK)
        c.setFont("Helvetica-Bold", 22)
        day = "{0}".format(self.begin_dt.day) if self.begin_dt else "–"
        c.drawCentredString(w / 2, h - header_h - 11 * mm, day)
        # Wochentag
        c.setFont("Helvetica", 7.5)
        c.setFillColor(HVW_MUTE)
        wd = WEEKDAYS_DE[self.begin_dt.weekday()] if self.begin_dt else ""
        c.drawCentredString(w / 2, 9.5 * mm, wd)
        # Trennlinie
        c.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
        c.setLineWidth(0.5)
        c.line(3 * mm, 8 * mm, w - 3 * mm, 8 * mm)
        # Zeit
        c.setFillColor(HVW_INK)
        c.setFont("Helvetica-Bold", 8)
        time_label = self._time_label()
        c.drawCentredString(w / 2, 3.2 * mm, time_label)

    def _time_label(self):
        if not self.begin_dt:
            return ""
        start = self.begin_dt.strftime("%H:%M")
        if (
            self.end_dt
            and self.end_dt.date() == self.begin_dt.date()
            and self.end_dt.strftime("%H:%M") != start
        ):
            return "{0}–{1}".format(start, self.end_dt.strftime("%H:%M"))
        return "{0} Uhr".format(start)


class ImageOrPlaceholder(Flowable):
    """Teaserbild oder neutrale Platzhalterfläche."""

    def __init__(self, path, width, height):
        Flowable.__init__(self)
        self.path = path
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.setStrokeColor(HVW_INK)
        c.setLineWidth(0.6)
        if self.path and os.path.isfile(self.path):
            try:
                c.drawImage(
                    self.path,
                    0,
                    0,
                    width=self.width,
                    height=self.height,
                    preserveAspectRatio=True,
                    anchor="c",
                    mask="auto",
                )
                c.rect(0, 0, self.width, self.height, fill=0, stroke=1)
                return
            except Exception:
                pass
        c.setFillColor(HVW_FOG)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=1)
        c.setFillColor(HVW_MUTE)
        c.setFont("Helvetica", 8)
        c.drawCentredString(self.width / 2, self.height / 2 - 3, "Bild folgt")


def build_styles():
    styles = getSampleStyleSheet()
    return {
        "period": ParagraphStyle(
            "Period",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=HVW_MUTE,
            alignment=2,
            spaceAfter=0,
        ),
        "prog": ParagraphStyle(
            "ProgTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=HVW_INK,
            alignment=2,
            spaceBefore=0,
            spaceAfter=1,
        ),
        "title": ParagraphStyle(
            "EventTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=HVW_INK,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "EventBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=HVW_MUTE,
            spaceAfter=3,
        ),
        "loc": ParagraphStyle(
            "EventLoc",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=HVW_INK,
        ),
        "caption": ParagraphStyle(
            "MuseumCaption",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=HVW_MUTE,
            alignment=1,
            spaceBefore=1.5,
        ),
    }


def make_cover(styles, logo_path, year, period_label):
    """Kompakter Kopf nur auf der ersten Seite — Programm folgt ohne Seitenumbruch."""
    parts = []
    title_block = [
        Paragraph("PROGRAMM {0}".format(year), styles["prog"]),
        Paragraph(escape_xml(period_label), styles["period"]),
    ]
    if logo_path and os.path.isfile(logo_path):
        logo_w = 46 * mm
        logo_h = logo_w * (163 / 715.0)
        logo = Image(logo_path, width=logo_w, height=logo_h)
        header = Table(
            [[logo, title_block]],
            colWidths=[52 * mm, None],
        )
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        parts.append(header)
    else:
        parts.extend(title_block)

    parts.append(Spacer(1, 2.5 * mm))
    parts.append(
        HRFlowable(width="100%", thickness=0.8, color=HVW_INK, spaceAfter=3 * mm)
    )

    photo_w = 47 * mm
    photo_h = 27 * mm
    cells = []
    for path, label in MUSEUM_PHOTOS:
        cell = []
        if path and os.path.isfile(path):
            cell.append(Image(path, width=photo_w, height=photo_h))
        else:
            cell.append(Spacer(photo_w, photo_h))
        cell.append(Paragraph(escape_xml(label), styles["caption"]))
        cells.append(cell)

    table = Table([cells], colWidths=[56 * mm, 56 * mm, 56 * mm], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    parts.append(table)
    parts.append(Spacer(1, 2 * mm))
    parts.append(
        HRFlowable(width="100%", thickness=0.8, color=HVW_INK, spaceAfter=4 * mm)
    )
    return parts


def make_event_block(event, locations_by_id, image_path, styles):
    begin_dt = parse_iso(event.get("begin"))
    end_dt = parse_iso(event.get("end"))
    title = pick_lang(event.get("title")) or "Ohne Titel"
    short = pick_lang(event.get("shortDescription"))
    long_plain = strip_html(pick_lang(event.get("descriptionAsHTML")))
    detail = short or (
        (long_plain[:260] + "…") if long_plain and len(long_plain) > 260 else long_plain
    )
    loc_label = ""
    loc_ids = event.get("locationIds") or []
    if loc_ids:
        loc_label = format_location(locations_by_id.get(loc_ids[0]))

    cal = CalendarLeaf(begin_dt, end_dt, width=26 * mm, height=34 * mm)
    img = ImageOrPlaceholder(image_path, width=48 * mm, height=34 * mm)

    text_bits = [
        Paragraph(escape_xml(title), styles["title"]),
    ]
    if detail:
        text_bits.append(Paragraph(escape_xml(detail), styles["body"]))
    if loc_label:
        text_bits.append(Paragraph(escape_xml(loc_label), styles["loc"]))
    text_cell = text_bits

    # [Kalender | Bild | Text]
    table = Table(
        [[cal, img, text_cell]],
        colWidths=[28 * mm, 50 * mm, None],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 3 * mm),
                ("RIGHTPADDING", (1, 0), (1, 0), 3.5 * mm),
                ("RIGHTPADDING", (2, 0), (2, 0), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ]
        )
    )
    return KeepTogether(
        [
            table,
            Spacer(1, 2.5 * mm),
            HRFlowable(
                width="100%",
                thickness=0.4,
                color=colors.Color(0.85, 0.85, 0.85),
                spaceAfter=3.5 * mm,
            ),
        ]
    )


def draw_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(HVW_INK)
    canvas.setLineWidth(0.6)
    y_line = 16 * mm
    canvas.line(doc.leftMargin, y_line + 6 * mm, A4[0] - doc.rightMargin, y_line + 6 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HVW_MUTE)
    canvas.drawString(doc.leftMargin, y_line, "Historischer Verein Winterthur")
    canvas.drawRightString(A4[0] - doc.rightMargin, y_line, "www.hvwinterthur.ch")
    canvas.drawString(doc.leftMargin, y_line - 4 * mm, "Römerstrasse 8, 8400 Winterthur")
    canvas.drawRightString(A4[0] - doc.rightMargin, y_line - 4 * mm, "info@hvwinterthur.ch")
    page_num = canvas.getPageNumber()
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(A4[0] / 2, 8 * mm, str(page_num))
    canvas.restoreState()


def write_pdf(path, events, locations_by_id, image_paths, year, period_label, logo_path, title=None):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    doc = BaseDocTemplate(
        path,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=12 * mm,
        bottomMargin=22 * mm,
        title=title or "Programm HVW",
        author="Historischer Verein Winterthur",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=frame, onPage=draw_footer)])

    styles = build_styles()
    story = make_cover(styles, logo_path, year, period_label)
    for event in events:
        img_path = image_paths.get(str(event.get("id")))
        story.append(make_event_block(event, locations_by_id, img_path, styles))
    doc.build(story)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Programm-PDF aus Eventfrog")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--org-ids", default=",".join(DEFAULT_ORG_IDS))
    parser.add_argument("--logo", default=DEFAULT_LOGO)
    args = parser.parse_args(argv)

    api_key = load_api_key()
    if not api_key:
        print(
            "Fehler: EVENTFROG_API_KEY fehlt (Env oder cronjobs/eventfrog_api_key).",
            file=sys.stderr,
        )
        return 1

    org_ids = [x.strip() for x in args.org_ids.split(",") if x.strip()]
    print_on = date.today()
    print(
        "Alle Anlässe ab Druckdatum {0}, Org-IDs: {1}".format(
            print_on.isoformat(), ", ".join(org_ids)
        )
    )

    events = get_all_events(org_ids, api_key, date_from=print_on.isoformat())
    events, skipped_openings = filter_attraction_events(events)
    if skipped_openings:
        print(
            "{0} Öffnungszeit(en)/Attraktion(en) entfernt.".format(skipped_openings)
        )
    events = select_upcoming_events(events, print_on)
    last_on = last_event_date(events, print_on)
    period_label = format_period_label(print_on, last_on)
    year_label = program_year_label(print_on, last_on)
    slug = "{0}_{1:02d}".format(print_on.year, print_on.month)
    download_name = download_basename(print_on, last_on) + ".pdf"
    print("{0} Veranstaltung(en), Periode «{1}».".format(len(events), period_label))

    loc_ids = set()
    for event in events:
        for lid in event.get("locationIds") or []:
            loc_ids.add(lid)
    locations_by_id = get_locations(api_key, list(loc_ids))

    cache_dir = tempfile.mkdtemp(prefix="hvw-pdf-img-")
    image_paths = {}
    print("Lade Teaser-Bilder …")
    for event in events:
        url = pick_image_url(event)
        path = download_image_as_jpeg(url, cache_dir) if url else None
        image_paths[str(event.get("id"))] = path
        status = "ok" if path else "fehlt"
        print("  [{0}] {1}".format(status, pick_lang(event.get("title")) or event.get("id")))

    out_path = os.path.abspath(args.output)
    write_pdf(
        out_path,
        events,
        locations_by_id,
        image_paths,
        year_label,
        period_label,
        args.logo,
        title=download_basename(print_on, last_on),
    )
    print("PDF geschrieben: {0} ({1} Bytes)".format(out_path, os.path.getsize(out_path)))

    meta_path = os.path.splitext(out_path)[0] + ".json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "printOn": print_on.isoformat(),
                "lastEventOn": last_on.isoformat(),
                "year": year_label,
                "periodLabel": period_label,
                "slug": slug,
                "eventCount": len(events),
                "format": "A4",
                "file": os.path.basename(out_path),
                "downloadName": download_name,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
        f.write("\n")
    print("Meta: {0}".format(meta_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
