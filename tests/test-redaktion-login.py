#!/usr/bin/env python3
"""Redaktion: E-Mail-Zugang ersetzt separates Passwort-Login unter /edit/."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
lib = (ROOT / "redaktion/lib.php").read_text(encoding="utf-8")
zugang_lib = (ROOT / "zugang/lib.php").read_text(encoding="utf-8")
api = (ROOT / "redaktion/api.php").read_text(encoding="utf-8")
serve = (ROOT / "zugang/serve.php").read_text(encoding="utf-8")
index = (ROOT / "redaktion/index.php").read_text(encoding="utf-8")
content = (ROOT / "js/content.js").read_text(encoding="utf-8")
zugang_page = (ROOT / "redaktion/zugang.php").read_text(encoding="utf-8")

if "function hvw_can_publish" not in lib:
    raise SystemExit("lib.php braucht hvw_can_publish()")
if "'freigabe' =>" in lib and "'name' => 'Freigabe'" in lib:
    raise SystemExit("Separates Freigabe-Login muss entfernt sein")
if "'redaktion' =>" not in lib or "'role' => 'freigabe'" not in lib:
    raise SystemExit("Benutzer redaktion braucht Freigabe-Rechte (role freigabe)")

if "function hvw_redaktion_session_from_zugang" not in zugang_lib:
    raise SystemExit("zugang/lib.php braucht hvw_redaktion_session_from_zugang()")
if "hvw_redaktion_session_from_zugang()" not in serve:
    raise SystemExit("serve.php muss Redaktions-Session aus Zugang setzen")
if "hvw_redaktion_session_from_zugang()" not in api:
    raise SystemExit("api.php muss Redaktions-Session aus Zugang setzen")
if "hvw_zugang_clear_cookie()" not in api:
    raise SystemExit("Logout muss E-Mail-Zugang beenden")

if "Redaktions-Modus" not in serve:
    raise SystemExit("Eingangsscreen muss Redaktions-Modus heissen")
if "Freigabe" in serve:
    raise SystemExit("Eingangsscreen darf Freigabe-Login nicht mehr erwähnen")
if "direkt Texte bearbeiten" not in serve:
    raise SystemExit("Eingangsscreen muss direkte Bearbeitung erwähnen")

if "hvw_zugang_ok()" not in index:
    raise SystemExit("index.php muss bei gültigem Zugang weiterleiten")

if "Redaktions-Modus" not in index:
    raise SystemExit("Redaktions-Login-Seite muss Redaktions-Modus nennen")

if "showLoginInvite" in content:
    raise SystemExit("Grüne Anmelde-Leiste muss entfernt sein")
if "20261020-edit-auto-redaktion" not in content:
    raise SystemExit("Editor-Asset-Version für Cache-Bust fehlt")

if "Benutzername <strong>redaktion</strong>" in zugang_page:
    raise SystemExit("zugang.php darf separates Redaktions-Passwort nicht mehr erwähnen")

migrate = (ROOT / "scripts/migrate-redaktion-config-local.php").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/migrate-redaktion-config.yml").read_text(encoding="utf-8")
if "unset($users['freigabe'])" not in migrate:
    raise SystemExit("Migrations-Skript muss freigabe entfernen")
if "migrate-redaktion-config-local.php" not in workflow:
    raise SystemExit("Workflow migrate-redaktion-config fehlt")

print("ok")
