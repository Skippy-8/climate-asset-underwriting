"""Base / Downside / Severe: monotone degradation, workbook parity in every case, and the analyses
the memos quote (sensitivities, grids, break-evens)."""
import numpy as np
import pytest

from cau.engine import property as P
from cau.engine import solar_storage as SS
from cau.engine import stress as ST
from cau.xlsx.evaluate import evaluate, load_model

MODELS = ("property", "solar_storage")


@pytest.mark.parametrize("model", MODELS)
def test_cases_degrade_monotonically(model):
    assert ST.monotone_violations(model) == []


@pytest.mark.parametrize("model", MODELS)
def test_each_case_is_strictly_worse_on_the_headline_metrics(model):
    t = ST.case_table(model)
    key = {"property": "Min_DSCR_SQ", "solar_storage": "Min_DSCR_Op"}[model]
    irr = {"property": "Lev_IRR_RF", "solar_storage": "Equity_IRR_AT"}[model]
    for k in (key, irr):
        b, d, s = t.loc[k, list(ST.CASES)]
        assert b > d > s, k


@pytest.mark.parametrize("model", MODELS)
def test_base_case_column_is_the_base_model(model):
    base = ST.ENGINES[model].run(ST.base_values(model)).scalars
    t = ST.case_table(model)
    for k in t.index:
        assert t.loc[k, "Base"] == pytest.approx(base[k])


def test_property_stresses_hold_the_closed_loan():
    t = ST.case_table("property")
    assert t.loc["Loan", "Downside"] == t.loc["Loan", "Severe"] == t.loc["Loan", "Base"]
    assert t.loc["Trap_Years_SQ", "Severe"] > 0 and t.loc["Min_DSCR_SQ", "Severe"] < ST.base_values("property")["DSCR_Default"]


def test_solar_stresses_resize_at_close_and_hit_the_fixed_schedule():
    base = SS.run(ST.base_values("solar_storage"))
    down = ST.run_case("solar_storage", "Downside")
    assert down.scalars["Debt"] < base.scalars["Debt"]                       # rate shock at close
    np.testing.assert_allclose(down.rows["Debt_Service"], base.rows["Debt_Service"])   # same sculpted profile
    assert down.scalars["Min_DSCR_Op"] == pytest.approx(down.scalars["Min_DSCR_P90"])   # runs at P90


def test_merchant_tail_is_floored_not_run_at_a_loss():
    r = ST.run_case("solar_storage", "Severe")
    post = r.rows["CFADS_Op"][int(r.inputs["PPA_Term"]):]
    assert (post >= 0).all()


@pytest.mark.parametrize("model", MODELS)
def test_workbook_reproduces_every_case_through_case_select(model, tmp_path):
    from conftest import MODELS as BUILDERS

    from cau.inputs import load_inputs
    builder = BUILDERS[model][1]
    path = builder.build(load_inputs(model), tmp_path / f"{model}.xlsx")
    m = load_model(path)
    t = ST.case_table(model)
    for i, case in enumerate(ST.CASES, start=1):
        got = evaluate(path, {"Case_Select": i}, model=m)
        assert got["All_Checks"] is True, case
        for k in t.index:
            want = t.loc[k, case]
            assert float(got[k]) == pytest.approx(want, rel=1e-6, abs=1e-9), f"{case} {k}"
            snap = got[f"Snap_{k}"]
            assert float(snap[i - 1]) == pytest.approx(want, rel=1e-12), f"snapshot {case} {k}"


@pytest.mark.parametrize("model,metric", [("property", "Lev_IRR_RF"), ("property", "Min_DSCR_SQ"),
                                          ("solar_storage", "Min_DSCR_Op"), ("solar_storage", "Equity_IRR_AT")])
def test_every_adverse_lever_is_adverse(model, metric):
    s = ST.sensitivities(model, metric)
    assert (s["change"] <= 1e-9).all(), s.to_string()


def test_generation_breakeven_is_where_coverage_reaches_one():
    be = ST.breakeven_generation()
    r = SS.run(dict(ST.base_values("solar_storage"), Gen_Case_Z=be["z"]))
    assert r.scalars["Min_DSCR_Op"] == pytest.approx(1.0, abs=1e-6)
    assert 0.5 < be["share_of_p50"] < 1 and be["exceedance"] > 0.99


def test_vacancy_breakeven_is_where_coverage_hits_the_default_covenant():
    be = ST.breakeven_vacancy()
    base = ST.base_values("property")
    loan = P.run(base).scalars["Loan"]
    r = P.run(dict(base, Vacancy_Rate=be["vacancy"], Loan_Override=loan))
    assert r.scalars["Min_DSCR_SQ"] == pytest.approx(base["DSCR_Default"], abs=1e-6)


def test_two_way_grid_moves_the_right_way():
    g = ST.grid("solar_storage", "PPA_Price", [45, 51, 57], "Gen_Case_Z", [0, 1.2816], "Equity_IRR_AT")
    assert (np.diff(g.to_numpy(), axis=1) > 0).all()        # higher PPA, higher IRR
    assert (np.diff(g.to_numpy(), axis=0) < 0).all()        # lower output, lower IRR
