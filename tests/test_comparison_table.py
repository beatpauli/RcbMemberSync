from datetime import date

from rcbcomparetool.comparator import ChangeType, ComparisonResult, FieldChange, PersonChange
from rcbcomparetool.mapper import timestamp_from_date

from rcbmembersync.comparison_table import SOURCE_CLUBDESK, SOURCE_EFA, build_table
from rcbmembersync.runners import ComparisonData, compare_files
from rcbmembersync.settings import DEMO_DIR


def _demo_table():
    return build_table(compare_files(DEMO_DIR / "efa.csv", DEMO_DIR / "clubdesk.csv"))


def _row(table, last_name):
    [row] = [row for row in table.rows if row.change.last_name == last_name]
    return row


def _changed(field_changes):
    change = PersonChange(
        change_type=ChangeType.CHANGED,
        efa_id="e-1",
        external_id="1001",
        last_name="Muster",
        first_name="Max",
        efa_record={},
        field_changes=field_changes,
    )
    return build_table(ComparisonData(ComparisonResult(changes=[change]), {"e-1": {}}, {"1001"})).rows[0]


def test_one_row_per_person():

    table = _demo_table()

    assert sorted(row.change.last_name for row in table.rows) == ["Alt", "Austritt", "Muster", "Neu", "Probe"]


def test_rows_sorted_changed_new_left():

    def _change(change_type, external_id):
        return PersonChange(change_type, f"e-{external_id}", external_id, "X", "Y", {}, [])

    # Comparator-Reihenfolge: nach ExternalId, Fälle gemischt
    changes = [
        _change(ChangeType.LEFT, "1"),
        _change(ChangeType.NEW, "2"),
        _change(ChangeType.CHANGED, "3"),
        _change(ChangeType.NEW, "4"),
        _change(ChangeType.CHANGED, "5"),
        _change(ChangeType.LEFT, "6"),
    ]
    efa_rows = {f"e-{c.external_id}": {} for c in changes}

    table = build_table(ComparisonData(ComparisonResult(changes=changes), efa_rows, set()))

    assert [(row.change.change_type, row.change.external_id) for row in table.rows] == [
        (ChangeType.CHANGED, "3"),
        (ChangeType.CHANGED, "5"),
        (ChangeType.NEW, "2"),
        (ChangeType.NEW, "4"),
        (ChangeType.LEFT, "1"),
        (ChangeType.LEFT, "6"),
    ]


def test_changed_person_shows_both_values_of_difference():

    row = _row(_demo_table(), "Muster")

    assert row.sources == (SOURCE_EFA, SOURCE_CLUBDESK)
    assert row.differences == {"E-Mail": ("max.muster@x.ch", "m.muster@x.ch")}
    assert row.values["Nachname"] == "Muster"
    assert "E-Mail" not in row.values
    assert row.transfer == "Import"
    assert row.importable


def test_several_differences():

    row = _row(_demo_table(), "Probe")

    assert set(row.differences) == {"Brevet", "E-Mail"}


def test_unchanged_person_is_not_shown():

    assert [row for row in _demo_table().rows if row.change.last_name == "Beispiel"] == []


def test_new_person_has_only_clubdesk_values():

    row = _row(_demo_table(), "Neu")

    assert row.sources == (SOURCE_CLUBDESK,)
    assert row.differences == {}
    assert row.values["E-Mail"] == "laura.neu@x.ch"
    assert row.importable


def test_left_person_is_manual_task_and_not_importable():

    row = _row(_demo_table(), "Austritt")

    assert row.sources == (SOURCE_EFA, SOURCE_CLUBDESK)
    assert row.differences == {"Ungültig ab": ("", "31.12.2025")}
    assert row.transfer == "von Hand: ab 31.12.2025 ungültig setzen"
    assert not row.importable


def test_efa_only_person_has_only_efa_source():

    row = _row(_demo_table(), "Alt")

    assert row.sources == (SOURCE_EFA,)
    assert set(row.differences) == {"Ungültig ab"}
    assert not row.importable


def test_changed_invalid_from_is_import_and_manual_task():

    timestamp = timestamp_from_date(date(2026, 3, 31))

    row = _changed([FieldChange("Email", "a@x.ch", "b@x.ch"), FieldChange("InvalidFrom", timestamp, "")])

    assert row.transfer == "Import; von Hand: „ab Datum ungültig“ entfernen"
    assert row.importable


def test_changed_only_invalid_from_is_not_importable():

    row = _changed([FieldChange("InvalidFrom", "", timestamp_from_date(date(2026, 3, 31)))])

    assert row.transfer == "von Hand: ab 31.03.2026 ungültig setzen"
    assert not row.importable
