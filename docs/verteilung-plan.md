# Weitergabe an andere Benutzer – Plan

Stand: 2026-10-31. Status: **freigegeben (2026-10-31).**

Der Mitgliederabgleich soll an eine andere Person übergeben werden können:

1. **Ausführbares Paket:** ohne Entwicklungsumgebung, ohne Geschwister-Projekte
   nebeneinander, ohne `pip install -e`.
2. **VPN unabhängig von Windows:** Die Verbindung muss auch dann zustande
   kommen, wenn sie in Windows nicht eingerichtet wurde.

## Entscheidungen (2026-10-31)

1. **Internet wird vorausgesetzt.** Fehlt es beim Einrichten, bricht der Start
   mit einer verständlichen Fehlermeldung ab.
2. **efa (mit efaCLI) und Java sind beim Empfänger installiert** – zumindest
   im ersten Schritt. Das Paket prüft das nur und meldet, was fehlt.
3. **Der VPN-Eintrag bleibt stehen**, wenn ihn das Programm angelegt hat.
4. **Zugangsdaten kommen im ersten Schritt mit ins Paket** (eine `.env` im
   Paketordner).
5. **Konfiguration, Ausschlussliste und Ausgabe liegen im Paketordner.**

## Ausgangslage

| Teil | Heute | Hindernis für die Weitergabe |
|---|---|---|
| Start | `marimo run app.py` aus der venv | Python, venv, vier editierbar installierte Projekte |
| ClubDesk | Playwright + Chromium (eigener Prozess, spawn) | Chromium muss vorhanden sein (`playwright install chromium`) |
| efa | efaCLI über `cmd` (`EFA_CLI`), braucht Java und eine efa-Installation | wird vorausgesetzt (Entscheidung 2) |
| Zugangsdaten | je eine `.env` in RcbClubdeskExport und RcbEfaExport | drei Projektverzeichnisse |
| Ausschlussliste | `RcbCompareTool/data/efa_ausschluss.csv` | liegt in einem Geschwister-Projekt |
| Ausgabe | `RcbMemberSync/output/` | im Programmverzeichnis (passt, Entscheidung 5) |
| VPN | `rasdial "<VPN_NAME>"` – Eintrag muss in Windows existieren | siehe Teil A |

Der VPN-Eintrag „RCB VPN“ auf dem Entwicklungsrechner ist **L2TP/IPsec mit
Pre-Shared Key**, Authentifizierung CHAP/MS-CHAPv2/PAP, Verschlüsselung
optional, kein Split-Tunneling.

## Teil A: VPN-Eintrag bei Bedarf anlegen (RcbEfaExport)

Windows kann einen L2TP-Eintrag **ohne Administratorrechte** für den aktuellen
Benutzer anlegen (PowerShell, Modul `VpnClient`):

```
Add-VpnConnection -Name <VPN_NAME> -ServerAddress <VPN_SERVER>
    -TunnelType L2tp -L2tpPsk <VPN_PSK> -AuthenticationMethod MSChapv2
    -EncryptionLevel Optional -RememberCredential -Force
```

Ablauf in `Vpn.connect()`:

1. Bereits verbunden → wie heute nichts tun.
2. Eintrag `VPN_NAME` fehlt (`Get-VpnConnection -Name …`) und `VPN_SERVER` +
   `VPN_PSK` sind gesetzt → Eintrag anlegen und stehen lassen
   (Entscheidung 3), im Log vermerken (ohne PSK).
3. `rasdial` wie heute.

Neue Werte in der `.env`: `VPN_SERVER`, `VPN_PSK`. Sind sie leer, verhält sich
alles wie heute (Eintrag muss existieren).

Den PSK nicht auf der Kommandozeile an PowerShell übergeben, sondern über eine
Umgebungsvariable des Kindprozesses; er erscheint nie im Log.

Risiken:
- **L2TP hinter NAT:** Steht der VPN-Server hinter einem NAT-Router, verlangt
  Windows je nach Gegenstelle den Registry-Eintrag
  `AssumeUDPEncapsulationContextOnSendRule` (Admin + Neustart). Das kann das
  Programm nicht selbst erledigen. Zu klären mit einem Test auf einem zweiten
  Rechner ohne eingerichtetes VPN.
- Die genaue Authentifizierungsmethode muss zum Server passen; heute sind
  CHAP, MS-CHAPv2 und PAP erlaubt.

## Teil B: Paket mit `uv` (Internet beim ersten Start)

Weil Internet vorausgesetzt wird (Entscheidung 1), bleibt das Paket klein:
Python, die Fremdbibliotheken und Chromium werden beim ersten Start geladen.

