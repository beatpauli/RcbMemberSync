"""
assign_ids.py

Phase 1 „IDs vergeben“ über die Kommandozeile (siehe docs/import-plan.md):
ClubDesk-Id als ExternalId nach efa übertragen, Zuordnung über den Namen
(PersonMatcher des Compare-Tools).

1. efa exportieren, ClubDesk exportieren oder Datei übernehmen → Laufverzeichnis
2. Namens-Matching, Zusammenfassung in der Konsole und im Laufverzeichnis
3. Freigabe durch Eingabe von „ja“
4. eine Importdatei Id|ExternalId, ein efaCLI-Import, efacli.log
5. Kontroll-Export: ist die ExternalId bei jeder Person angekommen?

Mehrdeutigkeiten werden nie eingespielt. Zusätzlich wird eine in efa schon
gesetzte ExternalId nie überschrieben: Ein wiederholter Lauf spielt nur
Personen ohne ExternalId ein, Abweichungen werden als Konflikt gemeldet.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rcbcomparetool.clubdesk import ClubDeskReader
from rcbcomparetool.efa import EfaReader
from rcbcomparetool.matcher import (
    Match,
    MatchResult,
    PersonMatcher,
    relevant_unmatched_clubdesk,
    write_import_file,
    write_unmatched_clubdesk_log,
    write_unmatched_efa_log,
)
from rcbcomparetool.person import Person
from rcbefaexport.config import Instance
from rcbefaexport.persons import ImportMode

from .apply import EFACLI_LOG_NAME, INSTANCE_LABELS, _default_client, efacli_log
from .run import CLUBDESK_NAME, EFA_AFTER_NAME, adopt_file, create_run_dir
from .runners import export_clubdesk, export_efa
from .settings import OUTPUT_DIR


IDS_IMPORT_NAME = "ids_import.csv"
SUMMARY_NAME = "ids_zusammenfassung.txt"
UNMATCHED_EFA_NAME = "ohne_treffer_efa.log"
UNMATCHED_CLUBDESK_NAME = "ohne_treffer_clubdesk.log"

# Freigabe in der Konsole
CONFIRM_WORD = "ja"


def _external_id(person: Person) -> str:
    return (person.external_id or "").strip()


def _name(person: Person) -> str:
    return f"{person.last_name}, {person.first_name}"


@dataclass(frozen=True)
class Conflict:
    match: Match
    reason: str


@dataclass
class IdPlan:
    match_result: MatchResult
    to_import: list[Match] = field(default_factory=list)     # efa ohne ExternalId
    already_set: list[Match] = field(default_factory=list)   # efa hat schon dieselbe ExternalId
    conflicts: list[Conflict] = field(default_factory=list)  # nie eingespielt


def plan_ids(efa_persons: list[Person], clubdesk_persons: list[Person]) -> IdPlan:
    """Namens-Matching und Aufteilung der Treffer: einspielen / schon gesetzt / Konflikt."""

    plan = IdPlan(match_result=PersonMatcher().match(efa_persons, clubdesk_persons))

    # ExternalId -> efa-Personen, die sie schon tragen
    assigned: dict[str, list[Person]] = {}
    for person in efa_persons:
        if _external_id(person):
            assigned.setdefault(_external_id(person), []).append(person)

    for match in plan.match_result.matches:

        efa_id = _external_id(match.efa)
        clubdesk_id = _external_id(match.clubdesk)
        others = [person for person in assigned.get(clubdesk_id, []) if person.efa_id != match.efa.efa_id]

        if not clubdesk_id:
            plan.conflicts.append(Conflict(match, "ClubDesk-Person ohne Id"))
        elif efa_id and efa_id != clubdesk_id:
            plan.conflicts.append(Conflict(match, f"efa hat schon die ExternalId {efa_id}, ClubDesk-Id ist {clubdesk_id}"))
        elif others:
            names = "; ".join(f"{_name(person)} ({person.efa_id})" for person in others)
            plan.conflicts.append(Conflict(match, f"ExternalId {clubdesk_id} ist in efa schon vergeben: {names}"))
        elif efa_id:
            plan.already_set.append(match)
        else:
            plan.to_import.append(match)

    return plan


def summary_lines(plan: IdPlan, instance: Instance, run_dir: Path) -> list[str]:

    result = plan.match_result
    unmatched_clubdesk = relevant_unmatched_clubdesk(result)

    lines = [
        f"Instanz: {INSTANCE_LABELS[instance].upper() if instance is Instance.REMOTE else INSTANCE_LABELS[instance]}",
        f"Laufverzeichnis: {run_dir}",
        "",
        f"Namenstreffer:                 {len(result.matches)}",
        f"  einzuspielen (ohne ExternalId): {len(plan.to_import)}",
        f"  ExternalId schon gesetzt:       {len(plan.already_set)}",
        f"  Konflikte (nicht eingespielt):  {len(plan.conflicts)}",
        f"Mehrdeutigkeiten (nie eingespielt): {len(result.ambiguities)}",
        f"efa ohne ClubDesk-Treffer:     {len(result.unmatched_efa)}  ({UNMATCHED_EFA_NAME})",
        f"ClubDesk ohne efa-Treffer:     {len(unmatched_clubdesk)}  ({UNMATCHED_CLUBDESK_NAME})",
    ]

    if plan.to_import:
        lines += ["", "Einzuspielen:"]
        lines += [
            f"  {_name(match.efa)}: ExternalId {_external_id(match.clubdesk)} (efa-Id {match.efa.efa_id})"
            for match in plan.to_import
        ]

    if plan.conflicts:
        lines += ["", "Konflikte (von Hand klären):"]
        lines += [f"  {_name(conflict.match.efa)}: {conflict.reason}" for conflict in plan.conflicts]

    if result.ambiguities:
        lines += ["", "Mehrdeutigkeiten (von Hand klären):"]
        lines += [
            f"  {ambiguity.key[0]}, {ambiguity.key[1]} ({ambiguity.reason}): "
            f"efa={len(ambiguity.efa)}, ClubDesk={len(ambiguity.clubdesk)}"
            for ambiguity in result.ambiguities
        ]

    return lines


def check_ids(plan: IdPlan, efa_persons: list[Person]) -> list[Match]:
    """Eingespielte Personen, deren ExternalId im Kontroll-Export nicht stimmt."""

    by_id = {person.efa_id: person for person in efa_persons}
    return [
        match
        for match in plan.to_import
        if match.efa.efa_id not in by_id or _external_id(by_id[match.efa.efa_id]) != _external_id(match.clubdesk)
    ]


def assign_ids(
    instance: Instance,
    clubdesk_file: Path | None = None,
    *,
    confirm: Callable[[str], str] = input,
    out: Callable[[str], None] = print,
    efa_exporter: Callable[..., Path] = export_efa,
    clubdesk_exporter: Callable[[Path], Path] = export_clubdesk,
    client_factory: Callable[[Instance], AbstractContextManager[Any]] = _default_client,
    base_dir: Path = OUTPUT_DIR,
) -> int:
    """
    Ganzer Ablauf von Phase 1; Rückgabe ist der Exit-Code (0 = ok).

    Eingespielt wird nur nach Eingabe von „ja“ – ausgelöst ausschliesslich
    vom Benutzer.
    """

    run_dir = create_run_dir(base_dir, instance)
    out(f"Laufverzeichnis: {run_dir}")

    out(f"efa-Export ({INSTANCE_LABELS[instance]}) …")
    efa_file = efa_exporter(instance, run_dir)

    if clubdesk_file is None:
        out("ClubDesk-Export …")
        clubdesk_file = clubdesk_exporter(run_dir)
    else:
        clubdesk_file = adopt_file(clubdesk_file, run_dir, CLUBDESK_NAME)

    plan = plan_ids(EfaReader().read(efa_file), ClubDeskReader().read(clubdesk_file))

    import_file = run_dir / "import" / IDS_IMPORT_NAME
    write_import_file(MatchResult(matches=plan.to_import), import_file)
    write_unmatched_efa_log(plan.match_result, run_dir / UNMATCHED_EFA_NAME)
    write_unmatched_clubdesk_log(plan.match_result, run_dir / UNMATCHED_CLUBDESK_NAME)

    lines = summary_lines(plan, instance, run_dir)
    (run_dir / SUMMARY_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")
    out("")
    for line in lines:
        out(line)
    out("")

    if not plan.to_import:
        out("Keine Person ohne ExternalId – nichts einzuspielen.")
        return 0

    out(f"Importdatei: {import_file}")
    answer = confirm(
        f"{len(plan.to_import)} ExternalIds in efa ({INSTANCE_LABELS[instance]}) einspielen? "
        f"Zur Freigabe „{CONFIRM_WORD}“ eingeben: "
    )
    if answer.strip() != CONFIRM_WORD:
        out("Abgebrochen, nichts eingespielt.")
        return 1

    header = [
        f"IDs vergeben (Phase 1), Instanz: {INSTANCE_LABELS[instance]}",
        f"efa-Datei: {efa_file}",
        f"ClubDesk-Datei: {clubdesk_file}",
        f"Einzuspielen: {len(plan.to_import)} Personen",
    ]

    with client_factory(instance) as efa, efacli_log(run_dir / EFACLI_LOG_NAME, header, efa) as write:
        try:
            records = efa.persons.import_file(import_file, ImportMode.UPDATE)
        except Exception as e:
            write(f"FEHLER  {import_file.name}: {type(e).__name__}: {e}")
            raise
        status = "ok     " if records == len(plan.to_import) else "FEHLER "
        write(f"{status} {import_file.name} ({ImportMode.UPDATE}): {records} von {len(plan.to_import)} Datensätzen importiert")

    out(f"efaCLI: {records} von {len(plan.to_import)} Datensätzen importiert (Protokoll: {EFACLI_LOG_NAME})")

    out("Kontroll-Export …")
    missing = check_ids(plan, EfaReader().read(efa_exporter(instance, run_dir, EFA_AFTER_NAME)))

    if missing:
        out(f"ExternalId NICHT angekommen bei {len(missing)} Personen:")
        for match in missing:
            out(f"  {_name(match.efa)}: erwartet {_external_id(match.clubdesk)} (efa-Id {match.efa.efa_id})")
        return 1

    out(f"Kontrolle ok: ExternalId bei allen {len(plan.to_import)} Personen angekommen.")
    return 0
