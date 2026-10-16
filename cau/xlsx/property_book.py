"""Builds models/property_underwriting.xlsx: every calculation is a live Excel formula that reads
named inputs, mirroring cau/engine/property.py line for line."""
from __future__ import annotations

from pathlib import Path

from cau.engine import stress as ST
from cau.engine.property import YEARS
from cau.inputs import Input
from cau.xlsx.book import BOLD, FMT, Book
from cau.xlsx.scenarios import scenario_values, scenarios_sheet

REPO = Path(__file__).resolve().parents[2]

TABS = [
    ("Summary", "Key outputs, status quo against the retrofit case"),
    ("Inputs", "Every assumption with its tag (Sourced / Estimated / Illustrative / Definition) and source id"),
    ("Sources", "Citations, URLs and retrieval dates"),
    ("RentRoll", "Unit mix and year-1 gross potential rent"),
    ("Energy", "Energy by end use before and after the retrofit; EUI; Scope 1 and 2 emissions"),
    ("Operating", "Eleven-year operating statement for both cases (year 11 feeds the exit value)"),
    ("Debt", "Loan sizing (LTV, DSCR and debt-yield limits) and the amortisation schedule"),
    ("Covenants", "DSCR and debt yield by year against cash-trap and default levels, with headroom"),
    ("Returns", "Sources and uses, exit value, unlevered and levered cash flows, IRR and multiple"),
    ("Retrofit", "Retrofit capex, payback, value impact, cost per tonne and BEPS position"),
    ("Scenarios", "Base / Downside / Severe (loan held at close), one-factor sensitivities, break-even vacancy"),
    ("Checks", "Integrity checks; the Cover shows whether all pass"),
]


def build(inputs: list[Input], path: Path) -> Path:
    b = Book(YEARS)
    b.inputs_sheet(inputs, scenario_values("property", inputs))
    b.sources_sheet(inputs)
    _rent_roll(b)
    _energy(b)
    _operating(b)
    _debt(b)
    _covenants(b)
    _returns(b)
    _retrofit(b)
    _checks(b)
    _summary(b)
    be = ST.breakeven_vacancy()
    scenarios_sheet(b, "property", [("Lev_IRR_RF", "levered IRR, retrofit", "pct"),
                                    ("Min_DSCR_SQ", "minimum DSCR, status quo", "x")],
                    [("Vacancy at which minimum DSCR hits the 1.10x default (loan held)", be["vacancy"], "pct1")])
    b.cover("Multifamily acquisition and decarbonization retrofit",
            "150 units, Washington DC (illustrative). Status quo against an electrification + solar retrofit.",
            inputs, TABS, REPO, "All_Checks")
    order = ["Cover", "Summary", "Inputs", "Sources", "RentRoll", "Energy", "Operating", "Debt", "Covenants",
             "Returns", "Retrofit", "Scenarios", "Checks"]
    b.wb._sheets = [b.wb[n] for n in order]
    return b.save(path)


# ── tabs ────────────────────────────────────────────────────────────────────

def _rent_roll(b: Book) -> None:
    ws = b.sheet("RentRoll", "Rent roll", "Year-1 in-place rents; growth is applied on the Operating tab.",
                 year_header=False)
    hdr = ["Unit type", "Units", "Avg size (sf)", "Rent ($/month)", "Annual GPR", "Total sf"]
    for c, h in zip("ABCDEF", hdr, strict=True):
        ws[f"{c}4"] = h
        ws[f"{c}4"].font = BOLD
    for c in "DEF":
        ws.column_dimensions[c].width = 15
    for row, k in enumerate(("Studio", "1BR", "2BR", "3BR"), start=5):
        ws[f"A{row}"] = k
        ws[f"B{row}"] = f"=Units_{k}"
        ws[f"C{row}"] = f"=SF_{k}"
        ws[f"D{row}"] = f"=Rent_{k}"
        ws[f"E{row}"] = f"=B{row}*D{row}*Months"
        ws[f"F{row}"] = f"=B{row}*C{row}"
        for c, f in zip("BCDEF", ("num", "num", "usd", "usd", "num"), strict=True):
            ws[f"{c}{row}"].number_format = FMT[f]
    ws["A9"] = "Total"
    ws["A9"].font = BOLD
    for c, f in zip("BEF", ("num", "usd", "num"), strict=True):
        ws[f"{c}9"] = f"=SUM({c}5:{c}8)"
        ws[f"{c}9"].number_format = FMT[f]
        ws[f"{c}9"].font = BOLD
    ws["D9"] = "=E9/B9/Months"
    ws["D9"].number_format = FMT["usd"]
    b.name("Units", "RentRoll", "$B$9")
    b.name("GPR_Y1", "RentRoll", "$E$9")
    b.name("NRSF", "RentRoll", "$F$9")


