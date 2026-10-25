import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", app_title="RCB-Mitglieder Abgleich")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo

    from rcbefaexport.config import Instance

    from rcbmembersync.apply import already_applied, apply_changes
    from rcbmembersync.comparison_table import build_table
    from rcbmembersync.run import create_run_dir
    from rcbmembersync.runners import compare_files, export_clubdesk, export_efa
    from rcbmembersync.settings import BASE_DIR, DEMO_DIR, OUTPUT_DIR, check_environment
    return (
        BASE_DIR,
        DEMO_DIR,
        Instance,
        OUTPUT_DIR,
        Path,
        already_applied,
        apply_changes,
        build_table,
        check_environment,
        compare_files,
        create_run_dir,
        export_clubdesk,
        export_efa,
        mo,
    )


@app.cell
def _(mo):
    # Dateipfade und Meldungen der beiden Seiten; gesetzt von Datei-Auswahl,
    # Textfeld, Export-Button oder Demodaten
    get_efa_path, set_efa_path = mo.state("")
    get_clubdesk_path, set_clubdesk_path = mo.state("")
    get_efa_message, set_efa_message = mo.state(None)
    get_clubdesk_message, set_clubdesk_message = mo.state(None)

    # Laufverzeichnis output/<Zeitstempel>[_LOKAL]; beim ersten Export angelegt.
    # Massgebend ist run_holder (kein State, löst keine Zellen aus); der
    # State dient nur der Anzeige. Würden die Export-Zellen vom State
    # abhängen, liefe ein Export nach dem Anlegen des Verzeichnisses ein
    # zweites Mal.
    run_holder = {"dir": None}
    get_run_dir, set_run_dir = mo.state(None)

    # Ergebnis des Einspielens (ApplyResult oder Fehlermeldung); nur die
    # Anzeige- und Freigabe-Zellen lesen es, nie die Einspiel-Zelle selbst
    get_apply_result, set_apply_result = mo.state(None)
    return (
        get_apply_result,
        get_clubdesk_message,
        get_clubdesk_path,
        get_efa_message,
        get_efa_path,
        get_run_dir,
        run_holder,
        set_apply_result,
        set_clubdesk_message,
        set_clubdesk_path,
        set_efa_message,
        set_efa_path,
        set_run_dir,
    )


@app.cell
def _(Instance, check_environment, mo):
    checks = check_environment()
    all_ok = all(check.ok for check in checks)

    demo_button = mo.ui.run_button(label="Demodaten laden", kind="neutral")

    instance_select = mo.ui.radio(
        options={
            "produktiv": Instance.REMOTE,
            "lokale Testinstanz (ohne VPN)": Instance.LOCAL,
        },
        value="produktiv",
        inline=True,
        label="**efa-Instanz**",
    )

    mo.vstack(
        [
            mo.md("# RCB-Mitglieder Abgleich"),
            mo.accordion(
                {
                    f"{'✅' if all_ok else '❌'} Konfiguration": mo.md(
                        "\n".join(
                            f"- {'✅' if check.ok else '❌'} **{check.name}**: {check.detail}"
                            for check in checks
                        )
                    ),
                }
            ),
            instance_select,
            mo.hstack(
                [demo_button, mo.md("_Erfundene Testdaten statt echter Exporte (Prototyp)_")],
                justify="start",
                align="center",
            ),
        ]
    )
    return demo_button, instance_select


@app.cell
def _(instance_select, run_holder, set_efa_message, set_efa_path, set_run_dir):
    # Neue Instanz → neuer Lauf. Die efa-Datei gehört zur alten Instanz und
    # wird verworfen; die ClubDesk-Datei bleibt gültig.
    instance = instance_select.value

    run_holder["dir"] = None
    set_run_dir(None)
    set_efa_path("")
    set_efa_message(None)
    return (instance,)


