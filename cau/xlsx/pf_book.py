"""Builds models/solar_storage_pf.xlsx: live formulas mirroring cau/engine/solar_storage.py.

Debt sculpting is closed form (see the engine docstring): target service =
MIN(CFADS_P50/1.35x, CFADS_P90/1.00x); debt = MIN(NPV(rate, target service), gearing cap);
service = target x (debt / NPV); interest = opening balance x rate; principal = service - interest.
No cell depends on itself, so the workbook needs no iterative calculation.
"""
from __future__ import annotations

from pathlib import Path

from cau.engine import stress as ST
from cau.engine.solar_storage import YEARS
from cau.inputs import Input
from cau.xlsx.book import FMT, Book
from cau.xlsx.scenarios import scenario_values, scenarios_sheet

REPO = Path(__file__).resolve().parents[2]

TABS = [
    ("Summary", "Key outputs"),
    ("Inputs", "Every assumption with its tag and source id"),
    ("Sources", "Citations, URLs and retrieval dates"),
    ("Capex_SU", "Capital costs, tax-credit proceeds, sources and uses"),
    ("Generation", "P50, P90 and operating-case output with degradation and curtailment"),
    ("Revenue", "PPA, merchant tail and battery toll"),
    ("Opex", "Solar and battery O&M and asset management"),
    ("CFADS", "Cash flow available for debt service: sizing (P50, P90) and operating case"),
    ("Debt_Sculpt", "Closed-form sculpted debt sizing and the repayment schedule"),
    ("Ratios", "DSCR by year (P50, P90, operating), LLCR and PLCR"),
    ("Tax", "MACRS depreciation and tax for a sponsor that can use losses"),
    ("Returns", "Project and equity cash flows, pre- and after-tax IRRs, avoided emissions"),
    ("Scenarios", "Base / Downside / Severe (rating-agency style), one-factor sensitivities, break-even output"),
    ("Checks", "Integrity checks; the Cover shows whether all pass"),
]


def build(inputs: list[Input], path: Path) -> Path:
    b = Book(YEARS)
    b.inputs_sheet(inputs, scenario_values("solar_storage", inputs))
    first, last = b.r("Inputs", "MACRS_Y1"), b.r("Inputs", "MACRS_Y6")
    b.name("MACRS_Table", "Inputs", f"$C${first}:$C${last}")
    b.sources_sheet(inputs)
    _capex(b)
    _generation(b)
    _revenue(b)
    _opex(b)
    _cfads(b)
    _debt(b)
    _ratios(b)
    _tax(b)
    _returns(b)
    _checks(b)
    _summary(b)
    be = ST.breakeven_generation()
    scenarios_sheet(b, "solar_storage", [("Min_DSCR_Op", "minimum operating DSCR", "x"),
                                         ("Equity_IRR_AT", "after-tax equity IRR", "pct")],
                    [("Output (share of P50, every year) at which minimum DSCR hits 1.00x", be["share_of_p50"], "pct1"),
                     ("Implied one-year exceedance probability of that output", be["exceedance"], "pct")])
    b.cover("Solar + storage project financing",
            "200 MWac solar + 100 MW / 400 MWh battery, West Texas (ERCOT), illustrative. Sculpted senior debt.",
            inputs, TABS, REPO, "All_Checks")
    order = ["Cover", "Summary", "Inputs", "Sources", "Capex_SU", "Generation", "Revenue", "Opex", "CFADS",
             "Debt_Sculpt", "Ratios", "Tax", "Returns", "Scenarios", "Checks"]
    b.wb._sheets = [b.wb[n] for n in order]
    return b.save(path)


def _flag(b, ws, row, key, label, cond):
    yr = lambda c: f"{c}{b.r(ws.title, 'Year')}"                                    # noqa: E731
    b.series(ws, row, key, label, "flag", lambda c, p, k: f"=IF({cond(yr(c))},1,0)", "int")


