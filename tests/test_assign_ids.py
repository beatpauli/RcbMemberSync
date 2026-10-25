import pytest

from rcbefaexport.config import Instance
from rcbefaexport.persons import ImportMode

from rcbmembersync.__main__ import main
from rcbmembersync.apply import EFACLI_LOG_NAME
from rcbmembersync.assign_ids import IDS_IMPORT_NAME, SUMMARY_NAME, assign_ids
from rcbmembersync.run import EFA_BEFORE_NAME
from rcbmembersync.settings import DEMO_DIR

from test_apply import FakeClient, FakePersons


# Demodaten: Muster ohne ExternalId (einzuspielen), Probe mit abweichender
# ExternalId (Konflikt), Beispiel/Austritt schon gesetzt
EFA_BEFORE = {
    "max.muster@x.ch|||1001|": "max.muster@x.ch||||",
    "peter.probe@x.ch|||1003|": "peter.probe@x.ch|||1009|",
}
# Kontroll-Export: ExternalId bei Muster angekommen
EFA_AFTER = {"peter.probe@x.ch|||1003|": "peter.probe@x.ch|||1009|"}


def _efa_exporter(before=EFA_BEFORE, after=EFA_AFTER):

    calls = []

    def export(instance, run_dir, name=EFA_BEFORE_NAME):
        calls.append((instance, name))
        replacements = before if name == EFA_BEFORE_NAME else after
        content = (DEMO_DIR / "efa.csv").read_bytes()
        for old, new in replacements.items():
            assert old.encode() in content
            content = content.replace(old.encode(), new.encode())
        (run_dir / name).write_bytes(content)
        return run_dir / name

    export.calls = calls
    return export


def _run(tmp_path, answer="ja", before=EFA_BEFORE, after=EFA_AFTER, records=None):

    persons = FakePersons({IDS_IMPORT_NAME: records} if records is not None else {})
    client = FakeClient(persons)
    output = []
    exporter = _efa_exporter(before, after)

    code = assign_ids(
        Instance.LOCAL,
        DEMO_DIR / "clubdesk.csv",
        confirm=lambda prompt: answer if answer is not None else pytest.fail("unerwartete Freigabe-Frage"),
        out=output.append,
        efa_exporter=exporter,
        clubdesk_exporter=lambda run_dir: pytest.fail("ClubDesk-Export statt Datei"),
        client_factory=client,
        base_dir=tmp_path,
    )
    [run_dir] = tmp_path.iterdir()
    return code, run_dir, persons, client, exporter, "\n".join(output)


def test_imports_only_persons_without_external_id(tmp_path):

    code, run_dir, persons, client, exporter, output = _run(tmp_path)

    assert code == 0
    assert persons.calls == [(IDS_IMPORT_NAME, ImportMode.UPDATE)]
    assert client.instances == [Instance.LOCAL]
    import_file = run_dir / "import" / IDS_IMPORT_NAME
    assert import_file.read_text(encoding="utf-8").splitlines() == ["Id|ExternalId", "e-1001|1001"]
    assert "Kontrolle ok" in output


def test_conflicting_external_id_is_reported_never_overwritten(tmp_path):

    code, run_dir, *_ = _run(tmp_path)

    summary = (run_dir / SUMMARY_NAME).read_text(encoding="utf-8")
    assert "Konflikte (nicht eingespielt):  1" in summary
    assert "Probe, Peter: efa hat schon die ExternalId 1009, ClubDesk-Id ist 1003" in summary
    assert "ExternalId schon gesetzt:       2" in summary


def test_log_contains_commands_and_result(tmp_path):

    _, run_dir, *_ = _run(tmp_path)

    log = (run_dir / EFACLI_LOG_NAME).read_text(encoding="utf-8")
    assert "IDs vergeben (Phase 1), Instanz: lokale Testinstanz" in log
    assert ">>> persons" in log
    assert f">>> import -impmode=update {run_dir / 'import' / IDS_IMPORT_NAME}" in log
    assert "ok      ids_import.csv (update): 1 von 1 Datensätzen importiert" in log


def test_nothing_is_imported_without_ja(tmp_path):

    code, run_dir, persons, client, exporter, output = _run(tmp_path, answer="Ja bitte")

    assert code == 1
    assert client.instances == []
    assert persons.calls == []
    assert not (run_dir / EFACLI_LOG_NAME).exists()
    assert "nichts eingespielt" in output


def test_missing_external_id_after_import_is_reported(tmp_path):

    code, _, _, _, exporter, output = _run(tmp_path, after=EFA_BEFORE, records=0)

    assert code == 1
    assert exporter.calls == [(Instance.LOCAL, EFA_BEFORE_NAME), (Instance.LOCAL, "efa_nachher.csv")]
    assert "0 von 1 Datensätzen importiert" in output
    assert "NICHT angekommen bei 1 Personen" in output
    assert "Muster, Max: erwartet 1001" in output


def test_nothing_to_import_opens_no_session(tmp_path):

    # Stand nach einem ersten Lauf: Muster hat die ExternalId schon
    code, _, persons, client, _, output = _run(tmp_path, answer=None, before=EFA_AFTER)

    assert code == 0
    assert client.instances == []
    assert persons.calls == []
    assert "nichts einzuspielen" in output


def test_command_line_help(capsys):

    with pytest.raises(SystemExit) as exit_info:
        main(["assign-ids", "--help"])

    assert exit_info.value.code == 0
    assert "--clubdesk-file" in capsys.readouterr().out
