import shutil

import pytest

from rcbcomparetool.comparator import ChangeType
from rcbefaexport.config import Instance
from rcbefaexport.persons import ImportMode

from rcbmembersync.apply import EFACLI_LOG_NAME, already_applied, apply_changes, confirmed
from rcbmembersync.runners import compare_files
from rcbmembersync.settings import DEMO_DIR


class FakePersons:
    """Ersatz für rcbefaexport Persons – ruft nie efaCLI auf."""

    def __init__(self, results=None):
        self.results = results or {}   # Dateiname -> Anzahl oder Exception
        self.calls = []

    def import_file(self, filename, mode):
        self.calls.append((filename.name, mode))
        result = self.results.get(filename.name, 1)
        if isinstance(result, Exception):
            raise result
        return result


class FakeClient:

    def __init__(self, persons, fail_on_enter=None):
        self.persons = persons
        self.fail_on_enter = fail_on_enter
        self.instances = []

    def __call__(self, instance):
        self.instances.append(instance)
        return self

    def __enter__(self):
        if self.fail_on_enter:
            raise self.fail_on_enter
        return self

    def __exit__(self, *args):
        return False


@pytest.fixture
def inputs(tmp_path):
    # Kopie der Demodaten: Demodaten selbst werden nie eingespielt
    source = tmp_path / "quelle"
    source.mkdir()
    efa_file = shutil.copy(DEMO_DIR / "efa.csv", source / "efa.csv")
    clubdesk_file = shutil.copy(DEMO_DIR / "clubdesk.csv", source / "clubdesk.csv")
    data = compare_files(efa_file, clubdesk_file)
    run_dir = tmp_path / "lauf"
    run_dir.mkdir()
    return run_dir, efa_file, clubdesk_file, data


def _importable(data):
    return [c for c in data.result.changes if c.change_type in (ChangeType.NEW, ChangeType.CHANGED)]


def test_imports_each_person_once_with_its_mode(inputs):

    run_dir, efa_file, clubdesk_file, data = inputs
    client = FakeClient(FakePersons())

    result = apply_changes(Instance.LOCAL, run_dir, efa_file, clubdesk_file, data.result, _importable(data), client)

    assert client.instances == [Instance.LOCAL]
    assert sorted(client.persons.calls) == [
        ("1001_Muster_Max.csv", ImportMode.UPDATE),
        ("1003_Probe_Peter.csv", ImportMode.UPDATE),
        ("1004_Neu_Laura.csv", ImportMode.ADDUPDATE),
    ]
    assert result.failed == []
    assert {p.name for p in run_dir.iterdir()} == {
        "efa_vorher.csv", "clubdesk.csv", "vergleich.csv", "import", EFACLI_LOG_NAME,
    }


def test_failures_do_not_stop_the_others_and_are_logged(inputs):

    run_dir, efa_file, clubdesk_file, data = inputs
    persons = FakePersons({
        "1001_Muster_Max.csv": 0,
        "1003_Probe_Peter.csv": RuntimeError("efaCLI hat keine Importmeldung ausgegeben"),
    })

    result = apply_changes(
        Instance.LOCAL, run_dir, efa_file, clubdesk_file, data.result, _importable(data), FakeClient(persons)
    )

    assert len(persons.calls) == 3
    assert sorted(o.file.path.name for o in result.failed) == ["1001_Muster_Max.csv", "1003_Probe_Peter.csv"]

    log = (run_dir / EFACLI_LOG_NAME).read_text(encoding="utf-8")
    assert "Instanz: lokale Testinstanz" in log
    assert "FEHLER  import -impmode=update 1001_Muster_Max.csv: 0 Datensätze importiert" in log
    assert "RuntimeError: efaCLI hat keine Importmeldung ausgegeben" in log
    assert "ok      import -impmode=addupdate 1004_Neu_Laura.csv" in log
    assert "Ende: 1 ok, 2 fehlgeschlagen" in log


def test_run_is_applied_only_once(inputs):

    run_dir, efa_file, clubdesk_file, data = inputs
    persons = FakePersons()
    apply_changes(Instance.LOCAL, run_dir, efa_file, clubdesk_file, data.result, _importable(data), FakeClient(persons))

    assert already_applied(run_dir)
    with pytest.raises(RuntimeError, match="bereits eingespielt"):
        apply_changes(Instance.LOCAL, run_dir, efa_file, clubdesk_file, data.result, _importable(data), FakeClient(persons))
    assert len(persons.calls) == 3


def test_failed_connection_leaves_no_log_so_run_can_be_repeated(inputs):

    run_dir, efa_file, clubdesk_file, data = inputs
    client = FakeClient(FakePersons(), fail_on_enter=ConnectionError("VPN nicht erreichbar"))

    with pytest.raises(ConnectionError):
        apply_changes(Instance.REMOTE, run_dir, efa_file, clubdesk_file, data.result, _importable(data), client)

    assert not already_applied(run_dir)
    assert client.persons.calls == []


def test_demo_data_is_never_applied(tmp_path):

    data = compare_files(DEMO_DIR / "efa.csv", DEMO_DIR / "clubdesk.csv")
    client = FakeClient(FakePersons())

    with pytest.raises(RuntimeError, match="Demodaten"):
        apply_changes(
            Instance.LOCAL, tmp_path, DEMO_DIR / "efa.csv", DEMO_DIR / "clubdesk.csv",
            data.result, _importable(data), client,
        )

    assert client.instances == []
    assert list(tmp_path.iterdir()) == []


def test_nothing_selected_opens_no_session(inputs):

    run_dir, efa_file, clubdesk_file, data = inputs
    client = FakeClient(FakePersons())

    result = apply_changes(Instance.LOCAL, run_dir, efa_file, clubdesk_file, data.result, [], client)

    assert result.outcomes == []
    assert client.instances == []
    assert not already_applied(run_dir)


def test_confirmation():

    assert not confirmed(Instance.LOCAL, False, "")
    assert confirmed(Instance.LOCAL, True, "")
    assert not confirmed(Instance.REMOTE, True, "")
    assert not confirmed(Instance.REMOTE, True, "Produktiv")
    assert not confirmed(Instance.REMOTE, False, "produktiv")
    assert confirmed(Instance.REMOTE, True, " produktiv ")
