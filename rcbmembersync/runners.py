"""
runners.py

Wrapper um die drei Bibliotheken: Exporte aus efa und ClubDesk, Abgleich.
Enthält keine Fachlogik – die liegt in den jeweiligen Projekten.
"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

from rcbcomparetool.clubdesk import ClubDeskReader
from rcbcomparetool.comparator import ComparisonResult, Comparator
from rcbcomparetool.efa import EfaReader

from .settings import DATA_DIR, project_dir


def export_efa() -> Path:
    """
    Exportiert die efa-Personen über RcbEfaExport (VPN + efaCLI, nur lesend).

    Die Konfiguration kommt aus der .env von RcbEfaExport (dort beim Import
    von rcbefaexport.config geladen).
    """

    from rcbefaexport import EfaClient
    from rcbefaexport.config import Config

    # vorerst immer die produktive Instanz (Standard von from_env)
    with EfaClient(Config.from_env()) as efa:
        return efa.persons.export()


def _export_clubdesk() -> Path:

    from rcbclubdeskexport import ClubDesk
    from rcbclubdeskexport.config import Config
    from rcbclubdeskexport.contacts import Contacts

    directory = project_dir("rcbclubdeskexport")
    env = dotenv_values(directory / ".env")

    # Bis ClubDesk die Pfade als Parameter annimmt (C2 in docs/plan.md):
    # Downloads nach data/, Session bleibt im ClubDesk-Projekt.
    Config.DOWNLOAD_DIR = DATA_DIR / "clubdesk"
    Config.SESSION_FILE = directory / "clubdesk.json"
    Config.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    with ClubDesk(
        username=env.get("CLUBDESK_USERNAME"),
        password=env.get("CLUBDESK_PASSWORD"),
        headless=True,
    ) as cd:
        cd.login()

        contacts = Contacts(cd)
        contacts.open()
        contacts.open_members()

        return contacts.export_csv()


def export_clubdesk() -> Path:
    """
    Exportiert die ClubDesk-Mitglieder über RcbClubdeskExport.

    Läuft in einem eigenen Thread: marimo-Zellen laufen in einer
    asyncio-Schleife, darin verweigert die Playwright-Sync-API den Start.
    """

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_export_clubdesk).result()


@dataclass
class ComparisonData:
    result: ComparisonResult
    efa_rows: dict[str, dict[str, str]]   # efa-Id -> Rohzeile
    clubdesk_ids: set[str]                # ExternalIds aller ClubDesk-Personen


def compare_files(efa_file: Path, clubdesk_file: Path) -> ComparisonData:
    """
    Liest beide Exporte und vergleicht sie (Phase 2).

    Liefert zusätzlich die efa-Rohzeilen und die ClubDesk-ExternalIds, damit
    die Anzeige beide Seiten einer Person nebeneinander zeigen kann.
    """

    efa_records = EfaReader().read_records(efa_file)
    clubdesk_persons = ClubDeskReader().read(clubdesk_file)

    clubdesk_ids = {
        person.external_id.strip()
        for person in clubdesk_persons
        if person.external_id and person.external_id.strip()
    }

    return ComparisonData(
        result=Comparator().compare(efa_records, clubdesk_persons),
        efa_rows={record.person.efa_id: record.row for record in efa_records},
        clubdesk_ids=clubdesk_ids,
    )
