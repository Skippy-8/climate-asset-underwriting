"""Debt sculpting and project-finance invariants."""
import numpy as np
import pytest

from cau.engine import solar_storage as SS
from cau.engine.finance import npv
from cau.inputs import load_inputs, values

TOL = 1e-6


def run(**kw):
    return SS.run(values(load_inputs("solar_storage"), **kw))


def test_sources_equal_uses(pf):
    s = pf.scalars
    assert abs(s["Total_Sources"] - s["Total_Uses"]) < TOL
    assert s["Equity"] > 0


def test_debt_is_the_present_value_of_its_service_and_repays_to_zero(pf):
    s, r = pf.scalars, pf.rows
    ten = int(pf.inputs["Tenor"])
    assert npv(s["Rate"], r["Debt_Service"]) == pytest.approx(s["Debt"], rel=1e-12)
    assert abs(r["End_Balance"][ten - 1]) < TOL * s["Debt"]
    assert (r["End_Balance"] >= -TOL * s["Debt"]).all()
    assert np.all(r["Debt_Service"][ten:] == 0)
    np.testing.assert_allclose(r["Principal"] + r["Interest"], r["Debt_Service"])


def test_sculpted_dscr_equals_the_binding_target_every_year(pf):
    v, r = pf.inputs, pf.rows
    ten = int(v["Tenor"])
    binding = np.minimum(r["DSCR_P50"][:ten] / v["DSCR_P50_Target"], r["DSCR_P90"][:ten] / v["DSCR_P90_Target"])
    np.testing.assert_allclose(binding, 1 / pf.scalars["Sculpt_Scale"], rtol=1e-9)
    assert pf.scalars["Sculpt_Scale"] == 1.0
    np.testing.assert_allclose(r["DSCR_P50"][:ten], v["DSCR_P50_Target"], rtol=1e-9)    # P50 binds in the base case
    assert (r["DSCR_P90"][:ten] >= v["DSCR_P90_Target"] - 1e-9).all()
    assert pf.scalars["LLCR"] == pytest.approx(v["DSCR_P50_Target"])                    # sculpted at a flat 1.35x


def test_each_leg_of_the_min_binds_where_it_is_tighter():
    r = run(Gen_Sigma_1yr=0.20)            # P90 = 74% of P50: P90 binds in some years, P50 in the others
    v, ten = r.inputs, int(r.inputs["Tenor"])
    p50, p90 = r.rows["DSCR_P50"][:ten], r.rows["DSCR_P90"][:ten]
    p90_binds, p50_binds = np.isclose(p90, v["DSCR_P90_Target"]), np.isclose(p50, v["DSCR_P50_Target"])
    assert p90_binds.any() and p50_binds.any() and (p90_binds | p50_binds).all()
    assert (p50 >= v["DSCR_P50_Target"] - 1e-9).all() and (p90 >= v["DSCR_P90_Target"] - 1e-9).all()
    assert abs(r.rows["End_Balance"][ten - 1]) < TOL * r.scalars["Debt"]


def test_gearing_cap_scales_service_down_and_still_repays():
    r = run(Max_Gearing=0.30)
    s, rows, ten = r.scalars, r.rows, int(r.inputs["Tenor"])
    assert s["Debt"] == pytest.approx(0.30 * s["Project_Capex"]) and s["Sculpt_Scale"] < 1
    assert (rows["DSCR_P50"][:ten] > r.inputs["DSCR_P50_Target"]).all()
    assert abs(rows["End_Balance"][ten - 1]) < TOL * s["Debt"]


def test_battery_end_of_life_steps_down_service(pf):
    life = int(pf.inputs["BESS_Life"])
    assert pf.rows["Rev_BESS"][life] == 0 and pf.rows["Debt_Service"][life] < pf.rows["Debt_Service"][life - 1]


def test_generation_uses_the_sourced_benchmarks(pf):
    v = pf.inputs
    y1 = v["PV_MWac"] * v["Hours_Per_Year"] * v["CF_P50"] * (1 - v["Curtailment"])
    assert pf.rows["Gen_P50"][0] == pytest.approx(y1)
    assert pf.scalars["P90_Factor"] == pytest.approx(1 - 1.2816 * v["Gen_Sigma_1yr"])
    assert pf.rows["Gen_P50"][1] / pf.rows["Gen_P50"][0] == pytest.approx(1 - v["Degradation"])


def test_benchmarks_wired_as_sourced(pf_inputs):
    by = {i.key: i for i in pf_inputs}
    expect = {"PV_Capex_Per_Wac": (1.38, "lbnl_uss_2025"), "BESS_Capex_Per_kWh": (334, "nlr_bess_2025"),
              "CF_P50": (0.329, "atb_2024b_pv"), "Curtailment": (0.071, "lbnl_uss_2025"),
              "Degradation": (0.007, "atb_2024b_pv"), "BESS_FOM_Pct": (0.025, "atb_2024b_bess"),
              "Merchant_Price": (24, "lbnl_uss_2025"), "Grid_CO2e_lb_MWh": (774.3, "egrid2022")}
    for k, (val, src) in expect.items():
        assert (by[k].value, by[k].source, by[k].tag) == (val, src, "Sourced"), k


def test_base_ppa_lands_on_the_stated_equity_hurdle(pf):
    """The PPA input is documented as solved for the sponsor hurdle; keep that statement true."""
    assert pf.scalars["Equity_IRR_AT"] == pytest.approx(pf.inputs["Equity_Hurdle"], abs=0.0025)


def test_after_tax_view_is_internally_consistent(pf):
    s, r = pf.scalars, pf.rows
    basis = s["Project_Capex"] - 0.5 * (0.30 * s["PV_Capex"] + 0.30 * s["BESS_Capex"])
    assert s["Dep_Basis"] == pytest.approx(basis)
    assert r["Depreciation"].sum() == pytest.approx(basis)                 # MACRS sums to 100%
    assert abs(s["Equity_NPV_At_IRR_AT"]) < TOL * s["Equity"]


@pytest.mark.parametrize("stress", [{"Gen_Case_Z": 1.2816}, {"Gen_Case_Z": 2.3263}, {"Merchant_Shock": -0.5}])
def test_operating_stresses_leave_the_closed_debt_alone(pf, stress):
    r = run(**stress)
    assert r.scalars["Debt"] == pytest.approx(pf.scalars["Debt"])
    np.testing.assert_allclose(r.rows["Debt_Service"], pf.rows["Debt_Service"])
    assert r.scalars["Equity_IRR"] <= pf.scalars["Equity_IRR"]


def test_rate_shock_resizes_the_debt_at_close(pf):
    r = run(Rate_Shock=0.02)
    assert r.scalars["Debt"] < pf.scalars["Debt"]
    assert r.scalars["Min_DSCR_P50"] == pytest.approx(pf.scalars["Min_DSCR_P50"])   # still sized to 1.35x


def test_capex_overrun_is_funded_with_equity(pf):
    r = run(Capex_Overrun=0.15)
    assert r.scalars["Debt"] == pytest.approx(pf.scalars["Debt"], rel=1e-12)        # cash flow is unchanged
    assert r.scalars["Equity"] > pf.scalars["Equity"] and r.scalars["Equity_IRR"] < pf.scalars["Equity_IRR"]
