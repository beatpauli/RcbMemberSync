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
