"""
run.py

Laufverzeichnis: alle Dateien eines Laufs liegen gemeinsam in
output/<YYYY-MM-DD_HHMM>[_LOKAL]/ (siehe docs/import-plan.md).
"""

import shutil
from datetime import datetime
from pathlib import Path

from rcbcomparetool.comparator import ComparisonResult, write_change_report
from rcbcomparetool.mapper import timestamp_prefix
from rcbefaexport.config import Instance


EFA_BEFORE_NAME = "efa_vorher.csv"
CLUBDESK_NAME = "clubdesk.csv"
COMPARISON_NAME = "vergleich.csv"


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


def adopt_file(source: Path, run_dir: Path, name: str, move: bool = False) -> Path:
    """
    Legt eine Eingabedatei unter festem Namen im Laufverzeichnis ab.

    Von Hand gewählte Dateien werden kopiert (Original bleibt unverändert),
    frische Exporte verschoben (move=True). Eine vorhandene Datei gleichen
    Namens wird ersetzt.
    """

    target = run_dir / name

    if source.resolve() == target.resolve():
        return target

    if move:
        shutil.move(source, target)
    else:
        shutil.copyfile(source, target)

    return target


def write_comparison(result: ComparisonResult, run_dir: Path) -> Path:
    """Ergebnis des Vergleichs (alle Unterschiede) als vergleich.csv ablegen."""

    path = run_dir / COMPARISON_NAME
    write_change_report(result, path)
    return path


def store_inputs(run_dir: Path, efa_file: Path, clubdesk_file: Path, result: ComparisonResult) -> None:
    """
    Beide Eingabedateien und den Vergleich im Laufverzeichnis ablegen.

    Wird bei der Freigabe aufgerufen, damit der Lauf vollständig
    nachvollziehbar ist – auch wenn die Dateien von Hand gewählt wurden.
    Exporte, die schon im Laufverzeichnis liegen, bleiben unverändert.
    """

    adopt_file(efa_file, run_dir, EFA_BEFORE_NAME)
    adopt_file(clubdesk_file, run_dir, CLUBDESK_NAME)
    write_comparison(result, run_dir)
