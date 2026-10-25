from rcbmembersync.comparison_table import SOURCE_CLUBDESK, SOURCE_EFA, build_table
from rcbmembersync.runners import compare_files
from rcbmembersync.settings import DEMO_DIR


def _demo_table():
    return build_table(compare_files(DEMO_DIR / "efa.csv", DEMO_DIR / "clubdesk.csv"))


def _rows_of(table, last_name):
    return [
        (source, row, changed)
        for row, source, changed in zip(table.rows, table.sources, table.changed_columns)
        if row["Nachname"] == last_name
    ]


def test_changed_person_has_efa_and_clubdesk_row_with_marked_difference():

    rows = _rows_of(_demo_table(), "Muster")

    assert [source for source, _, _ in rows] == [SOURCE_EFA, SOURCE_CLUBDESK]
    assert rows[0][1]["E-Mail"] == "max.muster@x.ch"
    assert rows[1][1]["E-Mail"] == "m.muster@x.ch"
    assert rows[0][2] == rows[1][2] == {"E-Mail"}


def test_unchanged_person_is_not_shown():

    assert _rows_of(_demo_table(), "Beispiel") == []


def test_new_person_has_only_clubdesk_row():

    rows = _rows_of(_demo_table(), "Neu")

    assert [source for source, _, _ in rows] == [SOURCE_CLUBDESK]
    assert rows[0][1]["Fall"] == "Neu"


def test_efa_only_person_has_only_efa_row():

    rows = _rows_of(_demo_table(), "Alt")

    assert [source for source, _, _ in rows] == [SOURCE_EFA]
    assert rows[0][1]["Fall"] == "Ausgetreten"
    assert rows[0][2] == {"Ungültig ab"}


def test_left_person_shows_invalid_from_date():

    rows = _rows_of(_demo_table(), "Austritt")

    assert [source for source, _, _ in rows] == [SOURCE_EFA, SOURCE_CLUBDESK]
    assert rows[0][1]["Ungültig ab"] == ""
    assert rows[1][1]["Ungültig ab"] == "31.12.2025"
