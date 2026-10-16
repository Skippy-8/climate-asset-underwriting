"""Excel-equivalent finance functions, so the engine and the workbook use the same definitions."""
from __future__ import annotations

import numpy as np


def pmt(rate: float, nper: float, pv: float) -> float:
    """Excel PMT(rate, nper, pv) with fv = 0, type = 0."""
    if rate == 0:
        return -pv / nper
    return -pv * rate / (1 - (1 + rate) ** -nper)


def fv(rate: float, nper: float, payment: float, pv: float) -> float:
    """Excel FV(rate, nper, pmt, pv) with type = 0."""
    if rate == 0:
        return -(pv + payment * nper)
    g = (1 + rate) ** nper
    return -(pv * g + payment * (g - 1) / rate)


def npv(rate: float, flows) -> float:
    """Excel NPV: the first flow is discounted one period."""
    f = np.asarray(flows, float)
    return float(np.sum(f / (1 + rate) ** np.arange(1, len(f) + 1)))


def irr(flows, guess: float = 0.1, tol: float = 1e-12) -> float:
    """IRR with flows[0] at t = 0. Like Excel's IRR (which iterates from a 10% guess), it returns the
    root nearest the guess, so cash flows with more than one sign change (a loss-making merchant tail)
    still give Excel's answer. The bracket is found by stepping outward from the guess, then bisected."""
    f = np.asarray(flows, float)
    t = np.arange(len(f))

    def v(r):
        return float(np.sum(f / (1 + r) ** t))

    def nearest_bracket(step: float, limit: int):
        """First sign change walking from the guess in direction ``step``; None if there is none."""
        a = guess
        for _ in range(limit):
            b = a + step
            if b <= -0.99:
                return None
            if v(a) * v(b) <= 0:
                return (min(a, b), max(a, b))
            a = b
        return None

    brackets = [x for x in (nearest_bracket(0.005, 400), nearest_bracket(-0.005, 200)) if x]
    if not brackets:
        raise ValueError("IRR not bracketed")
    lo, hi = min(brackets, key=lambda x: min(abs(x[0] - guess), abs(x[1] - guess)))
    f_lo = v(lo)
    for _ in range(300):
        mid = (lo + hi) / 2
        f_mid = v(mid)
        if abs(f_mid) < tol:
            break
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def amortize(loan: float, rates, amort_months: float, io_years: float, months: float = 12) -> dict:
    """Annual view of a monthly-pay loan: interest-only for ``io_years``, then level payments that
    are re-set each year on the remaining term (so a floating rate path re-amortises). ``rates`` is
    the annual rate for each year; the schedule has one entry per rate."""
    rates = np.asarray(rates, float)
    n = len(rates)
    beg, end, pay_m = np.zeros(n), np.zeros(n), np.zeros(n)
    bal = loan
    for k in range(n):
        year = k + 1
        i = rates[k] / months
        beg[k] = bal
        if year <= io_years:
            pay_m[k] = bal * i
            end[k] = bal
        else:
            remaining = amort_months - months * (year - 1 - io_years)
            pay_m[k] = pmt(i, remaining, -bal)
            end[k] = fv(i, months, pay_m[k], -bal)
        bal = end[k]
    service = pay_m * months
    return {"Beg_Balance": beg, "End_Balance": end, "Monthly_Payment": pay_m, "Debt_Service": service,
            "Principal": beg - end, "Interest": service - (beg - end)}


def irr_or_nan(flows, guess: float = 0.1) -> float:
    """IRR, or NaN when none exists in range (e.g. equity that never gets its money back). The
    workbooks show the same case as "n/m" through IFERROR."""
    try:
        return irr(flows, guess)
    except ValueError:
        return float("nan")