def _capex(b: Book) -> None:
    ws = b.sheet("Capex_SU", "Capital costs, sources and uses", "At financial close (year 0).", year_header=False)
    s = b.scalar
    b.section(ws, 4, "Size")
    s(ws, 5, "PV_MWdc", "Solar capacity (DC)", "MWdc", "=PV_MWac*ILR", "num1")
    s(ws, 6, "BESS_MWh", "Battery energy", "MWh", "=BESS_MW*BESS_Hours", "num")
    b.section(ws, 8, "Uses")
    s(ws, 9, "PV_Capex", "Solar equipment and installation", "$",
      "=PV_MWac*kW_per_MW*W_per_kW*PV_Capex_Per_Wac*(1+Capex_Overrun)")
    s(ws, 10, "BESS_Capex", "Battery equipment and installation", "$", "=BESS_Capex_Base*(1+Capex_Overrun)")
    s(ws, 7, "BESS_Capex_Base", "Battery cost at benchmark (O&M basis)", "$", "=BESS_MWh*kWh_per_MWh*BESS_Capex_Per_kWh")
    s(ws, 11, "Equipment_Capex", "Equipment capex", "$", "=PV_Capex+BESS_Capex")
    s(ws, 12, "Dev_Costs", "Development, owner and interconnection", "$", "=Owner_Dev_Pct*Equipment_Capex")
    s(ws, 13, "Project_Capex", "Project capex", "$", "=Equipment_Capex+Dev_Costs", bold=True)
    s(ws, 14, "IDC", "Interest during construction", "$", "=Debt*Rate*Constr_Years*Avg_Draw")
    s(ws, 15, "Fees", "Upfront financing fees", "$", "=Upfront_Fee*Debt")
    s(ws, 16, "DSRA", "Debt service reserve funding", "$", "=DSRA_Months/Months*INDEX(R_Debt_Service,1,1)")
    s(ws, 17, "Total_Uses", "Total uses", "$", "=Project_Capex+IDC+Fees+DSRA", bold=True)
    b.section(ws, 19, "Sources")
    s(ws, 20, "Debt_Src", "Senior debt", "$", "=Debt", define=False)
    s(ws, 21, "ITC_Proceeds", "Tax-credit transfer proceeds", "$",
      "=(ITC_PV*PV_Capex+ITC_BESS*BESS_Capex)*ITC_Transfer_Price")
    s(ws, 22, "Equity", "Sponsor equity", "$", "=Total_Uses-Debt-ITC_Proceeds")
    s(ws, 23, "Total_Sources", "Total sources", "$", "=Debt+ITC_Proceeds+Equity", bold=True)


def _generation(b: Book) -> None:
    T = "Generation"
    ws = b.sheet(T, "Generation", "MWh delivered after curtailment. P90/P99 are one-year exceedance levels: "
                 "P50 x (1 - z x sigma).")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    s = b.scalar
    s(ws, 5, "P90_Factor", "P90 / P50", "ratio", "=1-Z_P90*Gen_Sigma_1yr", "num4")
    s(ws, 6, "P99_Factor", "P99 / P50", "ratio", "=1-Z_P99*Gen_Sigma_1yr", "num4")
    s(ws, 7, "Op_Gen_Factor", "Operating case / P50", "ratio", "=1-Gen_Case_Z*Gen_Sigma_1yr", "num4")
    _flag(b, ws, 9, "PV_On", "Solar operating (1 = yes)", lambda y: f"{y}<=PV_Life")
    _flag(b, ws, 10, "BESS_On", "Battery operating (1 = yes)", lambda y: f"{y}<=BESS_Life")
    b.series(ws, 11, "Deg_Index", "Degradation index", "index", lambda c, p, k: f"=(1-Degradation)^({yr(c)}-1)", "num4")
    b.series(ws, 12, "Gen_P50", "Generation, P50", "MWh", lambda c, p, k: (
        f"=PV_MWac*Hours_Per_Year*CF_P50*(1-Curtailment)*{rr('Deg_Index', c)}*{rr('PV_On', c)}"), "num")
    b.series(ws, 13, "Gen_P90", "Generation, P90", "MWh", lambda c, p, k: f"={rr('Gen_P50', c)}*P90_Factor", "num")
    b.series(ws, 14, "Gen_Op", "Generation, operating case", "MWh", lambda c, p, k: f"={rr('Gen_P50', c)}*Op_Gen_Factor",
             "num")


