#!/usr/bin/env python3
"""Ein Redaktions-Login mit bisherigen Freigabe-Rechten."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lib = (ROOT / "redaktion/lib.php").read_text(encoding="utf-8")
serve = (ROOT / "zugang/serve.php").read_text(encoding="utf-8")
index = (ROOT / "redaktion/index.php").read_text(encoding="utf-8")
content = (ROOT / "js/content.js").read_text(encoding="utf-8")

if "function hvw_can_publish" not in lib:
    raise SystemExit("lib.php braucht hvw_can_publish()")
if "'freigabe' =>" in lib and "'name' => 'Freigabe'" in lib:
    raise SystemExit("Separates Freigabe-Login muss entfernt sein")
if "'redaktion' =>" not in lib or "'role' => 'freigabe'" not in lib:
    raise SystemExit("Benutzer redaktion braucht Freigabe-Rechte (role freigabe)")

if "Redaktions-Modus" not in serve:
    raise SystemExit("Eingangsscreen muss Redaktions-Modus heissen")
if "Freigabe" in serve:
    raise SystemExit("Eingangsscreen darf Freigabe-Login nicht mehr erwähnen")

if "Redaktions-Modus" not in index:
    raise SystemExit("Redaktions-Login-Seite muss Redaktions-Modus nennen")

if "20261019-redaktion-login" not in content:
    raise SystemExit("Editor-Asset-Version für Cache-Bust fehlt")

print("ok")
