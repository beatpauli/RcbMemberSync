from datetime import datetime

from rcbefaexport.config import Instance

from rcbmembersync.run import adopt_file, create_run_dir, store_inputs
from rcbmembersync.runners import compare_files
from rcbmembersync.settings import DEMO_DIR


NOW = datetime(2026, 10, 25, 14, 30)


def test_create_run_dir_productive(tmp_path):

    assert create_run_dir(tmp_path, Instance.REMOTE, NOW) == tmp_path / "2026-10-25_1430"
    assert (tmp_path / "2026-10-25_1430").is_dir()


def test_create_run_dir_local_is_marked(tmp_path):

    assert create_run_dir(tmp_path, Instance.LOCAL, NOW).name == "2026-10-25_1430_LOKAL"


def test_create_run_dir_same_minute_gets_counter(tmp_path):

    create_run_dir(tmp_path, Instance.REMOTE, NOW)

    assert create_run_dir(tmp_path, Instance.REMOTE, NOW).name == "2026-10-25_1430_2"


def test_adopt_file_copies_and_keeps_original(tmp_path):

    source = tmp_path / "gewählt.csv"
    source.write_text("a", encoding="utf-8")
    run_dir = create_run_dir(tmp_path, Instance.REMOTE, NOW)

    target = adopt_file(source, run_dir, "efa_vorher.csv")

    assert target == run_dir / "efa_vorher.csv"
    assert target.read_text(encoding="utf-8") == "a"
    assert source.exists()


def test_adopt_file_moves_export(tmp_path):

    source = tmp_path / "2026-10-25_persons_export.csv"
    source.write_text("a", encoding="utf-8")
    run_dir = create_run_dir(tmp_path, Instance.REMOTE, NOW)

    adopt_file(source, run_dir, "efa_vorher.csv", move=True)

    assert not source.exists()
    assert (run_dir / "efa_vorher.csv").exists()


def test_adopt_file_already_in_place_is_unchanged(tmp_path):

    run_dir = create_run_dir(tmp_path, Instance.REMOTE, NOW)
    target = run_dir / "efa_vorher.csv"
    target.write_text("a", encoding="utf-8")

    assert adopt_file(target, run_dir, "efa_vorher.csv") == target
    assert target.read_text(encoding="utf-8") == "a"


def test_store_inputs_writes_all_files(tmp_path):

    run_dir = create_run_dir(tmp_path, Instance.REMOTE, NOW)
    efa_file, clubdesk_file = DEMO_DIR / "efa.csv", DEMO_DIR / "clubdesk.csv"
    result = compare_files(efa_file, clubdesk_file).result

    store_inputs(run_dir, efa_file, clubdesk_file, result)

    assert sorted(p.name for p in run_dir.iterdir()) == ["clubdesk.csv", "efa_vorher.csv", "vergleich.csv"]
    assert (run_dir / "efa_vorher.csv").read_bytes() == efa_file.read_bytes()
    assert "Muster" in (run_dir / "vergleich.csv").read_text(encoding="utf-8")
