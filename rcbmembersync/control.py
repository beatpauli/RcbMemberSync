"""
control.py

Kontrolle nach dem Einspielen (siehe docs/import-plan.md, GUI Teil 4).

- efa erneut exportieren (efa_nachher.csv im Laufverzeichnis)
- mit der ClubDesk-Datei des Laufs vergleichen (vergleich_nachher.csv)
- je eingespielter Person prüfen, ob die importierten Werte angekommen
  sind: „<n> records imported“ von efaCLI beweist das nicht (InvalidFrom
  z.B. wird gemeldet, aber ignoriert)

Erwartet werden danach nur noch die nicht ausgewählten Personen und die
Einträge „von Hand“. Unterschiede bei Personen, die vor dem Einspielen
nicht auffielen, werden als unerwartet gemeldet.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rcbcomparetool.comparator import ChangeType, FieldChange, PersonChange
from rcbefaexport.config import Instance

from .apply import ApplyResult, ImportOutcome
from .import_files import import_row
from .run import CLUBDESK_NAME, COMPARISON_AFTER_NAME, EFA_AFTER_NAME, write_comparison
from .runners import ComparisonData, compare_files, export_efa


@dataclass(frozen=True)
class PersonCheck:
    outcome: ImportOutcome
    missing_person: bool = False                               # nach dem Import immer noch „neu“
    missing: list[FieldChange] = field(default_factory=list)   # importiert, aber nicht angekommen

    @property
    def arrived(self) -> bool:
        return not self.missing_person and not self.missing

    @property
    def message(self) -> str:
        if self.missing_person:
            return "Person fehlt in efa"
        if self.missing:
            return "; ".join(f"{fc.attribute}: in efa „{fc.old}“, erwartet „{fc.new}“" for fc in self.missing)
        return "alle Werte angekommen"


@dataclass
class ImportCheck:
    checks: list[PersonCheck]
    unexpected: list[PersonChange]   # Unterschiede bei Personen, die vorher nicht auffielen
    remaining: int                   # übrige Unterschiede von vorher (nicht ausgewählt / von Hand)

    @property
    def not_arrived(self) -> list[PersonCheck]:
        return [check for check in self.checks if not check.arrived]


@dataclass
class ControlResult:
    efa_file: Path
    comparison_file: Path
    data: ComparisonData
    check: ImportCheck


def _check(outcome: ImportOutcome, after: list[PersonChange]) -> PersonCheck:

    imported = set(import_row(outcome.file.change) or {}) - {"Id"}
    remaining = [change for change in after if change.external_id == outcome.file.change.external_id]

    if any(change.change_type is ChangeType.NEW for change in remaining):
        return PersonCheck(outcome, missing_person=True)

    missing = [
        field_change
        for change in remaining
        if change.change_type is ChangeType.CHANGED
        for field_change in change.field_changes
        if field_change.attribute in imported
    ]
    return PersonCheck(outcome, missing=missing)


def check_applied(apply_result: ApplyResult, after: list[PersonChange]) -> ImportCheck:
    """
    Vergleicht die Unterschiede nach dem Einspielen (after) mit denen davor
    (apply_result.before) und den eingespielten Personen.

    Geprüft werden nur die importierten Attribute: Eine eingespielte Person
    mit einem Eintrag „von Hand“ (InvalidFrom) bleibt danach zu Recht im
    Vergleich.
    """

    checks = [_check(outcome, after) for outcome in apply_result.outcomes]

    before_ids = {change.external_id for change in apply_result.before}
    applied_ids = {outcome.file.change.external_id for outcome in apply_result.outcomes}

    return ImportCheck(
        checks=checks,
        unexpected=[change for change in after if change.external_id not in before_ids],
        remaining=sum(
            1 for change in after if change.external_id in before_ids and change.external_id not in applied_ids
        ),
    )


def run_control(
    apply_result: ApplyResult,
    exporter: Callable[[Instance, Path, str], Path] = export_efa,
) -> ControlResult:
    """
    Kontroll-Export (nur lesend) aus der Instanz, in die eingespielt wurde,
    Vergleich mit der ClubDesk-Datei des Laufs und Prüfung je eingespielter
    Person. Kann wiederholt werden; efa_nachher.csv und vergleich_nachher.csv
    werden dann ersetzt.
    """

    run_dir = apply_result.run_dir
    efa_file = exporter(apply_result.instance, run_dir, EFA_AFTER_NAME)
    data = compare_files(efa_file, run_dir / CLUBDESK_NAME)

    return ControlResult(
        efa_file=efa_file,
        comparison_file=write_comparison(data.result, run_dir, COMPARISON_AFTER_NAME),
        data=data,
        check=check_applied(apply_result, data.result.changes),
    )
