import tomllib

import pytest
from dotenv import dotenv_values

from rcbmembersync.package_build import (
    START_SCRIPT,
    format_env_value,
    installed_constraints,
    merge_env_files,
    pyproject_text,
)


@pytest.mark.parametrize(
    "value",
    [
        "einfach",
        r"C:\Program Files (x86)\efa2\efaCLI.bat",
        "mit'apostroph",
        'mit"anführung',
        r"back\slash'und\"beides",
        "a#b $c ${d}",
        "",
    ],
)
def test_env_values_round_trip(tmp_path, value):
    env = tmp_path / ".env"
    env.write_text(f"KEY={format_env_value(value)}\n", encoding="utf-8")

    assert dotenv_values(env, interpolate=False)["KEY"] == value


def test_merge_env_files_first_file_wins(tmp_path):
    efa = tmp_path / "efa.env"
    efa.write_text("EFA_CLI=C:\\efa\\efaCLI.bat\nGEMEINSAM=efa\n", encoding="utf-8")
    clubdesk = tmp_path / "clubdesk.env"
    clubdesk.write_text("CLUBDESK_PASSWORD=g'heim\nGEMEINSAM=clubdesk\n", encoding="utf-8")
    target = tmp_path / ".env"

    keys = merge_env_files([efa, clubdesk], target)

    assert keys == ["EFA_CLI", "GEMEINSAM", "CLUBDESK_PASSWORD"]
    assert dotenv_values(target) == {
        "EFA_CLI": "C:\\efa\\efaCLI.bat",
        "GEMEINSAM": "efa",
        "CLUBDESK_PASSWORD": "g'heim",
    }


def test_merge_env_files_missing_source(tmp_path):
    with pytest.raises(FileNotFoundError, match=".env fehlt"):
        merge_env_files([tmp_path / "fehlt.env"], tmp_path / ".env")


def test_pyproject_uses_wheels_and_constraints():
    text = pyproject_text(
        {"RcbCompareTool": "RcbCompareTool-0.1.0-py3-none-any.whl"},
        ["marimo==0.25.2"],
        "3.12",
    )

    data = tomllib.loads(text)

    assert "RcbCompareTool" in data["project"]["dependencies"]
    assert data["project"]["requires-python"] == "==3.12.*"
    assert data["tool"]["uv"]["sources"]["RcbCompareTool"] == {
        "path": "wheels/RcbCompareTool-0.1.0-py3-none-any.whl"
    }
    assert data["tool"]["uv"]["constraint-dependencies"] == ["marimo==0.25.2"]


def test_constraints_without_own_projects_and_dev_tools():
    names = {pin.split("==")[0].lower() for pin in installed_constraints()}

    assert "marimo" in names
    assert "playwright" in names
    assert not names & {"rcbmembersync", "rcbcomparetool", "rcbclubdeskexport", "rcbefaexport", "pytest", "uv"}


def test_start_script_is_ascii_and_aborts_on_failed_download():
    START_SCRIPT.encode("ascii")

    assert "uv.exe sync --frozen" in START_SCRIPT
    assert "goto fehler_download" in START_SCRIPT
    assert "PLAYWRIGHT_BROWSERS_PATH" in START_SCRIPT