def _energy(b: Book) -> None:
    ws = b.sheet("Energy", "Energy and emissions",
                 "Annual quantities, held flat over the hold. Whole-building site EUI follows ENERGY STAR "
                 "(on-site solar consumed counts as site energy).", year_header=False)
    s = b.scalar
    b.section(ws, 4, "Baseline (status quo)")
    s(ws, 5, "Site_MMBtu_Base", "Site energy", "MMBtu/yr", "=GFA*Site_EUI_Base/kBtu_per_MMBtu", "num")
    s(ws, 6, "Gas_Heat_MMBtu", "Gas, space heating", "MMBtu/yr", "=Site_MMBtu_Base*Share_Heat_Gas", "num")
    s(ws, 7, "Gas_DHW_MMBtu", "Gas, hot water", "MMBtu/yr", "=Site_MMBtu_Base*Share_DHW_Gas", "num")
    s(ws, 8, "Gas_SQ_MMBtu", "Gas, owner-paid total", "MMBtu/yr", "=Gas_Heat_MMBtu+Gas_DHW_MMBtu", "num")
    s(ws, 9, "Common_kWh", "Electricity, common areas (owner)", "kWh/yr",
      "=Site_MMBtu_Base*Share_Common_Elec*kWh_per_MMBtu", "num")
    s(ws, 10, "Tenant_kWh", "Electricity, in-unit (tenant)", "kWh/yr",
      "=Site_MMBtu_Base*Share_Tenant_Elec*kWh_per_MMBtu", "num")
    s(ws, 11, "Gas_Price_MMBtu", "Gas price", "$/MMBtu", "=Gas_Price_Mcf/Gas_MMBtu_Per_Mcf", "usd2")
    b.section(ws, 13, "Retrofit")
    s(ws, 14, "HP_Heat_kWh", "Heat pump electricity, space heating", "kWh/yr",
      "=Gas_Heat_MMBtu*(1-Gas_Retained_Share)*Boiler_Eff*(1-Envelope_Heat_Reduction)/COP_Heat*kWh_per_MMBtu", "num")
    s(ws, 15, "HP_DHW_kWh", "Heat pump electricity, hot water", "kWh/yr",
      "=Gas_DHW_MMBtu*(1-Gas_Retained_Share)*Boiler_Eff/COP_DHW*kWh_per_MMBtu", "num")
    s(ws, 16, "Gas_RF_MMBtu", "Gas retained", "MMBtu/yr", "=Gas_SQ_MMBtu*Gas_Retained_Share", "num")
    s(ws, 17, "Common_RF_kWh", "Common-area electricity after LEDs", "kWh/yr", "=Common_kWh*(1-LED_Savings)", "num")
    s(ws, 18, "Owner_Gross_RF_kWh", "Owner electricity use", "kWh/yr",
      "=Common_RF_kWh+HP_Heat_kWh+HP_DHW_kWh", "num")
    s(ws, 19, "Solar_kWh", "Rooftop solar generation", "kWh/yr", "=Solar_kWdc*Solar_Yield", "num")
    s(ws, 20, "Grid_RF_kWh", "Owner grid purchases", "kWh/yr", "=Owner_Gross_RF_kWh-Solar_kWh", "num")
    b.section(ws, 22, "Energy use intensity")
    s(ws, 23, "EUI_Base", "Site EUI, status quo", "kBtu/sf", "=Site_EUI_Base", "num1")
    s(ws, 24, "EUI_RF", "Site EUI, retrofit", "kBtu/sf",
      "=(Tenant_kWh+Owner_Gross_RF_kWh+Gas_RF_MMBtu*kWh_per_MMBtu)*kBtu_per_MMBtu/kWh_per_MMBtu/GFA", "num1")
    s(ws, 25, "EUI_RF_Net_Solar", "Site EUI net of on-site solar", "kBtu/sf",
      "=(Tenant_kWh+Grid_RF_kWh+Gas_RF_MMBtu*kWh_per_MMBtu)*kBtu_per_MMBtu/kWh_per_MMBtu/GFA", "num1")
    s(ws, 26, "EUI_Reduction", "Site EUI reduction", "%", "=1-EUI_RF/EUI_Base", "pct1")
    b.section(ws, 28, "Emissions")
    s(ws, 29, "NG_tCO2e_MMBtu", "Natural gas factor (CO2 + CH4 + N2O)", "tCO2e/MMBtu",
      "=(NG_CO2_kg_MMBtu+(NG_CH4_g_MMBtu*GWP_CH4+NG_N2O_g_MMBtu*GWP_N2O)/g_per_kg)/kg_per_t", "num4")
    s(ws, 30, "Grid_tCO2e_kWh", "Grid factor", "tCO2e/kWh", "=Grid_CO2e_lb_MWh/kWh_per_MWh/lb_per_t", "sci")
    s(ws, 31, "Scope1_SQ", "Scope 1, status quo (owner gas)", "tCO2e/yr", "=Gas_SQ_MMBtu*NG_tCO2e_MMBtu", "num1")
    s(ws, 32, "Scope2_SQ", "Scope 2, status quo (owner electricity)", "tCO2e/yr", "=Common_kWh*Grid_tCO2e_kWh", "num1")
    s(ws, 33, "Scope1_RF", "Scope 1, retrofit", "tCO2e/yr", "=Gas_RF_MMBtu*NG_tCO2e_MMBtu", "num1")
    s(ws, 34, "Scope2_RF", "Scope 2, retrofit", "tCO2e/yr", "=Grid_RF_kWh*Grid_tCO2e_kWh", "num1")
    s(ws, 35, "Tenant_tCO2e", "Tenant electricity (Scope 3, cat. 13), both cases", "tCO2e/yr",
      "=Tenant_kWh*Grid_tCO2e_kWh", "num1")
    s(ws, 36, "Owner_tCO2e_SQ", "Owner Scope 1 + 2, status quo", "tCO2e/yr", "=Scope1_SQ+Scope2_SQ", "num1")
    s(ws, 37, "Owner_tCO2e_RF", "Owner Scope 1 + 2, retrofit", "tCO2e/yr", "=Scope1_RF+Scope2_RF", "num1")
    s(ws, 38, "tCO2e_Avoided", "Owner emissions avoided", "tCO2e/yr", "=Owner_tCO2e_SQ-Owner_tCO2e_RF", "num1",
      bold=True)


