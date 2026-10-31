from pathlib import Path

from rcbmembersync.settings import DEMO_DIR, LIBRARIES, check_environment, exclusion_file, project_dir


def test_project_dir_points_to_sibling_project():

    directory = project_dir("rcbcomparetool")

    assert (directory / "pyproject.toml").is_file()
    assert directory.name == "RcbCompareTool"


def test_check_environment_reports_all_libraries():

    names = {check.name for check in check_environment()}

    for name, needs_env in LIBRARIES.values():
        assert name in names
        assert (f"{name} .env" in names) == needs_env


def test_exclusion_file_is_in_compare_tool_data():
    path = exclusion_file(Path("C:/irgendwo/efa_vorher.csv"))

    assert path.name == "efa_ausschluss.csv"
    assert path.parent.name == "data"
    assert path.parent.parent == project_dir("rcbcomparetool")


def test_exclusion_file_for_demo_data_is_separate():
    assert exclusion_file(DEMO_DIR / "efa.csv") == DEMO_DIR / "efa_ausschluss.csv"


def _packaged(monkeypatch, tmp_path):
    """Paketbetrieb mit Paketordner tmp_path (ohne die echte .env zu laden)."""

    from rcbmembersync import settings

    monkeypatch.setattr(settings, "PACKAGED", True)
    monkeypatch.setattr(settings, "PACKAGE_ENV", tmp_path / ".env")
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")
    return settings


def test_packaged_paths_are_in_package_dir(monkeypatch, tmp_path):
    settings = _packaged(monkeypatch, tmp_path)

    assert settings.env_file("rcbefaexport") == tmp_path / ".env"
    assert settings.env_file("rcbclubdeskexport") == tmp_path / ".env"
    assert settings.exclusion_file(Path("C:/irgendwo/efa_vorher.csv")) == tmp_path / "data" / "efa_ausschluss.csv"
    assert settings.clubdesk_session_file() == tmp_path / "data" / "clubdesk.json"


def test_packaged_demo_data_keeps_own_exclusion_file(monkeypatch, tmp_path):
    settings = _packaged(monkeypatch, tmp_path)

    assert settings.exclusion_file(DEMO_DIR / "efa.csv") == DEMO_DIR / "efa_ausschluss.csv"


def test_development_paths_are_in_sibling_projects():
    from rcbmembersync import settings

    assert settings.env_file("rcbefaexport") == project_dir("rcbefaexport") / ".env"
    assert settings.clubdesk_session_file() == project_dir("rcbclubdeskexport") / "clubdesk.json"


def test_packaged_check_reports_one_env_and_efa(monkeypatch, tmp_path):
    settings = _packaged(monkeypatch, tmp_path)
    cli = tmp_path / "efaCLI.bat"
    cli.write_text("")
    (tmp_path / ".env").write_text(f"EFA_CLI={cli}\nEFA_REMOTE_PASSWORD=geheim\n", encoding="utf-8")

    checks = {check.name: check for check in settings.check_environment()}

    assert checks["Paket .env"].ok
    assert not any(name.endswith(" .env") and name != "Paket .env" for name in checks)
    assert checks["efaCLI"].ok
    assert "Java" in checks
    assert all("geheim" not in check.detail for check in checks.values())


def test_packaged_check_reports_missing_efa_cli(monkeypatch, tmp_path):
    settings = _packaged(monkeypatch, tmp_path)
    (tmp_path / ".env").write_text(f"EFA_CLI={tmp_path / 'fehlt.bat'}\n", encoding="utf-8")

    checks = {check.name: check for check in settings.check_environment()}

    assert not checks["efaCLI"].ok
    assert "ist efa installiert" in checks["efaCLI"].detail


def test_packaged_check_reports_missing_env(monkeypatch, tmp_path):
    settings = _packaged(monkeypatch, tmp_path)

    checks = {check.name: check for check in settings.check_environment()}

    assert not checks["Paket .env"].ok
    assert "efaCLI" not in checks
