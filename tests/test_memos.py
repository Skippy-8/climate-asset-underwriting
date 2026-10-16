"""The memos quote the models: every figure is rendered from model output, nothing is typed."""
import re

import pytest

from cau import memos
from cau.engine import property as P
from cau.engine import solar_storage as SS
from cau.inputs import load_inputs, values

# Phrases that legitimately contain digits: exceedance labels, chemistry and emission scopes.
ALLOWED = re.compile(r"Scope 1 and 2|Scope 1 \+ 2|Scope [123]|P50|P90|P99|tCO2e|CO2e|CO2")
# Spelled-out quantities would dodge the digit check, so they are banned outright.
SPELLED = re.compile(r"\b(five|six|seven|eight|nine|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
                     r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|hundred|thousand|million|billion)\b",
                     re.IGNORECASE)


@pytest.mark.parametrize("name", memos.MEMOS)
def test_committed_memo_matches_a_fresh_render(name):
    committed = (memos.ROOT / "memos" / f"{name}.md").read_text()
    assert committed == memos.render(name), "memo is stale: run `python -m cau.memos`"


@pytest.mark.parametrize("name", memos.MEMOS)
def test_templates_contain_no_typed_numbers(name):
    text = (memos.TEMPLATES / f"{name}.md").read_text()
    prose = ALLOWED.sub("", re.sub(r"\{[a-z0-9_]+\}", "", text))
    assert not re.findall(r"\d", prose), re.findall(r"\S*\d\S*", prose)
    spelled = [w for w in SPELLED.findall(prose) if w.lower() != "million" or "{t_life} million" not in text]
    assert not spelled, spelled


@pytest.mark.parametrize("name", memos.MEMOS)
def test_memo_is_two_to_three_pages(name):
    words = len(memos.render(name).split())
    assert 900 <= words <= 2000, words


def _money(text: str, label: str) -> float:
    """The first $X.Xm after ``label``."""
    m = re.search(re.escape(label) + r".*?\$([\d,]+\.\d)m", text, re.S)
    assert m, label
    return float(m.group(1).replace(",", "")) * 1e6


def test_property_memo_headline_numbers_parse_back_to_the_model():
    v = values(load_inputs("property"))
    s = P.run(v).scalars
    text = memos.render("property_investment_memo")
    assert _money(text, "giving a") == pytest.approx(s["Loan"], abs=0.05e6)
    assert _money(text, "Proceed with the acquisition at") == pytest.approx(v["Price"], abs=0.05e6)
    assert f"{s['Lev_IRR_SQ'] * 100:.1f}%" in text and f"{s['Lev_IRR_RF'] * 100:.1f}%" in text
    assert f"{s['Min_DSCR_SQ']:.2f}x" in text and f"{s['EUI_RF']:.1f}" in text
    assert f"{s['tCO2e_Avoided']:,.0f} tCO2e" in text
    assert f"${s['Utility_Savings_Y1']:,.0f}" in text


def test_credit_memo_headline_numbers_parse_back_to_the_model():
    r = SS.run(values(load_inputs("solar_storage")))
    s = r.scalars
    text = memos.render("solar_storage_credit_memo")
    assert _money(text, "Approve a") == pytest.approx(s["Debt"], abs=0.05e6)
    assert _money(text, "Senior debt |") == pytest.approx(s["Debt"], abs=0.05e6)
    assert _money(text, "Sponsor equity |") == pytest.approx(s["Equity"], abs=0.05e6)
    assert f"fixed at {s['Rate'] * 100:.2f}%" in text
    assert f"{s['Min_DSCR_P90']:.2f}x" in text and f"{s['LLCR']:.2f}x" in text
    assert f"{r.rows['Gen_P50'][0] / 1e3:,.0f} GWh" in text
    total = re.search(r"\*\*Total uses\*\* \| \*\*\$([\d,.]+)m\*\*", text)
    assert float(total.group(1).replace(",", "")) * 1e6 == pytest.approx(s["Total_Uses"], abs=0.05e6)
