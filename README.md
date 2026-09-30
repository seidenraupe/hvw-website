# Historischer Verein Winterthur — Website-Prototyp

Moderne HTML/CSS-Website aus den vorhandenen Wireframes/Mood-Referenzen, mit **Tailwind CSS Event-Karten** (Mobile First).

## Design-Richtung

- Visuell verwandt mit [museumschaffen.ch](https://www.museumschaffen.ch/) (gleicher Trägerverein)
- Klarere UX: grosse Touch-Ziele (min. 48px), hohe Kontraste, ruhige Navigation
- Typografie: Outfit (geometrisch, gut lesbar — nicht Inter), lokal aus @fontsource, ohne Google Fonts
- Schwarz/Weiss wie Museum Schaffen, mit klaren CTAs

## Event-Karten (Tailwind)

Raster **Mobile First**:

| Breakpoint | Spalten | Tailwind |
|---|---|---|
| Smartphone | 1 | `grid-cols-1` |
| Tablet (`md`) | 2 | `md:grid-cols-2` |
| Desktop (`lg`) | 3 | `lg:grid-cols-3` |

Platzhalterbilder tragen den Wasserzeichen-Vermerk **«finales Bild fehlt»**.

Datenquelle Titelseite: `/home-events.json` (eigener Hostpoint-Cron, wie Coucou/MuS).

## SEO & GEO

- `lang="de-CH"`, Canonical, Open Graph
- Geo-Meta (`geo.region`, `geo.placename`, Position Winterthur)
- JSON-LD: `NonprofitOrganization`, `WebSite`, `Event`, `FAQPage`, `Museum`
- `sameAs` zu museumschaffen.ch
- Semantische Event-Karten (`itemscope` Event / Place / `time`)

## Lokal ansehen

```bash
python3 -m http.server 8080
# → http://localhost:8080
```

## Soft-Launch: Programm auf Hostpoint

Produktive Zielumgebung ist **Hostpoint** (`www.hvwinterthur.ch`), nicht GitHub Pages.
GitHub bleibt nur Prototyp-/Quellrepo.

Solange die Gesamtwebsite noch nicht live geht:

- Stamm-URL `https://www.hvwinterthur.ch/` → Weiterleitung nach
  **`https://www.historischer-verein-winterthur.ch/`** (wie bisher)
- Die öffentliche Programmseite `/programm` ist entfernt (HTTP 410).
  Das Programm-PDF bleibt unter `/programm/Programm.pdf`.
- Interne Redaktion (Passwort, nicht öffentlich):
  **`https://www.hvwinterthur.ch/vorschau/`**
- Apache/Hostpoint: `.htaccess` (Stamm-Redirect, Programmseite weg)
- `robots.txt` + `noindex` auf Prototyp-Seiten

### Deploy auf Hostpoint (GitHub Actions)

Workflow: `.github/workflows/deploy.yml` — bei Push auf `main` (oder manuell unter Actions).

Baut `deploy/hostpoint-soft-launch/` **und** die interne Vorschau
(`deploy/hostpoint-vorschau/` → `/vorschau/`) und synct beides per rsync/SSH.
Der Soft-Launch-Sync lässt `/vorschau/` unangetastet (`--exclude vorschau/`).
Veröffentlichte Redaktionstexte in `/vorschau/data/content-live.json` und Entwürfe
werden bei Deploys **nicht überschrieben**. Neue Textfelder aus Git werden nur
**ergänzt** (Merge: Server gewinnt, Git liefert Startwerte für neue IDs).

#### Secrets (Repo → Settings → Secrets and variables → Actions)

| Secret | Inhalt |
|---|---|
| `SSH_PRIVATE_KEY` | Kompletter **privater** Key inkl. `-----BEGIN … PRIVATE KEY-----` / `END` (nicht `.pub`) |
| `SSH_HOST` | Server-Hostname aus Hostpoint «Server Übersicht», z. B. `sl45.web.hostpoint.ch` |
| `SSH_USER` | Hosting-Account exakt wie im Control Panel, z. B. `zozuhosa` |
| `SSH_TARGET_DIR` | Document Root mit `/` am Ende, z. B. `/home/zozuhosa/www/hvwinterthur.ch/` |
| `MAIL_SMTP_HOST` | SMTP-Server, z. B. `smtp.mail.hostpoint.ch` |
| `MAIL_SMTP_PORT` | Meist `587` |
| `MAIL_SMTP_USER` | SMTP-Benutzer (Postfach) |
| `MAIL_SMTP_PASSWORD` | SMTP-Passwort des Postfachs |
| `MAIL_FROM` | Absender, z. B. `noreply@hvwinterthur.ch` |
| `VORSCHAU_ALLOWED_EMAILS` | Optional: weitere Start-Adressen (die drei HVW-Adressen stehen bereits im Code) |

#### SSH bei Hostpoint vorbereiten

1. Im Control Panel SSH aktivieren (falls nötig)
2. Key-Paar erzeugen (ohne Passphrase): `ssh-keygen -t ed25519 -C "github-deploy-hvw" -f hvw_deploy -N ""`
3. Inhalt von `hvw_deploy.pub` bei Hostpoint als authorized key hinterlegen
4. Inhalt von `hvw_deploy` als Secret `SSH_PRIVATE_KEY` speichern

Der letzte Workflow-Fehler war: Hostname nicht auflösbar + Private Key nur ~11 Zeichen
(Secret `SSH_HOST` / `SSH_PRIVATE_KEY` falsch gesetzt).

#### Manueller Upload (Fallback)

```bash
./scripts/build-hostpoint-soft-launch.sh
# → deploy/hostpoint-soft-launch/
```

Inhalt per FTP/SFTP oder Hostpoint-Dateimanager in den Document Root hochladen.

### Eventfrog

Domain `www.hvwinterthur.ch` im Eventfrog-Cockpit für das Embed freischalten —
sonst bleibt das Widget leer.

### Cronjobs / Coucou-Export (Hostpoint)

Der frühere Plesk-Cron auf `giger-straehl.ch`
(`eventfrog_to_coucou.py` → Event-File für Coucou) ist nach Hostpoint migriert:

- Skripte: `cronjobs/` (siehe `cronjobs/README.md`)
- Öffentliche Dateien:
  - `https://www.hvwinterthur.ch/coucou_export.json` (Coucou, alle Org-IDs)
  - `https://www.hvwinterthur.ch/coucou` (tabellarische Kontrolle des aktuellen Exports)
  - `https://www.hvwinterthur.ch/guidle_export.json` (Kopie von Coucou, für Guidle)
  - `https://www.hvwinterthur.ch/mus_export.json` (Museum Schaffen, OrgID 5116588)
  - `https://www.hvwinterthur.ch/mus` (tabellarische Kontrolle des MuS-Exports)
  - `https://www.hvwinterthur.ch/home-events.json` (Titelseite, nächste 3 Anlässe; eigener Cron)
- Täglich nur auf Hostpoint (Cronjobs Manager), nicht über GitHub Actions
- Soft-Launch-Deploy löscht die Export-JSONs nicht (`rsync --exclude`)
- Skript-Updates nach Hostpoint: Action `deploy-cronjobs.yml` (bei Änderungen an `cronjobs/`)

### Programm (PDF)

Das aktuelle Programm gibt es als PDF (A4, druckbar: kompakter Kopf mit den
drei Museen, dann alle Anlässe ab Druckdatum bis zur letzten Veranstaltung).
Die HTML-Seite dazu ist entfernt:

```
https://www.hvwinterthur.ch/programm/Programm.pdf
```

Beim Speichern heisst die Datei `Programm HVW MM.JJJJ bis MM.JJJJ.pdf`
(Druckmonat bis letzte Veranstaltung; Punkte statt Schrägstrich, damit der Browser den Namen nicht abschneidet).

Erzeugung aus Eventfrog (alle drei Org-IDs):

```bash
pip install -r scripts/requirements-pdf.txt
EVENTFROG_API_KEY=… python3 scripts/generate-programm-pdf.py
```

Beim Soft-Launch-Deploy wird das PDF in GitHub Actions frisch erzeugt,
sofern die Eventfrog-API von GitHub aus antwortet. Schlägt der Abruf
fehl (z. B. HTTP 403), bleibt das PDF aus dem Repository.

### Google Analytics 4

Die Website wird mit **GA4** im Konto `thomas.giger@cloud-7.net` gemessen
(gleiche Analytics-Oberfläche wie bei Ihren anderen Websites).
Die frühere Mess-ID der öffentlichen Programmseite ist entfernt.

Aktuelle Measurement ID: **`G-8M4EZQDQ98`**

Der Google-Tag steht **inline** im `<head>` der Website
(wie von Google vorgesehen), damit die Tag-Erkennung greift. Dieselbe
Measurement ID steht in `data/analytics.json`.

1. Mit diesem Konto auf [analytics.google.com](https://analytics.google.com) anmelden
2. **Admin** → Property / Datenstream für `https://www.hvwinterthur.ch`
3. **Measurement ID** im Inline-Tag der HTML-Seiten und in
   `data/analytics.json` eintragen, neu deployen
4. In GA4 unter **Realtime** prüfen bzw. Tag-Setup erneut testen

### Später: volle Website live

`noindex` wieder auf `index,follow` setzen, `robots.txt` öffnen und den
kompletten Site-Build (nicht nur Soft-Launch) nach Hostpoint deployen.

## Struktur

```
programm/           Programm-PDF (die öffentliche HTML-Seite ist entfernt)
.htaccess           Apache/Hostpoint (HTTPS, Clean URLs)
robots.txt          Soft-Launch Indexierung
scripts/build-hostpoint-soft-launch.sh
deploy/hostpoint-soft-launch/   (generiertes Upload-Paket)
cronjobs/           Coucou- + Museum-Schaffen-Export für Hostpoint (täglich)
index.html          Startseite mit Event-Karten (Prototyp)
agenda.html         Agenda (Programm + Rückblick)
museen.html         Museum Schaffen / Lindengut / Mörsburg
partner.html        Partner / Netzwerk
sammlung.html       Ausgewählte Objekte
zitate.html         Stimmen aus Winterthur
ueber-uns.html      Verein + FAQ (GEO)
mitmachen.html      Mitgliedschaft
css/site.css        Motion & Placeholder-Styles
js/main.js          Event-Karten-Rendering
js/tailwind-config.js
data/home-events.json
images/             Logo, Foto, SVG-Platzhalter
reference/wireframes/  Mood-Referenzen aus dem Upload
scripts/            Eventfrog-Fetch / Hostpoint-Build
```

## Eventfrog aktualisieren

Die nächtlichen JSON-Exporte (`coucou_export.json`, `guidle_export.json`, `home-events.json`, `mus_export.json`) laufen
**nur** als Hostpoint-Crons, siehe `cronjobs/README.md`. GitHub erzeugt diese Dateien nicht.

Der API-Key liegt nicht im Repository-Code. Die Agenda-Seite (`agenda.html`) nutzt
zusätzlich das öffentliche Eventfrog-Widget (iframe + `embed.js`); dessen Widget-Key in der URL
ist kein API-Secret und muss im HTML stehen.

Live und Vorschau laden `/home-events.json` vom Hostpoint-Cron (`eventfrog_to_home.py`).
Optional, nur lokal ohne Hostpoint:

```bash
EVENTFROG_API_KEY=<key> node scripts/fetch-eventfrog-events.mjs
```

Fehlende Event-Bilder ergänzt das Fetch-Skript über die `og:image` der Eventfrog-Eventseite.

## Webling-Anmeldung (Mitmachen)

Die Seite `mitmachen.html` bettet das Webling-Mitgliedschaftsformular als **iframe** ein
(Anker `#anmeldeformular`) — technisch wie im vorherigen Prototyp
([prototyp-hvw](https://seidenraupe.github.io/prototyp-hvw/mitmachen.html#anmeldeformular)).

- iframe-`src`: `https://hvwinterthur.webling.ch/forms/memberform/d9e980cf304ee928a7e5`
- Referenz auch in `data/webling-form.json`
- Nach dem Absenden bleibt die Besucherin/der Besucher auf der HVW-Website

## Texte redigieren (ohne Layout zu ändern)

Auf Startseite, Agenda, Museen, Über uns, Mitmachen, Publikationen, Sammlung
und Stimmen sind ausgewählte Texte als Felder hinterlegt (`data-content`) —
einschliesslich der Einleitungen unter den Titeln und der Rückblick-Karten
auf der Agenda. Layout, Navigation, Eventfrog-Embed und das Webling-Formular
bleiben fest.

Ablauf: **anmelden → auf der echten Seite klicken → Entwurf speichern → Freigabe
schaut die Seite an → live schalten.**

- Anmeldung: `/redaktion/` (PHP, Hostpoint oder `php -S localhost:8080`)
- Live-Texte: `data/content-live.json` (öffentlich)
- Entwurf: `redaktion/storage/content-draft.json` (nicht öffentlich)
- Erlaubt: fett, kursiv, unterstrichen. Keine Farben, keine neuen Blöcke.
- Rollen: `redaktion` speichert Entwürfe; `freigabe` darf live schalten.
- Freigabe: von Änderung zu Änderung springen, einzeln **annehmen**, **ändern**
  oder **rückgängig** machen, danach die Seite live schalten.

Standard-Zugänge (sofort ändern, z. B. via `redaktion/config.local.php`):

| Benutzer   | Passwort            | Rolle    |
|------------|---------------------|----------|
| `redaktion` | `Redaktion-HVW-2026` | Entwurf  |
| `freigabe`  | `Freigabe-HVW-2026`  | Freigabe |

PHP muss in `data/` und `redaktion/storage/` schreiben dürfen.

### Redaktion im Web, ohne öffentliche Website

GitHub Pages führt kein PHP aus — dort kann man die Seiten ansehen, aber nicht
einloggen. Die Redaktion läuft deshalb auf Hostpoint, in einem **internen
Ordner**, der nicht verlinkt und nicht indexiert ist:

1. **Die öffentliche Programmseite ist entfernt.** Die Stamm-URL leitet
   weiter zur bestehenden Vereinswebsite.
2. **Vorschau:** `https://www.hvwinterthur.ch/vorschau/`
   — E-Mail (Allowlist) + Code, der an diese Adresse geht.
   Der Zugang gilt bis Mitternacht (Schweizer Zeit); am nächsten Tag
   braucht man einen neuen Code.
3. **Texte ändern:** Oben «Änderungsmodus — Anmelden»,
   oder `https://www.hvwinterthur.ch/vorschau/redaktion/`
   — Login `redaktion` oder `freigabe` (kein zweiter Mail-Code).
4. **E-Mail-Liste pflegen:** als Freigabe unter
   `https://www.hvwinterthur.ch/vorschau/redaktion/zugang.php`
5. Erst beim Launch wandert die Website an die Stamm-URL, der Mail-Code
   entfällt.

Start-Adressen (Code per Mail): `thomas.giger@hvwinterthur.ch`,
`christian.huggenberg@hvwinterthur.ch`, `gioia.joehri@hvwinterthur.ch`.
Weitere Adressen legt die Freigabe in der Vorschau an. SMTP-Passwort als
`MAIL_SMTP_PASSWORD` setzen — ohne SMTP kommt kein Code an.

Die Redaktionsleiste ist dunkelgrün, damit sie sich von der schwarzen Website unterscheidet.

### Redaktion und Weiterentwicklung parallel

Texte und Code sind getrennt:

| Spur | Wo | Was |
|---|---|---|
| Redaktion | Hostpoint `/vorschau/` | `data/content-live.json` und Entwurf auf dem **Server** |
| Entwicklung | GitHub `main` | HTML, CSS, JS, Schema, neue Feld-IDs |

Beim Deploy gilt: **Felder, die auf dem Server schon existieren, bleiben.** Git liefert nur Startwerte für **neue** Feld-IDs (Merge-Skript `scripts/merge-content-json.py`). Entwürfe werden gleich behandelt: vorhandene Änderungen bleiben, neue IDs kommen dazu.

Damit das so bleibt:

- Texte nur in der Vorschau redigieren, nicht in HTML oder in `data/content-live.json` «korrigieren».
- Feld-IDs (`data-content="…"`) nicht umbenennen — sonst hängt der Redaktionstext in der Luft.
- Neue Texte: ID in HTML + `data/content-schema.json` + Startwert in `data/content-live.json`.
- GitHub Pages zeigt die Git-Startwerte, nicht den Redaktionsstand auf Hostpoint.

Lokal zum Ausprobieren:

```bash
php -S localhost:8080
# → http://localhost:8080/redaktion/
```
