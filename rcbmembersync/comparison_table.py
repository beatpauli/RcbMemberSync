"""
comparison_table.py

Baut aus dem Comparator-Ergebnis die Zeilen der Datentabelle: eine Zeile je
Person. Abweichende Felder enthalten beide Werte (efa oben, ClubDesk unten),
die Spalte „Quelle“ zeigt die Reihenfolge an. In derselben Tabelle wird je
Person gewählt, ob ihre Änderungen nach efa übernommen werden.

Die Darstellung (HTML, Farben) macht app.py, damit dieses Modul ohne marimo
testbar bleibt.
"""

import unicodedata
from dataclasses import dataclass, field

from rcbcomparetool.comparator import ChangeType, PersonChange
from rcbcomparetool.mapper import date_from_timestamp, format_date

from .import_files import NOT_IMPORTABLE, import_row
from .runners import ComparisonData


SOURCE_EFA = "efa"
SOURCE_CLUBDESK = "ClubDesk"

COLUMN_CASE = "Fall"
COLUMN_SOURCE = "Quelle"
COLUMN_EXTERNAL_ID = "ClubDeskId"
COLUMN_TRANSFER = "Übernahme"

# efa-Spalte -> Anzeigename, in Anzeigereihenfolge
DISPLAY_COLUMNS = {
    "FirstName": "Vorname",
    "LastName": "Nachname",
    "FirstLastName": "Nachname, Vorname",
    "Email": "E-Mail",
    "NameAffix": "Brevet",
    "StatusId": "Ruderkategorie",
    "Gender": "Geschlecht",
    "Birthday": "Geburtsdatum",
    "InvalidFrom": "Ungültig ab",
}

CASE_LABELS = {
    ChangeType.NEW: "Neu",
    ChangeType.CHANGED: "Geändert",
    ChangeType.LEFT: "Ausgetreten",
}

TRANSFER_IMPORT = "Import"

# Reihenfolge der Fälle in der Tabelle; innerhalb eines Falls nach Nach- und
# Vorname
CASE_ORDER = (ChangeType.CHANGED, ChangeType.NEW, ChangeType.LEFT)


@dataclass
class TableRow:
    change: PersonChange
    sources: tuple[str, ...]                 # (efa,), (ClubDesk,) oder (efa, ClubDesk)
    values: dict[str, str]                   # Anzeigename -> Wert (Felder ohne Abweichung)
    differences: dict[str, tuple[str, str]]  # Anzeigename -> (efa-Wert, ClubDesk-Wert)
    transfer: str                            # Inhalt der Spalte „Übernahme“
    importable: bool                         # auswählbar: es entsteht eine Importdatei


@dataclass
class ComparisonTable:
    rows: list[TableRow] = field(default_factory=list)


def display_value(column: str, value: str) -> str:

    if column == "InvalidFrom" and value.strip():
        try:
            return format_date(date_from_timestamp(value))
        except ValueError:
            return value

    return value


def _invalid_from_task(old: str, new: str) -> str:

    if not new.strip():
        return "„ab Datum ungültig“ entfernen"

    task = f"ab {display_value('InvalidFrom', new)} ungültig setzen"
    if old.strip():
        task += f" (bisher {display_value('InvalidFrom', old)})"
    return task


def _transfer(change: PersonChange, importable: bool) -> str:
    """Import, von Hand (InvalidFrom ist nicht importierbar) oder beides."""

    parts = [TRANSFER_IMPORT] if importable else []

    for field_change in change.field_changes:
        if field_change.attribute in NOT_IMPORTABLE:
            parts.append(f"von Hand: {_invalid_from_task(field_change.old, field_change.new)}")

    return "; ".join(parts)


def _name_key(name: str) -> str:
    """Wie im Telefonbuch: ohne Gross-/Kleinschreibung, ä wie a, é wie e usw."""

    decomposed = unicodedata.normalize("NFKD", name.strip().casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _sort_key(change: PersonChange) -> tuple:

    return (
        CASE_ORDER.index(change.change_type),
        _name_key(change.last_name),
        _name_key(change.first_name),
    )


def build_table(data: ComparisonData) -> ComparisonTable:
    """
    Eine Zeile je Person.

    - efa-Wert: unveränderte efa-Rohzeile
    - ClubDesk-Wert: Import-Zeile des Comparators (ClubDesk-Werte in
      efa-Darstellung)
    - Abweichung: Spalten, in denen sich beide unterscheiden, also alles, was
      in efa zu ändern ist
    - Neu: nur ClubDesk-Werte; ausgetreten ohne ClubDesk-Datensatz: nur
      efa-Werte, die Abweichung zeigt das neue „Ungültig ab“
    - Sortiert nach Fall (geändert, neu, ausgetreten), dann Nach- und Vorname
    """

    table = ComparisonTable()

    changes = sorted(data.result.changes, key=_sort_key)

    for change in changes:

        efa_row = data.efa_rows.get(change.efa_id) if change.change_type is not ChangeType.NEW else None
        in_clubdesk = change.change_type is ChangeType.NEW or change.external_id in data.clubdesk_ids

        if efa_row is None:
            sources = (SOURCE_CLUBDESK,)
        elif in_clubdesk:
            sources = (SOURCE_EFA, SOURCE_CLUBDESK)
        else:
            sources = (SOURCE_EFA,)

        values = {}
        differences = {}

        for column, label in DISPLAY_COLUMNS.items():

            new = display_value(column, change.efa_record.get(column, ""))

            if efa_row is None:
                values[label] = new
                continue

            old = display_value(column, efa_row.get(column, ""))

            if old != new:
                differences[label] = (old, new)
            else:
                values[label] = old

        importable = import_row(change) is not None

        table.rows.append(
            TableRow(
                change=change,
                sources=sources,
                values=values,
                differences=differences,
                transfer=_transfer(change, importable),
                importable=importable,
            )
        )

    return table
