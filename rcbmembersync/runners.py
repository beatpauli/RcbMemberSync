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

from rcbefaexport.config import Instance

from .run import CLUBDESK_NAME, EFA_BEFORE_NAME, adopt_file
from .settings import project_dir


def export_efa(instance: Instance, run_dir: Path) -> Path:
    """
    Exportiert die efa-Personen über RcbEfaExport (efaCLI, nur lesend) und
    verschiebt die Datei als efa_vorher.csv ins Laufverzeichnis.

    VPN nur für die produktive Instanz. Die Konfiguration kommt aus der .env
    von RcbEfaExport (dort beim Import von rcbefaexport.config geladen).
    """

    from rcbefaexport import EfaClient
    from rcbefaexport.config import Config

    with EfaClient(Config.from_env(instance)) as efa:
        exported = efa.persons.export()

    return adopt_file(exported, run_dir, EFA_BEFORE_NAME, move=True)


def _export_clubdesk(download_dir: Path) -> Path:

    from rcbclubdeskexport import ClubDesk
    from rcbclubdeskexport.contacts import Contacts

    directory = project_dir("rcbclubdeskexport")
    env = dotenv_values(directory / ".env")

    # Session bleibt im ClubDesk-Projekt, damit sie mit dessen CLI geteilt wird
    with ClubDesk(
        username=env.get("CLUBDESK_USERNAME"),
        password=env.get("CLUBDESK_PASSWORD"),
        headless=True,
        download_dir=download_dir,
        session_file=directory / "clubdesk.json",
    ) as cd:
        cd.login()

        contacts = Contacts(cd)
        contacts.open()
        contacts.open_members()

        return contacts.export_csv()


def export_clubdesk(run_dir: Path) -> Path:
    """
    Exportiert die ClubDesk-Mitglieder über RcbClubdeskExport als
    clubdesk.csv ins Laufverzeichnis.

    Läuft in einem eigenen Thread: marimo-Zellen laufen in einer
    asyncio-Schleife, darin verweigert die Playwright-Sync-API den Start.
    """

    with ThreadPoolExecutor(max_workers=1) as executor:
        exported = executor.submit(_export_clubdesk, run_dir).result()

    return adopt_file(exported, run_dir, CLUBDESK_NAME, move=True)


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
