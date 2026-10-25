# Änderungen nach efa nachführen – Plan

Stand: 2026-10-25. Status: **freigegeben (2026-10-25).**

Bisher erzeugt RcbMemberSync nur die Importdateien, der Import nach efa läuft
manuell. Neu sollen die gefundenen Unterschiede direkt aus RcbMemberSync über
efaCLI in efa nachgeführt werden.

## Entscheidungen (2026-10-25)

1. **RcbMemberSync löst das Nachführen aus.** Die efaCLI-Ansteuerung liegt in
   RcbEfaExport (dort gibt es schon Prozess, Prompts, VPN und Instanzen).
   RcbMemberSync ruft sie nur auf. Das Compare-Tool ruft efaCLI weiterhin nie auf.
2. **Der Benutzer entscheidet, was eingespielt wird.** Es gibt keine
   automatische Sperre wegen veralteter Exporte.
3. **Eine Importdatei je Person**, ein efaCLI-`import` je Datei.
   - Name: `<ExternalId>_<LastName>_<FirstName>.csv`, Leerzeichen werden
     weggelassen, Umlaute bleiben (z.B. `1001_vonAllmen_Jürg.csv`).
   - Geänderte Person: Spalten `Id` + **alle** geänderten Attribute.
   - Neue Person: alle Attribute.
   - Ausgetretene Person: **keine Importdatei**. `InvalidFrom` lässt sich
     nicht importieren (Test 5); der Austritt wird wie bisher in der
     efa-Oberfläche von Hand gesetzt („ab Datum ungültig“). Die GUI listet die
     betroffenen Personen mit Datum auf.
   - Weil nur geänderte Attribute in der Datei stehen, überschreibt ein Import
     keine anderen, inzwischen in efa geänderten Werte (sofern efa fehlende
     Spalten unverändert lässt, siehe offene Punkte).
4. **Auswahl nur je Person, alles oder nichts.** ClubDesk ist führend: Stimmt
   ein Wert nicht, wird er in ClubDesk korrigiert, nicht beim Einspielen
   weggelassen.
5. **Definitive Freigabe durch den Benutzer** vor dem Einspielen. Angezeigt
   werden Instanz, Anzahl Personen je Fall; „produktiv“ ist deutlich
   hervorgehoben.
6. **Ein eigenes Verzeichnis je Lauf** für alle beteiligten Dateien (siehe
   „Laufverzeichnis“).
7. **Kontrolle nach dem Einspielen:** efa erneut exportieren und vergleichen.
8. **Log der efaCLI-Aufrufe** im Laufverzeichnis.
9. **Phase 1 (IDs vergeben)** ohne GUI, nur über eine Run-Config, mit **einer
   Importdatei für alle Personen** (`Id|ExternalId`).

Für Claude gilt zusätzlich: Ein Einspielen wird während der Entwicklung nie
selbst ausgelöst, auch nicht gegen die lokale Instanz. Das macht der Benutzer.

## efaCLI-Import (Quelle: efa-Wiki, Seite `access_cli`)

```
persons
import [-encoding=UTF-8|ISO-8859-1] [-csvsep=X] [-csvquote=X]
       [-impmode=add|update|addupdate] [-updversion=update|new] <filename>
```

Geplanter Aufruf je Datei (in der bestehenden efaCLI-Sitzung von RcbEfaExport):

| Fall | Befehl |
|---|---|
| geänderte Person, Phase 1 | `import -encoding=UTF-8 -csvsep=\| -impmode=update -updversion=update <datei>` |
| neue Person | `import -encoding=UTF-8 -csvsep=\| -impmode=addupdate -updversion=update <datei>` |

Weitere Hinweise aus der Doku:
- efaCLI kennt Return Codes (0 = ok, 10 = mit Fehlern, 11 = fehlgeschlagen),
  allerdings nur beim Aufruf mit `-cmd`. RcbEfaExport nutzt die interaktive
  Shell, Erfolg muss dort aus der Ausgabe erkannt werden.
- Das Passwort kann statt auf der Kommandozeile in `.efacred` im
  Heimatverzeichnis stehen. Heute übergibt RcbEfaExport es auf der
  Kommandozeile (in der Prozessliste sichtbar). Das ist eine mögliche Verbesserung,
  aber unabhängig vom Import.