def _operating(b: Book) -> None:
    T = "Operating"
    ws = b.sheet(T, "Operating statement", "Common lines are shared; utilities, NOI and cash flow are shown for "
                 "both cases. SQ = status quo, RF = retrofit.")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    row = 6
    b.section(ws, 5, "Indices")

    def idx(key, label, growth):
        nonlocal row
        b.series(ws, row, key, label, "index", lambda c, p, k: f"=(1+{growth})^({yr(c)}-1)", "num4", name_range=False)
        row += 1
    idx("Rent_Index", "Rent", "Rent_Growth")
    idx("OI_Index", "Other income", "Other_Income_Growth")
    idx("Exp_Index", "Operating expenses", "Expense_Growth")
    idx("Tax_Index", "Assessed value", "Tax_Growth")
    idx("Util_Index", "Utility prices", "Utility_Price_Growth")

    row += 1
    b.section(ws, row, "Revenue")
    row += 1
    S = b.series
    S(ws, row, "GPR", "Gross potential rent", "$", lambda c, p, k: f"=GPR_Y1*{rr('Rent_Index', c)}")
    row += 1
    S(ws, row, "Vacancy", "Vacancy and credit loss", "$", lambda c, p, k: f"=-{rr('GPR', c)}*Vacancy_Rate")
    row += 1
    S(ws, row, "Other_Income", "Other income", "$",
      lambda c, p, k: f"=Other_Income_Per_Unit*Units*{rr('OI_Index', c)}")
    row += 1
    S(ws, row, "EGI", "Effective gross income", "$",
      lambda c, p, k: f"={rr('GPR', c)}+{rr('Vacancy', c)}+{rr('Other_Income', c)}", total=True)
    row += 2

    b.section(ws, row, "Operating expenses (shared)")
    row += 1
    S(ws, row, "Taxes", "Real estate taxes", "$",
      lambda c, p, k: f"=Assessed_Value_Per_Unit*Units*Tax_Rate*{rr('Tax_Index', c)}")
    row += 1
    for key, label, inp in [("Insurance", "Insurance", "Insurance_Per_Unit"),
                            ("Water_Sewer", "Water and sewer", "Water_Sewer_Per_Unit"),
                            ("Repairs", "Repairs and maintenance", "Repairs_Per_Unit"),
                            ("Payroll", "Payroll", "Payroll_Per_Unit"), ("Admin", "G&A and marketing", "Admin_Per_Unit")]:
        S(ws, row, key, label, "$", lambda c, p, k, inp=inp: f"={inp}*Units*{rr('Exp_Index', c)}")
        row += 1
    S(ws, row, "Mgmt_Fee", "Management fee", "$", lambda c, p, k: f"=Mgmt_Fee_Pct*{rr('EGI', c)}")
    row += 1
    shared = ("Taxes", "Insurance", "Water_Sewer", "Repairs", "Payroll", "Admin", "Mgmt_Fee")
    S(ws, row, "Shared_Opex", "Shared operating expenses", "$",
      lambda c, p, k: "=" + "+".join(rr(x, c) for x in shared), total=True)
    row += 2

    b.section(ws, row, "Owner-paid utilities")
    row += 1
    S(ws, row, "Gas_Cost_SQ", "Gas, status quo", "$", lambda c, p, k: f"=Gas_SQ_MMBtu*Gas_Price_MMBtu*{rr('Util_Index', c)}")
    row += 1
    S(ws, row, "Elec_Cost_SQ", "Electricity, status quo", "$", lambda c, p, k: f"=Common_kWh*Elec_Price*{rr('Util_Index', c)}")
    row += 1
    S(ws, row, "Gas_Cost_RF", "Gas, retrofit", "$", lambda c, p, k: f"=Gas_RF_MMBtu*Gas_Price_MMBtu*{rr('Util_Index', c)}")
    row += 1
    S(ws, row, "Elec_Cost_RF", "Electricity, retrofit (grid purchases)", "$",
      lambda c, p, k: f"=Grid_RF_kWh*Elec_Price*{rr('Util_Index', c)}")
    row += 2

    b.section(ws, row, "Net operating income and cash flow")
    row += 1
    for case in ("SQ", "RF"):
        S(ws, row, f"Opex_{case}", f"Total operating expenses, {case}", "$",
          lambda c, p, k, case=case: f"={rr('Shared_Opex', c)}+{rr(f'Gas_Cost_{case}', c)}+{rr(f'Elec_Cost_{case}', c)}")
        row += 1
    for case in ("SQ", "RF"):
        S(ws, row, f"NOI_{case}", f"Net operating income, {case}", "$",
          lambda c, p, k, case=case: f"={rr('EGI', c)}-{rr(f'Opex_{case}', c)}", total=True)
        row += 1
    S(ws, row, "Reserves", "Replacement reserves", "$",
      lambda c, p, k: f"=Reserve_Per_Unit*Units*{rr('Exp_Index', c)}")
    row += 1
    for case in ("SQ", "RF"):
        S(ws, row, f"NCF_{case}", f"Net cash flow after reserves, {case}", "$",
          lambda c, p, k, case=case: f"={rr(f'NOI_{case}', c)}-{rr('Reserves', c)}", total=True)
        row += 1
    S(ws, row, "Boiler_Capex_SQ", "Boiler replacement (status quo only)", "$",
      lambda c, p, k: f"=IF({yr(c)}=Boiler_Replace_Year,Boiler_Replace_Cost*{rr('Exp_Index', c)},0)")


