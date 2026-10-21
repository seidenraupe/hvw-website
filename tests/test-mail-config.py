#!/usr/bin/env python3
"""Microsoft 365 / noreply@ für Edit-Zugangscodes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
example = (ROOT / "redaktion/config.mail.example.php").read_text(encoding="utf-8")
lib = (ROOT / "zugang/lib.php").read_text(encoding="utf-8")

if "smtp.office365.com" not in deploy:
    raise SystemExit("Deploy-Default muss smtp.office365.com sein")
if "noreply@hvwinterthur.ch" not in deploy:
    raise SystemExit("Deploy muss noreply@ als Default kennen")
if "MAIL_SMTP_PASSWORD fehlt" not in deploy:
    raise SystemExit("Deploy muss ohne Passwort config.mail.php schützen")
if "--exclude 'redaktion/config.mail.php'" not in deploy:
    raise SystemExit("Deploy muss config.mail.php optional vom rsync ausnehmen")

if "smtp.office365.com" not in example or "noreply@hvwinterthur.ch" not in example:
    raise SystemExit("config.mail.example.php muss M365/noreply dokumentieren")

if "Redaktions-Modus" not in lib or "noreply@hvwinterthur.ch" not in lib:
    raise SystemExit("zugang/lib.php Mail-Texte/Defaults fehlen")

print("ok")
