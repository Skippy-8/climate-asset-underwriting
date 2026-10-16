"""The property engine's financial invariants."""
import numpy as np
import pytest

from cau.engine import property as P
from cau.engine.finance import amortize, irr, npv, pmt
from cau.inputs import load_inputs, values


def test_sources_equal_uses(prop):
    s = prop.scalars
    for case in ("SQ", "RF"):
        assert abs(s["Loan"] + s[f"Equity_{case}"] - s[f"Uses_{case}"]) < 1e-6
    assert s["Uses_RF"] - s["Uses_SQ"] == pytest.approx(s["Retrofit_Net"])


def test_loan_is_the_tightest_of_the_three_sizing_tests(prop):
    s = prop.scalars
    assert s["Loan"] == min(s["Max_Loan_LTV"], s["Max_Loan_DSCR"], s["Max_Loan_DY"])


def test_schedule_balances_and_identities(prop):
    r = prop.rows
    assert (r["End_Balance"] >= 0).all()
    np.testing.assert_allclose(r["Debt_Service"], r["Interest"] + r["Principal"], atol=1e-6)
    io = prop.inputs["IO_Years"]
    assert np.all(r["Principal"][: int(io)] == 0)                       # interest-only years
    assert np.all(np.diff(r["End_Balance"][int(io):]) < 0)              # amortising after


def test_loan_amortises_to_exactly_zero_over_its_full_term(prop):
    v = prop.inputs
    years = int(v["IO_Years"] + v["Amort_Months"] / v["Months"])
    for rates in (np.full(years, 0.0691), np.linspace(0.05, 0.09, years)):   # fixed, and a floating path
        s = amortize(1_000_000, rates, v["Amort_Months"], v["IO_Years"], v["Months"])
        assert abs(s["End_Balance"][-1]) < 1e-6
        assert (s["End_Balance"] >= -1e-6).all()


def test_irr_is_the_root_of_npv(prop):
    for case in ("SQ", "RF"):
        cf = prop.returns[f"Lev_CF_{case}"]
        assert abs(npv(irr(cf), cf[1:]) + cf[0]) < 1e-4


def test_finance_functions_match_excel_definitions():
    assert pmt(0.06 / 12, 360, -1000) == pytest.approx(5.995505251527569)         # Excel PMT
    assert npv(0.1, [30, 40, 50]) - 100 == pytest.approx(-2.103681442524447)      # Excel NPV - 100


def test_energy_reconciles_and_retrofit_meets_beps(prop):
    s, v = prop.scalars, prop.inputs
    gas_plus_elec = s["Gas_SQ_MMBtu"] + (s["Common_kWh"] + s["Tenant_kWh"]) / v["kWh_per_MMBtu"]
    assert gas_plus_elec == pytest.approx(s["Site_MMBtu_Base"])
    assert s["EUI_RF"] < s["EUI_Base"] and s["EUI_Reduction"] >= v["BEPS_EUI_Cut"]
    assert s["Scope1_RF"] == 0 and s["tCO2e_Avoided"] > 0
    assert s["Solar_kWh"] <= s["Owner_Gross_RF_kWh"]


def test_natural_gas_factor_matches_epa(prop):
    # 53.06 kg CO2 + 1.0 g CH4 x 28 + 0.10 g N2O x 265 = 53.1145 kg CO2e per MMBtu
    assert prop.scalars["NG_tCO2e_MMBtu"] * 1000 == pytest.approx(53.1145)


def test_covenant_flags_follow_the_thresholds(prop):
    v, r = prop.inputs, prop.rows
    for case in ("SQ", "RF"):
        for d, flag in zip(r[f"DSCR_{case}"], r[f"DSCR_Flag_{case}"], strict=True):
            want = "BREACH" if d < v["DSCR_Default"] else "CASH TRAP" if d < v["DSCR_Trap"] else "OK"
            assert flag == want


def test_raising_vacancy_at_sizing_resizes_the_loan_instead_of_breaching():
    base = P.run(values(load_inputs("property")))
    worse = P.run(values(load_inputs("property"), Vacancy_Rate=0.15))
    assert worse.scalars["Loan"] < base.scalars["Loan"]
    assert worse.scalars["Min_DSCR_SQ"] >= base.inputs["DSCR_Trap"]


def test_vacancy_after_closing_trips_the_cash_trap():
    base = P.run(values(load_inputs("property")))
    closed = values(load_inputs("property"), Vacancy_Rate=0.15, Loan_Override=base.scalars["Loan"])
    r = P.run(closed)
    assert r.scalars["Min_DSCR_SQ"] < closed["DSCR_Trap"]
    assert {"CASH TRAP", "BREACH"} & set(r.rows["DSCR_Flag_SQ"])


def test_floating_rate_shock_lowers_coverage():
    base = values(load_inputs("property"), Debt_Option=2)
    shocked = dict(base, SOFR_Shock=0.02)
    a, b = P.run(base), P.run(shocked)
    assert b.scalars["Loan"] < a.scalars["Loan"]                     # sized on a higher rate
    assert b.scalars["Lev_IRR_SQ"] < a.scalars["Lev_IRR_SQ"]


def test_irr_returns_the_root_nearest_the_excel_guess_when_flows_change_sign_twice():
    flows = [-100, 60, 60, 60, -45]        # two sign changes, roots near 10.9% and -32%
    r = irr(flows)
    assert abs(npv(r, flows[1:]) + flows[0]) < 1e-6 and r > 0
