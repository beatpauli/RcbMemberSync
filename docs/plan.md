# RcbMemberSync – Plan

Bedienoberfläche (marimo-Notebook im App-Modus) für den kompletten Abgleich der
Mitgliederdaten zwischen ClubDesk und efa. Das Projekt enthält **keine**
Fachlogik, es steuert nur die drei bestehenden Bibliotheken an und zeigt die
Ergebnisse an.

| Projekt | Paket | Aufgabe | Technik |
|---|---|---|---|
| `RcbClubdeskExport` | `rcbclubdeskexport` | ClubDesk-Mitglieder als CSV exportieren | Playwright (Browser-Automation) |
| `RcbEfaExport` | `rcbefaexport` | efa-Personen als CSV exportieren | efaCLI (Subprozess) + VPN via `rasdial` |
| `RcbCompareTool` | `rcbcomparetool` | Phase 1 (ExternalId zuordnen) / Phase 2 (Abgleich) | reines Python |

## Ablauf in der Oberfläche

```
[Konfiguration prüfen]  .env vorhanden? alle Variablen gesetzt? (nur ja/nein, keine Werte anzeigen)
        │
        ▼
[1. ClubDesk-Export]    run_button → ClubDesk.login() → Contacts.export_csv() → Pfad
        │               alternativ: vorhandene CSV auswählen (Export überspringen)
        ▼
[2. efa-Export]         run_button → EfaClient (VPN, efaCLI) → persons.export() → Pfad
        │               alternativ: vorhandene CSV auswählen
        ▼
[3. Abgleich]           Phase 1 / Phase 2 wählen → run_button
        │               Phase 1: Matches, Mehrdeutigkeiten, ungematchte Personen als Tabellen
        │               Phase 2: Neu / Geändert / Ausgetreten, nicht vergleichbar, Konflikte
        ▼
[4. Ergebnis]           Dateien in output/ (gemeinsamer Zeitstempel) + Download-Buttons
                        Hinweis: Import über efaCLI erfolgt manuell ausserhalb des Tools
```

Grundsätze:
- Jeder Schritt mit Nebenwirkung (Login, VPN, efaCLI, Dateien schreiben) liegt
  hinter `mo.ui.run_button()` + `mo.stop(...)`. Sonst würde marimo wegen der
  Reaktivität einen Export bei jeder UI-Änderung erneut starten.
- Mehrdeutigkeiten werden nur angezeigt, nie in der UI aufgelöst (Regel aus
  `RcbCompareTool`).
- Das Einspielen nach efa erfolgt nur nach ausdrücklicher Freigabe durch den
  Benutzer (seit 2026-10-25, siehe `docs/import-plan.md`).

## Projektstruktur

```
RcbMemberSync/
  pyproject.toml          # Abhängigkeiten: marimo, python-dotenv
  requirements-dev.txt    # -e ../RcbCompareTool  -e ../RcbClubdeskExport  -e ../RcbEfaExport
  app.py                  # marimo-Notebook (nur UI, möglichst dünn)
  rcbmembersync/
    settings.py           # .env laden, Pfade (data/, output/), Konfigurationsprüfung
    runners.py            # Wrapper um die drei Bibliotheken (Export im Thread, Abgleich)
  tests/                  # Tests für settings/runners (ohne echte Exporte)
  .env.example
  data/  output/          # in .gitignore
```

Die Logik bleibt in `rcbmembersync/`, damit sie ohne marimo testbar ist.
`app.py` enthält nur UI-Elemente und Aufrufe.

## Ergebnisse der Analyse der drei Projekte

### RcbCompareTool – sofort nutzbar
- Installierbar (`pyproject.toml` mit `packages.find`).
- Saubere API: `ClubDeskReader().read()`, `EfaReader().read()/read_records()`,
  `PersonMatcher().match()`, `Comparator().compare()`, Writer mit Zielpfad als
  Parameter, `timestamp_prefix()`.
- Kleiner Nachteil: Pfadaufbau und Zusammenfassung stehen in `__main__.py`
  (`_run_assign_ids`, `_run_compare`). Zuerst dupliziere ich das in
  `runners.py`. Später kann man es optional in eine öffentliche Funktion im
  Compare-Tool auslagern.

### RcbClubdeskExport – kleine Anpassungen nötig
- **C1 Installierbarkeit:** In `pyproject.toml` fehlt
  `[tool.setuptools.packages.find]`. Wegen der Top-Level-`__main__.py` kann die
  automatische Paketerkennung von setuptools beim `pip install -e` scheitern.
  Ergänzen wie in den anderen beiden Projekten (`include = ["rcbclubdeskexport*"]`).
- **C2 Pfade relativ zum Arbeitsverzeichnis:** `Config.DOWNLOAD_DIR =
  Path("downloads")` und `Config.SESSION_FILE = Path("clubdesk.json")` landen
  dort, wo marimo gestartet wird. Vorschlag: optionale Konstruktor-Parameter
  `download_dir` / `session_file` in `ClubDesk`, Default wie bisher.