def _debt(b: Book) -> None:
    T = "Debt"
    ws = b.sheet(T, "Debt", "Sized on status-quo year-1 cash flow; the same loan funds both cases. "
                 "Monthly payments, shown annually.")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    d1 = b.cols[0]
    b.section(ws, 5, "Sizing")
    s = b.scalar
    s(ws, 6, "Rate_Fixed", "Fixed rate (Treasury + spread)", "%", "=UST_10Y+Fixed_Spread", "pct")
    s(ws, 7, "Rate_Float", "Floating rate (SOFR + shock + spread)", "%", "=SOFR+SOFR_Shock+Float_Spread", "pct")
    s(ws, 8, "Debt_Constant", "Annual debt constant (amortising)", "%",
      f"=PMT({d1}21/Months,Amort_Months,-1)*Months", "pct")
    s(ws, 9, "Max_Loan_LTV", "Maximum loan, LTV test", "$", "=LTV_Max*Price")
    s(ws, 10, "Max_Loan_DSCR", "Maximum loan, DSCR test", "$",
      f"={b.ref('Operating', 'NCF_SQ', d1)}/(DSCR_Sizing*Debt_Constant)")
    s(ws, 11, "Max_Loan_DY", "Maximum loan, debt-yield test", "$", f"={b.ref('Operating', 'NOI_SQ', d1)}/DY_Sizing")
    s(ws, 12, "Loan", "Loan amount", "$", "=IF(Loan_Override>0,Loan_Override,MIN(Max_Loan_LTV,Max_Loan_DSCR,Max_Loan_DY))", bold=True)
    s(ws, 13, "Binding_Test", "Binding constraint", "",
      '=IF(Loan_Override>0,"Override",IF(Loan=Max_Loan_DSCR,"DSCR",IF(Loan=Max_Loan_LTV,"LTV","Debt yield")))', "text")
    s(ws, 14, "LTV", "Loan to value", "%", "=Loan/Price", "pct1")
    b.section(ws, 20, "Schedule")
    S = b.series
    assert b.r(T, "Year") == 4
    S(ws, 21, "Rate", "Interest rate", "%", lambda c, p, k: "=IF(Debt_Option=1,Rate_Fixed,Rate_Float)", "pct")
    S(ws, 22, "IO_Flag", "Interest-only year (1 = yes)", "flag",
      lambda c, p, k: f"=IF({yr(c)}<=IO_Years,1,0)", "int", name_range=False)
    S(ws, 23, "Beg_Balance", "Opening balance", "$", lambda c, p, k: "=Loan" if p is None else f"={p}26")
    S(ws, 24, "Monthly_Payment", "Monthly payment", "$", lambda c, p, k: (
        f"=IF({rr('IO_Flag', c)}=1,{rr('Beg_Balance', c)}*{rr('Rate', c)}/Months,"
        f"PMT({rr('Rate', c)}/Months,Amort_Months-Months*({yr(c)}-1-IO_Years),-{rr('Beg_Balance', c)}))"), "usd")
    S(ws, 25, "Debt_Service", "Annual debt service", "$", lambda c, p, k: f"={rr('Monthly_Payment', c)}*Months")
    S(ws, 26, "End_Balance", "Closing balance", "$", lambda c, p, k: (
        f"=IF({rr('IO_Flag', c)}=1,{rr('Beg_Balance', c)},"
        f"FV({rr('Rate', c)}/Months,Months,{rr('Monthly_Payment', c)},-{rr('Beg_Balance', c)}))"))
    S(ws, 27, "Principal", "Principal repaid", "$", lambda c, p, k: f"={rr('Beg_Balance', c)}-{rr('End_Balance', c)}")
    S(ws, 28, "Interest", "Interest paid", "$", lambda c, p, k: f"={rr('Debt_Service', c)}-{rr('Principal', c)}")
    S(ws, 29, "DS_Check", "Check: service - interest - principal", "$", lambda c, p, k: (
        f"=ABS({rr('Debt_Service', c)}-{rr('Interest', c)}-{rr('Principal', c)})"), "usd2")


