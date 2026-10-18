# Cronjobs für hvwinterthur.ch (Hostpoint)

Migriert von Kreativ Media (`giger-straehl.ch` / Plesk).

## Was läuft täglich?

| Job | Skript | Ergebnis |
|---|---|---|
| Coucou-Export | `eventfrog_to_coucou.py` | `https://www.hvwinterthur.ch/coucou_export.json` (alle Org-IDs) |
| Guidle-Kopie | *(dieselbe Coucou-Datei)* | `https://www.hvwinterthur.ch/guidle_export.json` |
| Titelseite | `eventfrog_to_home.py` | `https://www.hvwinterthur.ch/home-events.json` (nächste 3 Anlässe) |
| Museum Schaffen | `eventfrog_to_mus.py` | `https://www.hvwinterthur.ch/mus_export.json` (nur OrgID `5116588`) |
| Programm-PDF | `eventfrog_to_programm_pdf.py` | `https://www.hvwinterthur.ch/dokumente/Programm.pdf` + `programm/Programm.json` |

Beide JSON-Exports nutzen **dasselbe Coucou-Record-Layout**, inkl. Kurz- und
Langbeschreibung (`description`, `description_long`, `description_html`).
`mus_export.json` holt die Agentur von museumschaffen.ch von hvwinterthur.ch ab.

**Coucou-Kategorien:** `category` ist ein Array: automatisch gemappte
Primärkategorie (Rubrik) plus immer **Historisches** (Coucou-ID **308**).

**Keine Attraktionen:** Eventfrog-Einträge vom Typ Attraktion (Öffnungszeiten,
z.B. Ausstellung «Erinnerungstank Haldengut» an jedem Werktag) gehören nicht
ins Coucou-/Guidle-/MuS-JSON und auch nicht auf die Titelseite. Der Export
behält nur Veranstaltungen (Führungen, Käfele, Vorträge, AfterWork, …).

Die früheren GitHub-Crons (Coucou-Export und Homepage-Events im Repo) sind
entfernt. Alle vier JSON-Dateien und das Agenda-Programm-PDF entstehen **nur**
auf Hostpoint (je eigener Cron). Das PDF nutzt dieselben Org-IDs und denselben
Attraktions-Filter wie Coucou/Titelseite; Logo und Museumsfotos liegen im
bereits deployten Webroot (`images/`).

## Hostpoint-Einrichtung

### 1. Dateien hochladen

Zielordner (ausserhalb des öffentlichen Webroots):

```text
/home/zozuhosa/cronjobs/
```

Inhalt:

- `eventfrog_to_coucou.py`
- `eventfrog_to_home.py`
- `eventfrog_to_mus.py`
- `eventfrog_to_programm_pdf.py`
- `generate-programm-pdf.py` (via Deploy-Action aus `scripts/`, nicht im Git unter `cronjobs/`)
- `requirements.txt`
- `eventfrog_api_key` (lokal aus `.example` erzeugen, **nicht** committen)

Oder GitHub Action **Deploy cronjobs to Hostpoint** manuell starten
(`.github/workflows/deploy-cronjobs.yml`) — legt Skripte + Key aus dem
Secret `EVENTFROG_API_KEY` ab.

### 2. Python-Abhängigkeit (einmalig per SSH)

```bash
cd ~/cronjobs
/usr/local/bin/python -m pip install --user -r requirements.txt
```

### 3. Cronjobs im Control Panel

Hostpoint → Server-Übersicht → **Advanced** → **Cronjobs Manager**

#### Coucou (alle Organisationen)

| Feld | Wert |
|---|---|
| Minute | `0` |
| Hour | `3` |
| Day / Month / Weekday | `*` |

Befehl:

```bash
cd /home/zozuhosa/cronjobs && /usr/local/bin/python eventfrog_to_coucou.py >/dev/null 2>&1
```

#### Museum Schaffen (`mus_export.json`)

| Feld | Wert |
|---|---|
| Minute | `5` |
| Hour | `3` |
| Day / Month / Weekday | `*` |

Befehl:

```bash
cd /home/zozuhosa/cronjobs && /usr/local/bin/python eventfrog_to_mus.py >/dev/null 2>&1
```

#### Titelseite (`home-events.json`)

| Feld | Wert |
|---|---|
| Minute | `10` |
| Hour | `3` |
| Day / Month / Weekday | `*` |

Befehl:

```bash
cd /home/zozuhosa/cronjobs && /usr/local/bin/python eventfrog_to_home.py >/dev/null 2>&1
```

#### Programm-PDF (`dokumente/Programm.pdf`)

| Feld | Wert |
|---|---|
| Minute | `15` |
| Hour | `3` |
| Day / Month / Weekday | `*` |

Befehl:

```bash
cd /home/zozuhosa/cronjobs && /usr/local/bin/python eventfrog_to_programm_pdf.py >/dev/null 2>&1
```

Nach dem ersten Deploy: `pip install --user -r requirements.txt` (enthält
reportlab/Pillow für das PDF).

### 4. Abnehmer-URLs

| Abnehmer | URL |
|---|---|
| Coucou | `https://www.hvwinterthur.ch/coucou_export.json` |
| Coucou-Kontrolle | `https://www.hvwinterthur.ch/coucou` |
| Guidle | `https://www.hvwinterthur.ch/guidle_export.json` |
| Titelseite | `https://www.hvwinterthur.ch/home-events.json` |
| museumschaffen.ch (Agentur) | `https://www.hvwinterthur.ch/mus_export.json` |
| MuS-Kontrolle | `https://www.hvwinterthur.ch/mus` |
| Agenda-Programm | `https://www.hvwinterthur.ch/dokumente/Programm.pdf` |

Alten Cron auf Kreativ Media deaktivieren, sobald Coucou umgestellt ist.

### 5. Prüfen

```bash
cd ~/cronjobs
/usr/local/bin/python eventfrog_to_coucou.py
/usr/local/bin/python eventfrog_to_home.py
/usr/local/bin/python eventfrog_to_mus.py
/usr/local/bin/python eventfrog_to_programm_pdf.py
curl -sI https://www.hvwinterthur.ch/coucou_export.json
curl -sI https://www.hvwinterthur.ch/guidle_export.json
curl -sI https://www.hvwinterthur.ch/home-events.json
curl -sI https://www.hvwinterthur.ch/mus_export.json
curl -sI https://www.hvwinterthur.ch/dokumente/Programm.pdf
```

## Hinweis

Die Exporte und das Programm-PDF laufen **täglich** über den Hostpoint-Cronjobs
Manager, nicht über GitHub Actions. Soft-Launch-Deploy (`Deploy via rsync`)
löscht `coucou_export.json`, `guidle_export.json`, `mus_export.json` und
`home-events.json` nicht (`rsync --exclude`). Beim Deploy wird das PDF zusätzlich
in GitHub Actions erzeugt; der Hostpoint-Cron hält es zwischen Deploys aktuell.

Skript-Änderungen im Repo werden mit der Action
`deploy-cronjobs.yml` nach `~/cronjobs/` synchronisiert (bei Push auf `main`
unter `cronjobs/` oder manuell per `workflow_dispatch`).

## Secrets

| Secret | Verwendung |
|---|---|
| `EVENTFROG_API_KEY` | Eventfrog Public API (für Deploy der Key-Datei auf Hostpoint) |
| `SSH_*` | Deploy der Cron-Skripte nach Hostpoint (wie Soft-Launch) |
