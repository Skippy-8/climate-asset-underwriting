"""Headless render of the dashboard: every tab, both assets, every case, and the levers; the numbers
shown must be the engine's."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from cau.engine import stress as ST

APP = str(Path(__file__).resolve().parents[1] / "dashboard" / "app.py")


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(APP, default_timeout=300).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def test_all_four_tabs_render(app):
    assert [t.label for t in app.tabs] == ["Budget vs actual", "Covenants", "Stress and sensitivity", "Decarbonization"]
    assert any("Pre-flight QC: grade D" in m.value for m in app.markdown)
    assert len(app.metric) >= 20


@pytest.mark.parametrize("asset,model", [("Multifamily, Washington DC", "property"), ("Solar + storage, ERCOT", "solar_storage")])
@pytest.mark.parametrize("case", ST.CASES)
def test_covenant_tab_shows_the_engine_numbers(app, asset, model, case):
    app.segmented_control(key="cov_asset").set_value(asset)
    app.selectbox(key="cov_case").set_value(case)
    app.run()
    assert not app.exception, [e.value for e in app.exception]
    s = ST.run_case(model, case).scalars
    if model == "property":
        assert metric(app, "Minimum DSCR") == f"{s['Min_DSCR_SQ']:.2f}x"
        assert metric(app, "Covenant flag-years") == f"{s['Trap_Years_SQ']:.0f}"
    else:
        assert metric(app, "Minimum DSCR, operating") == f"{s['Min_DSCR_Op']:.2f}x"
        assert metric(app, "Years in lock-up") == f"{s['Lockup_Years']:.0f}"


def test_stress_levers_rerun_the_engine(app):
    app.segmented_control(key="st_asset").set_value("Multifamily, Washington DC")
    app.run()
    base_dscr = metric(app, "Minimum DSCR")
    app.slider[0].set_value(15.0)                      # vacancy 15% with the loan held
    app.run()
    assert not app.exception
    assert float(metric(app, "Minimum DSCR").rstrip("x")) < float(base_dscr.rstrip("x"))


def test_solar_stress_tab_and_output_case(app):
    app.segmented_control(key="st_asset").set_value("Solar + storage, ERCOT")
    app.run()
    app.select_slider[0].set_value("P99")
    app.run()
    assert not app.exception, [e.value for e in app.exception]
    severe_like = ST.run_case("solar_storage", "Base", Gen_Case_Z=ST.base_values("solar_storage")["Z_P99"]).scalars
    assert metric(app, "Minimum DSCR, operating") == f"{severe_like['Min_DSCR_Op']:.2f}x"


def test_decarbonization_kpis_match_the_engine(app):
    from cau.engine import property as P
    s = P.run(ST.base_values("property")).scalars
    assert metric(app, "Site EUI") == f"{s['EUI_RF']:.1f} kBtu/sf"
    assert metric(app, "Owner emissions avoided") == f"{s['tCO2e_Avoided']:,.0f} tCO2e/yr"
