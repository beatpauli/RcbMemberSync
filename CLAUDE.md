# RcbMemberSync

marimo-Bedienoberfläche für Export und Abgleich der Mitgliederdaten zwischen
ClubDesk und efa. Steuert die drei Geschwister-Projekte an (editierbar
installiert über `requirements-dev.txt`):

- `../RcbClubdeskExport` (`rcbclubdeskexport`) – ClubDesk-Export via Playwright
- `../RcbEfaExport` (`rcbefaexport`) – efa-Export via efaCLI + VPN
- `../RcbCompareTool` (`rcbcomparetool`) – Phase 1 / Phase 2 Abgleich

Plan, Analyse und Entscheidungen: `docs/plan.md` (Abschnitt „Stand“).
GUI-Aufbau, Mockup und offene Fragen: `docs/ui-design.md`.
Änderungen nach efa nachführen (freigegeben 2026-10-25): `docs/import-plan.md`
– **hier weitermachen**.

## Regeln

- **Keine Fachlogik hier.** Matching/Vergleich gehören ins Compare-Tool, Export
  in die Export-Projekte. Hier nur Ablauf, Anzeige, Dateipfade.
- **Einspielen nach efa nur nach ausdrücklicher Freigabe durch den Benutzer**
  (Ablauf siehe `docs/import-plan.md`). Die efaCLI-Ansteuerung liegt in
  RcbEfaExport, RcbMemberSync ruft sie nur auf.
- **Claude löst ein Einspielen nie selbst aus** – auch nicht gegen die lokale
  Testinstanz, auch nicht zum Testen. Das macht ausschliesslich der Benutzer.
  Der lesende efa-Export ist erlaubt.
- Austritte werden nicht eingespielt (`InvalidFrom` lässt sich nicht
  importieren), sondern nur zum Nachführen von Hand aufgelistet.
- **Mehrdeutigkeiten nur anzeigen**, nie in der UI auflösen.
- Schritte mit Nebenwirkung (Login, VPN, efaCLI, Dateien schreiben) immer
  hinter `mo.ui.run_button()` + `mo.stop(...)`.
- Playwright (ClubDesk) nur in einem eigenen Prozess (spawn) aufrufen –
  marimo-Zellen laufen in einer asyncio-Schleife (Sync-API verweigert den
  Start), und marimo stellt unter Windows prozessweit die Selector-Schleife
  ein, die keinen Browser-Prozess starten kann; ein Worker-Thread reicht
  deshalb nicht.
- Export-Zellen (und später Einspielen) dürfen nicht von einem State
  abhängen, den sie selbst setzen – sonst laufen sie ein zweites Mal.
- Zugangsdaten bleiben in der `.env` des jeweiligen Projekts; nie Werte in der
  UI anzeigen oder loggen.
- `app.py` dünn halten, Logik in `rcbmembersync/` (ohne marimo testbar).
- Tests schreiben Ausgaben nur nach `tmp_path`.
- Änderungen an den Geschwister-Projekten nur als kleine, separate Schritte
  mit Rücksprache.
- In Kommentaren, Literals u.ä. Umlaute verwenden statt ae, oe, ue.
