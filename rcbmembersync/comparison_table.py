"""
comparison_table.py

Baut aus dem Comparator-Ergebnis die Zeilen der Datentabelle (Mockup v1):
pro Person der efa- und der ClubDesk-Datensatz direkt untereinander,
abweichende Werte markiert.
"""

from dataclasses import dataclass, field

from rcbcomparetool.comparator import ChangeType, PersonChange
from rcbcomparetool.mapper import date_from_timestamp, format_date

from .runners import ComparisonData


SOURCE_EFA = "efa"
SOURCE_CLUBDESK = "ClubDesk"

COLUMN_CASE = "Fall"
COLUMN_SOURCE = "Quelle"

# efa-Spalte -> Anzeigename, in Anzeigereihenfolge
DISPLAY_COLUMNS = {
    "FirstName": "Vorname",
    "LastName": "Nachname",
    "Email": "E-Mail",
    "NameAffix": "Brevet",
    "StatusId": "Ruderkategorie",
    "Gender": "Geschlecht",
    "Birthday": "Geburtsdatum",
    "AddressStreet": "Adresse",
    "AddressAdditional": "Adress-Zusatz",
    "AddressZip": "PLZ",
    "AddressCity": "Ort",
    "AddressCountry": "Land",
    "InvalidFrom": "Ungültig ab",
}

CASE_LABELS = {
    ChangeType.NEW: "Neu",
    ChangeType.CHANGED: "Geändert",
    ChangeType.LEFT: "Ausgetreten",
}


@dataclass
class ComparisonTable:
    rows: list[dict[str, str]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)                # je Zeile
    changed_columns: list[set[str]] = field(default_factory=list)   # je Zeile, Anzeigenamen


def _display_value(column: str, value: str) -> str:

    if column == "InvalidFrom" and value.strip():
        try:
            return format_date(date_from_timestamp(value))
        except ValueError:
            return value

    return value


def _row(change: PersonChange, source: str, record: dict[str, str]) -> dict[str, str]:

    row = {
        COLUMN_CASE: CASE_LABELS[change.change_type],
        COLUMN_SOURCE: source,
    }

    for column, label in DISPLAY_COLUMNS.items():
        row[label] = _display_value(column, record.get(column, ""))

    return row


def build_table(data: ComparisonData) -> ComparisonTable:
    """
    Erzeugt die Tabellenzeilen.

    - efa-Zeile: unveränderte efa-Rohzeile
    - ClubDesk-Zeile: Import-Zeile des Comparators (ClubDesk-Werte in
      efa-Darstellung)
    - markiert: Spalten, in denen sich die Import-Zeile von der efa-Rohzeile
      unterscheidet, also alles, was der Import in efa ändern würde
    - Neu: nur ClubDesk-Zeile; ausgetreten ohne ClubDesk-Datensatz: nur efa-Zeile
    """

    table = ComparisonTable()

    for change in data.result.changes:

        efa_row = data.efa_rows.get(change.efa_id) if change.change_type is not ChangeType.NEW else None

        if efa_row is None:
            changed = set()
        else:
            changed = {
                label
                for column, label in DISPLAY_COLUMNS.items()
                if efa_row.get(column, "") != change.efa_record.get(column, "")
            }

            table.rows.append(_row(change, SOURCE_EFA, efa_row))
            table.sources.append(SOURCE_EFA)
            table.changed_columns.append(changed)

        if change.change_type is ChangeType.NEW or change.external_id in data.clubdesk_ids:
            table.rows.append(_row(change, SOURCE_CLUBDESK, change.efa_record))
            table.sources.append(SOURCE_CLUBDESK)
            table.changed_columns.append(changed)

    return table
