#!/usr/bin/env python3
"""Mitmachen: Beteiligungskarten mit vorgefüllter Mail, ohne graue Webling-Box."""
from pathlib import Path
from urllib.parse import unquote

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

expected = {
    "ursina.largiader@hvwinterthur.ch": "Kulturvermittler/Laienführer Mörsburg",
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
    if block.count(part) < 3:
        raise SystemExit(f"Mail-Vorlage unvollständig: {part}")
if "Teilweise entschädigt" not in block or block.count("Ehrenamtlich") < 2:
    raise SystemExit("Einsatzart fehlt")
print("mitmachen beteiligung ok")
print(unquote("Kulturvermittler/Laienf%C3%BChrer%20M%C3%B6rsburg"))