def _revenue(b: Book) -> None:
    T = "Revenue"
    ws = b.sheet(T, "Revenue", "As-generated PPA, then merchant at the ERCOT solar market value; battery tolling "
                 "for the battery's life.")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    g = lambda k, c: b.ref("Generation", k, c)                               # noqa: E731
    _flag(b, ws, 5, "PPA_On", "PPA in force (1 = yes)", lambda y: f"{y}<=PPA_Term")
    _flag(b, ws, 6, "Toll_On", "Toll in force (1 = yes)", lambda y: f"AND({y}<=Toll_Term,{y}<=BESS_Life)")
    S = b.series
    S(ws, 7, "PPA_Price_Row", "PPA price", "$/MWh", lambda c, p, k: f"=PPA_Price*(1+PPA_Escalator)^({yr(c)}-1)", "usd2")
    S(ws, 8, "Merchant_Price_Row", "Merchant price, base", "$/MWh",
      lambda c, p, k: f"=Merchant_Price*(1+Merchant_Escalation)^({yr(c)}-1)", "usd2")
    S(ws, 9, "Price_Base", "Realised solar price, sizing case", "$/MWh", lambda c, p, k: (
        f"={rr('PPA_On', c)}*{rr('PPA_Price_Row', c)}+(1-{rr('PPA_On', c)})*{rr('Merchant_Price_Row', c)}"), "usd2")
    S(ws, 10, "Price_Op", "Realised solar price, operating case", "$/MWh", lambda c, p, k: (
        f"={rr('PPA_On', c)}*{rr('PPA_Price_Row', c)}+(1-{rr('PPA_On', c)})*{rr('Merchant_Price_Row', c)}"
        f"*(1+Merchant_Shock)"), "usd2")
    S(ws, 12, "Rev_PV_P50", "Solar revenue, P50", "$", lambda c, p, k: f"={g('Gen_P50', c)}*{rr('Price_Base', c)}")
    S(ws, 13, "Rev_PV_P90", "Solar revenue, P90", "$", lambda c, p, k: f"={g('Gen_P90', c)}*{rr('Price_Base', c)}")
    S(ws, 14, "Rev_PV_Op", "Solar revenue, operating case", "$", lambda c, p, k: f"={g('Gen_Op', c)}*{rr('Price_Op', c)}")
    S(ws, 15, "Rev_BESS", "Battery toll revenue", "$",
      lambda c, p, k: f"=Toll_Price*BESS_MW*kW_per_MW*Months*{rr('Toll_On', c)}")


def _opex(b: Book) -> None:
    T = "Opex"
    ws = b.sheet(T, "Operating costs", "Solar O&M is ATB's all-in figure; battery O&M includes augmentation.")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    g = lambda k, c: b.ref("Generation", k, c)                               # noqa: E731
    S = b.series
    S(ws, 5, "Esc_Index", "Escalation index", "index", lambda c, p, k: f"=(1+Opex_Escalation)^({yr(c)}-1)", "num4")
    S(ws, 6, "Opex_PV", "Solar O&M", "$",
      lambda c, p, k: f"=PV_FOM_Per_kWac*PV_MWac*kW_per_MW*{rr('Esc_Index', c)}*{g('PV_On', c)}")
    S(ws, 7, "Opex_BESS", "Battery O&M incl. augmentation", "$",
      lambda c, p, k: f"=BESS_FOM_Pct*BESS_Capex_Base*{rr('Esc_Index', c)}*{g('BESS_On', c)}")
    S(ws, 8, "Opex_AM", "Asset management", "$", lambda c, p, k: f"=Asset_Mgmt*{rr('Esc_Index', c)}*{g('PV_On', c)}")
    S(ws, 9, "Opex", "Total operating costs", "$",
      lambda c, p, k: f"={rr('Opex_PV', c)}+{rr('Opex_BESS', c)}+{rr('Opex_AM', c)}", total=True)


def _cfads(b: Book) -> None:
    ws = b.sheet("CFADS", "Cash flow available for debt service", "Pre-tax (the project is a pass-through "
                 "entity). Sizing cases use base prices; the operating case carries the stress inputs. After the PPA "
                 "the plant is idled rather than run at a loss, so merchant-year cash flow is floored at zero.")
    rv = lambda k, c: b.ref("Revenue", k, c)                                 # noqa: E731
    op = lambda c: b.ref("Opex", "Opex", c)                                  # noqa: E731
    for row, case in ((5, "P50"), (6, "P90"), (7, "Op")):
        label = {"P50": "CFADS, P50 (sizing)", "P90": "CFADS, P90 (sizing)", "Op": "CFADS, operating case"}[case]
        b.series(ws, row, f"CFADS_{case}", label, "$", lambda c, p, k, case=case: (
            f"=IF({rv('PPA_On', c)}=1,{rv(f'Rev_PV_{case}', c)}+{rv('Rev_BESS', c)}-{op(c)},"
            f"MAX({rv(f'Rev_PV_{case}', c)}+{rv('Rev_BESS', c)}-{op(c)},0))"), total=case == "Op")


