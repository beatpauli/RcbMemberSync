"""
package_build.py

Baut das Paket zur Weitergabe (siehe docs/verteilung-plan.md, Teil B):

    python -m rcbmembersync.package_build

Ergebnis: dist/RcbMemberSync/ und dist/RcbMemberSync_<Datum>.zip. Python,
die Fremdbibliotheken und Chromium lädt der Empfänger beim ersten Start
(RcbMemberSync.cmd, braucht Internet).

Das Paket enthält die Zugangsdaten (.env) – dist/ wird nie eingecheckt, das
ZIP nicht per E-Mail oder über öffentliche Ablagen weitergeben.
"""

import shutil
import subprocess
import sys
from datetime import date
from importlib.metadata import distributions
from pathlib import Path

from dotenv import dotenv_values

from .settings import BASE_DIR, DEMO_DIR, project_dir


PACKAGE_NAME = "RcbMemberSync"
DIST_DIR = BASE_DIR / "dist"

# Paketname -> Projektname der Geschwister-Projekte (als Wheels mitgeliefert)
SIBLINGS = {
    "rcbcomparetool": "RcbCompareTool",
    "rcbclubdeskexport": "RcbClubdeskExport",
    "rcbefaexport": "RcbEfaExport",
}

# Werden nicht ins Paket übernommen (Entwicklungswerkzeuge, eigene Projekte)
NOT_CONSTRAINED = {"rcbmembersync", "pip", "pytest", "uv", "iniconfig", "pluggy", "packaging"} | {
    name.lower() for name in SIBLINGS.values()
}

# Ohne Umlaute: die Windows-Konsole zeigt sie je nach Codepage falsch an
START_SCRIPT = r"""@echo off
setlocal
cd /d "%~dp0"

rem Alles bleibt im Paketordner: Python, Pakete, Cache, Chromium
set "UV_PYTHON_INSTALL_DIR=%~dp0python"
set "UV_CACHE_DIR=%~dp0.uv-cache"
set "UV_PYTHON_PREFERENCE=only-managed"
set "PLAYWRIGHT_BROWSERS_PATH=%~dp0browsers"

echo Einrichten bzw. pruefen (beim ersten Start einige Minuten) ...
uv.exe sync --frozen --no-dev
if errorlevel 1 goto fehler_download

rem Der ClubDesk-Export laeuft ohne Fenster (headless), die Shell reicht
if not exist "browsers\chromium_headless_shell-*" (
    echo Lade Chromium fuer den ClubDesk-Export ...
    uv.exe run --frozen --no-sync python -m playwright install --only-shell chromium
    if errorlevel 1 goto fehler_download
)

echo Starte RcbMemberSync, der Browser oeffnet sich ...
uv.exe run --frozen --no-sync marimo run app.py
goto ende

:fehler_download
echo.
echo FEHLER: Einrichten fehlgeschlagen.
echo Beim ersten Start braucht RcbMemberSync eine Internetverbindung, um
echo Python, die Programmbibliotheken und Chromium herunterzuladen.
echo Bitte Internetverbindung pruefen und erneut starten.
echo.
pause
exit /b 1

:ende
endlocal
"""

README_TEXT = """RcbMemberSync – Mitgliederabgleich ClubDesk / efa
====================================================

Voraussetzungen
- Windows
- efa mit efaCLI und Java sind installiert (Java im PATH).
  In .env muss EFA_CLI auf efaCLI.bat zeigen (z.B.
  C:\\Program Files (x86)\\efa2\\efaCLI.bat), EFA_EXPORT_PATH auf ein
  bestehendes Verzeichnis.
- Internetverbindung beim ersten Start.
- Das VPN wird bei Bedarf selbst eingerichtet.

Start
- Doppelklick auf RcbMemberSync.cmd. Beim ersten Start werden Python,
  die Programmbibliotheken und Chromium in diesen Ordner geladen.
- Der Browser öffnet sich mit der Oberfläche. Unter „Konfiguration“
  steht, ob alles gefunden wurde.
- Beenden: Fenster mit RcbMemberSync.cmd schliessen.

Ablage
- .env                     Zugangsdaten und Pfade
- data/efa_ausschluss.csv  Ausschlussliste der efa-Gäste
- output/                  ein Verzeichnis je Lauf

ACHTUNG: .env enthält Zugangsdaten zu ClubDesk, efa (produktiv) und
VPN. Diesen Ordner und das ZIP nicht per E-Mail oder über öffentliche
Ablagen weitergeben.
"""


def format_env_value(value: str) -> str:
    """Wert für eine .env-Zeile, so dass python-dotenv ihn unverändert zurückliest."""

    if "'" not in value and "\n" not in value:
        return f"'{value}'"

    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    return f'"{escaped}"'


def merge_env_files(sources: list[Path], target: Path) -> list[str]:
    """
    Fasst die .env-Dateien der Geschwister-Projekte zu einer zusammen.

    Bei gleichem Schlüssel gilt die erste Datei. Liefert die Schlüssel
    (nie die Werte, die sind Zugangsdaten).
    """

    merged: dict[str, str] = {}

    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f".env fehlt: {source}")

        # Ohne Auflösung von ${...}: beim Lesen im Paket wird wie bisher aufgelöst
        for key, value in dotenv_values(source, interpolate=False).items():
            merged.setdefault(key, value or "")

    lines = ["# Zugangsdaten und Pfade für das Paket – nicht weitergeben", ""]
    lines += [f"{key}={format_env_value(value)}" for key, value in merged.items()]

    target.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return list(merged)


