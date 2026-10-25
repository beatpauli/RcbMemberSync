# RcbMemberSync

Bedienoberfläche (marimo-Notebook im App-Modus) für den Abgleich der
Mitgliederdaten zwischen ClubDesk und efa. Steuert die drei Bibliotheken
`RcbClubdeskExport`, `RcbEfaExport` und `RcbCompareTool` an. Die Fachlogik
liegt dort, hier nur Ablauf und Darstellung.

Plan und Entscheidungen: `docs/plan.md`.

## Installation (Windows)

Die drei Projekte müssen als Geschwisterordner neben `RcbMemberSync` liegen.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
playwright install chromium
```

Zugangsdaten bleiben in der `.env` des jeweiligen Projekts
(`RcbClubdeskExport/.env`, `RcbEfaExport/.env`).

## Starten

```
marimo run app.py      # App-Modus (Bedienoberfläche)
marimo edit app.py     # Entwicklung
```

Phase 1 „IDs vergeben“ (ClubDesk-Id als ExternalId nach efa, Zuordnung über
den Namen) läuft ohne Oberfläche, Freigabe durch Eingabe von `ja`:

```
python -m rcbmembersync assign-ids                          # produktiv
python -m rcbmembersync assign-ids --instance local         # lokale Testinstanz
python -m rcbmembersync assign-ids --clubdesk-file PFAD     # ClubDesk-Datei statt Export
```

Run-Configs: „IDs vergeben produktiv“ und „IDs vergeben lokal“.

## Tests

```
python -m pytest
```