def _debt(b: Book) -> None:
    T = "Debt_Sculpt"
    ws = b.sheet(T, "Debt sizing and sculpting", "Closed form: debt = NPV of target service at the coupon, capped "
                 "by gearing; no circular references.")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    cf = lambda k, c: b.ref("CFADS", k, c)                                   # noqa: E731
    _flag(b, ws, 12, "Tenor_On", "Within tenor (1 = yes)", lambda y: f"{y}<=Tenor")
    S = b.series
    S(ws, 13, "DS_Target", "Target service = MIN(P50/1.35x, P90/1.00x)", "$", lambda c, p, k: (
        f"=MIN({cf('CFADS_P50', c)}/DSCR_P50_Target,{cf('CFADS_P90', c)}/DSCR_P90_Target)*{rr('Tenor_On', c)}"))
    S(ws, 14, "Debt_Service", "Scheduled debt service", "$", lambda c, p, k: f"={rr('DS_Target', c)}*Sculpt_Scale")
    S(ws, 15, "Beg_Balance", "Opening balance", "$", lambda c, p, k: "=Debt" if p is None else f"={p}18")
    S(ws, 16, "Interest", "Interest", "$", lambda c, p, k: f"={rr('Beg_Balance', c)}*Rate")
    S(ws, 17, "Principal", "Principal", "$", lambda c, p, k: f"={rr('Debt_Service', c)}-{rr('Interest', c)}")
    S(ws, 18, "End_Balance", "Closing balance", "$", lambda c, p, k: f"={rr('Beg_Balance', c)}-{rr('Principal', c)}")
    assert b.r(T, "End_Balance") == 18
    s = b.scalar
    s(ws, 5, "Rate", "Coupon (Treasury + spread + shock)", "%", "=UST_10Y+Debt_Spread+Rate_Shock", "pct")
    s(ws, 6, "Debt_Capacity_Sculpt", "Debt supported by target service (NPV)", "$", f"=NPV(Rate,{b.span(T, 'DS_Target', here=T)})")
    s(ws, 7, "Debt_Capacity_Gearing", "Gearing cap", "$", "=Max_Gearing*Project_Capex")
    s(ws, 8, "Debt", "Senior debt", "$", "=MIN(Debt_Capacity_Sculpt,Debt_Capacity_Gearing)", bold=True)
    s(ws, 9, "Sculpt_Scale", "Service scale (1 = DSCR targets bind)", "ratio", "=Debt/Debt_Capacity_Sculpt", "num4")
    s(ws, 10, "Gearing", "Debt / project capex", "%", "=Debt/Project_Capex", "pct1")


