# Datensicherung Website HVW (Hostpoint Code + Inhalt)

Zielablage in Microsoft Teams:

**HVW → 02-Sekretariat → 04-Kommunikation → Website → `00_Datensicherung Website HVW Code+Inhalt`**

Dort jedes Backup als eigenen Ordner ablegen, z. B. `2026-10-01_hostpoint-vollbackup`.

## Was wird gesichert?

| Teil | Inhalt |
|------|--------|
| **`hvwinterthur.ch/`** | Document Root **1:1** wie auf Hostpoint: öffentliche HTML/CSS, `data/content-live.json`, Uploads, `/edit/` (Redaktion), `/vorschau/` (Daten-Backup), JSON-Exports (`home-events.json`, …), `dokumente/`, … |
| **`cronjobs-hostpoint/`** | Optional: Skripte unter `~/cronjobs/` (Eventfrog-Crons) |
| **`github-quellcode/`** | Optional: ZIP des Git-Repos (`main`) zum Zeitpunkt des Backups |
| **`BACKUP-INFO.txt`**, **`manifest-dateien.txt`** | Zeitstempel, Quellpfad, Dateizahl, Grösse |

Redaktionsdaten liegen **auf dem Server**, nicht vollständig in Git — deshalb ist dieses Hostpoint-Backup für «Inhalt» nötig zusätzlich zum GitHub-Repo.

## Variante A — GitHub Actions (empfohlen)

1. GitHub: **Actions** → **Backup Hostpoint (Vollständig)** → **Run workflow**
2. Optionen: Cronjobs und Git-ZIP nach Bedarf (Standard: beide an)
3. Nach Abschluss: **Artifacts** → `hostpoint-vollbackup` → `hostpoint-backup-latest.tar.gz` herunterladen
4. In Teams im Ordner `00_Datensicherung Website HVW Code+Inhalt`:
   - neuer Unterordner mit Datum, z. B. `2026-10-01_hostpoint`
   - Archiv hochladen **oder** entpacken und Ordner `hostpoint-backup-…` ablegen

Artefakte bei GitHub werden **90 Tage** aufbewahrt — für Langzeitarchiv unbedingt nach Teams kopieren.

## Variante B — Lokal per SSH (Hostpoint-Zugang nötig)

```bash
chmod +x scripts/backup-hostpoint-full.sh
key=~/.ssh/hostpoint_hvw   # privater Key
host=sl45.web.hostpoint.ch   # aus Control Panel
user=zozuhosa                # Hosting-Account
target=/home/zozuhosa/www/hvwinterthur.ch/
out=~/Downloads/hvw-backups

BACKUP_INCLUDE_CRONJOBS=1 \
BACKUP_GIT_ARCHIVE= \
  ./scripts/backup-hostpoint-full.sh "$host" "$user" "$target" "$key" "$out"
```

Ergebnis: `~/Downloads/hvw-backups/hostpoint-backup-YYYY-MM-DDTHHMMSSZ.tar.gz`

Optional Git-ZIP vorher:

```bash
git archive --format=zip -o /tmp/repo-main.zip main
BACKUP_GIT_ARCHIVE=/tmp/repo-main.zip ./scripts/backup-hostpoint-full.sh …
```

## Wiederherstellung (Kurz)

- **Einzelne Dateien:** aus `hvwinterthur.ch/` per SFTP/rsync zurück auf Hostpoint spiegeln
- **Ganzer Stand:** Document Root nur mit Vorsicht überschreiben (Live-Exports, Redaktion). Im Zweifel nur `edit/data/`, `data/`, `vorschau/` gezielt zurückspielen

## Regelmässigkeit

Empfehlung: nach grösseren Redaktionsrunden, vor Deploys mit Datenmigration, mindestens **monatlich** plus vor Go-Live-Meilensteinen.
