"""
Kommandozeile von RcbMemberSync.

    python -m rcbmembersync assign-ids [--instance local] [--clubdesk-file PFAD]
"""

import argparse
import sys
from pathlib import Path

from rcbefaexport.config import Instance

from .assign_ids import assign_ids


def main(argv: list[str] | None = None) -> int:

    parser = argparse.ArgumentParser(prog="python -m rcbmembersync")
    commands = parser.add_subparsers(dest="command", required=True)

    ids = commands.add_parser(
        "assign-ids",
        help="Phase 1: ClubDesk-Id als ExternalId nach efa übertragen (Zuordnung über den Namen).",
    )
    ids.add_argument(
        "--instance",
        type=Instance,
        choices=list(Instance),
        default=Instance.REMOTE,
        help="efa-Instanz: remote = produktiv (Standard, über VPN), local = lokale Testinstanz.",
    )
    ids.add_argument(
        "--clubdesk-file",
        type=Path,
        default=None,
        help="ClubDesk-Export verwenden statt neu zu exportieren (wird ins Laufverzeichnis kopiert).",
    )

    args = parser.parse_args(argv)

    try:
        return assign_ids(args.instance, args.clubdesk_file)
    except KeyboardInterrupt:
        print("\nAbgebrochen.")
        return 1
    except Exception as e:
        print(f"FEHLER: {type(e).__name__}: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