def _covenants(b: Book) -> None:
    T = "Covenants"
    ws = b.sheet(T, "Covenant tests", "DSCR on net cash flow after reserves over annual debt service; debt "
                 "yield on NOI over the opening balance. Headroom = NOI decline that would hit the cash-trap level.")
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    S = b.series
    S(ws, 5, "Cov_In_Hold", "In hold period (1 = yes)", "flag", lambda c, p, k: f"=IF({yr(c)}<=Hold_Years,1,0)", "int")
    row = 7
    for case, name in (("SQ", "status quo"), ("RF", "retrofit")):
        b.section(ws, row, f"Case: {name}")
        row += 1
        S(ws, row, f"DSCR_{case}", "DSCR", "x", lambda c, p, k, case=case: (
            f"={b.ref('Operating', f'NCF_{case}', c)}/{b.ref('Debt', 'Debt_Service', c)}"), "x")
        row += 1
        S(ws, row, f"DSCR_Headroom_{case}", "DSCR headroom to cash trap", "%", lambda c, p, k, case=case: (
            f"=1-DSCR_Trap/{rr(f'DSCR_{case}', c)}"), "pct1")
        row += 1
        S(ws, row, f"DSCR_Flag_{case}", "DSCR status", "", lambda c, p, k, case=case: (
            f'=IF({rr(f"DSCR_{case}", c)}<DSCR_Default,"BREACH",IF({rr(f"DSCR_{case}", c)}<DSCR_Trap,"CASH TRAP","OK"))'),
          "text")
        row += 1
        S(ws, row, f"DY_{case}", "Debt yield", "%", lambda c, p, k, case=case: (
            f"={b.ref('Operating', f'NOI_{case}', c)}/{b.ref('Debt', 'Beg_Balance', c)}"), "pct")
        row += 1
        S(ws, row, f"DY_Headroom_{case}", "Debt-yield headroom to cash trap", "%", lambda c, p, k, case=case: (
            f"=1-DY_Trap/{rr(f'DY_{case}', c)}"), "pct1")
        row += 1
        S(ws, row, f"DY_Flag_{case}", "Debt-yield status", "", lambda c, p, k, case=case: (
            f'=IF({rr(f"DY_{case}", c)}<DY_Default,"BREACH",IF({rr(f"DY_{case}", c)}<DY_Trap,"CASH TRAP","OK"))'),
          "text")
        row += 1
        S(ws, row, f"DSCR_Hold_{case}", "DSCR within hold (for the minimum)", "x", lambda c, p, k, case=case: (
            f'=IF({rr("Cov_In_Hold", c)}=1,{rr(f"DSCR_{case}", c)},"")'), "x", name_range=False)
        row += 1
        S(ws, row, f"DY_Hold_{case}", "Debt yield within hold (for the minimum)", "%", lambda c, p, k, case=case: (
            f'=IF({rr("Cov_In_Hold", c)}=1,{rr(f"DY_{case}", c)},"")'), "pct", name_range=False)
        row += 1
        for m in ("DSCR", "DY"):
            S(ws, row, f"{m}_Flag_Hold_{case}", f"{m} status within hold", "", lambda c, p, k, case=case, m=m: (
                f'=IF({rr("Cov_In_Hold", c)}=1,{rr(f"{m}_Flag_{case}", c)},"")'), "text", name_range=False)
            row += 1
        row -= 1
        row += 2
    b.section(ws, row, "Summary over the hold")
    row += 1
    for case in ("SQ", "RF"):
        b.scalar(ws, row, f"Min_DSCR_{case}", f"Minimum DSCR, {case}", "x",
                 f"=MIN({b.span(T, f'DSCR_Hold_{case}', here=T)})", "x")
        row += 1
        b.scalar(ws, row, f"Min_DY_{case}", f"Minimum debt yield, {case}", "%",
                 f"=MIN({b.span(T, f'DY_Hold_{case}', here=T)})", "pct")
        row += 1
        b.scalar(ws, row, f"Trap_Years_{case}", f"Covenant flag-years in the hold (DSCR + debt yield), {case}",
                 "count", f'=COUNTIF({b.span(T, f"DSCR_Flag_Hold_{case}", here=T)},"<>OK")-'
                 f'COUNTIF({b.span(T, f"DSCR_Flag_Hold_{case}", here=T)},"")+'
                 f'COUNTIF({b.span(T, f"DY_Flag_Hold_{case}", here=T)},"<>OK")-'
                 f'COUNTIF({b.span(T, f"DY_Flag_Hold_{case}", here=T)},"")', "int")
        row += 1