@app.cell
def _(get_run_dir, instance, mo):
    _run_dir = get_run_dir()

    mo.md(
        f"Laufverzeichnis: `{_run_dir}`"
        if _run_dir
        else "Laufverzeichnis: _wird beim ersten Export angelegt_"
        + (" _(markiert mit `_LOKAL`)_" if instance.value == "local" else "")
    )
    return


@app.cell
def _(DEMO_DIR, demo_button, mo, set_clubdesk_path, set_efa_path):
    mo.stop(not demo_button.value)

    set_efa_path(str(DEMO_DIR / "efa.csv"))
    set_clubdesk_path(str(DEMO_DIR / "clubdesk.csv"))
    return


@app.cell
def _(BASE_DIR, mo, set_clubdesk_path, set_efa_path):
    efa_export_button = mo.ui.run_button(label="Export", kind="success")
    clubdesk_export_button = mo.ui.run_button(label="Export", kind="success")


    def _browser(setter):
        return mo.ui.file_browser(
            initial_path=BASE_DIR.parent,
            filetypes=[".csv"],
            multiple=False,
            restrict_navigation=False,
            on_change=lambda files: setter(str(files[0].path)) if files else None,
        )


    efa_browser = _browser(set_efa_path)
    clubdesk_browser = _browser(set_clubdesk_path)
    return (
        clubdesk_browser,
        clubdesk_export_button,
        efa_browser,
        efa_export_button,
    )


@app.cell
def _(get_clubdesk_path, get_efa_path, mo, set_clubdesk_path, set_efa_path):
    efa_path_field = mo.ui.text(
        value=get_efa_path(),
        placeholder="pfad/datei.csv",
        full_width=True,
        on_change=set_efa_path,
    )
    clubdesk_path_field = mo.ui.text(
        value=get_clubdesk_path(),
        placeholder="pfad/datei.csv",
        full_width=True,
        on_change=set_clubdesk_path,
    )
    return clubdesk_path_field, efa_path_field


@app.cell
def _(OUTPUT_DIR, already_applied, create_run_dir, instance, run_holder, set_run_dir):
    def ensure_run_dir(new_if_applied=False):
        """
        Laufverzeichnis des aktuellen Laufs, beim ersten Aufruf angelegt.

        new_if_applied: Exporte nach dem Einspielen beginnen einen neuen
        Lauf. Die Einspiel-Zelle nutzt das nie – ein zweiter Durchlauf mit
        noch gedrücktem Button würde sonst in einem neuen Lauf erneut
        einspielen.
        """
        if run_holder["dir"] is None or (new_if_applied and already_applied(run_holder["dir"])):
            run_holder["dir"] = create_run_dir(OUTPUT_DIR, instance)
            set_run_dir(run_holder["dir"])   # nur für die Anzeige
        return run_holder["dir"]
    return (ensure_run_dir,)


@app.cell
def _(
    efa_export_button,
    ensure_run_dir,
    export_efa,
    instance,
    mo,
    set_efa_message,
    set_efa_path,
):
    mo.stop(not efa_export_button.value)

    _title = "efa-Export läuft (VPN, efaCLI) …" if instance.value == "remote" else "efa-Export läuft (lokale Testinstanz) …"
    try:
        with mo.status.spinner(title=_title):
            _file = export_efa(instance, ensure_run_dir(new_if_applied=True))
        set_efa_path(str(_file))
        set_efa_message(("success", f"Export erstellt: {_file.name}"))
    except Exception as _e:
        set_efa_message(("danger", f"Export fehlgeschlagen: {_e}"))
    return


@app.cell
def _(
    clubdesk_export_button,
    ensure_run_dir,
    export_clubdesk,
    mo,
    set_clubdesk_message,
    set_clubdesk_path,
):
    mo.stop(not clubdesk_export_button.value)

    try:
        with mo.status.spinner(title="ClubDesk-Export läuft …"):
            _file = export_clubdesk(ensure_run_dir(new_if_applied=True))
        set_clubdesk_path(str(_file))
        set_clubdesk_message(("success", f"Export erstellt: {_file.name}"))
    except Exception as _e:
        set_clubdesk_message(("danger", f"Export fehlgeschlagen: {_e}"))
    return


