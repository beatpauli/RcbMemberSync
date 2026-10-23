import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", app_title="RcbMemberSync")


@app.cell
def _():
    import marimo as mo

    from rcbmembersync.settings import check_environment
    return check_environment, mo


@app.cell
def _(mo):
    mo.md("""
    # RcbMemberSync

    Abgleich der Mitgliederdaten zwischen **ClubDesk** (führend) und **efa**.
    Das Tool erzeugt nur Dateien – der Import nach efa über efaCLI erfolgt
    manuell.
    """)
    return


@app.cell
def _(check_environment, mo):
    checks = check_environment()
    all_ok = all(check.ok for check in checks)

    mo.vstack(
        [
            mo.md("## Konfiguration"),
            mo.callout(
                mo.md(
                    "\n".join(
                        f"- {'✅' if check.ok else '❌'} **{check.name}**: {check.detail}"
                        for check in checks
                    )
                ),
                kind="success" if all_ok else "danger",
            ),
        ]
    )
    return


@app.cell
def _(mo):
    mo.vstack(
        [
            mo.md("## 1. ClubDesk-Export"),
            mo.callout(mo.md("Noch nicht umgesetzt (Schritt 4 im Plan)."), kind="neutral"),
            mo.md("## 2. efa-Export"),
            mo.callout(mo.md("Noch nicht umgesetzt (Schritt 3 im Plan)."), kind="neutral"),
            mo.md("## 3. Abgleich"),
            mo.callout(mo.md("Noch nicht umgesetzt (Schritt 2 im Plan)."), kind="neutral"),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
