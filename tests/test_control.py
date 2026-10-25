import shutil

import pytest

from rcbcomparetool.comparator import ChangeType
from rcbefaexport.config import Instance

from rcbmembersync.apply import apply_changes
from rcbmembersync.control import run_control
from rcbmembersync.run import COMPARISON_AFTER_NAME, EFA_AFTER_NAME, EFA_BEFORE_NAME
from rcbmembersync.runners import compare_files
from rcbmembersync.settings import DEMO_DIR

from test_apply import FakeClient, FakePersons


@pytest.fixture
def applied(tmp_path):
    # Kopie der Demodaten, eingespielt mit dem Ersatz-Client (nie efaCLI)
    source = tmp_path / "quelle"
    source.mkdir()
    efa_file = shutil.copy(DEMO_DIR / "efa.csv", source / "efa.csv")
    clubdesk_file = shutil.copy(DEMO_DIR / "clubdesk.csv", source / "clubdesk.csv")
    data = compare_files(efa_file, clubdesk_file)
    run_dir = tmp_path / "lauf"
    run_dir.mkdir()
    selected = [c for c in data.result.changes if c.change_type in (ChangeType.NEW, ChangeType.CHANGED)]
    apply_result = apply_changes(
        Instance.LOCAL, run_dir, efa_file, clubdesk_file, data.result, selected, FakeClient(FakePersons())
    )
    return apply_result


def _exporter(replacements):
    """Ersatz für den efa-Export: efa_vorher.csv mit ersetzten Werten."""

    calls = []

    def export(instance, run_dir, name):
        calls.append((instance, name))
        content = (run_dir / EFA_BEFORE_NAME).read_bytes()
        for old, new in replacements.items():
            content = content.replace(old.encode(), new.encode())
        (run_dir / name).write_bytes(content)
        return run_dir / name

    export.calls = calls
    return export


def _checks(result):
    return {check.outcome.file.change.last_name: check for check in result.check.checks}


def test_export_and_comparison_are_stored_in_run_dir(applied):

    apply_result = applied
    exporter = _exporter({})

    result = run_control(apply_result, exporter)

    assert exporter.calls == [(Instance.LOCAL, EFA_AFTER_NAME)]
    assert result.efa_file == apply_result.run_dir / EFA_AFTER_NAME
    assert result.comparison_file == apply_result.run_dir / COMPARISON_AFTER_NAME
    assert result.comparison_file.is_file()


def test_nothing_arrived(applied):

    apply_result = applied

    result = run_control(apply_result, _exporter({}))

    checks = _checks(result)
    assert not checks["Muster"].arrived
    assert checks["Muster"].message == "Email: in efa „max.muster@x.ch“, erwartet „m.muster@x.ch“"
    assert checks["Neu"].missing_person
    assert checks["Neu"].message == "Person fehlt in efa"
    assert len(result.check.not_arrived) == 3


def test_arrived_partly_arrived_and_unexpected(applied):

    apply_result = applied
    exporter = _exporter({
        "max.muster@x.ch": "m.muster@x.ch",    # angekommen
        "peter.probe@x.ch": "p.probe@x.ch",    # nur E-Mail angekommen, Brevet nicht
        "anna@x.ch": "anna.b@x.ch",            # inzwischen in efa geändert: unerwartet
    })

    result = run_control(apply_result, exporter)

    checks = _checks(result)
    assert checks["Muster"].arrived
    assert checks["Muster"].message == "alle Werte angekommen"
    assert [fc.attribute for fc in checks["Probe"].missing] == ["NameAffix"]
    assert [change.last_name for change in result.check.unexpected] == ["Beispiel"]
    # Austritte (von Hand) bleiben erwartungsgemäss
    assert result.check.remaining == 2