def _ratios(b: Book) -> None:
    T = "Ratios"
    ws = b.sheet(T, "Coverage ratios", "DSCR shown inside the tenor only. LLCR = NPV of P50 CFADS over the tenor / "
                 "debt; PLCR = over the project life.")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    cf = lambda k, c: b.ref("CFADS", k, c)                                   # noqa: E731
    dt = lambda k, c: b.ref("Debt_Sculpt", k, c)                             # noqa: E731
    S = b.series
    for row, case in ((5, "P50"), (6, "P90"), (7, "Op")):
        S(ws, row, f"DSCR_{case}", f"DSCR, {case}", "x", lambda c, p, k, case=case: (
            f'=IF({dt("Tenor_On", c)}=1,{cf(f"CFADS_{case}", c)}/{dt("Debt_Service", c)},"")'), "x")
    S(ws, 8, "CFADS_P50_Tenor", "P50 CFADS inside the tenor", "$", lambda c, p, k: f"={cf('CFADS_P50', c)}*{dt('Tenor_On', c)}",
      name_range=False)
    S(ws, 9, "CFADS_Op_Tenor", "Operating CFADS inside the tenor", "$", lambda c, p, k: (
        f"={cf('CFADS_Op', c)}*{dt('Tenor_On', c)}"), name_range=False)
    S(ws, 10, "Parity", "Check: target - scheduled service / scale", "$", lambda c, p, k: (
        f"=MIN({cf('CFADS_P50', c)}/DSCR_P50_Target,{cf('CFADS_P90', c)}/DSCR_P90_Target)*{dt('Tenor_On', c)}"
        f"-{dt('Debt_Service', c)}/Sculpt_Scale"), "usd2")
    S(ws, 11, "Parity_Abs", "Absolute parity error", "$", lambda c, p, k: f"=ABS({rr('Parity', c)})", "usd2",
      name_range=False)
    S(ws, 12, "Lockup_Flag", "Below lock-up (1 = yes)", "flag", lambda c, p, k: (
        f'=IF({dt("Tenor_On", c)}=1,IF({cf("CFADS_Op", c)}/{dt("Debt_Service", c)}<DSCR_Lockup,1,0),0)'), "int",
      name_range=False)
    S(ws, 13, "Default_Flag", "Below default trigger (1 = yes)", "flag", lambda c, p, k: (
        f'=IF({dt("Tenor_On", c)}=1,IF({cf("CFADS_Op", c)}/{dt("Debt_Service", c)}<DSCR_Default_PF,1,0),0)'), "int",
      name_range=False)
    s = b.scalar
    row = 15
    for case in ("P50", "P90", "Op"):
        s(ws, row, f"Min_DSCR_{case}", f"Minimum DSCR, {case}", "x", f"=MIN({b.span(T, f'DSCR_{case}', here=T)})", "x")
        s(ws, row + 1, f"Avg_DSCR_{case}", f"Average DSCR, {case}", "x", f"=AVERAGE({b.span(T, f'DSCR_{case}', here=T)})", "x")
        row += 2
    s(ws, row, "LLCR", "LLCR (P50)", "x", f"=NPV(Rate,{b.span(T, 'CFADS_P50_Tenor', here=T)})/Debt", "x")
    s(ws, row + 1, "PLCR", "PLCR (P50)", "x", f"=NPV(Rate,{b.span('CFADS', 'CFADS_P50')})/Debt", "x")
    s(ws, row + 2, "LLCR_Op", "LLCR, operating case", "x", f"=NPV(Rate,{b.span(T, 'CFADS_Op_Tenor', here=T)})/Debt", "x")
    s(ws, row + 3, "Lockup_Years", "Years below the distribution lock-up (operating case)", "years",
      f"=SUM({b.span(T, 'Lockup_Flag', here=T)})", "int")
    s(ws, row + 4, "Default_Years", "Years below the default trigger (operating case)", "years",
      f"=SUM({b.span(T, 'Default_Flag', here=T)})", "int")


def _tax(b: Book) -> None:
    T = "Tax"
    ws = b.sheet(T, "Tax", "Sponsor-level tax on operating CFADS less interest and MACRS depreciation; losses "
                 "are used as they arise (a tax-efficient sponsor). Texas has no corporate income tax.")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    b.scalar(ws, 5, "Dep_Basis", "Depreciable basis (less 50% of credits)", "$",
             "=Project_Capex-ITC_Basis_Reduction*(ITC_PV*PV_Capex+ITC_BESS*BESS_Capex)")
    S = b.series
    S(ws, 7, "Depreciation", "MACRS depreciation", "$", lambda c, p, k: (
        f"=IF({yr(c)}<=COUNT(MACRS_Table),Dep_Basis*INDEX(MACRS_Table,{yr(c)}),0)"))
    S(ws, 8, "Taxable_Income", "Taxable income", "$", lambda c, p, k: (
        f"={b.ref('CFADS', 'CFADS_Op', c)}-{b.ref('Debt_Sculpt', 'Interest', c)}-{rr('Depreciation', c)}"))
    S(ws, 9, "Tax", "Tax (negative = benefit used by the sponsor)", "$", lambda c, p, k: f"=Tax_Rate*{rr('Taxable_Income', c)}")


