"""
settings.py

Pfade und Prüfung der Umgebung (installierte Bibliotheken, .env-Dateien).
Zugangsdaten werden hier nie gelesen oder angezeigt, nur ob die Datei existiert.
"""

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# Paketname -> Anzeigename; True = Projekt braucht eine eigene .env
LIBRARIES = {
    "rcbclubdeskexport": ("RcbClubdeskExport", True),
    "rcbefaexport": ("RcbEfaExport", True),
    "rcbcomparetool": ("RcbCompareTool", False),
}


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


def check_environment() -> list[CheckResult]:
    """
    Prüft, ob die drei Bibliotheken importierbar sind und die benötigten
    .env-Dateien in den jeweiligen Projektordnern existieren.
    """

    results = []

    for package, (name, needs_env) in LIBRARIES.items():

        try:
            directory = project_dir(package)
        except ImportError as e:
            results.append(CheckResult(name, False, f"nicht installiert ({e})"))
            continue

        results.append(CheckResult(name, True, f"installiert ({directory})"))

        if needs_env:
            env_file = directory / ".env"
            results.append(
                CheckResult(
                    f"{name} .env",
                    env_file.is_file(),
                    "vorhanden" if env_file.is_file() else f"fehlt ({env_file})",
                )
            )

    return results
