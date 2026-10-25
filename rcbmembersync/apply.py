"""
apply.py

Einspielen der ausgewählten Änderungen nach efa (siehe docs/import-plan.md,
GUI Teil 3).

- Eingabedateien und Vergleich im Laufverzeichnis ablegen, eine Importdatei
  je Person schreiben
- eine efaCLI-Sitzung, darin ein Import je Datei; schlägt eine Person fehl,
  laufen die übrigen weiter
- jeder Import mit Ergebnis in efacli.log

Ein Lauf wird nur einmal eingespielt: efacli.log wird exklusiv angelegt und
dient als Sperre. Ausgelöst wird ausschliesslich vom Benutzer über die GUI.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rcbcomparetool.comparator import ChangeType, ComparisonResult, PersonChange
from rcbefaexport.config import Instance

from .import_files import ImportFile, write_import_files
from .run import store_inputs
from .settings import DEMO_DIR


EFACLI_LOG_NAME = "efacli.log"

# Bestätigungswort für die produktive Instanz
CONFIRM_PRODUCTIVE = "produktiv"

INSTANCE_LABELS = {
    Instance.REMOTE: "produktiv",
    Instance.LOCAL: "lokale Testinstanz",
}

# Jede Importdatei enthält genau eine Person
EXPECTED_RECORDS = 1


@dataclass(frozen=True)
class ImportOutcome:
    file: ImportFile
    records: int | None = None   # laut efaCLI importierte Datensätze
    error: str | None = None     # Ausnahme beim Import

    @property
    def ok(self) -> bool:
        return self.error is None and self.records == EXPECTED_RECORDS

    @property
    def message(self) -> str:
        if self.error is not None:
            return self.error
        if self.records == 0:
            return "0 Datensätze importiert (efaCLI meldet keinen Grund, z.B. Id unbekannt)"
        return f"{self.records} Datensätze importiert"


@dataclass
class ApplyResult:
    run_dir: Path
    instance: Instance
    outcomes: list[ImportOutcome] = field(default_factory=list)
    before: list[PersonChange] = field(default_factory=list)   # alle Unterschiede vor dem Einspielen

    @property
    def failed(self) -> list[ImportOutcome]:
        return [outcome for outcome in self.outcomes if not outcome.ok]


def already_applied(run_dir: Path | None) -> bool:
    """True, wenn in diesem Laufverzeichnis schon eingespielt wurde."""

    return run_dir is not None and (run_dir / EFACLI_LOG_NAME).exists()


def is_demo_file(path: Path) -> bool:
    return path.resolve().is_relative_to(DEMO_DIR.resolve())


def confirmed(instance: Instance, checked: bool, typed: str) -> bool:
    """Freigabe: Häkchen gesetzt, bei produktiv zusätzlich „produktiv“ eingetippt."""

    if not checked:
        return False
    return instance is Instance.LOCAL or typed.strip() == CONFIRM_PRODUCTIVE


def _default_client(instance: Instance) -> AbstractContextManager[Any]:

    from rcbefaexport import EfaClient
    from rcbefaexport.config import Config

    return EfaClient(Config.from_env(instance))


def _case_counts(changes: list[PersonChange]) -> str:

    new = sum(1 for change in changes if change.change_type is ChangeType.NEW)
    changed = sum(1 for change in changes if change.change_type is ChangeType.CHANGED)
    return f"{len(changes)} Personen ({new} neu, {changed} geändert)"


def import_all(files: list[ImportFile], efa: Any, log_path: Path, header: list[str]) -> list[ImportOutcome]:
    """
    Importiert jede Datei einzeln über efa.persons.import_file und protokolliert
    jeden an efaCLI gesendeten Befehl sowie das Ergebnis je Datei. Fehler einer
    Person brechen den Lauf nicht ab.

    Das Log wird exklusiv angelegt (FileExistsError, falls es schon existiert)
    und nach jeder Zeile geschrieben, damit es auch bei einem Absturz den
    Stand zeigt.
    """

    outcomes = []

    with log_path.open("x", encoding="utf-8") as log:

        def write(text: str) -> None:
            log.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {text}\n")
            log.flush()

        for line in header:
            write(line)

        # Befehle, die die Sitzung nach dem Schliessen des Logs sendet
        # (z.B. quit), werden nicht mehr protokolliert
        efa.on_command = lambda command: write(f">>> {command}")
        try:
            for file in files:
                try:
                    outcome = ImportOutcome(file, records=efa.persons.import_file(file.path, file.mode))
                except Exception as e:
                    outcome = ImportOutcome(file, error=f"{type(e).__name__}: {e}")

                outcomes.append(outcome)
                status = "ok     " if outcome.ok else "FEHLER "
                write(f"{status} {file.path.name} ({file.mode}): {outcome.message}")
        finally:
            efa.on_command = None

        failed = sum(1 for outcome in outcomes if not outcome.ok)
        write(f"Ende: {len(outcomes) - failed} ok, {failed} fehlgeschlagen")

    return outcomes


def apply_changes(
    instance: Instance,
    run_dir: Path,
    efa_file: Path,
    clubdesk_file: Path,
    result: ComparisonResult,
    changes: list[PersonChange],
    client_factory: Callable[[Instance], AbstractContextManager[Any]] = _default_client,
) -> ApplyResult:
    """
    Spielt die ausgewählten Änderungen nach efa ein.

    Kommt die efaCLI-Sitzung nicht zustande (z.B. VPN), wird nichts
    eingespielt und kein Log angelegt – der Lauf kann wiederholt werden.
    """

    if already_applied(run_dir):
        raise RuntimeError(f"Dieser Lauf wurde bereits eingespielt ({run_dir.name}).")

    if is_demo_file(efa_file) or is_demo_file(clubdesk_file):
        raise RuntimeError("Demodaten werden nicht eingespielt.")

    store_inputs(run_dir, efa_file, clubdesk_file, result)
    files = write_import_files(changes, run_dir)

    apply_result = ApplyResult(run_dir=run_dir, instance=instance, before=list(result.changes))

    if not files:
        return apply_result

    header = [
        f"Einspielen nach efa, Instanz: {INSTANCE_LABELS[instance]}",
        f"efa-Datei: {efa_file}",
        f"ClubDesk-Datei: {clubdesk_file}",
        f"Ausgewählt: {_case_counts([file.change for file in files])}",
    ]

    with client_factory(instance) as efa:
        apply_result.outcomes = import_all(files, efa, run_dir / EFACLI_LOG_NAME, header)

    return apply_result
