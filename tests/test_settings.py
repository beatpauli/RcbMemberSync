from rcbmembersync.settings import LIBRARIES, check_environment, project_dir


def test_project_dir_points_to_sibling_project():

    directory = project_dir("rcbcomparetool")

    assert (directory / "pyproject.toml").is_file()
    assert directory.name == "RcbCompareTool"


def test_check_environment_reports_all_libraries():

    names = {check.name for check in check_environment()}

    for name, needs_env in LIBRARIES.values():
        assert name in names
        assert (f"{name} .env" in names) == needs_env
