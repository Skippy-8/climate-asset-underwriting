"""The README's headline figures are typed by hand, so hold them to the engines."""
from pathlib import Path

import pytest

from cau.memos import facts

README = (Path(__file__).resolve().parents[1] / "README.md").read_text()

PROPERTY = ["price", "loan", "ltv", "min_dscr_sq", "min_dscr_rf", "lev_sq", "lev_rf", "eui_base", "eui_rf",
            "t_avoided", "t_avoided_pct", "irr_delta", "beps_penalty"]
SOLAR = ["debt", "gearing", "min_dscr_p50", "min_dscr_p90", "eq_irr_at", "be_share", "severe_min", "ppa_premium",
         "low_debt_cut", "hurdle"]


@pytest.mark.parametrize("memo,keys", [("property_investment_memo", PROPERTY), ("solar_storage_credit_memo", SOLAR)])
def test_readme_headline_numbers_match_the_engine(memo, keys):
    f = facts(memo)
    missing = [(k, f[k]) for k in keys if str(f[k]) not in README]
    assert not missing, missing