def _returns(b: Book) -> None:
    T = "Returns"
    ws = b.sheet(T, "Returns", "Year 0 = closing. The exit is at the end of the hold on forward (next-year) NOI.",
                 year0=True)
    rr = lambda k, c: b.ref(T, k, c, here=T)                                 # noqa: E731
    yr = lambda c: f"{c}{b.r(T, 'Year')}"                                    # noqa: E731
    S = b.series
    S(ws, 5, "In_Hold", "In hold period (1 = yes)", "flag", lambda c, p, k: f"=IF({yr(c)}<=Hold_Years,1,0)", "int")
    S(ws, 6, "Exit_Flag", "Exit year (1 = yes)", "flag", lambda c, p, k: f"=IF({yr(c)}=Hold_Years,1,0)", "int")
    first, last = b.cols[0], b.cols[-1]

    def cf_row(row, key, label, year0, fn):
        S(ws, row, key, label, "$", fn, total=False, name_range=False)
        ws[f"C{row}"] = year0
        ws[f"C{row}"].number_format = FMT["usd"]
        b.name(f"R_{key}", T, f"$C${row}:${last}${row}")

    cf_row(8, "Unlev_CF_SQ", "Unlevered cash flow, status quo", "=-(Price+Closing_Costs)",
           lambda c, p, k: (f"={rr('In_Hold', c)}*({b.ref('Operating', 'NCF_SQ', c)}-{b.ref('Operating', 'Boiler_Capex_SQ', c)})"
                            f"+{rr('Exit_Flag', c)}*Net_Sale_SQ"))
    cf_row(9, "Unlev_CF_RF", "Unlevered cash flow, retrofit", "=-(Price+Closing_Costs+Retrofit_Net)",
           lambda c, p, k: f"={rr('In_Hold', c)}*{b.ref('Operating', 'NCF_RF', c)}+{rr('Exit_Flag', c)}*Net_Sale_RF")
    for row, case in ((10, "SQ"), (11, "RF")):
        u = b.r(T, f"Unlev_CF_{case}")
        cf_row(row, f"Lev_CF_{case}", f"Levered cash flow, {case}", f"=C{u}+Loan-Loan_Fees",
               lambda c, p, k, u=u: (f"={c}{u}-{rr('In_Hold', c)}*{b.ref('Debt', 'Debt_Service', c)}"
                                     f"-{rr('Exit_Flag', c)}*{b.ref('Debt', 'End_Balance', c)}"))
    s = b.scalar
    b.section(ws, 13, "Sources and uses")
    s(ws, 14, "Closing_Costs", "Closing costs", "$", "=Closing_Cost_Pct*Price")
    s(ws, 15, "Loan_Fees", "Loan fees", "$", "=Loan_Fee_Pct*Loan")
    s(ws, 16, "Uses_SQ", "Total uses, status quo", "$", "=Price+Closing_Costs+Loan_Fees")
    s(ws, 17, "Uses_RF", "Total uses, retrofit (adds retrofit capex)", "$", "=Uses_SQ+Retrofit_Net")
    s(ws, 18, "Equity_SQ", "Equity, status quo", "$", "=Uses_SQ-Loan")
    s(ws, 19, "Equity_RF", "Equity, retrofit", "$", "=Uses_RF-Loan")
    b.section(ws, 21, "Exit")
    for row, case in ((22, "SQ"), (25, "RF")):
        s(ws, row, f"NOI_Fwd_{case}", f"Forward NOI at exit, {case}", "$",
          f"=INDEX({b.span('Operating', f'NOI_{case}')},1,Hold_Years+1)")
        s(ws, row + 1, f"Exit_Value_{case}", f"Gross exit value, {case}", "$", f"=NOI_Fwd_{case}/Exit_Cap")
        s(ws, row + 2, f"Net_Sale_{case}", f"Net sale proceeds, {case}", "$", f"=Exit_Value_{case}*(1-Sale_Cost_Pct)")
    b.section(ws, 29, "Returns")
    row = 30
    for case in ("SQ", "RF"):
        s(ws, row, f"Unlev_IRR_{case}", f"Unlevered IRR, {case}", "%", f'=IFERROR(IRR(C8:{last}8),"n/m")' if case == "SQ"
          else f'=IFERROR(IRR(C9:{last}9),"n/m")', "pct", bold=True)
        row += 1
        lr = b.r(T, f"Lev_CF_{case}")
        s(ws, row, f"Lev_IRR_{case}", f"Levered IRR, {case}", "%", f'=IFERROR(IRR(C{lr}:{last}{lr}),"n/m")', "pct", bold=True)
        row += 1
        s(ws, row, f"Equity_Multiple_{case}", f"Equity multiple, {case}", "x",
          f"=SUM({first}{lr}:{last}{lr})/-C{lr}", "x")
        row += 1
        s(ws, row, f"Lev_NPV_At_IRR_{case}", f"Check: NPV at the IRR, {case}", "$",
          f"=IF(ISNUMBER(Lev_IRR_{case}),NPV(Lev_IRR_{case},{first}{lr}:{last}{lr})+C{lr},0)", "usd2")
        row += 1
    s(ws, row, "Going_In_Cap", "Going-in cap rate (year-1 NOI, status quo)", "%",
      f"={b.ref('Operating', 'NOI_SQ', first)}/Price", "pct")
    row += 1
    s(ws, row, "Price_Per_Unit", "Price per unit", "$", "=Price/Units")