## Laufverzeichnis

```
output/
  2026-10-25_1430/            # bzw. 2026-10-25_1430_LOKAL für die Testinstanz
    efa_vorher.csv            # efa-Export (bzw. Kopie der gewählten Datei)
    clubdesk.csv              # ClubDesk-Export (bzw. Kopie der gewählten Datei)
    vergleich.csv             # Ergebnis des Vergleichs (alle Unterschiede)
    import/
      1001_Muster_Max.csv     # eine Datei je ausgewählter Person
      1004_Neu_Laura.csv
    efacli.log                # jeder efaCLI-Aufruf mit Ausgabe und Ergebnis
    efa_nachher.csv           # Kontroll-Export nach dem Einspielen
    vergleich_nachher.csv     # Kontroll-Vergleich
```

- Das Verzeichnis entsteht bei der ersten Aktion der Sitzung (Export oder
  Dateiwahl). Exporte werden direkt dorthin geschrieben, von Hand gewählte
  Dateien dorthin kopiert.
- Für ClubDesk braucht es dafür den Download-Pfad als Parameter (C2 in
  `docs/plan.md`). Für efa reicht `Config.export_dir`.
- Zugangsdaten erscheinen nie im Log.

## Ablauf in der GUI

```
[Instanz wählen]   produktiv (Standard) | lokal
        │
[efa / ClubDesk]   Export oder Datei wählen  → Laufverzeichnis
        │
[Datentabelle]     wie heute (efa blau, ClubDesk grün, Unterschiede rot),
        │          zusätzlich Auswahl je Person (alle / keine / einzeln)
        │          nur Neu und Geändert sind auswählbar
        │
[Austritte]        Liste „In efa von Hand ungültig setzen“: Name, ExternalId,
        │          ungültig ab (Datum aus dem Comparator), nicht auswählbar
        │
[Freigabe]         Zusammenfassung + ausdrückliche Bestätigung
        │
[Einspielen]       Importdateien je Person schreiben, dann je Datei ein
        │          efaCLI-import, Fortschritt, Log
        │
[Kontrolle]        efa neu exportieren + vergleichen
                   erwartet: nur noch die nicht ausgewählten Personen
```

## Phase 1 (IDs vergeben) über Run-Config

```
python -m rcbmembersync assign-ids [--instance local] [--clubdesk-file PFAD]
```

1. efa exportieren (und ClubDesk exportieren oder Datei verwenden) → Laufverzeichnis
2. Namens-Matching über das Compare-Tool (`PersonMatcher`)
3. Zusammenfassung in der Konsole: Matches, Mehrdeutigkeiten (werden **nie**
   eingespielt), ungematchte Personen
4. Freigabe durch Eingabe von `ja` in der Konsole
5. Eine Importdatei `Id|ExternalId` mit allen Matches (`write_import_file` des
   Compare-Tools), ein efaCLI-`import -impmode=update`, Log im Laufverzeichnis
6. Kontroll-Export

Run-Configs: „IDs vergeben produktiv“ und „IDs vergeben lokal“.

## Aufteilung auf die Projekte

| Projekt | Neu |
|---|---|
| RcbEfaExport | `persons.import_file(pfad, mode)`: `persons` + efaCLI-`import` (immer `-updversion=update`) in der bestehenden Sitzung; liefert die Anzahl importierter Datensätze aus „`<n>` records imported“ |
| RcbClubdeskExport | Download-Pfad als Parameter (C2) – **erledigt** |
| RcbCompareTool | – (Phase-1-Importdatei bereits auf `Id\|ExternalId` korrigiert) |
| RcbMemberSync | Instanzauswahl, Laufverzeichnis, Auswahl je Person, Importdateien je Person, Freigabe, Einspielen, Kontrolle, Log; `assign-ids` als Kommandozeile |

## Regeln, die bei Freigabe angepasst werden

- `RcbMemberSync/CLAUDE.md`: „efaCLI-Import niemals auslösen“ ersetzen durch
  „Einspielen nur nach ausdrücklicher Freigabe durch den Benutzer; Claude
  löst es nie selbst aus“.
