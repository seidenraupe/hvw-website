#!/usr/bin/env python3
"""Mitmachen: Beteiligungskarten mit vorgefüllter Mail, ohne graue Webling-Box."""
from pathlib import Path

html = (Path(__file__).resolve().parents[1] / "mitmachen.html").read_text(encoding="utf-8")
if "Online-Anmeldung über Webling" in html or "bg-hvw-fog p-5" in html:
    raise SystemExit("graue Erklärungsbox ist wieder da")
if not (
    html.find('id="beitraege-heading"')
    < html.find('id="anmelde-heading"')
    < html.find('id="beteiligung-heading"')
    < html.find("</main>")
):
    raise SystemExit("Reihenfolge: Kategorien, Anmeldeformular, Beteiligung am Seitenende")
if "Laienführer" in html or "Kulturvermittler" in html or "ursina.largiader" in html:
    raise SystemExit("Laienführer/Kultur-Vermittler darf nicht mehr auf Mitmachen stehen")

expected = {
    "josip.spec@hvwinterthur.ch": "Katalogisierung der Sammlung",
    "christian.huggenberg@hvwinterthur.ch": "Vereinsvorstand",
}
for addr, needle in expected.items():
    if f"mailto:{addr}?" not in html:
        raise SystemExit(f"Mail-Adresse fehlt: {addr}")
    if needle not in html:
        raise SystemExit(f"Kartentext fehlt: {needle}")

start = html.find('id="beteiligung-heading"')
end = html.find("</main>", start)
block = html[start:end]
for part in ("subject=", "body=", "Guten%20Tag", "Interesse melden"):
    if block.count(part) < 2:
        raise SystemExit(f"Mail-Vorlage unvollständig: {part}")
if "Teilweise entschädigt" in block:
    raise SystemExit("entschädigte Laienführer-Karte ist noch da")
if block.count("Ehrenamtlich") < 2:
    raise SystemExit("Einsatzart fehlt")
print("mitmachen beteiligung ok")