def _retrofit(b: Book) -> None:
    T = "Retrofit"
    ws = b.sheet(T, "Decarbonization retrofit", "Capex at closing, funded with equity. Savings are owner-paid "
                 "utilities only; tenant electricity is unchanged.", year_header=False)
    s = b.scalar
    d1 = b.cols[0]
    b.section(ws, 4, "Capex")
    s(ws, 5, "HP_Capex", "Central heat pump plant (heat + hot water)", "$", "=HP_Capex_Per_Unit*Units")
    s(ws, 6, "Envelope_Capex", "Envelope and air sealing", "$", "=Envelope_Capex_Per_SF*GFA")
    s(ws, 7, "LED_Capex", "LEDs and controls", "$", "=LED_Capex_Per_Unit*Units")
    s(ws, 8, "Solar_Capex", "Rooftop solar", "$", "=Solar_kWdc*Solar_Capex_Per_W*W_per_kW")
    s(ws, 9, "Retrofit_Gross", "Gross retrofit capex", "$", "=HP_Capex+Envelope_Capex+LED_Capex+Solar_Capex", bold=True)
    s(ws, 10, "Solar_ITC_Amt", "Less: solar tax credit", "$", "=Solar_ITC*Solar_Capex")
    s(ws, 11, "Retrofit_Net", "Net retrofit capex", "$", "=Retrofit_Gross-Solar_ITC_Amt", bold=True)
    b.section(ws, 13, "Economics")
    op = lambda k: b.ref("Operating", k, d1)                                 # noqa: E731
    s(ws, 14, "Utility_Savings_Y1", "Owner utility savings, year 1", "$",
      f"={op('Gas_Cost_SQ')}+{op('Elec_Cost_SQ')}-{op('Gas_Cost_RF')}-{op('Elec_Cost_RF')}")
    s(ws, 15, "Payback_Years", "Simple payback on utility savings", "years", "=Retrofit_Net/Utility_Savings_Y1", "num1")
    s(ws, 16, "Payback_Net_Boiler_Years", "Payback net of the avoided boiler replacement", "years",
      "=(Retrofit_Net-Boiler_Replace_Cost)/Utility_Savings_Y1", "num1")
    s(ws, 17, "Exit_Value_Uplift", "Exit value uplift from higher NOI", "$", "=Exit_Value_RF-Exit_Value_SQ")
    s(ws, 18, "Lev_IRR_Delta", "Levered IRR, retrofit minus status quo", "%", "=Lev_IRR_RF-Lev_IRR_SQ", "pct")
    s(ws, 19, "Cost_Per_tCO2e", "Net capex per tonne avoided over measure life", "$/tCO2e",
      "=Retrofit_Net/(tCO2e_Avoided*Measure_Life)", "usd")
    b.section(ws, 21, "DC Building Energy Performance Standards")
    s(ws, 22, "BEPS_Met", "Retrofit meets the 20% site EUI pathway", "TRUE/FALSE", "=EUI_Reduction>=BEPS_EUI_Cut", "text")
    s(ws, 23, "BEPS_Max_Penalty", "Maximum penalty exposure if not met (not in IRR)", "$",
      "=MIN(BEPS_Penalty_Per_SF*GFA,BEPS_Penalty_Cap)")