@app.cell
def _(
    clubdesk_browser,
    clubdesk_export_button,
    clubdesk_path_field,
    efa_browser,
    efa_export_button,
    efa_path_field,
    get_clubdesk_message,
    get_efa_message,
    mo,
):
    def _panel(title, button, path_field, browser, message):
        items = [
            mo.md(f"### {title}"),
            button,
            path_field,
            mo.accordion({"Datei wählen …": browser}),
        ]
        if message is not None:
            kind, text = message
            items.append(mo.callout(text, kind=kind))
        return mo.vstack(items)


    mo.hstack(
        [
            _panel("efa-Daten", efa_export_button, efa_path_field, efa_browser, get_efa_message()),
            _panel("ClubDesk-Daten", clubdesk_export_button, clubdesk_path_field, clubdesk_browser, get_clubdesk_message()),
        ],
        widths="equal",
        gap=2,
    )
    return


@app.cell
def _(Path, compare_files, get_clubdesk_path, get_efa_path, mo):
    efa_file = Path(get_efa_path().strip().strip('"'))
    clubdesk_file = Path(get_clubdesk_path().strip().strip('"'))

    mo.stop(
        not get_efa_path().strip() or not get_clubdesk_path().strip(),
        mo.callout("Sobald beide Dateien definiert sind, erscheint hier die Datentabelle.", kind="neutral"),
    )

    _missing = [str(f) for f in (efa_file, clubdesk_file) if not f.is_file()]
    mo.stop(bool(_missing), mo.callout(f"Datei nicht gefunden: {', '.join(_missing)}", kind="danger"))

    try:
        data = compare_files(efa_file, clubdesk_file)
    except Exception as _e:
        mo.stop(True, mo.callout(f"Dateien konnten nicht gelesen werden: {_e}", kind="danger"))
    return clubdesk_file, data, efa_file


@app.cell
def _(data, mo):
    # Ausgewählte ClubDeskIds, neu je Abgleich; None = Vorgabe (alle mit Import).
    # allow_self_loops: gesetzt wird der State aus dem on_change der
    # Datentabelle, also aus der Zelle, die ihn liest – ohne diese Option
    # würde die Tabelle nicht neu aufgebaut. Keine Endlosschleife: on_change
    # setzt nur, wenn eine Zeile ohne Import angehakt ist.
    get_selected_ids, set_selected_ids = mo.state(None, allow_self_loops=True)
    return get_selected_ids, set_selected_ids


