"""Year-one monthly budget (from the property engine) and an illustrative actuals file for the
budget-vs-actual monitor.

The budget is the engine's year-one operating statement (status-quo case) spread across twelve
months: flat for most lines, seasonal for gas (heating load) and electricity (cooling of common
areas). The seasonal weights are illustrative.

The actuals are SYNTHETIC: a seeded draw around the budget with a few deliberate business variances
(a cold winter, a spring repairs spike, softer Q3 leasing) and four deliberate data defects that the
pre-flight QC in cau/qc.py has to catch before any variance is reported: a duplicated row, a missing
month for one line, a sign error and an unmapped GL line.

    python -m cau.actuals          # rewrite data/actuals/property_actuals_ytd.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from cau.engine import property as P
from cau.inputs import DATA, load_inputs, values

ACTUALS = DATA / "actuals" / "property_actuals_ytd.csv"
MONTHS_YTD = 9

# line -> (engine row, "revenue" | "expense"); vacancy is a negative revenue line (contra-revenue)
CHART_OF_ACCOUNTS = {
    "Gross potential rent": ("GPR", "revenue"),
    "Vacancy and credit loss": ("Vacancy", "contra"),
    "Other income": ("Other_Income", "revenue"),
    "Real estate taxes": ("Taxes", "expense"),
    "Insurance": ("Insurance", "expense"),
    "Water and sewer": ("Water_Sewer", "expense"),
    "Repairs and maintenance": ("Repairs", "expense"),
    "Payroll": ("Payroll", "expense"),
    "G&A and marketing": ("Admin", "expense"),
    "Management fee": ("Mgmt_Fee", "expense"),
    "Gas": ("Gas_Cost_SQ", "expense"),
    "Electricity": ("Elec_Cost_SQ", "expense"),
}

# Illustrative monthly shapes (January first); each sums to 1.
SEASONAL = {
    "Gas": np.array([18, 16, 12, 7, 4, 3, 3, 3, 4, 7, 10, 13], float),
    "Electricity": np.array([8, 7, 7, 7, 8, 10, 11, 11, 9, 7, 7, 8], float),
}


def period(m: int) -> str:
    return f"Y1-M{m:02d}"


def budget(v: dict | None = None) -> pd.DataFrame:
    """Monthly budget for year one: columns period, line, kind, amount."""
    v = v or values(load_inputs("property"))
    r = P.run(v)
    rows = []
    for line, (key, kind) in CHART_OF_ACCOUNTS.items():
        annual = float(r.rows[key][0])
        w = SEASONAL.get(line, np.ones(12))
        w = w / w.sum()
        rows += [{"period": period(m + 1), "line": line, "kind": kind, "amount": annual * w[m]} for m in range(12)]
    return pd.DataFrame(rows)


def synthetic_actuals(seed: int = 7) -> pd.DataFrame:
    """Year-to-date actuals with business variances and planted data defects (see module doc)."""
    rng = np.random.default_rng(seed)
    b = budget()
    b = b[b["period"].isin([period(m) for m in range(1, MONTHS_YTD + 1)])].copy()
    b["month"] = b["period"].str[-2:].astype(int)
    shock = np.ones(len(b))
    is_ = lambda line, months: (b["line"] == line) & b["month"].isin(months)        # noqa: E731
    shock[is_("Gas", [1, 2]).to_numpy()] *= 1.22                     # cold January-February
    shock[is_("Repairs and maintenance", [4, 5]).to_numpy()] *= 1.45  # spring make-ready spike
    shock[is_("Vacancy and credit loss", [7, 8, 9]).to_numpy()] *= 1.60   # softer Q3 leasing
    shock[is_("Other income", list(range(1, 10))).to_numpy()] *= 0.88
    shock[is_("Payroll", list(range(1, 10))).to_numpy()] *= 1.04
    noise = 1 + rng.normal(0, 0.015, len(b))
    a = b.assign(amount=(b["amount"] * shock * noise).round(2))[["period", "line", "amount"]]
    # planted defects
    dup = a[(a["line"] == "Repairs and maintenance") & (a["period"] == period(4))]
    a = pd.concat([a, dup], ignore_index=True)                                         # duplicated row
    a = a[~((a["line"] == "Electricity") & (a["period"] == period(6)))]               # missing month
    a.loc[(a["line"] == "Insurance") & (a["period"] == period(3)), "amount"] *= -1     # sign error
    legal = pd.DataFrame([{"period": period(5), "line": "Legal fees", "amount": 6400.0}])
    a = pd.concat([a, legal], ignore_index=True)                                       # unmapped GL line
    return a.sort_values(["period", "line"]).reset_index(drop=True)


def write() -> Path:
    ACTUALS.parent.mkdir(parents=True, exist_ok=True)
    synthetic_actuals().to_csv(ACTUALS, index=False)
    return ACTUALS


if __name__ == "__main__":
    print(f"wrote {write()}")