def _checks(b: Book) -> None:
    T = "Checks"
    ws = b.sheet(T, "Checks", "Each check returns TRUE when it passes.", year_header=False)
    checks = [
        ("Check_SU_SQ", "Sources = uses, status quo", "=ABS(Loan+Equity_SQ-Uses_SQ)<=Tolerance"),
        ("Check_SU_RF", "Sources = uses, retrofit", "=ABS(Loan+Equity_RF-Uses_RF)<=Tolerance"),
        ("Check_Loan_Limits", "Loan within LTV, DSCR and debt-yield limits",
         "=OR(Loan_Override>0,AND(Loan<=Max_Loan_LTV+Tolerance,Loan<=Max_Loan_DSCR+Tolerance,"
         "Loan<=Max_Loan_DY+Tolerance))"),
        ("Check_Balance", "Loan balance never negative", f"=MIN({b.span('Debt', 'End_Balance')})>=0"),
        ("Check_Debt_Service", "Debt service = interest + principal every year",
         f"=MAX({b.span('Debt', 'DS_Check')})<=Tolerance"),
        ("Check_Shares", "End-use shares sum to 100%",
         "=ABS(Share_Heat_Gas+Share_DHW_Gas+Share_Common_Elec+Share_Tenant_Elec-1)<=Tolerance"),
        ("Check_Energy", "Baseline energy by end use reconciles to site energy",
         "=ABS(Gas_SQ_MMBtu+(Common_kWh+Tenant_kWh)/kWh_per_MMBtu-Site_MMBtu_Base)<=Tolerance"),
        ("Check_Solar", "Solar does not exceed owner electricity use", "=Solar_kWh<=Owner_Gross_RF_kWh"),
        ("Check_IRR_SQ", "NPV at the levered IRR is zero, status quo", "=ABS(Lev_NPV_At_IRR_SQ)<=Tolerance*Equity_SQ"),
        ("Check_IRR_RF", "NPV at the levered IRR is zero, retrofit", "=ABS(Lev_NPV_At_IRR_RF)<=Tolerance*Equity_RF"),
        ("Check_Hold", "Hold period fits the model columns",
         f"=AND(Hold_Years>=1,Hold_Years<=COUNT(Operating!{b.cols[0]}4:{b.cols[-1]}4)-1)"),
    ]
    for row, (key, label, f) in enumerate(checks, start=4):
        b.scalar(ws, row, key, label, "", f, "text")
    row = 4 + len(checks) + 1
    b.scalar(ws, row, "All_Checks", "All checks pass", "", "=AND(" + ",".join(k for k, _, _ in checks) + ")",
             "text", bold=True)


def _summary(b: Book) -> None:
    ws = b.wb.create_sheet("Summary")
    ws.sheet_view.showGridLines = False
    for c, w in zip("ABCD", (46, 18, 18, 14), strict=True):
        ws.column_dimensions[c].width = w
    ws["A1"] = "Summary"
    ws["A1"].font = BOLD
    for c, h in zip("ABCD", ["Metric", "Status quo", "Retrofit", "Unit"], strict=True):
        ws[f"{c}3"] = h
        ws[f"{c}3"].font = BOLD
    rows = [
        ("Purchase price", "=Price", "=Price", "$", "usd"),
        ("Price per unit", "=Price_Per_Unit", "=Price_Per_Unit", "$", "usd"),
        ("Going-in cap rate", "=Going_In_Cap", "=Going_In_Cap", "%", "pct"),
        ("Loan amount", "=Loan", "=Loan", "$", "usd"),
        ("Loan to value", "=LTV", "=LTV", "%", "pct1"),
        ("Binding sizing test", "=Binding_Test", "=Binding_Test", "", "text"),
        ("Equity", "=Equity_SQ", "=Equity_RF", "$", "usd"),
        ("Minimum DSCR over hold", "=Min_DSCR_SQ", "=Min_DSCR_RF", "x", "x"),
        ("Minimum debt yield over hold", "=Min_DY_SQ", "=Min_DY_RF", "%", "pct"),
        ("Unlevered IRR", "=Unlev_IRR_SQ", "=Unlev_IRR_RF", "%", "pct"),
        ("Levered IRR", "=Lev_IRR_SQ", "=Lev_IRR_RF", "%", "pct"),
        ("Equity multiple", "=Equity_Multiple_SQ", "=Equity_Multiple_RF", "x", "x"),
        ("Gross exit value", "=Exit_Value_SQ", "=Exit_Value_RF", "$", "usd"),
        ("Site EUI", "=EUI_Base", "=EUI_RF", "kBtu/sf", "num1"),
        ("Owner Scope 1 + 2 emissions", "=Owner_tCO2e_SQ", "=Owner_tCO2e_RF", "tCO2e/yr", "num1"),
        ("Net retrofit capex", "", "=Retrofit_Net", "$", "usd"),
        ("Owner utility savings, year 1", "", "=Utility_Savings_Y1", "$", "usd"),
        ("Simple payback", "", "=Payback_Years", "years", "num1"),
        ("Cost per tonne avoided", "", "=Cost_Per_tCO2e", "$/tCO2e", "usd"),
        ("Meets DC BEPS 20% pathway", "", "=BEPS_Met", "", "text"),
    ]
    for row, (label, sq, rf, unit, fmt) in enumerate(rows, start=4):
        ws[f"A{row}"], ws[f"D{row}"] = label, unit
        for c, f in (("B", sq), ("C", rf)):
            if f:
                ws[f"{c}{row}"] = f
                ws[f"{c}{row}"].number_format = FMT[fmt]
