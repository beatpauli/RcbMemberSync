# GUI-Design – Stand der Diskussion

Stand: 2026-10-23. Ergänzt `docs/plan.md` (Architektur, Entscheidungen) um den
Aufbau der Oberfläche.

## Zusammenarbeit

- Ideen kommen als **draw.io-Mockup** (`docs/mockup.drawio`, XML, direkt lesbar)
  oder als Stichworte/Screenshot im Chat.
- Im Mockup nur Elemente verwenden, die marimo hat: Buttons, Radio/Dropdown,
  Datei-Auswahl, Tabellen, Tabs, Accordion, Callouts.
- Vorgehen in Runden: Mockup → Prototyp in `app.py` mit Testdaten (Beispiele
  aus den Tests des Compare-Tools, keine echten Exporte) → Feedback.
- Vorschlag (noch nicht umgesetzt, Antwort offen): Run-Config „Notebook
  bearbeiten“ um `--watch` ergänzen, damit Änderungen an `app.py` live im
  Browser erscheinen.

## Mockup v1 (`docs/mockup.drawio`)

```
┌ RCB-Mitglieder Abgleich ───────────────────────────────┐
│  efa-Daten                │  ClubDesk-Daten            │
│  [Export]                 │  [Export]                  │
│  [pfad/datei.csv      ]   │  [pfad/datei.csv      ]    │
│                                                        │
│  Vorname │ Nachname │ eMail            │ Brevet        │
│  Max     │ Muster   │ max.muster@x.ch  │ A    (blau)   │
│  Max     │ Muster   │ m.muster@x.ch    │ A    (grün)   │
│                       ^^^ rot = Unterschied            │
└────────────────────────────────────────────────────────┘
```

Aus den Notizen im Mockup:
- **Export-Button:** startet den Export aus der jeweiligen Applikation; der Pfad
  der neuen Datei erscheint im Feld „Dateipfad“.
- **Dateipfad:** bestehende Datei von Hand wählen *oder* per Export erzeugen.
  Sobald beide Dateien definiert sind, erscheint die Datentabelle.
- **Datentabelle:** Daten beider Quellen, pro Person die beiden Datensätze
  direkt untereinander. Unterschiede hervorgehoben (wie genau, ist offen; im
  Beispiel rote Schrift).

Technische Einschätzung:
- Datei wählen → `mo.ui.file_browser` (liefert echten Pfad, kein Upload).
- Tabelle erscheint automatisch → passt zur marimo-Reaktivität; der Vergleich
  ist nebenwirkungsfrei und darf automatisch laufen. Nur Exporte und das
  Schreiben der Importdateien hinter `run_button`.
- Rote Unterschiede → `Comparator` liefert `PersonChange.field_changes`
  (`attribute` = efa-Spalte, `old` = efa, `new` = ClubDesk); `mo.ui.table`
  kann Zellen per `style_cell` einfärben.

## Offene Fragen zum Mockup

1. Welche Personen in der Tabelle: nur mit Unterschieden oder alle? (Comparator
   liefert heute nur Neu/Geändert/Ausgetreten.)
2. Neue / ausgetretene Personen haben nur eine Seite: eine Zeile mit Spalte
   „Fall“ (Neu/Geändert/Ausgetreten) oder Filter/Tabs?
3. Phase 1 (IDs vergeben): wo im Fenster? Darstellung von Mehrdeutigkeiten und
   ungematchten Personen?
4. Ergebnis: wo ist der Button, der `efa_updates.csv` bzw. `efa_import.csv`
   schreibt? Download nötig?
5. Spalten: alle 15 gepflegten Spalten oder Auswahl?
6. Farben bestätigen: blau = efa, grün = ClubDesk?
7. `docs/mockup.drawio` und `docs/RcbMemberSync_Mockup.drawio` sind identisch –
   welche Datei bleibt?

## Umsetzung v1 (2026-10-24)

`app.py` nach Mockup v1 umgesetzt. Für die offenen Fragen vorläufig gewählt
(bis zur Klärung):
- Tabelle zeigt nur Personen mit Änderungen (Ergebnis des Comparators),
  Spalten „Fall“ und „Quelle“ vorne, danach 13 Datenspalten mit deutschen
  Namen (`Id`/`ExternalId` ausgeblendet, `InvalidFrom` als Datum).
- Neu: nur ClubDesk-Zeile; ausgetreten ohne ClubDesk-Datensatz: nur efa-Zeile.
- Rot markiert = alles, was der Import in efa ändern würde (Vergleich
  efa-Rohzeile ↔ Import-Zeile).
- Blau = efa, grün = ClubDesk wie im Mockup.
- Phase 1 und das Schreiben/Herunterladen der Importdateien noch **nicht** drin.
- Button „Demodaten laden“ mit erfundenen Daten (`tests/fixtures/demo/`), weil
  die echte efa-Datei noch fast keine ExternalIds hat.
- Datei wählen über `mo.ui.file_browser` in einem Accordion unter dem Pfadfeld.

## Nächster Schritt

Feedback zu v1 und Antworten auf die offenen Fragen → Mockup v2 bzw.
Anpassungen (u.a. Phase 1, Ausgabedateien).