def _returns(b: Book) -> None:
    T = "Returns"
    ws = b.sheet(T, "Returns", "Year 0 = financial close. Equity receives operating CFADS less scheduled debt "
                 "service, and the DSRA back at maturity.", year0=True)
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    cf = lambda c: b.ref("CFADS", "CFADS_Op", c)                             # noqa: E731
    ds = lambda c: b.ref("Debt_Sculpt", "Debt_Service", c)                   # noqa: E731
    tx = lambda k, c: b.ref("Tax", k, c)                                     # noqa: E731
    last = b.cols[-1]
    S = b.series
    S(ws, 5, "DSRA_Release", "DSRA released at maturity", "$", lambda c, p, k: f"=IF({yr(c)}=Tenor,DSRA,0)")

    def cf_row(row, key, label, year0, fn):
        S(ws, row, key, label, "$", fn, name_range=False)
        ws[f"C{row}"] = year0
        ws[f"C{row}"].number_format = FMT["usd"]
        b.name(f"R_{key}", T, f"$C${row}:${last}${row}")

    cf_row(7, "Project_CF", "Project cash flow, pre-tax", "=-Project_Capex+ITC_Proceeds", lambda c, p, k: f"={cf(c)}")
    cf_row(8, "Equity_CF", "Equity cash flow, pre-tax", "=-Equity",
           lambda c, p, k: f"={cf(c)}-{ds(c)}+{rr('DSRA_Release', c)}")
    cf_row(9, "Project_CF_AT", "Project cash flow, after tax", "=C7",
           lambda c, p, k: f"={cf(c)}-Tax_Rate*({cf(c)}-{tx('Depreciation', c)})")
    cf_row(10, "Equity_CF_AT", "Equity cash flow, after tax", "=C8", lambda c, p, k: f"={c}8-{tx('Tax', c)}")
    s = b.scalar
    first = b.cols[0]
    s(ws, 12, "Project_IRR", "Project IRR, pre-tax", "%", f'=IFERROR(IRR(C7:{last}7),"n/m")', "pct")
    s(ws, 13, "Equity_IRR", "Equity IRR, pre-tax", "%", f'=IFERROR(IRR(C8:{last}8),"n/m")', "pct")
    s(ws, 14, "Project_IRR_AT", "Project IRR, after tax", "%", f'=IFERROR(IRR(C9:{last}9),"n/m")', "pct")
    s(ws, 15, "Equity_IRR_AT", "Equity IRR, after tax", "%", f'=IFERROR(IRR(C10:{last}10),"n/m")', "pct", bold=True)
    s(ws, 16, "Equity_Multiple", "Equity multiple, pre-tax", "x", f"=SUM({first}8:{last}8)/Equity", "x")
    s(ws, 17, "Equity_NPV_At_IRR", "Check: NPV at the pre-tax equity IRR", "$", f"=IF(ISNUMBER(Equity_IRR),NPV(Equity_IRR,{first}8:{last}8)+C8,0)", "usd2")
    s(ws, 18, "Equity_NPV_At_IRR_AT", "Check: NPV at the after-tax equity IRR", "$",
      f"=IF(ISNUMBER(Equity_IRR_AT),NPV(Equity_IRR_AT,{first}10:{last}10)+C10,0)", "usd2")
    b.section(ws, 20, "Output and emissions")
    g1 = b.ref("Generation", "Gen_P50", first)
    s(ws, 21, "Gen_Y1_P50", "Generation, year 1 (P50)", "MWh", f"={g1}", "num")
    s(ws, 22, "Net_CF_Y1", "Net capacity factor, year 1", "%", f"={g1}/(PV_MWac*Hours_Per_Year)", "pct1")
    s(ws, 23, "tCO2e_Avoided_Y1", "Grid emissions displaced, year 1 (average rate)", "tCO2e", f"={g1}*Grid_CO2e_lb_MWh/lb_per_t", "num")
    s(ws, 24, "tCO2e_Avoided_Life", "Grid emissions displaced, project life", "tCO2e",
      f"=SUM({b.span('Generation', 'Gen_P50')})*Grid_CO2e_lb_MWh/lb_per_t", "num")
    s(ws, 25, "Capex_Per_tCO2e", "Project capex per tonne displaced", "$/tCO2e", "=Project_Capex/tCO2e_Avoided_Life", "usd2")