@app.cell
def _(build_table, data, get_selected_ids, mo, set_selected_ids):
    from collections import Counter
    from html import escape

    from rcbcomparetool.comparator import ChangeType

    from rcbmembersync.comparison_table import (
        CASE_LABELS,
        COLUMN_CASE,
        COLUMN_EXTERNAL_ID,
        COLUMN_SOURCE,
        COLUMN_TRANSFER,
        DISPLAY_COLUMNS,
    )

    table = build_table(data)
    counts = Counter(change.change_type for change in data.result.changes)

    _DIFFERENCE_STYLE = "color:#cc0000;font-weight:bold"
    _MANUAL_COLOR = "#777777"


    def _stacked(values, style=""):
        # Werte untereinander: efa oben, ClubDesk unten (wie Spalte „Quelle“)
        return mo.Html(f'<span style="{style}">' + "<br>".join(escape(v) or "–" for v in values) + "</span>")


    def _table_row(row):
        cells = {
            COLUMN_CASE: CASE_LABELS[row.change.change_type],
            COLUMN_SOURCE: _stacked(row.sources) if len(row.sources) > 1 else row.sources[0],
        }
        for label in DISPLAY_COLUMNS.values():
            if label in row.differences:
                cells[label] = _stacked(row.differences[label], _DIFFERENCE_STYLE)
            else:
                cells[label] = row.values.get(label, "")
        cells[COLUMN_TRANSFER] = row.transfer
        cells[COLUMN_EXTERNAL_ID] = row.change.external_id
        return cells


    def _style_cell(row_id, column, value):
        # Zeilen ohne Import (nur von Hand nachzuführen) grau
        return {} if table.rows[int(row_id)].importable else {"color": _MANUAL_COLOR}


    _summary = mo.hstack(
        [
            mo.stat(counts[ChangeType.NEW], label="Neu", bordered=True),
            mo.stat(counts[ChangeType.CHANGED], label="Geändert", bordered=True),
            mo.stat(counts[ChangeType.LEFT], label="Ausgetreten", bordered=True),
            mo.stat(len(data.result.not_comparable), label="Ohne ExternalId", bordered=True),
        ],
        justify="start",
    )

    _items = [mo.md("## Datentabelle"), _summary]

    if data.result.not_comparable:
        _count = len(data.result.not_comparable)
        _items.append(
            mo.callout(
                f"{_count} {'Person' if _count == 1 else 'Personen'} ohne ExternalId "
                f"{'kann' if _count == 1 else 'können'} nicht verglichen werden "
                "(Phase 1 „IDs vergeben“ nötig).",
                kind="warn",
            )
        )

    for _conflict in data.result.conflicts:
        _items.append(mo.callout(_conflict, kind="warn"))

    # Auswahl je Person direkt in der Datentabelle. Vorausgewählt sind alle
    # Personen mit Import – ClubDesk ist führend.
    _importable_ids = {row.change.external_id for row in table.rows if row.importable}
    _selected = _importable_ids if get_selected_ids() is None else get_selected_ids()


    def _keep_importable(value):
        # marimo kann einzelne Checkboxen nicht sperren: Wird eine Zeile ohne
        # Import (z.B. ausgetreten) angehakt, wird die Tabelle mit der
        # bereinigten Auswahl neu aufgebaut – das Häkchen verschwindet sofort.
        ids = {row[COLUMN_EXTERNAL_ID] for row in value}
        if ids - _importable_ids:
            set_selected_ids(ids & _importable_ids)


    data_table = (
        mo.ui.table(
            [_table_row(row) for row in table.rows],
            selection="multi",
            initial_selection=[i for i, row in enumerate(table.rows) if row.change.external_id in _selected],
            on_change=_keep_importable,
            pagination=False,
            show_column_summaries=False,
            show_data_types=False,
            freeze_columns_left=[COLUMN_CASE, COLUMN_SOURCE, "Vorname", "Nachname"],
            style_cell=_style_cell,
        )
        if table.rows
        else None
    )

    if data_table is None:
        _items.append(mo.callout("Keine Unterschiede zwischen efa und ClubDesk.", kind="success"))

    mo.vstack(_items)
    return COLUMN_EXTERNAL_ID, data_table, table


@app.cell
def _(COLUMN_EXTERNAL_ID, data_table, mo, table):
    mo.stop(data_table is None)

    _selected_ids = {row[COLUMN_EXTERNAL_ID] for row in data_table.value}
    _importable = [row for row in table.rows if row.importable]
    # nur Personen mit Import, auch falls eine Zeile „von Hand“ kurz angehakt war
    selected_changes = [row.change for row in _importable if row.change.external_id in _selected_ids]

    _hint = f"**{len(selected_changes)} von {len(_importable)} Personen zum Import ausgewählt.**"

    mo.vstack(
        [
            mo.md(
                "Abweichende Felder: oben efa, unten ClubDesk. Pro Person werden alle "
                "Änderungen übernommen oder keine – stimmt etwas nicht, in ClubDesk "
                "korrigieren und neu abgleichen. „Ungültig ab“ lässt sich nicht "
                "importieren und ist in der efa-Oberfläche von Hand nachzuführen."
            ),
            data_table,
            mo.md(_hint),
        ]
    )
    return (selected_changes,)


