from rcbcomparetool.comparator import ChangeType, FieldChange, PersonChange
from rcbefaexport.persons import ImportMode

from rcbmembersync.import_files import (
    NEW_PERSON_HEADER,
    import_file_name,
    leavers,
    write_import_files,
)
from rcbmembersync.runners import compare_files
from rcbmembersync.settings import DEMO_DIR


def _demo_result():
    return compare_files(DEMO_DIR / "efa.csv", DEMO_DIR / "clubdesk.csv").result


def _change(change_type=ChangeType.CHANGED, last_name="Muster", first_name="Max", field_changes=()):
    return PersonChange(
        change_type=change_type,
        efa_id="e-1",
        external_id="1001",
        last_name=last_name,
        first_name=first_name,
        efa_record={},
        field_changes=list(field_changes),
    )


def _read(path):
    return path.read_bytes().decode("utf-8")


def test_import_file_name_removes_spaces_and_keeps_umlauts():

    change = _change(last_name="von Allmen", first_name="Jürg Peter")

    assert import_file_name(change) == "1001_vonAllmen_JürgPeter.csv"


def test_import_file_name_removes_characters_invalid_on_windows():

    assert import_file_name(_change(last_name='A/B:C"D')) == "1001_ABCD_Max.csv"


def test_changed_person_file_contains_id_and_changed_attributes(tmp_path):

    [muster] = [c for c in _demo_result().changes if c.last_name == "Muster"]

    [file] = write_import_files([muster], tmp_path)

    assert file.path == tmp_path / "import" / "1001_Muster_Max.csv"
    assert file.mode is ImportMode.UPDATE
    assert _read(file.path) == "Id|Email\r\ne-1001|m.muster@x.ch\r\n"


def test_changed_person_with_several_attributes(tmp_path):

    [probe] = [c for c in _demo_result().changes if c.last_name == "Probe"]

    [file] = write_import_files([probe], tmp_path)

    assert _read(file.path) == (
        "Id|NameAffix|Email\r\n"
        "e-1003|B|p.probe@x.ch\r\n"
    )


def test_new_person_file_contains_all_columns_except_invalid_from(tmp_path):

    [new] = [c for c in _demo_result().changes if c.change_type is ChangeType.NEW]

    [file] = write_import_files([new], tmp_path)
    header, values = _read(file.path).splitlines()

    assert file.path.name == "1004_Neu_Laura.csv"
    assert file.mode is ImportMode.ADDUPDATE
    assert header.split("|") == list(NEW_PERSON_HEADER)
    assert "InvalidFrom" not in header
    assert values.split("|")[0] == new.efa_id   # vom Comparator erzeugte Id
    assert "Laura" in values and "laura.neu@x.ch" in values


def test_left_persons_get_no_file_but_are_listed(tmp_path):

    result = _demo_result()

    files = write_import_files(result.changes, tmp_path)

    assert {f.path.name for f in files} == {"1001_Muster_Max.csv", "1003_Probe_Peter.csv", "1004_Neu_Laura.csv"}
    assert {c.last_name for c in leavers(result)} == {"Alt", "Austritt"}


def test_changed_person_with_only_invalid_from_gets_no_file(tmp_path):

    change = _change(field_changes=[FieldChange("InvalidFrom", "", "1767222000000")])

    assert write_import_files([change], tmp_path) == []


def test_file_is_utf8_without_bom(tmp_path):

    change = _change(last_name="Müller", field_changes=[FieldChange("LastName", "Muller", "Müller")])

    [file] = write_import_files([change], tmp_path)

    assert not file.path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert _read(file.path) == "Id|LastName\r\ne-1|Müller\r\n"