def installed_constraints() -> list[str]:
    """Versionen der Fremdbibliotheken aus der Entwicklungsumgebung (so getestet)."""

    pins = {
        dist.metadata["Name"].lower(): f"{dist.metadata['Name']}=={dist.version}"
        for dist in distributions()
        if dist.metadata["Name"]
    }

    return sorted(pin for name, pin in pins.items() if name not in NOT_CONSTRAINED)


def pyproject_text(wheels: dict[str, str], constraints: list[str], python: str) -> str:
    """pyproject.toml des Pakets: RcbMemberSync plus die Geschwister als Wheels."""

    dependencies = ["marimo", "python-dotenv", *wheels]

    def toml_list(items: list[str]) -> str:
        return "[\n" + "".join(f'    "{item}",\n' for item in items) + "]"

    sources = "".join(
        f'{name} = {{ path = "wheels/{wheel}" }}\n' for name, wheel in wheels.items()
    )

    return (
        "[build-system]\n"
        'requires = ["setuptools>=69"]\n'
        'build-backend = "setuptools.build_meta"\n'
        "\n"
        "[project]\n"
        f'name = "{PACKAGE_NAME}"\n'
        'version = "0.1.0"\n'
        f'requires-python = "=={python}.*"\n'
        f"dependencies = {toml_list(dependencies)}\n"
        "\n"
        "[tool.setuptools.packages.find]\n"
        'include = ["rcbmembersync*"]\n'
        "\n"
        "[tool.uv]\n"
        f"constraint-dependencies = {toml_list(constraints)}\n"
        "\n"
        "[tool.uv.sources]\n"
        f"{sources}"
    )


def _uv() -> Path:

    uv = Path(sys.executable).parent / "uv.exe"

    if not uv.is_file():
        raise FileNotFoundError(f"uv fehlt ({uv}) – pip install -e .[dev]")

    return uv


def _run(*args, cwd: Path | None = None):

    print(">", " ".join(str(arg) for arg in args))
    subprocess.run([str(arg) for arg in args], cwd=cwd, check=True)


def copy_sources(target: Path):
    """app.py, rcbmembersync/ und die Demodaten (erfunden) in den Paketordner."""

    shutil.copy2(BASE_DIR / "app.py", target / "app.py")

    shutil.copytree(
        BASE_DIR / "rcbmembersync",
        target / "rcbmembersync",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )

    shutil.copytree(DEMO_DIR, target / DEMO_DIR.relative_to(BASE_DIR))


def build(dist_dir: Path = DIST_DIR) -> Path:
    """Baut den Paketordner und das ZIP; liefert den Pfad des ZIP."""

    uv = _uv()
    target = dist_dir / PACKAGE_NAME

    if target.exists():
        shutil.rmtree(target)

    (target / "wheels").mkdir(parents=True)
    (target / "data").mkdir()
    (target / "output").mkdir()

    wheels = {}

    for package, name in SIBLINGS.items():
        directory = project_dir(package)

        # setuptools legt im Projekt build/ an – nur entfernen, was wir angelegt haben
        had_build_dir = (directory / "build").exists()

        _run(uv, "build", "--wheel", "--out-dir", target / "wheels", directory)
        wheels[name] = next((target / "wheels").glob(f"{package}-*.whl")).name

        if not had_build_dir:
            shutil.rmtree(directory / "build", ignore_errors=True)

    copy_sources(target)
    shutil.copy2(uv, target / "uv.exe")

    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    (target / ".python-version").write_text(python + "\n", encoding="utf-8")
    (target / "pyproject.toml").write_text(
        pyproject_text(wheels, installed_constraints(), python), encoding="utf-8"
    )
    _run(uv, "lock", cwd=target)

    keys = merge_env_files(
        [project_dir("rcbefaexport") / ".env", project_dir("rcbclubdeskexport") / ".env"],
        target / ".env",
    )
    print(".env mit", len(keys), "Einträgen:", ", ".join(keys))

    exclusion = project_dir("rcbcomparetool") / "data" / "efa_ausschluss.csv"
    if exclusion.is_file():
        shutil.copy2(exclusion, target / "data" / exclusion.name)
    else:
        print("Hinweis: keine Ausschlussliste gefunden:", exclusion)

    (target / "RcbMemberSync.cmd").write_text(START_SCRIPT, encoding="ascii", newline="\r\n")
    (target / "LIESMICH.txt").write_text(README_TEXT, encoding="utf-8")

    archive = shutil.make_archive(
        str(dist_dir / f"{PACKAGE_NAME}_{date.today().isoformat()}"),
        "zip",
        root_dir=dist_dir,
        base_dir=PACKAGE_NAME,
    )

    return Path(archive)


if __name__ == "__main__":
    print("Paket:", build())
