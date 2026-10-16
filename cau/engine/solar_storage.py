"""Solar + storage project financing engine: 200 MWac solar and a 100 MW / 400 MWh battery in
West Texas (ERCOT), with debt sculpted to target DSCRs.

Reference implementation for cau/xlsx/pf_book.py; the tests hold the two to the same numbers.

Two cash flows, deliberately separate:
* the **sizing case** is what the lender sizes on at financial close: P50 and P90 generation at
  base prices. Debt service is sculpted on it and then fixed;
* the **operating case** is what actually happens: generation at ``1 - Gen_Case_Z * sigma`` of P50
  (0 = P50, Z_P90 = P90, Z_P99 = P99) and merchant prices after the ``Merchant_Shock``. DSCRs and
  equity returns are measured on it against the fixed schedule.
A rate shock and a capex overrun act at close: the first re-sizes the debt, the second is funded
with equity.

Sculpting without circularity: target service each year is
``min(CFADS_P50 / DSCR_P50_Target, CFADS_P90 / DSCR_P90_Target)`` inside the tenor. The debt that
service can carry is its present value at the coupon, ``NPV(r, target service)``; capped by gearing,
debt = ``min(PV, Max_Gearing * capex)`` and the schedule is scaled by debt / PV. Interest is
opening balance x r and principal is service minus interest, so the balance reaches exactly zero at
maturity. Nothing in the sizing depends on uses that depend on debt, so no iteration is needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from cau.engine.finance import irr_or_nan as irr
from cau.engine.finance import npv

YEARS = 30


@dataclass
class PFResult:
    inputs: dict
    rows: dict = field(default_factory=dict)
    scalars: dict = field(default_factory=dict)
    returns: dict = field(default_factory=dict)


def run(v: dict) -> PFResult:
    r = PFResult(inputs=dict(v))
    R, S = r.rows, r.scalars
    t = np.arange(1, YEARS + 1, dtype=float)

    # ── capex and credits (year 0) ──────────────────────────────────────────
    S["PV_MWdc"] = v["PV_MWac"] * v["ILR"]
    S["BESS_MWh"] = v["BESS_MW"] * v["BESS_Hours"]
    S["PV_Capex"] = v["PV_MWac"] * v["kW_per_MW"] * v["W_per_kW"] * v["PV_Capex_Per_Wac"] * (1 + v["Capex_Overrun"])
    S["BESS_Capex_Base"] = S["BESS_MWh"] * v["kWh_per_MWh"] * v["BESS_Capex_Per_kWh"]
    S["BESS_Capex"] = S["BESS_Capex_Base"] * (1 + v["Capex_Overrun"])
    S["Equipment_Capex"] = S["PV_Capex"] + S["BESS_Capex"]
    S["Dev_Costs"] = v["Owner_Dev_Pct"] * S["Equipment_Capex"]
    S["Project_Capex"] = S["Equipment_Capex"] + S["Dev_Costs"]
    S["ITC_Proceeds"] = (v["ITC_PV"] * S["PV_Capex"] + v["ITC_BESS"] * S["BESS_Capex"]) * v["ITC_Transfer_Price"]

    # ── generation ──────────────────────────────────────────────────────────
    pv_on = (t <= v["PV_Life"]).astype(float)
    bess_on = (t <= v["BESS_Life"]).astype(float)
    deg = (1 - v["Degradation"]) ** (t - 1)
    R["Gen_P50"] = v["PV_MWac"] * v["Hours_Per_Year"] * v["CF_P50"] * (1 - v["Curtailment"]) * deg * pv_on
    S["P90_Factor"] = 1 - v["Z_P90"] * v["Gen_Sigma_1yr"]
    S["P99_Factor"] = 1 - v["Z_P99"] * v["Gen_Sigma_1yr"]
    S["Op_Gen_Factor"] = 1 - v["Gen_Case_Z"] * v["Gen_Sigma_1yr"]
    R["Gen_P90"] = R["Gen_P50"] * S["P90_Factor"]
    R["Gen_Op"] = R["Gen_P50"] * S["Op_Gen_Factor"]

    # ── prices and revenue ──────────────────────────────────────────────────
    ppa_on = (t <= v["PPA_Term"]).astype(float)
    ppa_px = v["PPA_Price"] * (1 + v["PPA_Escalator"]) ** (t - 1)
    merch_px = v["Merchant_Price"] * (1 + v["Merchant_Escalation"]) ** (t - 1)
    R["Price_Base"] = ppa_on * ppa_px + (1 - ppa_on) * merch_px
    R["Price_Op"] = ppa_on * ppa_px + (1 - ppa_on) * merch_px * (1 + v["Merchant_Shock"])
    toll_on = (t <= min(v["Toll_Term"], v["BESS_Life"])).astype(float)
    R["Rev_BESS"] = v["Toll_Price"] * v["BESS_MW"] * v["kW_per_MW"] * v["Months"] * toll_on
    R["Rev_PV_P50"] = R["Gen_P50"] * R["Price_Base"]
    R["Rev_PV_P90"] = R["Gen_P90"] * R["Price_Base"]
    R["Rev_PV_Op"] = R["Gen_Op"] * R["Price_Op"]

    # ── operating costs ─────────────────────────────────────────────────────
    esc = (1 + v["Opex_Escalation"]) ** (t - 1)
    R["Opex_PV"] = v["PV_FOM_Per_kWac"] * v["PV_MWac"] * v["kW_per_MW"] * esc * pv_on
    R["Opex_BESS"] = v["BESS_FOM_Pct"] * S["BESS_Capex_Base"] * esc * bess_on   # O&M scope ignores EPC overruns
    R["Opex_AM"] = v["Asset_Mgmt"] * esc * pv_on
    R["Opex"] = R["Opex_PV"] + R["Opex_BESS"] + R["Opex_AM"]

    # ── CFADS ───────────────────────────────────────────────────────────────
    # In merchant years the owner idles or retires the plant rather than run it at a loss, so
    # cash flow after the PPA is floored at zero. (Contracted years are not floored.)
    def floor(x):
        return np.where(ppa_on > 0, x, np.maximum(x, 0.0))
    R["CFADS_P50"] = floor(R["Rev_PV_P50"] + R["Rev_BESS"] - R["Opex"])
    R["CFADS_P90"] = floor(R["Rev_PV_P90"] + R["Rev_BESS"] - R["Opex"])
    R["CFADS_Op"] = floor(R["Rev_PV_Op"] + R["Rev_BESS"] - R["Opex"])

    # ── sculpting (closed form) ─────────────────────────────────────────────
    rate = v["UST_10Y"] + v["Debt_Spread"] + v["Rate_Shock"]
    S["Rate"] = rate
    tenor_on = (t <= v["Tenor"]).astype(float)
    R["DS_Target"] = np.minimum(R["CFADS_P50"] / v["DSCR_P50_Target"], R["CFADS_P90"] / v["DSCR_P90_Target"]) * tenor_on
    S["Debt_Capacity_Sculpt"] = npv(rate, R["DS_Target"])
    S["Debt_Capacity_Gearing"] = v["Max_Gearing"] * S["Project_Capex"]
    debt = min(S["Debt_Capacity_Sculpt"], S["Debt_Capacity_Gearing"])
    S["Debt"] = debt
    S["Sculpt_Scale"] = debt / S["Debt_Capacity_Sculpt"]
    S["Gearing"] = debt / S["Project_Capex"]
    R["Debt_Service"] = R["DS_Target"] * S["Sculpt_Scale"]
    beg, end, interest = np.zeros(YEARS), np.zeros(YEARS), np.zeros(YEARS)
    bal = debt
    for k in range(YEARS):
        beg[k] = bal
        interest[k] = bal * rate
        bal = bal - (R["Debt_Service"][k] - interest[k])
        end[k] = bal
    R["Beg_Balance"], R["End_Balance"], R["Interest"] = beg, end, interest
    R["Principal"] = R["Debt_Service"] - interest

    # ── sources and uses ────────────────────────────────────────────────────
    S["IDC"] = debt * rate * v["Constr_Years"] * v["Avg_Draw"]
    S["Fees"] = v["Upfront_Fee"] * debt
    S["DSRA"] = v["DSRA_Months"] / v["Months"] * R["Debt_Service"][0]
    S["Total_Uses"] = S["Project_Capex"] + S["IDC"] + S["Fees"] + S["DSRA"]
    S["Equity"] = S["Total_Uses"] - debt - S["ITC_Proceeds"]
    S["Total_Sources"] = debt + S["ITC_Proceeds"] + S["Equity"]

    # ── coverage ratios ─────────────────────────────────────────────────────
    with np.errstate(divide="ignore", invalid="ignore"):
        for case in ("P50", "P90", "Op"):
            R[f"DSCR_{case}"] = np.where(tenor_on > 0, R[f"CFADS_{case}"] / R["Debt_Service"], np.nan)
    ten = tenor_on > 0
    for case in ("P50", "P90", "Op"):
        S[f"Min_DSCR_{case}"] = float(np.min(R[f"DSCR_{case}"][ten]))
        S[f"Avg_DSCR_{case}"] = float(np.mean(R[f"DSCR_{case}"][ten]))
    S["LLCR"] = npv(rate, R["CFADS_P50"] * tenor_on) / debt
    S["PLCR"] = npv(rate, R["CFADS_P50"]) / debt
    S["LLCR_Op"] = npv(rate, R["CFADS_Op"] * tenor_on) / debt
    op = np.where(ten, R["DSCR_Op"], np.inf)
    S["Lockup_Years"] = float((op < v["DSCR_Lockup"]).sum())
    S["Default_Years"] = float((op < v["DSCR_Default_PF"]).sum())
    R["Parity"] = np.minimum(R["CFADS_P50"] / v["DSCR_P50_Target"], R["CFADS_P90"] / v["DSCR_P90_Target"]) * tenor_on \
        - R["Debt_Service"] / S["Sculpt_Scale"]

    # ── returns ─────────────────────────────────────────────────────────────
    release = np.where(t == v["Tenor"], S["DSRA"], 0.0)
    eq = np.concatenate([[-S["Equity"]], R["CFADS_Op"] - R["Debt_Service"] + release])
    proj = np.concatenate([[-S["Project_Capex"] + S["ITC_Proceeds"]], R["CFADS_Op"]])
    r.returns["Equity_CF"], r.returns["Project_CF"] = eq, proj
    S["Equity_IRR"] = irr(eq)
    S["Project_IRR"] = irr(proj)
    S["Equity_Multiple"] = eq[1:].sum() / S["Equity"]
    S["Equity_NPV_At_IRR"] = npv(S["Equity_IRR"], eq[1:]) + eq[0] if np.isfinite(S["Equity_IRR"]) else 0.0

    # ── tax (after-tax view for a sponsor that can use losses as they arise) ─
    macrs = np.zeros(YEARS)
    table = [v[f"MACRS_Y{k}"] for k in range(1, 7)]
    macrs[: len(table)] = table
    S["Dep_Basis"] = S["Project_Capex"] - v["ITC_Basis_Reduction"] * (v["ITC_PV"] * S["PV_Capex"]
                                                                       + v["ITC_BESS"] * S["BESS_Capex"])
    R["Depreciation"] = S["Dep_Basis"] * macrs
    R["Taxable_Income"] = R["CFADS_Op"] - R["Interest"] - R["Depreciation"]
    R["Tax"] = v["Tax_Rate"] * R["Taxable_Income"]
    eq_at = eq.copy()
    eq_at[1:] -= R["Tax"]
    proj_at = proj.copy()
    proj_at[1:] -= v["Tax_Rate"] * (R["CFADS_Op"] - R["Depreciation"])
    r.returns["Equity_CF_AT"], r.returns["Project_CF_AT"] = eq_at, proj_at
    S["Equity_IRR_AT"] = irr(eq_at)
    S["Project_IRR_AT"] = irr(proj_at)
    S["Equity_NPV_At_IRR_AT"] = (npv(S["Equity_IRR_AT"], eq_at[1:]) + eq_at[0]
                                 if np.isfinite(S["Equity_IRR_AT"]) else 0.0)

    # ── output and emissions ────────────────────────────────────────────────
    S["Gen_Y1_P50"] = R["Gen_P50"][0]
    S["Net_CF_Y1"] = R["Gen_P50"][0] / (v["PV_MWac"] * v["Hours_Per_Year"])
    S["tCO2e_Avoided_Y1"] = R["Gen_P50"][0] * v["Grid_CO2e_lb_MWh"] / v["lb_per_t"]
    S["tCO2e_Avoided_Life"] = R["Gen_P50"].sum() * v["Grid_CO2e_lb_MWh"] / v["lb_per_t"]
    S["Capex_Per_tCO2e"] = S["Project_Capex"] / S["tCO2e_Avoided_Life"]
    return r
