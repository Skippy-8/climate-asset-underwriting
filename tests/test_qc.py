"""Pre-flight QC must catch every planted defect before a variance is reported."""
import pandas as pd
import pytest

from cau import actuals as A
from cau import qc


@pytest.fixture(scope="module")
def report():
    return qc.run(pd.read_csv(A.ACTUALS), A.budget(), A.CHART_OF_ACCOUNTS)


def test_committed_actuals_file_is_the_seeded_synthetic_one():
    pd.testing.assert_frame_equal(pd.read_csv(A.ACTUALS), A.synthetic_actuals().reset_index(drop=True), check_dtype=False)


def test_budget_ties_to_the_engine_year_one():
    from cau.engine import property as P
    from cau.inputs import load_inputs, values
    r = P.run(values(load_inputs("property")))
    b = A.budget()
    for line, (key, _) in A.CHART_OF_ACCOUNTS.items():
        assert b.loc[b["line"] == line, "amount"].sum() == pytest.approx(r.rows[key][0])


def test_every_planted_defect_is_caught(report):
    f = report.findings
    got = set(zip(f["check"], f["period"], f["line"], strict=True))
    assert ("duplicate", "Y1-M04", "Repairs and maintenance") in got
    assert ("unmapped_line", "Y1-M05", "Legal fees") in got
    assert ("sign_error", "Y1-M03", "Insurance") in got
    assert ("missing", "Y1-M06", "Electricity") in got
    assert report.grade == "D"
    assert len(report.removed) == 3 and len(report.clean) == len(pd.read_csv(A.ACTUALS)) - 3


def test_clean_file_grades_a():
    b = A.budget()
    ytd = b[b["period"].isin([A.period(m) for m in range(1, 7)])][["period", "line", "amount"]]
    assert qc.run(ytd, b, A.CHART_OF_ACCOUNTS).grade == "A"


def test_schema_failure_is_reported_not_raised():
    rep = qc.run(pd.DataFrame({"month": ["x"], "value": [1]}), A.budget(), A.CHART_OF_ACCOUNTS)
    assert rep.grade == "D" and rep.findings.iloc[0]["check"] == "schema" and rep.clean.empty


def test_variance_never_claims_a_result_for_an_incomplete_line(report):
    v = qc.variance(report.clean, A.budget(), A.CHART_OF_ACCOUNTS)
    inc = v[v["status"] == "incomplete"]
    assert set(inc["line"]) == {"Insurance", "Electricity"}
    assert inc["favourable"].isna().all()


def test_noi_uses_only_complete_months(report):
    v = qc.variance(report.clean, A.budget(), A.CHART_OF_ACCOUNTS)
    complete = qc.complete_periods(report.clean, A.CHART_OF_ACCOUNTS)
    assert "Y1-M03" not in complete and "Y1-M06" not in complete
    noi = v.iloc[-1]
    b = A.budget()
    assert noi["budget"] == pytest.approx(qc.noi_by_period(b[b["period"].isin(complete)], A.CHART_OF_ACCOUNTS).sum())
    assert noi["months"] == len(complete)


def test_favourability_follows_line_type():
    b = A.budget()
    ytd = b[b["period"] == A.period(1)][["period", "line", "amount"]].copy()
    ytd.loc[ytd["line"] == "Payroll", "amount"] *= 1.5            # an expense overrun
    ytd.loc[ytd["line"] == "Other income", "amount"] *= 1.5       # extra revenue
    v = qc.variance(ytd, b, A.CHART_OF_ACCOUNTS).set_index("line")
    assert v.loc["Payroll", "status"] == "unfavourable" and v.loc["Other income", "status"] == "favourable"
