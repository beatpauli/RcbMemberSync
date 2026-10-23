# RcbMemberSync

marimo-Bedienoberfläche für Export und Abgleich der Mitgliederdaten zwischen
ClubDesk und efa. Steuert die drei Geschwister-Projekte an (editierbar
installiert über `requirements-dev.txt`):

- `../RcbClubdeskExport` (`rcbclubdeskexport`) – ClubDesk-Export via Playwright
- `../RcbEfaExport` (`rcbefaexport`) – efa-Export via efaCLI + VPN
- `../RcbCompareTool` (`rcbcomparetool`) – Phase 1 / Phase 2 Abgleich

Plan, Analyse und Entscheidungen: `docs/plan.md`.

## Regeln

- **Keine Fachlogik hier.** Matching/Vergleich gehören ins Compare-Tool, Export
  in die Export-Projekte. Hier nur Ablauf, Anzeige, Dateipfade.
- **efaCLI-Import niemals auslösen.** Der lesende efa-Export über
  RcbEfaExport ist erlaubt; der Import der erzeugten Dateien passiert manuell.
- **Mehrdeutigkeiten nur anzeigen**, nie in der UI auflösen.
- Schritte mit Nebenwirkung (Login, VPN, efaCLI, Dateien schreiben) immer
  hinter `mo.ui.run_button()` + `mo.stop(...)`.
- Playwright (ClubDesk) nur in einem Worker-Thread aufrufen – marimo-Zellen
  laufen in einer asyncio-Schleife, die Sync-API verweigert dort den Start.
- Zugangsdaten bleiben in der `.env` des jeweiligen Projekts; nie Werte in der
  UI anzeigen oder loggen.
- `app.py` dünn halten, Logik in `rcbmembersync/` (ohne marimo testbar).
- Tests schreiben Ausgaben nur nach `tmp_path`.
- Änderungen an den Geschwister-Projekten nur als kleine, separate Schritte
  mit Rücksprache.
- In Kommentaren, Literals u.ä. Umlaute verwenden statt ae, oe, ue.