- `RcbMemberSync/docs/plan.md`, Entscheidung 1: entsprechend ergänzen.
- `RcbCompareTool/CLAUDE.md`: unverändert, das Compare-Tool ruft efaCLI nie auf.

## Offene Punkte

Die ursprünglichen Punkte 1–6 (Teil-Update, Versionierung, Schlüssel, neue
Person, Rückmeldung, Wertformate) sind durch die Tests geklärt, siehe
„Testergebnisse“. Ein Attribut zu leeren ist nicht nötig: Der Comparator
übernimmt nur nicht-leere ClubDesk-Werte.

Neu offen:

1. **`StatusId`:** Produktiv (keine leeren Werte): `Breitensport`,
   `Fitnesssport`, `Jugendsport`, `Lehrgang`, `Leistungssport` sowie `Gast`,
   `Gast_Jugendsport`, `Gast_Schulsport`, `Gast_Wahlsport`. Die
   Ruderkategorien passen zur Annahme des Comparators; `Gast…`-Werte meldet
   er als Konflikt und lässt sie unangetastet (sicher). Lokal (`RCB_KOPIE`)
   stehen dagegen nur leer / `Gast` / `andere` – die lokale Kopie ist für
   `StatusId` nicht repräsentativ.
   **Geklärt:** Die `Gast…`-Einträge sind keine echten Personen, sondern
   Platzhalter für Fahrten ohne eigenen Personeneintrag („Gast 1–9“,
   „Jugendsport 1–9“, „Schulsport 1–9“, „Kantonsschule Wahlsport_1–9“). Sie
   werden nie Mitglieder, haben keinen Namenstreffer in ClubDesk (geprüft
   2026-10-25), erhalten in Phase 1 keine `ExternalId` und werden in Phase 2
   nie angefasst → keine Änderung am Compare-Tool, keine Doppeleintrag-Prüfung
   nötig.
   Offen: Lokale Kopie vor den Abschlusstests mit produktiven Daten auffrischen?

## Testergebnisse lokale Instanz (2026-10-25)

Testdateien und Exporte nach jedem Schritt: `data/efacli-test/` (nicht
versioniert).

- **Teil-Update funktioniert (Punkt 1 geklärt):** `Id|Email` mit
  `-impmode=update -updversion=update` ändert nur `Email`. Alle anderen
  Spalten bleiben erhalten, ausser `ChangeCount` (+1) und `LastModified`.
  Keine anderen Personen betroffen.
- **Schlüssel ist `Id` (Punkt 3 geklärt).**
- **`-updversion=update` (Punkt 2 entschieden):** keine neue Version,
  weiterhin genau eine Zeile je `Id`. Wird immer so verwendet; Versionen in
  efa spielen keine Rolle, `-updversion=new` wird nicht gebraucht.
- **Rückmeldung (Punkt 5 geklärt):** `INFO - CLI001 - <n> records imported
  from <datei>`. Bei unbekannter `Id` oder `-impmode=update` für eine nicht
  existierende Person: `0 records imported`, **ohne** Fehlermeldung.
  → Erfolg = Anzahl importierter Datensätze entspricht den Datenzeilen der
  Datei.
- **Prompt:** Nach jedem `import` kehrt efaCLI ins Menü `main` zurück, vor
  jedem Import ist also erneut `persons` nötig (wie beim Export).
- `import` direkt im Menü `main` wird ohne Meldung ignoriert.
- **Neue Person (Punkt 4 geklärt):** efa übernimmt eine vorgegebene `Id`.
  Ergebnisse:
  - `Id` + 13 Attribute, `-impmode=add`: **0** records (Grund unbekannt)
  - dieselbe Datei, `-impmode=addupdate`: 1 record, `Id` übernommen
  - alle 30 Spalten wie im Export, `-impmode=add`: 1 record, `Id` übernommen
  - ohne `Id`, `-impmode=add`: 1 record, efa vergibt eine eigene `Id`

  → Neue Personen mit `-impmode=addupdate` und der vom Comparator erzeugten
  `Id` importieren (mit genau diesem Dateiformat erfolgreich getestet).
  `FirstLastName` („Nachname, Vorname“), `ValidFrom` (Importzeitpunkt) und
  `InvalidFrom` (`9223372036854775807` = unbegrenzt gültig) setzt efa selbst.
