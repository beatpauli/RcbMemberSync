"""
import_files.py

Laufverzeichnis und efaCLI-Importdateien je Person (siehe docs/import-plan.md).

- Geänderte Person: Spalten Id + alle geänderten Attribute (Teil-Update)
- Neue Person: alle gepflegten Spalten ausser InvalidFrom, mit der vom
  Comparator erzeugten Id
- Ausgetretene Person: keine Datei (InvalidFrom lässt sich nicht importieren),
  wird nur zum Nachführen von Hand aufgelistet
"""

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rcbcomparetool.comparator import UPDATES_FILE_HEADER, ChangeType, ComparisonResult, PersonChange
from rcbcomparetool.mapper import timestamp_prefix
from rcbefaexport.config import Instance
from rcbefaexport.persons import ImportMode


IMPORT_SUBDIR = "import"
IMPORT_DELIMITER = "|"

# InvalidFrom ignoriert efa beim Import (Test an der lokalen Instanz)
NOT_IMPORTABLE = {"InvalidFrom"}

NEW_PERSON_HEADER = tuple(column for column in UPDATES_FILE_HEADER if column not in NOT_IMPORTABLE)

# Zeichen, die in Windows-Dateinamen nicht erlaubt sind, plus Leerzeichen
_FILENAME_REMOVE = re.compile(r'[\s\\/:*?"<>|]')


@dataclass(frozen=True)
class ImportFile:
    path: Path
    change: PersonChange
    mode: ImportMode


def create_run_dir(base_dir: Path, instance: Instance, now: datetime | None = None) -> Path:
    """
    Legt das Laufverzeichnis <base_dir>/<YYYY-MM-DD_HHMM>[_LOKAL] an.

    Gibt es das Verzeichnis schon (zweiter Lauf in derselben Minute), wird
    ein Zähler angehängt.
    """

    name = timestamp_prefix(now)
    if instance is Instance.LOCAL:
        name += "_LOKAL"

    run_dir = base_dir / name
    counter = 2
    while run_dir.exists():
        run_dir = base_dir / f"{name}_{counter}"
        counter += 1

    run_dir.mkdir(parents=True)
    return run_dir


def import_file_name(change: PersonChange) -> str:
    """<ExternalId>_<LastName>_<FirstName>.csv, ohne Leerzeichen, Umlaute bleiben."""

    parts = (change.external_id, change.last_name, change.first_name)
    return "_".join(_FILENAME_REMOVE.sub("", part) for part in parts) + ".csv"


def import_row(change: PersonChange) -> dict[str, str] | None:
    """Spalten und Werte der Importdatei; None, wenn nichts zu importieren ist."""

    if change.change_type is ChangeType.NEW:
        return {column: change.efa_record.get(column, "") for column in NEW_PERSON_HEADER}

    if change.change_type is ChangeType.CHANGED:
        row = {"Id": change.efa_id}
        for field_change in change.field_changes:
            if field_change.attribute not in NOT_IMPORTABLE:
                row[field_change.attribute] = field_change.new
        return row if len(row) > 1 else None

    return None   # ausgetreten


def leavers(result: ComparisonResult) -> list[PersonChange]:
    """Ausgetretene Personen – in efa von Hand ungültig setzen."""

    return [change for change in result.changes if change.change_type is ChangeType.LEFT]


def write_import_files(changes: list[PersonChange], run_dir: Path) -> list[ImportFile]:
    """
    Schreibt je Person eine Importdatei nach <run_dir>/import/.

    Format wie an der lokalen Instanz getestet: UTF-8 ohne BOM, Delimiter '|',
    CRLF. Personen ohne importierbare Änderung (z.B. ausgetreten) werden
    übersprungen.
    """

    directory = run_dir / IMPORT_SUBDIR
    directory.mkdir(parents=True, exist_ok=True)

    files = []

    for change in changes:

        row = import_row(change)
        if row is None:
            continue

        path = directory / import_file_name(change)

        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=IMPORT_DELIMITER, lineterminator="\r\n")
            writer.writerow(row.keys())
            writer.writerow(row.values())

        mode = ImportMode.ADDUPDATE if change.change_type is ChangeType.NEW else ImportMode.UPDATE
        files.append(ImportFile(path=path, change=change, mode=mode))

    return files