@app.cell
def _(
    already_applied,
    clubdesk_file,
    efa_file,
    get_apply_result,
    instance,
    mo,
    run_holder,
    selected_changes,
    table,
):
    from rcbcomparetool.comparator import ChangeType as _ChangeType

    from rcbmembersync.apply import CONFIRM_PRODUCTIVE, INSTANCE_LABELS, is_demo_file
    from rcbmembersync.comparison_table import TRANSFER_MANUAL

    # Nach dem Einspielen neu aufbauen: Formular zurücksetzen, Sperre anzeigen
    get_apply_result()

    _heading = mo.md("## Freigabe und Einspielen")
    _run_dir = run_holder["dir"]

    mo.stop(
        is_demo_file(efa_file) or is_demo_file(clubdesk_file),
        mo.vstack([_heading, mo.callout("Demodaten werden nicht nach efa eingespielt.", kind="neutral")]),
    )
    mo.stop(
        already_applied(_run_dir),
        mo.vstack([
            _heading,
            mo.callout(
                f"Der Lauf `{_run_dir.name if _run_dir else ''}` ist eingespielt. Für ein weiteres "
                "Einspielen efa (und bei Bedarf ClubDesk) neu exportieren – das beginnt einen neuen Lauf.",
                kind="neutral",
            ),
        ]),
    )
    mo.stop(
        not selected_changes,
        mo.vstack([_heading, mo.callout("Keine Person zum Import ausgewählt.", kind="neutral")]),
    )

    _new = sum(1 for _c in selected_changes if _c.change_type is _ChangeType.NEW)
    _changed = len(selected_changes) - _new
    _manual = sum(1 for _row in table.rows if TRANSFER_MANUAL in _row.transfer)
    _productive = instance.value == "remote"

    _instance_info = mo.callout(
        mo.md(f"### Instanz: {INSTANCE_LABELS[instance].upper() if _productive else INSTANCE_LABELS[instance]}"),
        kind="danger" if _productive else "info",
    )

    _summary = mo.md(
        "\n".join(
            [
                f"- **{len(selected_changes)} Personen** werden eingespielt: {_new} neu, {_changed} geändert",
                f"- Von Hand in efa nachzuführen (Spalte „Übernahme“): {_manual} Personen – "
                "werden nicht eingespielt",
                f"- efa-Datei: `{efa_file}`",
                f"- ClubDesk-Datei: `{clubdesk_file}`",
                f"- Laufverzeichnis: `{_run_dir}`" if _run_dir else "- Laufverzeichnis: _wird beim Einspielen angelegt_",
            ]
        )
    )

    _items = [_heading, _instance_info, _summary]

    # Hinweis, falls die efa-Datei dem Namen nach von der anderen Instanz stammt
    _efa_is_local = "_LOKAL" in str(efa_file)
    if _efa_is_local == _productive:
        _items.append(
            mo.callout(
                f"Die efa-Datei stammt dem Namen nach von der "
                f"{'lokalen Testinstanz' if _efa_is_local else 'produktiven Instanz'}, eingespielt wird "
                f"aber in die Instanz „{INSTANCE_LABELS[instance]}“. Bitte prüfen.",
                kind="warn",
            )
        )

    confirm_checkbox = mo.ui.checkbox(label="Ich habe die Auswahl geprüft und gebe das Einspielen frei.")
    confirm_text = (
        mo.ui.text(label=f"Zur Bestätigung „{CONFIRM_PRODUCTIVE}“ eintippen:", placeholder=CONFIRM_PRODUCTIVE)
        if _productive
        else None
    )

    _items.append(confirm_checkbox)
    if confirm_text is not None:
        _items.append(confirm_text)

    mo.vstack(_items)
    return confirm_checkbox, confirm_text


