"""The Scenarios tab shared by both workbooks.

The live panel at the top is formulas: it shows whichever case Case_Select picks. The tables below are
a snapshot of all three cases (and the one-factor sensitivities) computed by the Python engine at
build time, because a workbook can only show one case at a time without data tables.
tests/test_stress.py flips Case_Select to each case and requires the workbook to reproduce every
snapshot number, so the snapshot cannot drift from the live model.
"""
from __future__ import annotations

from cau.engine import stress as ST
from cau.xlsx.book import BOLD, FMT, HEAD, HEAD_FILL, MUTED, Book

KIND_FMT = {"usd": "usd", "x": "x", "pct": "pct", "int": "int", "yrs": "num1", "num1": "num1"}


def scenario_values(model: str, inputs) -> dict[str, list[float]]:
    """[Base, Downside, Severe] for every input any case overrides."""
    base = {i.key: i.value for i in inputs}
    keys = sorted({k for c in ST.CASES for k in ST.case_overrides(model, c)})
    return {k: [ST.case_overrides(model, c).get(k, base[k]) for c in ST.CASES] for k in keys}


def scenarios_sheet(b: Book, model: str, sens_metrics: list[tuple[str, str, str]], breakevens: list[tuple]) -> None:
    ws = b.wb.create_sheet("Scenarios")
    ws.sheet_view.showGridLines = False
    for c, w in zip("ABCDE", (46, 18, 18, 18, 30), strict=True):
        ws.column_dimensions[c].width = w
    ws["A1"] = "Stress cases"
    ws["A1"].font = BOLD
    ws["A2"] = ST.spec()[model]["note"]
    ws["A2"].font = MUTED
    table = ST.case_table(model)

    # live panel
    ws["A4"] = "Case currently shown (Inputs!Case_Select)"
    ws["A4"].font = BOLD
    ws["B4"] = '=CHOOSE(Case_Select,"Base","Downside","Severe")'
    row = 5
    for key, r in table.iterrows():
        ws[f"A{row}"], ws[f"B{row}"] = r["metric"], f"={key}"
        ws[f"B{row}"].number_format = FMT[KIND_FMT[r["kind"]]]
        row += 1

    # snapshot of all three cases
    row += 1
    ws[f"A{row}"] = ("Snapshot of all three cases (Python engine at build time; set Case_Select to reproduce any "
                     "column live)")
    ws[f"A{row}"].font = BOLD
    row += 1
    for c, h in zip("ABCD", ["Metric", *ST.CASES], strict=True):
        ws[f"{c}{row}"] = h
        ws[f"{c}{row}"].font = HEAD
        ws[f"{c}{row}"].fill = HEAD_FILL
    for key, r in table.iterrows():
        row += 1
        ws[f"A{row}"] = r["metric"]
        for c, case in zip("BCD", ST.CASES, strict=True):
            ws[f"{c}{row}"] = float(r[case])
            ws[f"{c}{row}"].number_format = FMT[KIND_FMT[r["kind"]]]
        b.name(f"Snap_{key}", "Scenarios", f"$B${row}:$D${row}")

    # one-factor sensitivities
    for metric, label, kind in sens_metrics:
        row += 2
        ws[f"A{row}"] = f"One factor at a time from the base case: {label}"
        ws[f"A{row}"].font = BOLD
        row += 1
        for c, h in zip("ABC", ["Lever", "Value", "Change from base"], strict=True):
            ws[f"{c}{row}"] = h
            ws[f"{c}{row}"].font = HEAD
            ws[f"{c}{row}"].fill = HEAD_FILL
        for _, s in ST.sensitivities(model, metric).iterrows():
            row += 1
            ws[f"A{row}"], ws[f"B{row}"], ws[f"C{row}"] = s["lever"], float(s["value"]), float(s["change"])
            ws[f"B{row}"].number_format = ws[f"C{row}"].number_format = FMT[kind]

    # break-evens
    row += 2
    ws[f"A{row}"] = "Break-evens (Python engine)"
    ws[f"A{row}"].font = BOLD
    for label, value, kind in breakevens:
        row += 1
        ws[f"A{row}"], ws[f"B{row}"] = label, float(value)
        ws[f"B{row}"].number_format = FMT[kind]
