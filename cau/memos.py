"""Render the two memos from templates so every figure in them comes from the models.

memos/templates/<name>.md holds the prose with ``{placeholders}``; ``facts()`` fills them from the
engines, the stress tables, the inputs and the source register. tests/test_memos.py requires the
committed memos to equal a fresh render and the templates to contain no typed numbers.

    python -m cau.memos            # rewrite memos/*.md
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from cau.engine import property as P
from cau.engine import solar_storage as SS
from cau.engine import stress as ST
from cau.inputs import fingerprint, load_inputs, load_sources, values

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "memos" / "templates"
MEMOS = ("property_investment_memo", "solar_storage_credit_memo")


# ── formatting ──────────────────────────────────────────────────────────────

def m(x: float, d: int = 1) -> str:
    """$ millions."""
    return f"${x / 1e6:,.{d}f}m"


def usd(x: float) -> str:
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


def pct(x: float, d: int = 1) -> str:
    return "n/m" if not np.isfinite(x) else f"{x * 100:.{d}f}%"


def bp(x: float) -> str:
    return f"{x * 1e4:.0f} bp"


def xx(x: float) -> str:
    return f"{x:.2f}x"


def num(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}"


FMT = {"usd": m, "x": xx, "pct": pct, "int": lambda v: num(v), "yrs": lambda v: f"{v:.1f} yrs", "num1": lambda v: num(v, 1)}


def md_table(header: list[str], rows: list[list[str]], align: str | None = None) -> str:
    align = align or "l" + "r" * (len(header) - 1)
    sep = ["---:" if a == "r" else "---" for a in align]
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def case_table(model: str, keys: list[str] | None = None) -> str:
    t = ST.case_table(model)
    keys = keys or list(t.index)
    rows = [[t.loc[k, "metric"], *[FMT[t.loc[k, "kind"]](t.loc[k, c]) for c in ST.CASES]] for k in keys]
    return md_table(["", *ST.CASES], rows)


def stress_definition_table(model: str, levers: list[tuple[str, str, callable]]) -> str:
    base = ST.base_values(model)
    rows = []
    for key, label, f in levers:
        vals = [ST.spec()[model]["cases"][c].get(key, base[key]) for c in ST.CASES]
        rows.append([label, *[f(v) for v in vals]])
    return md_table(["Assumption", *ST.CASES], rows)


def sensitivity_lines(model: str, metric: str, f, n: int = 3, delta=None) -> str:
    """The ``n`` most adverse one-factor levers. ``delta`` formats the change (bp for rates)."""
    delta = delta or f
    s = ST.sensitivities(model, metric).head(n)
    return "\n".join(f"- {r.lever}: {f(r.value)} ({'+' if r.change >= 0 else '-'}{delta(abs(r.change))} from base)"
                      for r in s.itertuples())


# ── facts ───────────────────────────────────────────────────────────────────

def property_facts() -> dict:
    v = values(load_inputs("property"))
    r = P.run(v)
    S, R = r.scalars, r.rows
    src = load_sources()
    hud = src["hud_safmr_fy2026"]["data"]
    be = ST.breakeven_vacancy()
    t = ST.case_table("property")
    f = {
        "units": num(S["Units"]), "gfa": num(v["GFA"]), "nrsf": num(S["NRSF"]), "price": m(v["Price"]),
        "price_unit": usd(S["Price_Per_Unit"]), "going_in_cap": pct(S["Going_In_Cap"], 2),
        "rent_studio": usd(v["Rent_Studio"]), "rent_1br": usd(v["Rent_1BR"]), "rent_2br": usd(v["Rent_2BR"]),
        "rent_3br": usd(v["Rent_3BR"]), "hud_2br_low": usd(hud["two_bed_low"]), "hud_2br_high": usd(hud["two_bed_high"]),
        "hud_fy": str(hud["fiscal_year"]),
        "gpr_y1": m(S["GPR_Y1"], 2), "vacancy": pct(v["Vacancy_Rate"]), "egi_y1": m(R["EGI"][0], 2),
        "opex_y1": m(R["Opex_SQ"][0], 2), "opex_ratio": pct(R["Opex_SQ"][0] / R["EGI"][0]),
        "noi_y1": m(R["NOI_SQ"][0], 2), "ncf_y1": m(R["NCF_SQ"][0], 2), "reserves": usd(v["Reserve_Per_Unit"]),
        "tax_rate": pct(v["Tax_Rate"], 2), "rent_growth": pct(v["Rent_Growth"]), "exp_growth": pct(v["Expense_Growth"]),
        "loan": m(S["Loan"]), "ltv": pct(S["LTV"]), "rate_fixed": pct(v["UST_10Y"] + v["Fixed_Spread"], 2),
        "ust": pct(v["UST_10Y"], 2), "fixed_spread": bp(v["Fixed_Spread"]), "sofr": pct(v["SOFR"], 2),
        "float_spread": bp(v["Float_Spread"]), "io_years": num(v["IO_Years"]), "amort_years": num(v["Amort_Months"] / v["Months"]),
        "max_ltv_loan": m(S["Max_Loan_LTV"]), "max_dscr_loan": m(S["Max_Loan_DSCR"]), "max_dy_loan": m(S["Max_Loan_DY"]),
        "ltv_max": pct(v["LTV_Max"], 0), "dscr_sizing": xx(v["DSCR_Sizing"]), "dy_sizing": pct(v["DY_Sizing"]),
        "debt_constant": pct(S["Debt_Constant"], 2),
        "min_dscr_sq": xx(S["Min_DSCR_SQ"]), "min_dscr_rf": xx(S["Min_DSCR_RF"]), "min_dy_sq": pct(S["Min_DY_SQ"]),
        "dscr_trap": xx(v["DSCR_Trap"]), "dscr_default": xx(v["DSCR_Default"]), "dy_trap": pct(v["DY_Trap"]),
        "dy_default": pct(v["DY_Default"]), "dscr_headroom_y1": pct(R["DSCR_Headroom_SQ"][0]),
        "equity_sq": m(S["Equity_SQ"]), "equity_rf": m(S["Equity_RF"]), "hold": num(v["Hold_Years"]),
        "exit_cap": pct(v["Exit_Cap"], 2), "exit_sq": m(S["Exit_Value_SQ"]), "exit_rf": m(S["Exit_Value_RF"]),
        "unlev_sq": pct(S["Unlev_IRR_SQ"]), "unlev_rf": pct(S["Unlev_IRR_RF"]), "lev_sq": pct(S["Lev_IRR_SQ"]),
        "lev_rf": pct(S["Lev_IRR_RF"]), "em_sq": xx(S["Equity_Multiple_SQ"]), "em_rf": xx(S["Equity_Multiple_RF"]),
        "irr_delta": bp(abs(S["Lev_IRR_RF"] - S["Lev_IRR_SQ"])),
        "hp_capex": m(S["HP_Capex"], 2), "hp_unit": usd(v["HP_Capex_Per_Unit"]), "env_capex": m(S["Envelope_Capex"], 2),
        "led_capex": m(S["LED_Capex"], 2), "solar_capex": m(S["Solar_Capex"], 2), "solar_itc": m(S["Solar_ITC_Amt"], 2),
        "retro_gross": m(S["Retrofit_Gross"], 2), "retro_net": m(S["Retrofit_Net"], 2),
        "solar_kw": num(v["Solar_kWdc"]), "solar_mwh": num(S["Solar_kWh"] / 1e3), "solar_yield": num(v["Solar_Yield"], 1),
        "cop_heat": num(v["COP_Heat"], 1), "cop_dhw": num(v["COP_DHW"], 1), "boiler_eff": pct(v["Boiler_Eff"], 0),
        "elec_price": f"${v['Elec_Price']:.4f}/kWh", "gas_price": f"${v['Gas_Price_Mcf']:.2f}/Mcf",
        "savings_y1": usd(S["Utility_Savings_Y1"]), "payback": num(S["Payback_Years"], 1),
        "payback_boiler": num(S["Payback_Net_Boiler_Years"], 1), "boiler_cost": usd(v["Boiler_Replace_Cost"]),
        "boiler_year": num(v["Boiler_Replace_Year"]), "exit_uplift": m(S["Exit_Value_Uplift"], 2),
        "eui_base": num(S["EUI_Base"], 1), "eui_rf": num(S["EUI_RF"], 1), "eui_net": num(S["EUI_RF_Net_Solar"], 1),
        "eui_cut": pct(S["EUI_Reduction"]), "beps_cut": pct(v["BEPS_EUI_Cut"], 0),
        "beps_met": "meets" if S["BEPS_Met"] else "does not meet", "beps_penalty": m(S["BEPS_Max_Penalty"], 2),
        "beps_per_sf": usd(v["BEPS_Penalty_Per_SF"]),
        "owner_t_sq": num(S["Owner_tCO2e_SQ"]), "owner_t_rf": num(S["Owner_tCO2e_RF"]), "t_avoided": num(S["tCO2e_Avoided"]),
        "t_avoided_pct": pct(S["tCO2e_Avoided"] / S["Owner_tCO2e_SQ"], 0), "tenant_t": num(S["Tenant_tCO2e"]),
        "scope1_sq": num(S["Scope1_SQ"]), "scope2_sq": num(S["Scope2_SQ"]), "scope2_rf": num(S["Scope2_RF"]),
        "cost_per_t": usd(S["Cost_Per_tCO2e"]), "measure_life": num(v["Measure_Life"]),
        "grid_rate": num(v["Grid_CO2e_lb_MWh"], 1),
        "be_vacancy": pct(be["vacancy"]), "trap_years_severe": num(t.loc["Trap_Years_SQ", "Severe"]),
        "severe_min_dscr": xx(t.loc["Min_DSCR_SQ", "Severe"]),
        "severe_vs_default": "below" if t.loc["Min_DSCR_SQ", "Severe"] < v["DSCR_Default"] else "above",
    }
    # year-one utility savings by measure (the pieces add up to the total)
    price_e, price_g = v["Elec_Price"], S["Gas_Price_MMBtu"]
    hp_no_env = S["Gas_Heat_MMBtu"] * (1 - v["Gas_Retained_Share"]) * v["Boiler_Eff"] / v["COP_Heat"] * v["kWh_per_MMBtu"]
    parts = {"solar": S["Solar_kWh"] * price_e,
             "led": (S["Common_kWh"] - S["Common_RF_kWh"]) * price_e,
             "envelope": (hp_no_env - S["HP_Heat_kWh"]) * price_e,
             "electrification": (S["Gas_SQ_MMBtu"] - S["Gas_RF_MMBtu"]) * price_g - (hp_no_env + S["HP_DHW_kWh"]) * price_e}
    assert abs(sum(parts.values()) - S["Utility_Savings_Y1"]) < 1e-6, "savings decomposition does not add up"
    f.update({f"save_{k}": usd(x) for k, x in parts.items()})
    f["electrification_sign"] = "saves" if parts["electrification"] >= 0 else "adds"
    f["electrification_abs"] = usd(abs(parts["electrification"]))
    f["stress_definition"] = stress_definition_table("property", [
        ("Vacancy_Rate", "Vacancy and credit loss", pct), ("Rent_Growth", "Rent growth", pct),
        ("Expense_Growth", "Expense growth", pct), ("Utility_Price_Growth", "Utility price growth", pct),
        ("Exit_Cap", "Exit cap rate", lambda x: pct(x, 2)), ("HP_Capex_Per_Unit", "Heat pump cost per unit", usd),
        ("COP_Heat", "Heat pump COP (heating)", lambda x: num(x, 1))])
    f["stress_table"] = case_table("property", ["Min_DSCR_SQ", "Min_DSCR_RF", "Min_DY_SQ", "Trap_Years_SQ",
                                                "Lev_IRR_SQ", "Lev_IRR_RF", "Equity_Multiple_RF", "Exit_Value_RF",
                                                "Payback_Years"])
    f["sens_irr"] = sensitivity_lines("property", "Lev_IRR_RF", pct, delta=bp)
    top = ST.sensitivities("property", "Lev_IRR_RF").iloc[0]
    f["top_lever"], f["top_lever_bp"] = top["lever"].lower(), bp(abs(top["change"]))
    f["sources_table"] = _sources_table("property")
    f["returns_table"] = md_table(["", "Status quo", "Retrofit"], [
        ["Equity", f["equity_sq"], f["equity_rf"]], ["Unlevered IRR", f["unlev_sq"], f["unlev_rf"]],
        ["Levered IRR", f["lev_sq"], f["lev_rf"]], ["Equity multiple", f["em_sq"], f["em_rf"]],
        ["Gross exit value", f["exit_sq"], f["exit_rf"]], ["Minimum DSCR", f["min_dscr_sq"], f["min_dscr_rf"]]])
    f["retrofit_table"] = md_table(["Measure", "Cost"], [
        [f"Central air-to-water heat pumps, heat and hot water ({f['hp_unit']}/unit)", f["hp_capex"]],
        ["Envelope and air sealing", f["env_capex"]], ["Common-area LEDs and controls", f["led_capex"]],
        [f"Rooftop solar, {f['solar_kw']} kWdc", f["solar_capex"]], ["Less: solar tax credit", f"({f['solar_itc']})"],
        ["Net retrofit capex", f["retro_net"]]])
    f["energy_table"] = md_table(["", "Status quo", "Retrofit"], [
        ["Site EUI (kBtu/sf)", f["eui_base"], f["eui_rf"]],
        ["Owner Scope 1 (tCO2e/yr)", f["scope1_sq"], num(S["Scope1_RF"])],
        ["Owner Scope 2 (tCO2e/yr)", f["scope2_sq"], f["scope2_rf"]],
        ["Owner Scope 1 + 2 (tCO2e/yr)", f["owner_t_sq"], f["owner_t_rf"]],
        ["Tenant electricity, Scope 3 (tCO2e/yr)", f["tenant_t"], f["tenant_t"]]])
    return f


def solar_facts() -> dict:
    v = values(load_inputs("solar_storage"))
    r = SS.run(v)
    S, R = r.scalars, r.rows
    lb = load_sources()["lbnl_uss_2025"]["data"]
    be = ST.breakeven_generation()
    t = ST.case_table("solar_storage")
    ten = int(v["Tenor"])
    life = int(v["BESS_Life"])
    f = {
        "pv_mwac": num(v["PV_MWac"]), "pv_mwdc": num(S["PV_MWdc"]), "ilr": num(v["ILR"], 2), "bess_mw": num(v["BESS_MW"]),
        "bess_mwh": num(S["BESS_MWh"]), "bess_hours": num(v["BESS_Hours"]),
        "pv_capex_w": f"${v['PV_Capex_Per_Wac']:.2f}/Wac", "pv_capex": m(S["PV_Capex"]),
        "bess_capex_kwh": f"${v['BESS_Capex_Per_kWh']:.0f}/kWh", "bess_capex": m(S["BESS_Capex"]),
        "dev_pct": pct(v["Owner_Dev_Pct"], 0), "dev": m(S["Dev_Costs"]), "project_capex": m(S["Project_Capex"]),
        "idc": m(S["IDC"]), "fees": m(S["Fees"]), "dsra": m(S["DSRA"]), "dsra_months": num(v["DSRA_Months"]),
        "uses": m(S["Total_Uses"]), "debt": m(S["Debt"]), "itc": m(S["ITC_Proceeds"]), "equity": m(S["Equity"]),
        "debt_share": pct(S["Debt"] / S["Total_Uses"]), "itc_share": pct(S["ITC_Proceeds"] / S["Total_Uses"]),
        "equity_share": pct(S["Equity"] / S["Total_Uses"]), "gearing": pct(S["Gearing"]),
        "max_gearing": pct(v["Max_Gearing"], 0), "itc_rate": pct(v["ITC_PV"], 0), "itc_price": f"{v['ITC_Transfer_Price']:.2f}",
        "cf": pct(v["CF_P50"]), "curtailment": pct(v["Curtailment"]), "net_cf": pct(S["Net_CF_Y1"]),
        "gen_y1": num(S["Gen_Y1_P50"] / 1e3), "degradation": pct(v["Degradation"]), "sigma": pct(v["Gen_Sigma_1yr"], 0),
        "p90_factor": pct(S["P90_Factor"]), "p99_factor": pct(S["P99_Factor"]),
        "ppa": f"${v['PPA_Price']:.2f}/MWh", "ppa_term": num(v["PPA_Term"]), "hurdle": pct(v["Equity_Hurdle"], 0),
        "lbnl_avg": f"${lb['ppa_avg']}/MWh", "lbnl_low": f"${lb['ppa_iqr_low']}", "lbnl_high": f"${lb['ppa_iqr_high']}/MWh",
        "lbnl_year": str(lb["year"]), "ppa_premium": pct(v["PPA_Price"] / lb["ppa_iqr_high"] - 1, 0),
        "ercot_lcoe": f"${lb['ercot_lcoe_after_credit']}/MWh", "merchant": f"${v['Merchant_Price']:.0f}/MWh",
        "flat_block": f"${lb['ercot_flat_block']}/MWh", "toll": f"${v['Toll_Price']:.0f}/kW-month",
        "toll_term": num(v["Toll_Term"]), "bess_life": num(life), "toll_rev": m(R["Rev_BESS"][0], 1),
        "pv_rev_y1": m(R["Rev_PV_P50"][0], 1), "opex_y1": m(R["Opex"][0], 1), "cfads_y1": m(R["CFADS_P50"][0], 1),
        "bess_share": pct(R["Rev_BESS"][0] / (R["Rev_BESS"][0] + R["Rev_PV_P50"][0]), 0),
        "rate": pct(S["Rate"], 2), "ust": pct(v["UST_10Y"], 2), "spread": bp(v["Debt_Spread"]), "tenor": num(ten),
        "t50": xx(v["DSCR_P50_Target"]), "t90": xx(v["DSCR_P90_Target"]),
        "min_dscr_p50": xx(S["Min_DSCR_P50"]), "min_dscr_p90": xx(S["Min_DSCR_P90"]), "avg_dscr_p90": xx(S["Avg_DSCR_P90"]),
        "llcr": xx(S["LLCR"]), "plcr": xx(S["PLCR"]), "ds_y1": m(R["Debt_Service"][0], 1),
        "ds_before": m(R["Debt_Service"][life - 1], 1), "ds_after": m(R["Debt_Service"][life], 1),
        "lockup": xx(v["DSCR_Lockup"]), "default": xx(v["DSCR_Default_PF"]),
        "proj_irr": pct(S["Project_IRR"]), "proj_irr_at": pct(S["Project_IRR_AT"]), "eq_irr": pct(S["Equity_IRR"]),
        "eq_irr_at": pct(S["Equity_IRR_AT"]), "be_share": pct(be["share_of_p50"]), "be_exceed": pct(be["exceedance"], 2),
        "be_return": num(1 / (1 - be["exceedance"]), 0),
        "t_y1": num(S["tCO2e_Avoided_Y1"]), "t_life": num(S["tCO2e_Avoided_Life"] / 1e6, 2),
        "capex_per_t": usd(S["Capex_Per_tCO2e"]), "grid_rate": num(v["Grid_CO2e_lb_MWh"], 1),
        "severe_min": xx(t.loc["Min_DSCR_Op", "Severe"]), "severe_lockup": num(t.loc["Lockup_Years", "Severe"]),
        "severe_default": num(t.loc["Default_Years", "Severe"]), "down_min": xx(t.loc["Min_DSCR_Op", "Downside"]),
        "severe_eq": pct(t.loc["Equity_IRR_AT", "Severe"]), "down_eq": pct(t.loc["Equity_IRR_AT", "Downside"]),
        "severe_debt": m(t.loc["Debt", "Severe"]),
        "gearing_clause": "the cap does not bind" if S["Sculpt_Scale"] >= 1 else "the cap binds and service is scaled down",
        "p99_clause": (f"P99 output still covers debt service above the {xx(v['DSCR_Default_PF'])} default trigger"
                       if t.loc["Min_DSCR_Op", "Severe"] >= v["DSCR_Default_PF"]
                       else f"P99 output takes coverage below the {xx(v['DSCR_Default_PF'])} default trigger"),
        "itc_price_usd": f"${v['ITC_Transfer_Price']:.2f}",
    }
    low = SS.run(dict(v, PPA_Price=lb["ppa_iqr_high"]))
    f.update({"low_ppa": f"${lb['ppa_iqr_high']:.2f}/MWh", "low_debt": m(low.scalars["Debt"]),
              "low_debt_cut": m(S["Debt"] - low.scalars["Debt"]), "low_eq_irr": pct(low.scalars["Equity_IRR_AT"]),
              "low_equity": m(low.scalars["Equity"])})
    f["su_table"] = md_table(["Uses", "", "Sources", ""], [
        ["Solar (" + f["pv_capex_w"] + ")", f["pv_capex"], "Senior debt", f"{f['debt']} ({f['debt_share']})"],
        ["Battery (" + f["bess_capex_kwh"] + ")", f["bess_capex"], "Tax-credit transfer", f"{f['itc']} ({f['itc_share']})"],
        ["Development, owner, interconnection", f["dev"], "Sponsor equity", f"{f['equity']} ({f['equity_share']})"],
        ["Interest during construction", f["idc"], "", ""], ["Financing fees", f["fees"], "", ""],
        [f"Debt service reserve ({f['dsra_months']} months)", f["dsra"], "", ""],
        ["**Total uses**", f"**{f['uses']}**", "**Total sources**", f"**{f['uses']}**"]], "lrlr")
    f["stress_definition"] = stress_definition_table("solar_storage", [
        ("Gen_Case_Z", "Output, every year", lambda z: {0: "P50", v["Z_P90"]: "P90 (one-year)",
                                                         v["Z_P99"]: "P99 (one-year)"}.get(z, num(z, 2))),
        ("Merchant_Shock", "Merchant tail price", lambda x: "base" if x == 0 else pct(x, 0)),
        ("Capex_Overrun", "EPC overrun (equity-funded)", lambda x: "none" if x == 0 else "+" + pct(x, 0)),
        ("Rate_Shock", "Rate at pricing", lambda x: "base" if x == 0 else "+" + bp(x))])
    f["stress_table"] = case_table("solar_storage")
    f["sens_dscr"] = sensitivity_lines("solar_storage", "Min_DSCR_Op", xx, n=2)
    f["sens_irr"] = sensitivity_lines("solar_storage", "Equity_IRR_AT", pct, n=4, delta=bp)
    f["ratios_table"] = md_table(["", "Value"], [
        ["Coupon (fixed, swapped)", f["rate"]], ["Tenor", f["tenor"] + " years"], ["Gearing", f["gearing"]],
        [f"Minimum DSCR, P50 (target {f['t50']})", f["min_dscr_p50"]],
        [f"Minimum DSCR, P90 (target {f['t90']})", f["min_dscr_p90"]], ["LLCR / PLCR", f"{f['llcr']} / {f['plcr']}"],
        ["Debt service, year 1", f["ds_y1"]]])
    f["sources_table"] = _sources_table("solar_storage")
    return f


def _sources_table(model: str) -> str:
    src = load_sources()
    used = sorted({i.source for i in load_inputs(model) if i.tag == "Sourced"})
    return "\n".join(f"- {src[s]['citation']} ({src[s]['url']})" for s in used)


def facts(name: str) -> dict:
    model = "property" if name == "property_investment_memo" else "solar_storage"
    f = property_facts() if model == "property" else solar_facts()
    src = load_sources()
    f["as_of"] = str(max(src[i.source]["retrieved"] for i in load_inputs(model)))
    f["fingerprint"] = fingerprint(load_inputs(model))
    return f


def render(name: str) -> str:
    return (TEMPLATES / f"{name}.md").read_text().format_map(facts(name))


def write_all() -> list[Path]:
    out = []
    for name in MEMOS:
        p = ROOT / "memos" / f"{name}.md"
        p.write_text(render(name))
        out.append(p)
    return out


if __name__ == "__main__":
    for p in write_all():
        print(f"wrote {p.relative_to(ROOT)}")
