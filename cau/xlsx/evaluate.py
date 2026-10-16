"""Evaluate a generated workbook's formulas without Excel, so tests can compare the workbook's
numbers with the Python engine. Uses the ``formulas`` package (pure-Python Excel calculator)."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

_REF = re.compile(r"^'?(?P<sheet>[^'!]+)'?!\$?(?P<c1>[A-Z]+)\$?(?P<r1>\d+)(?::\$?(?P<c2>[A-Z]+)\$?(?P<r2>\d+))?$")


def evaluate(path: Path, set_inputs: dict | None = None, model=None) -> dict:
    """Return {defined name: value}; ranges come back as 1-D numpy arrays (row order).

    ``set_inputs`` overrides named single-cell inputs (e.g. {"Case_Select": 2}) before calculating;
    pass a loaded ``model`` (from ``load_model``) to evaluate several settings without reparsing."""
    from openpyxl.utils import column_index_from_string, get_column_letter

    model = model or load_model(path)
    wb = load_workbook(path)
    feed = {}
    for name, value in (set_inputs or {}).items():
        m = _REF.match(wb.defined_names[name].attr_text)
        feed[f"'[{Path(path).name}]{m['sheet'].upper()}'!{m['c1']}{m['r1']}"] = value
    sol = model.calculate(inputs=feed) if feed else model.calculate()
    cells = {}
    for k, v in sol.items():
        m = re.match(r"^'\[[^\]]+\](?P<sheet>[^']+)'!(?P<ref>[A-Z]+\d+(?::[A-Z]+\d+)?)$", k)
        if m:
            cells[(m["sheet"].upper(), m["ref"])] = v.value if hasattr(v, "value") else v

    def cell(sheet, c, r):
        val = cells.get((sheet.upper(), f"{c}{r}"))
        if val is None:
            return None
        x = np.asarray(val).ravel()[0]
        return x.item() if hasattr(x, "item") else x

    out = {}
    for name, dn in wb.defined_names.items():
        m = _REF.match(dn.attr_text)
        if not m:
            continue
        if not m["c2"]:
            out[name] = cell(m["sheet"], m["c1"], m["r1"])
        else:
            c1, c2 = column_index_from_string(m["c1"]), column_index_from_string(m["c2"])
            out[name] = np.array([cell(m["sheet"], get_column_letter(c), m["r1"]) for c in range(c1, c2 + 1)],
                                 dtype=object)
    return out


def load_model(path: Path):
    import formulas
    return formulas.ExcelModel().loads(str(path)).finish()
