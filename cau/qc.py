"""Pre-flight QC for a monthly actuals file before any budget-vs-actual variance is reported.

Adapted from quantlab's data-quality grader (quantlab/data/quality.py): a schema and completeness
profile for any table, then domain checks that each produce findings, and a grade. Nothing is
silently fixed: ``clean`` applies a stated policy and returns what it removed, so the dashboard can
show the reader exactly what was excluded.

Checks: required columns; non-numeric amounts; duplicated (period, line) rows; lines not in the chart
of accounts; sign errors (expenses and revenue must be positive, vacancy negative); missing
(period, line) combinations; and amounts far from budget (flagged for review, not removed).
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

REQUIRED = ("period", "line", "amount")
SEVERE = {"schema", "non_numeric", "duplicate", "unmapped_line", "sign_error"}


@dataclass
class QCReport:
    profile: pd.DataFrame
    findings: pd.DataFrame
    grade: str
    clean: pd.DataFrame
    removed: pd.DataFrame


def profile(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column type, completeness, cardinality and range (as in quantlab's quality.profile)."""
    rows = []
    for c in df.columns:
        s = df[c]
        rows.append({"column": c, "dtype": str(s.dtype), "non_null_pct": round(100 * s.notna().mean(), 1) if len(s) else 0.0,
                     "distinct": int(s.nunique(dropna=True)),
                     "min": s.min() if pd.api.types.is_numeric_dtype(s) else None,
                     "max": s.max() if pd.api.types.is_numeric_dtype(s) else None})
    return pd.DataFrame(rows)


def run(actuals: pd.DataFrame, budget: pd.DataFrame, chart: dict, review_band: float = 0.5) -> QCReport:
    """``chart`` maps line -> (engine key, kind) with kind in revenue / contra / expense."""
    f: list[dict] = []
    missing_cols = [c for c in REQUIRED if c not in actuals.columns]
    if missing_cols:
        f.append({"check": "schema", "period": "", "line": "", "detail": f"missing columns {missing_cols}"})
        empty = pd.DataFrame(columns=list(REQUIRED))
        return QCReport(profile(actuals), pd.DataFrame(f), "D", empty, actuals)
    a = actuals[list(REQUIRED)].copy()
    a["amount_num"] = pd.to_numeric(a["amount"], errors="coerce")
    for r in a[a["amount_num"].isna()].itertuples():
        f.append({"check": "non_numeric", "period": r.period, "line": r.line, "detail": f"amount {r.amount!r}"})

    dup_mask = a.duplicated(["period", "line"], keep="first")
    for r in a[dup_mask].itertuples():
        f.append({"check": "duplicate", "period": r.period, "line": r.line, "detail": "second row for this period and line"})

    unmapped = ~a["line"].isin(chart)
    for r in a[unmapped].drop_duplicates(["period", "line"]).itertuples():
        f.append({"check": "unmapped_line", "period": r.period, "line": r.line, "detail": "not in the chart of accounts"})

    kind = a["line"].map(lambda x: chart.get(x, (None, None))[1])
    bad_sign = ((kind.isin(["revenue", "expense"]) & (a["amount_num"] < 0))
                | ((kind == "contra") & (a["amount_num"] > 0)))
    for r in a[bad_sign].itertuples():
        f.append({"check": "sign_error", "period": r.period, "line": r.line,
                  "detail": f"amount {r.amount_num:,.2f} has the wrong sign for this {chart[r.line][1]} line"})

    periods = sorted(a["period"].dropna().unique())
    have = set(zip(a["period"], a["line"], strict=True))
    for p in periods:
        for line in chart:
            if (p, line) not in have:
                f.append({"check": "missing", "period": p, "line": line, "detail": "no amount reported"})

    ok = ~(dup_mask | unmapped | bad_sign | a["amount_num"].isna())
    clean = a[ok].assign(amount=a.loc[ok, "amount_num"])[list(REQUIRED)].reset_index(drop=True)
    removed = a[~ok][list(REQUIRED)].reset_index(drop=True)

    bud = budget.set_index(["period", "line"])["amount"]
    for r in clean.itertuples():
        key = (r.period, r.line)
        if key in bud.index and bud[key] != 0 and abs(r.amount / bud[key] - 1) > review_band:
            f.append({"check": "review", "period": r.period, "line": r.line,
                      "detail": f"{r.amount / bud[key] - 1:+.0%} against budget"})

    findings = pd.DataFrame(f, columns=["check", "period", "line", "detail"])
    checks = set(findings["check"])
    grade = "A" if not checks else "D" if checks & SEVERE else "B" if checks <= {"review"} else "C"
    return QCReport(profile(actuals), findings, grade, clean, removed)


def variance(clean: pd.DataFrame, budget: pd.DataFrame, chart: dict, threshold: float = 0.05,
             min_usd: float = 5000.0) -> pd.DataFrame:
    """Year-to-date budget vs actual by line over the periods that have actuals. Favourable means
    more revenue or less expense. A line is flagged when it misses by more than ``threshold`` and
    ``min_usd``. Lines with any missing month are reported as incomplete, not netted."""
    periods = sorted(clean["period"].unique())
    bud = budget[budget["period"].isin(periods)]
    out = []
    for line, (_, kind) in chart.items():
        b = bud.loc[bud["line"] == line, "amount"].sum()
        got = clean[clean["line"] == line]
        complete = got["period"].nunique() == len(periods)
        act = got["amount"].sum()
        var = act - b
        favourable = var >= 0 if kind in ("revenue", "contra") else var <= 0
        pct = var / abs(b) if b else 0.0
        flag = "incomplete" if not complete else (
            ("unfavourable" if not favourable else "favourable")
            if abs(pct) > threshold and abs(var) > min_usd else "within tolerance")
        out.append({"line": line, "kind": kind, "budget": b, "actual": act, "variance": var, "variance_pct": pct,
                    "favourable": None if not complete else favourable, "status": flag,
                    "months": got["period"].nunique()})
    t = pd.DataFrame(out)
    # NOI only over months where every line reported: a missing expense would otherwise flatter it
    complete = complete_periods(clean, chart)
    noi_b = noi_by_period(bud[bud["period"].isin(complete)], chart).sum()
    noi_a = noi_by_period(clean[clean["period"].isin(complete)], chart).sum()
    total = {"line": "Net operating income (complete months)", "kind": "total", "budget": noi_b, "actual": noi_a,
             "variance": noi_a - noi_b, "variance_pct": (noi_a - noi_b) / abs(noi_b) if noi_b else 0.0,
             "favourable": noi_a >= noi_b, "status": "total", "months": len(complete)}
    return pd.concat([t, pd.DataFrame([total])], ignore_index=True)


def complete_periods(clean: pd.DataFrame, chart: dict) -> list[str]:
    """Periods in which every chart-of-accounts line has an amount."""
    n = clean.groupby("period")["line"].nunique()
    return sorted(n[n == len(chart)].index)


def noi_by_period(df: pd.DataFrame, chart: dict) -> pd.Series:
    sign = df["line"].map(lambda x: {"revenue": 1, "contra": 1, "expense": -1}[chart[x][1]])
    return (df["amount"] * sign).groupby(df["period"]).sum()