@app.cell
def _(confirm_checkbox, confirm_text, instance, mo):
    from rcbmembersync.apply import confirmed

    ready = confirmed(instance, confirm_checkbox.value, confirm_text.value if confirm_text is not None else "")

    apply_button = mo.ui.run_button(label="In efa einspielen", kind="danger", disabled=not ready)

    mo.hstack(
        [apply_button, mo.md("" if ready else "_Erst nach der Freigabe aktiv._")],
        justify="start",
        align="center",
    )
    return apply_button, ready


@app.cell
def _(
    apply_button,
    apply_changes,
    clubdesk_file,
    data,
    efa_file,
    ensure_run_dir,
    instance,
    mo,
    ready,
    selected_changes,
    set_apply_result,
):
    # Einziger Ort, an dem nach efa eingespielt wird – nur nach Klick und
    # Freigabe. Liest keinen State, den sie selbst setzt; ein zweiter
    # Durchlauf scheitert zudem an der Sperre im Laufverzeichnis (efacli.log).
    mo.stop(not apply_button.value or not ready)

    try:
        with mo.status.spinner(title="Einspielen nach efa läuft …"):
            _result = apply_changes(instance, ensure_run_dir(), efa_file, clubdesk_file, data.result, selected_changes)
        set_apply_result(_result)
    except Exception as _e:
        set_apply_result(f"{type(_e).__name__}: {_e}")
    return


@app.cell
def _(get_apply_result, mo):
    from rcbmembersync.apply import EFACLI_LOG_NAME, INSTANCE_LABELS as _LABELS
    from rcbmembersync.comparison_table import CASE_LABELS as _CASES

    _result = get_apply_result()
    mo.stop(_result is None)

    if isinstance(_result, str):
        _output = mo.callout(
            mo.md(
                f"**Einspielen abgebrochen:** {_result}\n\n"
                "Kam die efaCLI-Verbindung nicht zustande, wurde nichts eingespielt und der Lauf "
                f"kann wiederholt werden. Sonst zeigt `{EFACLI_LOG_NAME}` im Laufverzeichnis den Stand."
            ),
            kind="danger",
        )
    else:
        _failed = _result.failed
        _ok = len(_result.outcomes) - len(_failed)

        _rows = [
            {
                "Ergebnis": "ok" if _o.ok else "FEHLER",
                "Fall": _CASES[_o.file.change.change_type],
                "Vorname": _o.file.change.first_name,
                "Nachname": _o.file.change.last_name,
                "Meldung": _o.message,
                "Datei": _o.file.path.name,
                "ClubDeskId": _o.file.change.external_id,
            }
            for _o in _result.outcomes
        ]


        def _style_result(row_id, column, value):
            return {} if _rows[int(row_id)]["Ergebnis"] == "ok" else {"color": "#cc0000", "fontWeight": "bold"}


        _output = mo.vstack(
            [
                mo.md(f"## Ergebnis Einspielen ({_LABELS[_result.instance]})"),
                mo.callout(
                    mo.md(
                        f"**{_ok} von {len(_result.outcomes)} Personen eingespielt.**"
                        + (f" **{len(_failed)} fehlgeschlagen**, Meldung in der Tabelle." if _failed else "")
                        + f"\n\nProtokoll: `{_result.run_dir / EFACLI_LOG_NAME}`"
                    ),
                    kind="warn" if _failed else "success",
                ),
                mo.ui.table(
                    _rows,
                    selection=None,
                    pagination=False,
                    show_column_summaries=False,
                    show_data_types=False,
                    style_cell=_style_result,
                ),
                mo.md(
                    "„importiert“ heisst noch nicht, dass jeder Wert in efa angekommen ist. "
                    "Zur Kontrolle efa neu exportieren und abgleichen: Erwartet werden nur noch "
                    "die nicht ausgewählten Personen und die Einträge „von Hand“."
                ),
            ]
        )

    _output
    return


if __name__ == "__main__":
    app.run()