- **Wertformate (Punkt 6 teilweise geklärt):** `Birthday` als `TT.MM.JJJJ`,
  `Gender` als `weiblich`/`männlich`, `NameAffix` als Kurzcode (`A`) werden
  korrekt übernommen.
- **`InvalidFrom` lässt sich nicht importieren (Test 5):** `Id|InvalidFrom`
  mit `-impmode=update` meldet `1 records imported` und erhöht `ChangeCount`,
  `InvalidFrom` bleibt aber `9223372036854775807` (unbegrenzt gültig).
  Vermutlich ein von efa verwaltetes Versionierungsfeld.
  → **Austritte können so nicht nachgeführt werden.** Entscheid: Austritte
  bleiben ein Schritt von Hand in der efa-Oberfläche („ab Datum ungültig“),
  die GUI listet sie nur auf. Das Compare-Tool bleibt unverändert: Es liefert
  das Austrittsdatum und lässt Personen weg, die in efa bereits ungültig sind,
  die Liste erledigt sich also nach dem Nachführen von Hand von selbst.
  → **„`<n>` records imported“ beweist nicht, dass ein Wert übernommen
  wurde.** Die Kontrolle nach dem Einspielen muss je Person prüfen, ob die
  Werte im Kontroll-Export angekommen sind.

## Geklärt (2026-10-25)

- **Phase 1, Zielspalte `ExternalId`:** `MembershipNo` enthält in efa bereits
  Werte unbekannter Bedeutung und hat keinen Einfluss auf den Vergleich.
  `ExternalId` war unbenutzt und trifft die Bedeutung (ID in ClubDesk). Das
  Compare-Tool schreibt die Phase-1-Datei jetzt mit `Id|ExternalId`.
- **Fehler beim Einspielen:** Schlägt der Import einer Person fehl, laufen die
  übrigen Personen weiter. Am Ende werden alle fehlgeschlagenen Personen
  gemeldet (GUI und `efacli.log`); der Kontroll-Vergleich zeigt sie wieder an.

## Umsetzungsstand

- [x] RcbEfaExport: `persons.import_file(pfad, mode)` (`2fbdb06`)
- [x] RcbClubdeskExport: Download-Pfad als Parameter, C2 (`59c649e`)
- [x] RcbMemberSync: `import_files.py` – Laufverzeichnis
      (`create_run_dir`), Importdatei je Person (`write_import_files`),
      Liste der Austritte (`leavers`). Dateinamen ohne Leerzeichen und ohne
      unter Windows unzulässige Zeichen (`\/:*?"<>|`), Umlaute bleiben.
- [x] RcbMemberSync GUI Teil 1: Instanzauswahl (Wechsel verwirft die
      efa-Datei und beginnt einen neuen Lauf), Laufverzeichnis beim ersten
      Export, Exporte landen als `efa_vorher.csv` / `clubdesk.csv` darin
      (`run.py`). Von Hand gewählte Dateien und `vergleich.csv` werden erst
      bei der Freigabe abgelegt (`store_inputs`), weil Dateien nur hinter
      einem Button geschrieben werden.
- [x] GUI Teil 2: Auswahl direkt in der Datentabelle, eine Zeile je
      Person. Abweichende Felder zeigen beide Werte rot untereinander
      (oben efa, unten ClubDesk; Spalte „Quelle“ entsprechend). Spalte
      „Übernahme“: `Import` und/oder `von Hand: …` (Austritte, jede
      `InvalidFrom`-Änderung). Vorausgewählt sind alle Personen mit
      Import; angehakte Zeilen „von Hand“ werden ignoriert. Keine
      zusätzlichen Tabellen (Wunsch Benutzer 2026-10-25).
- [ ] GUI Teil 3: Freigabe, Einspielen, `efacli.log`
- [ ] GUI Teil 4: Kontrolle (Export + Vergleich danach)
- [ ] RcbMemberSync: `assign-ids` als Kommandozeile + Run-Configs