def _checks(b: Book) -> None:
    ws = b.sheet("Checks", "Checks", "Each check returns TRUE when it passes.", year_header=False)
    checks = [
        ("Check_SU", "Sources = uses", "=ABS(Total_Sources-Total_Uses)<=Tolerance"),
        ("Check_Debt_PV", "Debt = NPV of scheduled debt service at the coupon",
         f"=ABS(NPV(Rate,{b.span('Debt_Sculpt', 'Debt_Service')})-Debt)<=Tolerance*Debt"),
        ("Check_Repaid", "Debt fully repaid at maturity",
         f"=ABS(INDEX({b.span('Debt_Sculpt', 'End_Balance')},1,Tenor))<=Tolerance*Debt"),
        ("Check_No_Negative", "Balance never negative", f"=MIN({b.span('Debt_Sculpt', 'End_Balance')})>=-Tolerance*Debt"),
        ("Check_Parity", "Scheduled service = target service x scale in every year",
         f"=MAX(Ratios!{b.cols[0]}11:{b.cols[-1]}11)<=Tolerance*Debt"),
        ("Check_DSCR_P50", "P50 DSCR at or above target", "=Min_DSCR_P50>=DSCR_P50_Target-Tolerance"),
        ("Check_DSCR_P90", "P90 DSCR at or above target", "=Min_DSCR_P90>=DSCR_P90_Target-Tolerance"),
        ("Check_Gearing", "Debt within gearing cap", "=Debt<=Debt_Capacity_Gearing+Tolerance"),
        ("Check_Tenor", "Debt matures inside the PPA and the model", f"=AND(Tenor<=PPA_Term,Tenor<=COUNT(Generation!"
                                                                      f"{b.cols[0]}4:{b.cols[-1]}4))"),
        ("Check_IRR", "NPV at the equity IRRs is zero",
         "=AND(ABS(Equity_NPV_At_IRR)<=Tolerance*Equity,ABS(Equity_NPV_At_IRR_AT)<=Tolerance*Equity)"),
    ]
    for row, (key, label, f) in enumerate(checks, start=4):
        b.scalar(ws, row, key, label, "", f, "text")
    row = 4 + len(checks) + 1
    b.scalar(ws, row, "All_Checks", "All checks pass", "", "=AND(" + ",".join(k for k, _, _ in checks) + ")",
             "text", bold=True)


def _summary(b: Book) -> None:
    from cau.xlsx.book import BOLD
    ws = b.wb.create_sheet("Summary")
    ws.sheet_view.showGridLines = False
    for c, w in zip("ABC", (50, 20, 14), strict=True):
        ws.column_dimensions[c].width = w
    ws["A1"] = "Summary"
    ws["A1"].font = BOLD
    rows = [
        ("Project capex", "=Project_Capex", "$", "usd"), ("Senior debt", "=Debt", "$", "usd"),
        ("Gearing (debt / project capex)", "=Gearing", "%", "pct1"), ("Tax-credit proceeds", "=ITC_Proceeds", "$", "usd"),
        ("Sponsor equity", "=Equity", "$", "usd"), ("Coupon", "=Rate", "%", "pct"),
        ("Minimum DSCR, P50", "=Min_DSCR_P50", "x", "x"), ("Minimum DSCR, P90", "=Min_DSCR_P90", "x", "x"),
        ("Minimum DSCR, operating case", "=Min_DSCR_Op", "x", "x"), ("LLCR", "=LLCR", "x", "x"),
        ("PLCR", "=PLCR", "x", "x"), ("Project IRR, pre-tax", "=Project_IRR", "%", "pct"),
        ("Equity IRR, pre-tax", "=Equity_IRR", "%", "pct"), ("Equity IRR, after tax", "=Equity_IRR_AT", "%", "pct"),
        ("Generation, year 1 (P50)", "=Gen_Y1_P50", "MWh", "num"), ("Net capacity factor, year 1", "=Net_CF_Y1", "%", "pct1"),
        ("Grid emissions displaced, year 1", "=tCO2e_Avoided_Y1", "tCO2e", "num"),
    ]
    for row, (label, f, unit, fmt) in enumerate(rows, start=3):
        ws[f"A{row}"], ws[f"B{row}"], ws[f"C{row}"] = label, f, unit
        ws[f"B{row}"].number_format = FMT[fmt]
