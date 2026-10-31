"""
settings.py

Pfade und Prüfung der Umgebung (installierte Bibliotheken, .env-Dateien).
Zugangsdaten werden hier nie angezeigt, nur ob die Datei existiert.

Zwei Betriebsarten (siehe docs/verteilung-plan.md):
- Entwicklung: jedes Geschwister-Projekt hat seine eigene .env, die
  Ausschlussliste liegt bei RcbCompareTool.
- Paket: eine einzige .env im Paketordner, Ausschlussliste und
  ClubDesk-Session unter data/ im Paketordner.
"""

import shutil
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from rcbcomparetool.exclusion import EXCLUSION_FILE_NAME


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# Im Paket liegt die .env direkt im Paketordner; in der Entwicklung gibt es
# dort keine (die .env-Dateien liegen in den Geschwister-Projekten).
PACKAGE_ENV = BASE_DIR / ".env"
PACKAGED = PACKAGE_ENV.is_file()

if PACKAGED:
    # rcbefaexport.config liest die Umgebung (load_dotenv beim Import, ohne
    # override) – mit override gelten die Werte des Pakets auch dann, wenn
    # rcbefaexport zuerst importiert wurde.
    load_dotenv(PACKAGE_ENV, override=True)

CLUBDESK_SESSION_NAME = "clubdesk.json"

# Erfundene Testdaten für den Prototyp (keine echten Mitglieder)
DEMO_DIR = BASE_DIR / "tests" / "fixtures" / "demo"

# Paketname -> Anzeigename; True = Projekt braucht eine eigene .env
LIBRARIES = {
    "rcbclubdeskexport": ("RcbClubdeskExport", True),
    "rcbefaexport": ("RcbEfaExport", True),
    "rcbcomparetool": ("RcbCompareTool", False),
}


def exclusion_file(efa_file: Path) -> Path:
    """
    Ausschlussliste für efa-Gäste (siehe RcbCompareTool docs/ausschlussliste-plan.md).

    Liegt bei RcbCompareTool unter data/, im Paket unter data/ im Paketordner.
    Zu den Demo-Daten gehört eine eigene (fehlende, also leere) Liste – sonst
    wären alle echten Einträge „veraltet“.
    """

    if efa_file.resolve().parent == DEMO_DIR.resolve():
        return DEMO_DIR / EXCLUSION_FILE_NAME

    if PACKAGED:
        return DATA_DIR / EXCLUSION_FILE_NAME

    return project_dir("rcbcomparetool") / "data" / EXCLUSION_FILE_NAME


def env_file(package: str) -> Path:
    """.env mit den Zugangsdaten eines Geschwister-Projekts (im Paket: die gemeinsame)."""

    if PACKAGED:
        return PACKAGE_ENV

    return project_dir(package) / ".env"


def clubdesk_session_file() -> Path:
    """
    ClubDesk-Session. In der Entwicklung im ClubDesk-Projekt, damit sie mit
    dessen CLI geteilt wird; im Paket unter data/.
    """

    if PACKAGED:
        return DATA_DIR / CLUBDESK_SESSION_NAME

    return project_dir("rcbclubdeskexport") / CLUBDESK_SESSION_NAME


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def project_dir(package: str) -> Path:
    """
    Liefert den Projektordner eines editierbar installierten Pakets
    (Ordner oberhalb des Paketordners).
    """

    module = import_module(package)

    return Path(module.__file__).resolve().parents[1]


def _env_check(name: str, path: Path) -> CheckResult:

    return CheckResult(
        name,
        path.is_file(),
        "vorhanden" if path.is_file() else f"fehlt ({path})",
    )


def _efa_checks() -> list[CheckResult]:
    """efaCLI und Java müssen beim Benutzer installiert sein (efaCLI findet Java über PATH)."""

    path = env_file("rcbefaexport")

    if not path.is_file():
        return []

    # Nur der Pfad wird gelesen und angezeigt, keine Zugangsdaten
    cli = dotenv_values(path).get("EFA_CLI") or ""

    if not cli:
        cli_check = CheckResult("efaCLI", False, "EFA_CLI ist in der .env nicht gesetzt")
    elif Path(cli).is_file():
        cli_check = CheckResult("efaCLI", True, f"vorhanden ({cli})")
    else:
        cli_check = CheckResult("efaCLI", False, f"nicht gefunden ({cli}) – ist efa installiert?")

    java = shutil.which("java")

    java_check = CheckResult(
        "Java",
        java is not None,
        f"gefunden ({java})" if java else "nicht gefunden (PATH) – wird von efaCLI gebraucht",
    )

    return [cli_check, java_check]


def check_environment() -> list[CheckResult]:
    """
    Prüft, ob die drei Bibliotheken importierbar sind, die benötigten
    .env-Dateien existieren (im Paket: die gemeinsame) und efaCLI und Java
    gefunden werden.
    """

    results = []

    if PACKAGED:
        results.append(_env_check("Paket .env", PACKAGE_ENV))

    for package, (name, needs_env) in LIBRARIES.items():

        try:
            directory = project_dir(package)
        except ImportError as e:
            results.append(CheckResult(name, False, f"nicht installiert ({e})"))
            continue

        if PACKAGED:
            results.append(CheckResult(name, True, "installiert"))
            continue

        results.append(CheckResult(name, True, f"installiert ({directory})"))

        if needs_env:
            results.append(_env_check(f"{name} .env", directory / ".env"))

    return results + _efa_checks()
