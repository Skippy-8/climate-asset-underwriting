"""Base / Downside / Severe cases, one-factor sensitivities, two-way grids and break-evens for both
models, all driven by data/stress_cases.yaml.

Post-closing logic lives here rather than in the scenario file: when a model's cases set
``hold_loan``, the stress runs reuse the base-case loan (``Loan_Override``), so the lender's view is a
closed loan meeting worse operations rather than a re-sized new loan.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
import yaml

from cau.engine import property as P
from cau.engine import solar_storage as SS
from cau.inputs import DATA, load_inputs, values

ENGINES = {"property": P, "solar_storage": SS}
CASES = ("Base", "Downside", "Severe")

# Metrics reported for each model: key -> (label, kind) where kind drives formatting.
METRICS = {
    "property": [
        ("Loan", "Loan amount", "usd"), ("Min_DSCR_SQ", "Minimum DSCR, status quo", "x"),
        ("Min_DSCR_RF", "Minimum DSCR, retrofit", "x"), ("Min_DY_SQ", "Minimum debt yield, status quo", "pct"),
        ("Trap_Years_SQ", "Covenant flag-years, status quo", "int"),
        ("Lev_IRR_SQ", "Levered IRR, status quo", "pct"), ("Lev_IRR_RF", "Levered IRR, retrofit", "pct"),
        ("Equity_Multiple_RF", "Equity multiple, retrofit", "x"), ("Exit_Value_RF", "Exit value, retrofit", "usd"),
        ("Payback_Years", "Retrofit simple payback", "yrs"), ("EUI_RF", "Site EUI after retrofit", "num1"),
    ],
    "solar_storage": [
        ("Debt", "Senior debt", "usd"), ("Min_DSCR_Op", "Minimum DSCR (operating case)", "x"),
        ("Avg_DSCR_Op", "Average DSCR (operating case)", "x"), ("LLCR_Op", "LLCR (operating case)", "x"),
        ("Lockup_Years", "Years in distribution lock-up", "int"), ("Default_Years", "Years below the default trigger", "int"),
        ("Equity", "Sponsor equity", "usd"), ("Equity_IRR", "Equity IRR, pre-tax", "pct"),
        ("Equity_IRR_AT", "Equity IRR, after tax", "pct"), ("Project_IRR", "Project IRR, pre-tax", "pct"),
    ],
}

# Metrics that must get no better from Base to Downside to Severe (direction = -1 means lower is worse).
MONOTONE = {
    "property": {"Min_DSCR_SQ": -1, "Min_DSCR_RF": -1, "Min_DY_SQ": -1, "Lev_IRR_SQ": -1, "Lev_IRR_RF": -1,
                 "Exit_Value_RF": -1, "Payback_Years": +1, "EUI_RF": +1},
    "solar_storage": {"Min_DSCR_Op": -1, "Avg_DSCR_Op": -1, "LLCR_Op": -1, "Lockup_Years": +1, "Default_Years": +1,
                      "Equity_IRR": -1, "Equity_IRR_AT": -1,
                      "Project_IRR": -1, "Debt": -1, "Equity": +1},
}


@lru_cache(maxsize=1)
def spec() -> dict:
    return yaml.safe_load((DATA / "stress_cases.yaml").read_text())


def base_values(model: str) -> dict:
    return values(load_inputs(model))


def case_overrides(model: str, case: str) -> dict:
    """The input overrides for one case, including the held loan where the model holds it."""
    s = spec()[model]
    over = dict(s["cases"][case])
    if s.get("hold_loan") and case != "Base":
        over["Loan_Override"] = ENGINES[model].run(base_values(model)).scalars["Loan"]
    return over


def run_case(model: str, case: str, **extra):
    v = dict(base_values(model), **case_overrides(model, case))
    v.update(extra)
    return ENGINES[model].run(v)


def case_table(model: str) -> pd.DataFrame:
    """Rows = metrics, columns = Base / Downside / Severe."""
    res = {c: run_case(model, c).scalars for c in CASES}
    rows = [{"key": k, "metric": label, "kind": kind, **{c: float(res[c][k]) for c in CASES}}
            for k, label, kind in METRICS[model]]
    return pd.DataFrame(rows).set_index("key")


def sensitivities(model: str, metric: str) -> pd.DataFrame:
    """One lever at a time from the base case: the metric's value and its change from base."""
    base = ENGINES[model].run(base_values(model)).scalars[metric]
    hold = {}
    if spec()[model].get("hold_loan"):
        hold["Loan_Override"] = ENGINES[model].run(base_values(model)).scalars["Loan"]
    out = []
    for s in spec()["sensitivities"][model]:
        v = dict(base_values(model), **hold, **s["set"])
        val = ENGINES[model].run(v).scalars[metric]
        out.append({"lever": s["label"], "value": val, "change": val - base})
    return pd.DataFrame(out).sort_values("change").reset_index(drop=True)


def grid(model: str, x_key: str, xs, y_key: str, ys, metric: str, hold_loan: bool = True) -> pd.DataFrame:
    """Two-way sensitivity: rows = y values, columns = x values, cells = metric."""
    base = base_values(model)
    hold = {}
    if hold_loan and spec()[model].get("hold_loan"):
        hold["Loan_Override"] = ENGINES[model].run(base).scalars["Loan"]
    data = [[ENGINES[model].run(dict(base, **hold, **{x_key: x, y_key: y})).scalars[metric] for x in xs] for y in ys]
    return pd.DataFrame(data, index=pd.Index(ys, name=y_key), columns=pd.Index(xs, name=x_key))


def _bisect(f, lo: float, hi: float, iters: int = 80) -> float:
    a = f(lo)
    for _ in range(iters):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (a > 0):
            lo, a = mid, f(mid)
        else:
            hi = mid
    return (lo + hi) / 2


def breakeven_generation() -> dict:
    """Uniform output haircut (every year, debt fixed at close) at which the minimum operating DSCR
    reaches 1.00x, expressed as a share of P50 and as a one-year exceedance level."""
    from math import erf, sqrt
    base = base_values("solar_storage")
    sigma = base["Gen_Sigma_1yr"]

    def gap(z):
        return SS.run(dict(base, Gen_Case_Z=z)).scalars["Min_DSCR_Op"] - 1.0

    z = _bisect(gap, 0.0, 1 / sigma - 1e-6)
    exceed = 0.5 * (1 + erf(z / sqrt(2)))           # P(output >= level) under the normal assumption
    return {"z": z, "share_of_p50": 1 - z * sigma, "exceedance": exceed}


def breakeven_vacancy(threshold_key: str = "DSCR_Default") -> dict:
    """Vacancy (loan held at the base size) at which the status-quo minimum DSCR hits the given
    covenant level."""
    base = base_values("property")
    loan = P.run(base).scalars["Loan"]
    level = base[threshold_key]

    def gap(vac):
        return P.run(dict(base, Vacancy_Rate=vac, Loan_Override=loan)).scalars["Min_DSCR_SQ"] - level

    vac = _bisect(gap, base["Vacancy_Rate"], 0.6)
    return {"vacancy": vac, "level": level}


def monotone_violations(model: str) -> list[str]:
    t = case_table(model)
    bad = []
    for key, direction in MONOTONE[model].items():
        seq = t.loc[key, list(CASES)].to_numpy(float)
        steps = np.diff(seq) * direction
        if (steps < -1e-9).any():
            bad.append(f"{key}: {seq}")
    return bad