- **Playwright Sync-API in marimo (per Spike geprüft, 2026-10-23):** marimo
  0.25 führt Zellen in einer laufenden asyncio-Schleife aus. Ein direkter
  Aufruf von `sync_playwright()` scheitert mit „Sync API inside the asyncio
  loop“. In einem eigenen Thread (`ThreadPoolExecutor`) funktioniert er.
  → Der ClubDesk-Export läuft in `runners.py` immer in einem Worker-Thread.
- `headless` lässt sich bereits übergeben. Für die UI ist `headless=True`
  sinnvoll, sofern der Login ohne Interaktion klappt.

### RcbEfaExport – nutzbar, mit Hinweisen
- Installierbar, API passt: `with EfaClient(cfg) as efa: efa.persons.export()`
  liefert einen `Path`.
- **E1 Config beim Import:** `config.py` ruft `load_dotenv()` beim Import auf,
  und die Dataclass-Defaults werden zu diesem Zeitpunkt aus der Umgebung
  gelesen. Das funktioniert bei einer editierbaren Installation (die `.env`
  im efa-Projekt wird gefunden). Für RcbMemberSync übergebe ich die Werte
  explizit: `Config(cli=..., host=..., ...)` geht ohne Änderung am
  efa-Projekt.
- **E2 Kein Timeout:** `TerminalReader.read_until_prompt()` liest Zeichen für
  Zeichen ohne Timeout. Hängt efaCLI, hängt auch die UI. Für den Anfang
  vertretbar, später eventuell einen Timeout ergänzen.
- **E3 Dateiname nur mit Datum:** `YYYY-MM-DD_persons_export.csv`. Ein zweiter
  Export am selben Tag überschreibt den ersten. Für den Abgleich unkritisch.
- Nebenbei gefunden (unabhängig von der UI):
  - In `terminal.py` steht im Zweig ohne Zeilenumbruch `"INF0"` mit einer Null
    statt `"INFO"`.
  - In `client.py` ist `_wait_for` doppelt definiert und wird nicht benutzt.

## Schritte

1. **Gerüst:** Projekt anlegen, venv, editierbare Installation der drei
   Projekte. Dafür ist C1 nötig, ausserdem `playwright install chromium`.
   Prüfen, dass alle drei importierbar sind.
2. **Abgleich-Seite** auf vorhandenen CSV-Dateien (ohne Exporte): Phase
   wählen, Tabellen, Downloads. Damit ist die UI bereits nutzbar.
3. **efa-Export** einbinden (VPN, efaCLI, Spinner, Fehleranzeige).
4. **ClubDesk-Export** einbinden (Thread-Spike für Playwright, C2).
5. Feinschliff: Konfigurationsprüfung, Log-Ausgabe in der UI.

Änderungen an den drei bestehenden Projekten (C1, C2, optional E2) jeweils als
kleine, eigene Commits im betroffenen Projekt.

### Stand (2026-10-23)

- Schritt 1 **erledigt**: Gerüst, venv, editierbare Installation, C1 in
  RcbClubdeskExport committet (`97e78d2`), Playwright-Spike ok.
- Erstes `app.py` mit Konfigurationsprüfung und Platzhaltern, PyCharm-Run-Configs
  (App starten, Notebook bearbeiten, All Tests).
- GUI-Aufbau in Diskussion: Mockup v1 und offene Fragen in `docs/ui-design.md`.
- Nächster Schritt: offene Fragen in `docs/ui-design.md` klären, dann Schritt 2.

## Entscheidungen (2026-10-23)

1. **efaCLI-Export darf ausgelöst werden.** Die UI startet über RcbEfaExport
   den lesenden Export. Der **Import** nach efa bleibt manuell und wird nie
   ausgelöst.
   *Geändert 2026-10-25:* RcbMemberSync spielt die Änderungen nach
   ausdrücklicher Freigabe durch den Benutzer selbst nach efa ein, siehe
   `docs/import-plan.md`.
2. **Zugangsdaten pro Projekt:** Jedes Projekt behält seine eigene `.env`.
   RcbMemberSync liest sie aus dem jeweiligen Projektordner, der über den
   Speicherort des installierten Pakets ermittelt wird (editierbare
   Installation). efa macht das in `config.py` schon selbst. Für ClubDesk lädt
   `settings.py` die `.env` des Projekts mit `dotenv_values()`, ohne die
   Prozess-Umgebung zu verändern.
3. **ClubDesk headless:** Der Login funktioniert ohne sichtbaren Browser →
   `headless=True`.
4. **Eigenes Git-Repository** für RcbMemberSync.

Noch offen: Die App muss auf einem Windows-Rechner mit efaCLI und VPN-Profil
laufen. Ich gehe davon aus, dass es nur diesen einen Rechner gibt.
