from datetime import date

from rcbcomparetool.comparator import ChangeType, ComparisonResult, FieldChange, PersonChange
from rcbcomparetool.mapper import timestamp_from_date

from rcbmembersync.runners import compare_files
from rcbmembersync.selection import manual_tasks, selectable_changes, selection_rows
from rcbmembersync.settings import DEMO_DIR


def _demo_result():
    return compare_files(DEMO_DIR / "efa.csv", DEMO_DIR / "clubdesk.csv").result


def _changed(field_changes):
    return PersonChange(
        change_type=ChangeType.CHANGED,
        efa_id="e-1",
        external_id="1001",
        last_name="Muster",
        first_name="Max",
        efa_record={},
        field_changes=field_changes,
    )


def test_only_new_and_changed_persons_are_selectable():

    changes = selectable_changes(_demo_result())

    assert {(c.change_type, c.last_name) for c in changes} == {
        (ChangeType.CHANGED, "Muster"),
        (ChangeType.CHANGED, "Probe"),
        (ChangeType.NEW, "Neu"),
    }


def test_selection_rows_summarise_changes():

    rows = {row["Nachname"]: row for row in selection_rows(selectable_changes(_demo_result()))}

    assert rows["Muster"] == {
        "Fall": "Geändert",
        "ExternalId": "1001",
        "Nachname": "Muster",
        "Vorname": "Max",
        "Änderungen": "E-Mail",
    }
    assert rows["Probe"]["Änderungen"] == "Brevet, Adresse, Ort, PLZ"
    assert rows["Neu"]["Änderungen"] == "neue Person, alle Angaben"


def test_leavers_are_manual_tasks():

    tasks = {row["Nachname"]: row for row in manual_tasks(_demo_result())}

    assert set(tasks) == {"Alt", "Austritt"}
    assert tasks["Austritt"]["Fall"] == "Ausgetreten"
    assert tasks["Austritt"]["Aufgabe"] == "ab 31.12.2025 ungültig setzen"


def test_changed_invalid_from_is_manual_task_and_not_in_summary():

    timestamp = timestamp_from_date(date(2026, 3, 31))
    change = _changed([FieldChange("Email", "a@x.ch", "b@x.ch"), FieldChange("InvalidFrom", timestamp, "")])
    result = ComparisonResult(changes=[change])

    assert selection_rows(selectable_changes(result))[0]["Änderungen"] == "E-Mail"
    assert manual_tasks(result)[0]["Aufgabe"] == "„ab Datum ungültig“ entfernen"


def test_changed_only_invalid_from_is_not_selectable():

    change = _changed([FieldChange("InvalidFrom", "", timestamp_from_date(date(2026, 3, 31)))])
    result = ComparisonResult(changes=[change])

    assert selectable_changes(result) == []
    assert manual_tasks(result)[0]["Aufgabe"] == "ab 31.03.2026 ungültig setzen"