```
RcbMemberSync/                 # ZIP entpacken, irgendwo hin
  RcbMemberSync.cmd            # Doppelklick: einrichten (falls nötig) und starten
  uv.exe                       # https://github.com/astral-sh/uv, feste Version
  pyproject.toml, uv.lock      # Abhängigkeiten mit festen Versionen
  wheels/                      # die vier eigenen Projekte als Wheels
  app.py
  .env                         # alle Zugangsdaten und Pfade (Entscheidung 4)
  data/efa_ausschluss.csv      # Ausschlussliste
  output/                      # Laufverzeichnisse
  .venv/, browsers/            # entstehen beim ersten Start
```

`RcbMemberSync.cmd`:
1. `uv sync --frozen` – lädt beim ersten Mal Python und alle Pakete in
   `.venv` (danach in Sekunden erledigt). Schlägt das fehl, Meldung „Keine
   Internetverbindung oder Download fehlgeschlagen“ und Abbruch.
2. Chromium nach `browsers/` laden, falls es fehlt
   (`PLAYWRIGHT_BROWSERS_PATH`), gleiche Fehlerbehandlung.
3. `marimo run app.py` – der Browser öffnet sich.

Ein Build-Skript in RcbMemberSync (`tools/build_package.py`) baut die Wheels,
erzeugt `uv.lock`, legt `uv.exe`, `.env` und die Ausschlussliste dazu und
packt alles als ZIP nach `dist/` (nicht versioniert).

Dazu nötig:
- **Eine `.env` im Paketordner** statt der `.env` je Projekt. Im
  Entwicklungsmodus bleibt alles wie heute. Das Build-Skript stellt sie aus
  den bestehenden `.env`-Dateien zusammen.
- `settings.project_dir()` / `check_environment()` müssen ohne
  Geschwister-Verzeichnisse funktionieren; zusätzlich prüfen, ob `EFA_CLI`
  existiert und Java gefunden wird (Entscheidung 2).
- `EFA_CLI` und `EFA_EXPORT_PATH` zeigen auf die efa-Installation des
  Empfängers, müssen in der `.env` also vor der Übergabe angepasst werden.

**Hinweis zu Entscheidung 4:** Mit den Zugangsdaten im Paket kann jede Person,
die das ZIP in die Hände bekommt, auf ClubDesk, efa (produktiv) und das VPN
zugreifen. Das ZIP also nicht per E-Mail oder über öffentliche Ablagen
weitergeben; `dist/` steht in `.gitignore`.

## Aufteilung auf die Projekte

| Projekt | Änderung |
|---|---|
| RcbEfaExport | Teil A (`vpn.py`, `config.py`, `.env.example`, README); `.env` von aussen vorgebbar |
| RcbClubdeskExport | `.env` von aussen vorgebbar; Browser-Pfad über `PLAYWRIGHT_BROWSERS_PATH` (keine Codeänderung nötig) |
| RcbCompareTool | – (Pfad der Ausschlussliste wird schon übergeben) |
| RcbMemberSync | Paketmodus (eine `.env`, Pfade im Paketordner), Prüfungen efa/Java, Build-Skript, Startskript, Anleitung für den Empfänger |

## Reihenfolge

1. Teil A in RcbEfaExport, getestet auf einem Rechner ohne VPN-Eintrag
   (den VPN-Test macht der Benutzer).
2. Paketmodus in RcbMemberSync (und `.env` von aussen in den beiden
   Export-Projekten).
3. Build-Skript und Startskript, Probelauf auf einem zweiten Rechner.

## Geklärt bei der Freigabe (2026-10-31)

- Projektregel in `CLAUDE.md` ergänzt: im Paket liegen die Zugangsdaten in
  einer `.env` im Paketordner.
- VPN-Server und PSK stehen fest im Paket, wie die übrigen Zugangsdaten.

## Umsetzungsstand

- [x] RcbEfaExport, Teil A: `Vpn.ensure_exists()` legt den fehlenden Eintrag
      an (`VPN_SERVER`, `VPN_PSK`), `connect()` ruft es vor `rasdial` auf.
      Authentifizierung wie der bestehende Eintrag (CHAP, MS-CHAPv2, PAP).
      Getestet mit Ersatz für `subprocess.run` und am 2026-10-31 durch den
      Benutzer mit der produktiven Instanz und einem neuen Namen
      (`RCB VPN Test`): Fehlen erkannt, Eintrag angelegt, Verbindung und
      Export erfolgreich. Das NAT-Risiko trat auf dem Entwicklungsrechner
      nicht auf; ob dort früher schon etwas an der Registry eingestellt
      wurde, zeigt erst der Probelauf auf einem zweiten Rechner.
- [ ] Paketmodus in RcbMemberSync, `.env` von aussen in den Export-Projekten
- [ ] Build-Skript und Startskript, Probelauf auf einem zweiten Rechner
