"""
selection.py

Auswahl der zu übernehmenden Änderungen (eine Zeile je Person) und Liste der
Aufgaben, die in efa von Hand erledigt werden müssen (siehe docs/import-plan.md).

- Auswählbar sind nur Personen mit Importdatei (neu oder geändert). Eine
  Person wird ganz oder gar nicht übernommen.
- Von Hand: Austritte und jede Änderung an InvalidFrom, weil efa diese
  Spalte beim Import ignoriert.
"""

from rcbcomparetool.comparator import ChangeType, ComparisonResult, PersonChange

from .comparison_table import CASE_LABELS, DISPLAY_COLUMNS, display_value
from .import_files import NOT_IMPORTABLE, import_row


COLUMN_CASE = "Fall"
COLUMN_EXTERNAL_ID = "ExternalId"
COLUMN_LAST_NAME = "Nachname"
COLUMN_FIRST_NAME = "Vorname"
COLUMN_CHANGES = "Änderungen"
COLUMN_TASK = "Aufgabe"


def _label(attribute: str) -> str:
    return DISPLAY_COLUMNS.get(attribute, attribute)


def _person_columns(change: PersonChange) -> dict[str, str]:
    return {
        COLUMN_CASE: CASE_LABELS[change.change_type],
        COLUMN_EXTERNAL_ID: change.external_id,
        COLUMN_LAST_NAME: change.last_name,
        COLUMN_FIRST_NAME: change.first_name,
    }


def selectable_changes(result: ComparisonResult) -> list[PersonChange]:
    """Personen, für die eine Importdatei entsteht."""

    return [change for change in result.changes if import_row(change) is not None]


def selection_rows(changes: list[PersonChange]) -> list[dict[str, str]]:
    """Eine Tabellenzeile je auswählbarer Person, in derselben Reihenfolge."""

    rows = []

    for change in changes:

        if change.change_type is ChangeType.NEW:
            summary = "neue Person, alle Angaben"
        else:
            summary = ", ".join(
                _label(field_change.attribute)
                for field_change in change.field_changes
                if field_change.attribute not in NOT_IMPORTABLE
            )

        rows.append({**_person_columns(change), COLUMN_CHANGES: summary})

    return rows


def _invalid_from_task(old: str, new: str) -> str:

    if not new.strip():
        return "„ab Datum ungültig“ entfernen"

    task = f"ab {display_value('InvalidFrom', new)} ungültig setzen"
    if old.strip():
        task += f" (bisher {display_value('InvalidFrom', old)})"
    return task


def manual_tasks(result: ComparisonResult) -> list[dict[str, str]]:
    """Aufgaben, die in der efa-Oberfläche von Hand zu erledigen sind."""

    rows = []

    for change in result.changes:
        for field_change in change.field_changes:
            if field_change.attribute == "InvalidFrom":
                rows.append(
                    {
                        **_person_columns(change),
                        COLUMN_TASK: _invalid_from_task(field_change.old, field_change.new),
                    }
                )

    return rows
