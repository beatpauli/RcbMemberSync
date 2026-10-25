import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", app_title="RCB-Mitglieder Abgleich")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo

    from rcbefaexport.config import Instance

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
    return (
        get_clubdesk_message,
        get_clubdesk_path,
        get_efa_message,
        get_efa_path,
        get_run_dir,
        run_holder,
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
def _(OUTPUT_DIR, create_run_dir, instance, run_holder, set_run_dir):
    def ensure_run_dir():
        """Laufverzeichnis des aktuellen Laufs, beim ersten Aufruf angelegt."""
        if run_holder["dir"] is None:
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
            _file = export_efa(instance, ensure_run_dir())
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
            _file = export_clubdesk(ensure_run_dir())
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
    _efa_file = Path(get_efa_path().strip().strip('"'))
    _clubdesk_file = Path(get_clubdesk_path().strip().strip('"'))

    mo.stop(
        not get_efa_path().strip() or not get_clubdesk_path().strip(),
        mo.callout("Sobald beide Dateien definiert sind, erscheint hier die Datentabelle.", kind="neutral"),
    )

    _missing = [str(f) for f in (_efa_file, _clubdesk_file) if not f.is_file()]
    mo.stop(bool(_missing), mo.callout(f"Datei nicht gefunden: {', '.join(_missing)}", kind="danger"))

    try:
        data = compare_files(_efa_file, _clubdesk_file)
    except Exception as _e:
        mo.stop(True, mo.callout(f"Dateien konnten nicht gelesen werden: {_e}", kind="danger"))
    return (data,)


@app.cell
def _(data, mo):
    # Ausgewählte ClubDeskIds, neu je Abgleich; None = Vorgabe (alle mit Import)
    get_selected_ids, set_selected_ids = mo.state(None)
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


if __name__ == "__main__":
    app.run()
