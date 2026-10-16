"""Property engine: a 150-unit multifamily acquisition with and without a decarbonization retrofit.

This is the reference implementation. The Excel workbook (cau/xlsx/property_book.py) computes the
same quantities with live formulas, and the tests require the two to agree.

Conventions shared with the workbook:
* annual periods, years 1..11 (year 11 only supplies the forward NOI for the exit value);
* two cases on one rent roll: status quo (SQ) keeps the gas boilers and replaces them in
  ``Boiler_Replace_Year``; retrofit (RF) electrifies heat and hot water at closing, adds envelope
  work, LEDs and rooftop solar, funded with equity;
* the loan is sized on the status-quo year-1 cash flow (a lender does not lend on projected savings)
  and is the same in both cases;
* DSCR is on net cash flow after reserves; debt yield is NOI over the opening loan balance.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from cau.engine.finance import amortize, npv, pmt
from cau.engine.finance import irr_or_nan as irr

YEARS = 11


@dataclass
class PropertyResult:
    inputs: dict
    rows: dict = field(default_factory=dict)     # per-year arrays, index 0 = year 1
    scalars: dict = field(default_factory=dict)  # single values
    returns: dict = field(default_factory=dict)  # year-0..11 cash flow arrays


def run(v: dict) -> PropertyResult:
    r = PropertyResult(inputs=dict(v))
    R, S = r.rows, r.scalars
    t = np.arange(1, YEARS + 1, dtype=float)

    # ── rent roll ───────────────────────────────────────────────────────────
    types = ("Studio", "1BR", "2BR", "3BR")
    units = sum(v[f"Units_{k}"] for k in types)
    S["Units"] = units
    S["NRSF"] = sum(v[f"Units_{k}"] * v[f"SF_{k}"] for k in types)
    S["GPR_Y1"] = sum(v[f"Units_{k}"] * v[f"Rent_{k}"] for k in types) * v["Months"]

    # ── energy (annual quantities, held flat) ───────────────────────────────
    site = v["GFA"] * v["Site_EUI_Base"] / v["kBtu_per_MMBtu"]
    gas_heat = site * v["Share_Heat_Gas"]
    gas_dhw = site * v["Share_DHW_Gas"]
    common_kwh = site * v["Share_Common_Elec"] * v["kWh_per_MMBtu"]
    tenant_kwh = site * v["Share_Tenant_Elec"] * v["kWh_per_MMBtu"]
    electrified = 1 - v["Gas_Retained_Share"]
    hp_heat_kwh = (gas_heat * electrified * v["Boiler_Eff"] * (1 - v["Envelope_Heat_Reduction"]) / v["COP_Heat"]
                   * v["kWh_per_MMBtu"])
    hp_dhw_kwh = gas_dhw * electrified * v["Boiler_Eff"] / v["COP_DHW"] * v["kWh_per_MMBtu"]
    gas_rf = (gas_heat + gas_dhw) * v["Gas_Retained_Share"]
    common_rf = common_kwh * (1 - v["LED_Savings"])
    owner_gross_rf = common_rf + hp_heat_kwh + hp_dhw_kwh
    solar_kwh = v["Solar_kWdc"] * v["Solar_Yield"]
    grid_rf = owner_gross_rf - solar_kwh
    S.update(Site_MMBtu_Base=site, Gas_Heat_MMBtu=gas_heat, Gas_DHW_MMBtu=gas_dhw, Gas_SQ_MMBtu=gas_heat + gas_dhw,
             Common_kWh=common_kwh, Tenant_kWh=tenant_kwh, HP_Heat_kWh=hp_heat_kwh, HP_DHW_kWh=hp_dhw_kwh,
             Common_RF_kWh=common_rf, Owner_Gross_RF_kWh=owner_gross_rf, Solar_kWh=solar_kwh, Grid_RF_kWh=grid_rf,
             Gas_RF_MMBtu=gas_rf)
    gas_price = v["Gas_Price_Mcf"] / v["Gas_MMBtu_Per_Mcf"]
    S["Gas_Price_MMBtu"] = gas_price

    # ── operating statement ─────────────────────────────────────────────────
    rent_idx = (1 + v["Rent_Growth"]) ** (t - 1)
    oi_idx = (1 + v["Other_Income_Growth"]) ** (t - 1)
    exp_idx = (1 + v["Expense_Growth"]) ** (t - 1)
    tax_idx = (1 + v["Tax_Growth"]) ** (t - 1)
    util_idx = (1 + v["Utility_Price_Growth"]) ** (t - 1)
    R["GPR"] = S["GPR_Y1"] * rent_idx
    R["Vacancy"] = -R["GPR"] * v["Vacancy_Rate"]
    R["Other_Income"] = v["Other_Income_Per_Unit"] * units * oi_idx
    R["EGI"] = R["GPR"] + R["Vacancy"] + R["Other_Income"]
    R["Taxes"] = v["Assessed_Value_Per_Unit"] * units * v["Tax_Rate"] * tax_idx
    R["Insurance"] = v["Insurance_Per_Unit"] * units * exp_idx
    R["Water_Sewer"] = v["Water_Sewer_Per_Unit"] * units * exp_idx
    R["Repairs"] = v["Repairs_Per_Unit"] * units * exp_idx
    R["Payroll"] = v["Payroll_Per_Unit"] * units * exp_idx
    R["Admin"] = v["Admin_Per_Unit"] * units * exp_idx
    R["Mgmt_Fee"] = v["Mgmt_Fee_Pct"] * R["EGI"]
    R["Gas_Cost_SQ"] = S["Gas_SQ_MMBtu"] * gas_price * util_idx
    R["Elec_Cost_SQ"] = common_kwh * v["Elec_Price"] * util_idx
    R["Gas_Cost_RF"] = gas_rf * gas_price * util_idx
    R["Elec_Cost_RF"] = grid_rf * v["Elec_Price"] * util_idx
    common = R["Taxes"] + R["Insurance"] + R["Water_Sewer"] + R["Repairs"] + R["Payroll"] + R["Admin"] + R["Mgmt_Fee"]
    R["Opex_SQ"] = common + R["Gas_Cost_SQ"] + R["Elec_Cost_SQ"]
    R["Opex_RF"] = common + R["Gas_Cost_RF"] + R["Elec_Cost_RF"]
    R["NOI_SQ"] = R["EGI"] - R["Opex_SQ"]
    R["NOI_RF"] = R["EGI"] - R["Opex_RF"]
    R["Reserves"] = v["Reserve_Per_Unit"] * units * exp_idx
    R["NCF_SQ"] = R["NOI_SQ"] - R["Reserves"]
    R["NCF_RF"] = R["NOI_RF"] - R["Reserves"]
    R["Boiler_Capex_SQ"] = np.where(t == v["Boiler_Replace_Year"], v["Boiler_Replace_Cost"] * exp_idx, 0.0)

    # ── retrofit capex ──────────────────────────────────────────────────────
    S["HP_Capex"] = v["HP_Capex_Per_Unit"] * units
    S["Envelope_Capex"] = v["Envelope_Capex_Per_SF"] * v["GFA"]
    S["LED_Capex"] = v["LED_Capex_Per_Unit"] * units
    S["Solar_Capex"] = v["Solar_kWdc"] * v["Solar_Capex_Per_W"] * v["W_per_kW"]
    S["Solar_ITC_Amt"] = v["Solar_ITC"] * S["Solar_Capex"]
    S["Retrofit_Gross"] = S["HP_Capex"] + S["Envelope_Capex"] + S["LED_Capex"] + S["Solar_Capex"]
    S["Retrofit_Net"] = S["Retrofit_Gross"] - S["Solar_ITC_Amt"]

    # ── debt ────────────────────────────────────────────────────────────────
    fixed = v["UST_10Y"] + v["Fixed_Spread"]
    floating = np.full(YEARS, v["SOFR"] + v["SOFR_Shock"] + v["Float_Spread"])
    rate = np.full(YEARS, fixed) if v["Debt_Option"] == 1 else floating
    R["Rate"] = rate
    S["Debt_Constant"] = pmt(rate[0] / v["Months"], v["Amort_Months"], -1) * v["Months"]
    S["Max_Loan_LTV"] = v["LTV_Max"] * v["Price"]
    S["Max_Loan_DSCR"] = R["NCF_SQ"][0] / (v["DSCR_Sizing"] * S["Debt_Constant"])
    S["Max_Loan_DY"] = R["NOI_SQ"][0] / v["DY_Sizing"]
    sized = min(S["Max_Loan_LTV"], S["Max_Loan_DSCR"], S["Max_Loan_DY"])
    loan = v["Loan_Override"] if v["Loan_Override"] > 0 else sized
    S["Loan"] = loan
    S["LTV"] = loan / v["Price"]
    sched = amortize(loan, rate, v["Amort_Months"], v["IO_Years"], v["Months"])
    for k in ("Beg_Balance", "End_Balance", "Debt_Service", "Principal", "Interest"):
        R[k] = sched[k]

    # ── covenants ───────────────────────────────────────────────────────────
    for case in ("SQ", "RF"):
        dscr = R[f"NCF_{case}"] / R["Debt_Service"]
        dy = R[f"NOI_{case}"] / R["Beg_Balance"]
        R[f"DSCR_{case}"], R[f"DY_{case}"] = dscr, dy
        R[f"DSCR_Headroom_{case}"] = 1 - v["DSCR_Trap"] / dscr
        R[f"DY_Headroom_{case}"] = 1 - v["DY_Trap"] / dy
        R[f"DSCR_Flag_{case}"] = np.where(dscr < v["DSCR_Default"], "BREACH",
                                          np.where(dscr < v["DSCR_Trap"], "CASH TRAP", "OK"))
        R[f"DY_Flag_{case}"] = np.where(dy < v["DY_Default"], "BREACH", np.where(dy < v["DY_Trap"], "CASH TRAP", "OK"))
        hold = t <= v["Hold_Years"]
        S[f"Min_DSCR_{case}"] = float(dscr[hold].min())
        S[f"Min_DY_{case}"] = float(dy[hold].min())
        S[f"Trap_Years_{case}"] = float(sum((R[f"{m}_Flag_{case}"][hold] != "OK").sum() for m in ("DSCR", "DY")))

    # ── returns (year 0..11) ────────────────────────────────────────────────
    H = int(v["Hold_Years"])
    in_hold = (t <= H).astype(float)
    exit_ = (t == H).astype(float)
    S["Closing_Costs"] = v["Closing_Cost_Pct"] * v["Price"]
    S["Loan_Fees"] = v["Loan_Fee_Pct"] * loan
    for case in ("SQ", "RF"):
        noi_fwd = R[f"NOI_{case}"][H]          # year H+1
        gross = noi_fwd / v["Exit_Cap"]
        net_sale = gross - v["Sale_Cost_Pct"] * gross
        S[f"Exit_Value_{case}"], S[f"Net_Sale_{case}"] = gross, net_sale
        retro = S["Retrofit_Net"] if case == "RF" else 0.0
        boiler = R["Boiler_Capex_SQ"] if case == "SQ" else np.zeros(YEARS)
        uses = v["Price"] + S["Closing_Costs"] + S["Loan_Fees"] + retro
        S[f"Uses_{case}"] = uses
        S[f"Equity_{case}"] = uses - loan
        unlev = np.concatenate([[-(v["Price"] + S["Closing_Costs"] + retro)],
                                in_hold * (R[f"NCF_{case}"] - boiler) + exit_ * net_sale])
        lev = unlev.copy()
        lev[0] += loan - S["Loan_Fees"]
        lev[1:] -= in_hold * R["Debt_Service"] + exit_ * R["End_Balance"]
        r.returns[f"Unlev_CF_{case}"], r.returns[f"Lev_CF_{case}"] = unlev, lev
        S[f"Unlev_IRR_{case}"] = irr(unlev)
        S[f"Lev_IRR_{case}"] = irr(lev)
        S[f"Equity_Multiple_{case}"] = lev[1:].sum() / -lev[0]
        S[f"Lev_NPV_At_IRR_{case}"] = (npv(S[f"Lev_IRR_{case}"], lev[1:]) + lev[0]
                                       if np.isfinite(S[f"Lev_IRR_{case}"]) else 0.0)
    S["Going_In_Cap"] = R["NOI_SQ"][0] / v["Price"]
    S["Price_Per_Unit"] = v["Price"] / units

    # ── retrofit KPIs ───────────────────────────────────────────────────────
    sav = R["Gas_Cost_SQ"][0] + R["Elec_Cost_SQ"][0] - R["Gas_Cost_RF"][0] - R["Elec_Cost_RF"][0]
    S["Utility_Savings_Y1"] = sav
    S["Payback_Years"] = S["Retrofit_Net"] / sav
    S["Payback_Net_Boiler_Years"] = (S["Retrofit_Net"] - v["Boiler_Replace_Cost"]) / sav
    S["Exit_Value_Uplift"] = S["Exit_Value_RF"] - S["Exit_Value_SQ"]
    to_kbtu = v["kBtu_per_MMBtu"] / v["kWh_per_MMBtu"]          # kBtu per kWh
    S["EUI_Base"] = v["Site_EUI_Base"]
    S["EUI_RF"] = (tenant_kwh + owner_gross_rf) * to_kbtu / v["GFA"]
    S["EUI_RF_Net_Solar"] = (tenant_kwh + grid_rf) * to_kbtu / v["GFA"]
    S["EUI_Reduction"] = 1 - S["EUI_RF"] / S["EUI_Base"]
    S["BEPS_Met"] = S["EUI_Reduction"] >= v["BEPS_EUI_Cut"]
    S["BEPS_Max_Penalty"] = min(v["BEPS_Penalty_Per_SF"] * v["GFA"], v["BEPS_Penalty_Cap"])
    ng_t = (v["NG_CO2_kg_MMBtu"] + (v["NG_CH4_g_MMBtu"] * v["GWP_CH4"] + v["NG_N2O_g_MMBtu"] * v["GWP_N2O"])
            / v["g_per_kg"]) / v["kg_per_t"]
    grid_t = v["Grid_CO2e_lb_MWh"] / v["kWh_per_MWh"] / v["lb_per_t"]
    S["NG_tCO2e_MMBtu"], S["Grid_tCO2e_kWh"] = ng_t, grid_t
    S["Scope1_SQ"] = S["Gas_SQ_MMBtu"] * ng_t
    S["Scope2_SQ"] = common_kwh * grid_t
    S["Scope1_RF"] = gas_rf * ng_t
    S["Scope2_RF"] = grid_rf * grid_t
    S["Tenant_tCO2e"] = tenant_kwh * grid_t
    S["Owner_tCO2e_SQ"] = S["Scope1_SQ"] + S["Scope2_SQ"]
    S["Owner_tCO2e_RF"] = S["Scope1_RF"] + S["Scope2_RF"]
    S["tCO2e_Avoided"] = S["Owner_tCO2e_SQ"] - S["Owner_tCO2e_RF"]
    S["Cost_Per_tCO2e"] = S["Retrofit_Net"] / (S["tCO2e_Avoided"] * v["Measure_Life"])
    return r
