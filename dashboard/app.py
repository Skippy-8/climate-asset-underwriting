"""Portfolio monitoring and covenant dashboard for the two illustrative assets.

    streamlit run dashboard/app.py

Four tabs: budget vs actual with pre-flight QC, covenant headroom, stress and sensitivity, and
decarbonization KPIs. Every number comes from the same Python engines that the Excel workbooks and
the memos are tested against.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))          # for `ui` when run by streamlit
from ui import (  # noqa: E402
    base,
    case,
    case_table,
    chart,
    fmt_m,
    fmt_pct,
    grid,
    header,
    kpis,
    pal,
    run,
    sensitivities,
    style,
    threshold,
)

from cau import actuals as A  # noqa: E402
from cau import qc  # noqa: E402
from cau.engine import stress as ST  # noqa: E402

st.set_page_config(page_title="Asset monitoring", page_icon=":material/monitoring:", layout="wide")

MODELS = {"Multifamily, Washington DC": "property", "Solar + storage, ERCOT": "solar_storage"}
st.title("Climate-aligned asset monitoring")
st.caption("Illustrative assets built on public benchmarks. Budget-vs-actual figures are synthetic and labelled "
           "as such. Not real properties, projects or transactions.")

tabs = st.tabs(["Budget vs actual", "Covenants", "Stress and sensitivity", "Decarbonization"])


# ── 1. budget vs actual ─────────────────────────────────────────────────────

def budget_vs_actual() -> None:
    header("Multifamily, year one", "Budget vs actual",
           "Year-to-date actuals against the underwritten year-one budget. The file is checked before any "
           "variance is reported; rows that fail are removed and listed, never fixed silently.")
    up = st.file_uploader("Upload actuals (CSV with period, line, amount); leave empty for the illustrative file",
                          type=["csv"], key="actuals_upload")
    raw = pd.read_csv(up) if up is not None else pd.read_csv(A.ACTUALS)
    if up is None:
        st.info("Showing the illustrative actuals file: synthetic data with planted defects for the QC to catch.",
                icon=":material/info:")
    bud = A.budget()
    rep = qc.run(raw, bud, A.CHART_OF_ACCOUNTS)
    counts = rep.findings["check"].value_counts()
    removed = len(rep.removed)
    label = {"A": "Clean", "B": "Review items only", "C": "Gaps found", "D": "Defects found"}[rep.grade]
    icon = ":material/check_circle:" if rep.grade == "A" else ":material/warning:" if rep.grade in "BC" else ":material/error:"
    st.markdown(f"**Pre-flight QC: grade {rep.grade}, {label.lower()}** {icon}")
    kpis([("Rows read", f"{len(raw):,}", None), ("Rows removed", f"{removed:,}", "Duplicates, unmapped lines, sign errors"),
          ("Missing period-lines", f"{int(counts.get('missing', 0)):,}", "Line-months with no amount"),
          ("Review flags", f"{int(counts.get('review', 0)):,}", "More than 50% from budget; kept, but worth a look")])
    with st.expander("QC findings", expanded=rep.grade != "A"):
        st.dataframe(rep.findings, hide_index=True, width="stretch",
                     column_config={"check": "Check", "period": "Period", "line": "Line", "detail": "Detail"})
        if removed:
            st.caption("Removed before the variance:")
            st.dataframe(rep.removed, hide_index=True, width="stretch",
                         column_config={"amount": st.column_config.NumberColumn("Amount", format="$%,.0f")})
        st.caption("Column profile")
        st.dataframe(rep.profile, hide_index=True, width="stretch")
    if rep.clean.empty:
        st.error("Nothing usable after QC; fix the file and upload again.")
        return

    var = qc.variance(rep.clean, bud, A.CHART_OF_ACCOUNTS)
    noi = var.iloc[-1]
    flagged = var[var["status"] == "unfavourable"]
    months = int(noi["months"])
    n_periods = rep.clean["period"].nunique()
    kpis([("NOI, actual", f"${noi['actual'] / 1e6:,.2f}m", f"{months} of {n_periods} months complete"),
          ("NOI, budget", f"${noi['budget'] / 1e6:,.2f}m", "Same complete months"),
          ("NOI variance", f"{noi['variance'] / 1e3:+,.0f}k ({noi['variance_pct']:+.1%})",
           "Only months where every line reported; a missing expense would flatter NOI"),
          ("Lines over tolerance", f"{len(flagged)}", "Unfavourable by more than 5% and $5,000")])

    p = pal()
    lines = var.iloc[:-1].copy()
    lines["signed"] = np.where(lines["favourable"].fillna(False).astype(bool), 1, -1) * lines["variance"].abs()
    lines.loc[lines["status"] == "incomplete", "signed"] = 0.0      # no variance claimed for a short line
    lines = lines.sort_values("signed")
    colour = [p["neutral"] if s == "incomplete" else p["series"][0] if f is True else p["critical"]
              for s, f in zip(lines["status"], lines["favourable"], strict=True)]
    fig = go.Figure(go.Bar(
        x=lines["signed"], y=lines["line"], orientation="h",
        marker={"color": colour, "line": {"color": p["surface"], "width": 2}},
        text=["incomplete: not reported" if s == "incomplete" else f"{v / 1e3:+,.1f}k"
              for s, v in zip(lines["status"], lines["signed"], strict=True)], textposition="outside",
        textfont={"color": p["ink"], "size": 11}, cliponaxis=False,
        customdata=np.stack([lines["budget"], lines["actual"], lines["status"]], axis=1),
        hovertemplate="%{y}<br>Budget $%{customdata[0]:,.0f}<br>Actual $%{customdata[1]:,.0f}"
                      "<br>%{customdata[2]}<extra></extra>", showlegend=False))
    fig.add_vline(x=0, line={"color": p["axis"], "width": 1})
    style(fig, "YTD variance by line: right = favourable, left = unfavourable (red); grey = line missing a month",
          height=430,
          y_title="", x_title="Variance to budget ($, signed so favourable is positive)")
    fig.update_layout(hovermode="closest")
    chart(fig, "var_bar")

    b_noi = qc.noi_by_period(bud, A.CHART_OF_ACCOUNTS)
    complete = qc.complete_periods(rep.clean, A.CHART_OF_ACCOUNTS)
    a_noi = qc.noi_by_period(rep.clean, A.CHART_OF_ACCOUNTS).reindex(sorted(rep.clean["period"].unique()))
    a_noi[~a_noi.index.isin(complete)] = np.nan                    # gap, not a false spike
    fig = go.Figure()
    fig.add_scatter(x=b_noi.index, y=b_noi.values, name="Budget", mode="lines",
                    line={"color": p["neutral"], "width": 2, "dash": "dot"})
    fig.add_scatter(x=a_noi.index, y=a_noi.values, name="Actual (complete months)", mode="lines+markers",
                    line={"color": p["series"][0], "width": 2}, marker={"size": 8, "line": {"color": p["surface"], "width": 2}})
    style(fig, "Monthly NOI: budget vs actual (gaps = months with a line missing)", y_title="NOI ($)", y_fmt="$,.0f")
    chart(fig, "noi_line")
    st.dataframe(var, hide_index=True, width="stretch", column_config={
        "line": "Line", "kind": "Type", "budget": st.column_config.NumberColumn("Budget YTD", format="$%,.0f"),
        "actual": st.column_config.NumberColumn("Actual YTD", format="$%,.0f"),
        "variance": st.column_config.NumberColumn("Variance", format="$%,.0f"),
        "variance_pct": st.column_config.NumberColumn("Variance %", format="percent"),
        "favourable": "Favourable", "status": "Status", "months": "Months"})


# ── 2. covenants ────────────────────────────────────────────────────────────

def pad_axis(fig: go.Figure, series: list, floor: float) -> None:
    """Range from below the lowest covenant level to above the data, so threshold lines and their
    labels never sit on the plot edge."""
    lo = min(float(np.nanmin(x)) for x in series)
    hi = max(float(np.nanmax(x)) for x in series)
    bottom, top = min(lo, floor), max(hi, floor)
    span = top - bottom
    fig.update_yaxes(range=[bottom - 0.18 * span, top + 0.08 * span])


def covenants() -> None:
    header("Debt monitoring", "Covenant headroom",
           "Coverage by year against the covenant levels, for each stress case. Property cases hold the "
           "closed loan; solar cases run the operating case against the schedule fixed at close.")
    c1, c2 = st.columns([2, 1])
    asset = c1.segmented_control("Asset", list(MODELS), default=list(MODELS)[0], key="cov_asset")
    name = c2.selectbox("Case", ST.CASES, key="cov_case")
    model = MODELS[asset or list(MODELS)[0]]
    r = case(model, name)
    v, S, R = r.inputs, r.scalars, r.rows
    p = pal()
    if model == "property":
        hold = int(v["Hold_Years"])
        years = np.arange(1, hold + 1)
        kpis([("Loan", fmt_m(S["Loan"]), "Held at the base-case size"), ("Minimum DSCR", f"{S['Min_DSCR_SQ']:.2f}x", "Status quo"),
              ("Minimum debt yield", fmt_pct(S["Min_DY_SQ"]), "Status quo"),
              ("Covenant flag-years", f"{S['Trap_Years_SQ']:.0f}", "Cash-trap or breach flags in the hold, DSCR and debt yield")])
        fig = go.Figure()
        for i, (case_key, label) in enumerate((("SQ", "Status quo"), ("RF", "Retrofit"))):
            fig.add_scatter(x=years, y=R[f"DSCR_{case_key}"][:hold], name=label, mode="lines+markers",
                            line={"color": p["series"][i], "width": 2}, marker={"size": 8, "line": {"color": p["surface"], "width": 2}},
                            hovertemplate="%{y:.2f}x")
        threshold(fig, v["DSCR_Trap"], f"Cash trap {v['DSCR_Trap']:.2f}x", "warning")
        threshold(fig, v["DSCR_Default"], f"Default {v['DSCR_Default']:.2f}x", "critical")
        style(fig, f"DSCR by year, {name} case", y_title="DSCR (x)", y_fmt=".2f", x_title="Year")
        pad_axis(fig, [R["DSCR_SQ"][:hold], R["DSCR_RF"][:hold]], v["DSCR_Default"])
        chart(fig, "prop_dscr")
        fig = go.Figure()
        for i, (case_key, label) in enumerate((("SQ", "Status quo"), ("RF", "Retrofit"))):
            fig.add_scatter(x=years, y=R[f"DY_{case_key}"][:hold], name=label, mode="lines+markers",
                            line={"color": p["series"][i], "width": 2}, marker={"size": 8, "line": {"color": p["surface"], "width": 2}},
                            hovertemplate="%{y:.1%}")
        threshold(fig, v["DY_Trap"], f"Cash trap {v['DY_Trap']:.1%}", "warning")
        threshold(fig, v["DY_Default"], f"Default {v['DY_Default']:.1%}", "critical")
        style(fig, f"Debt yield by year, {name} case", y_title="Debt yield", y_fmt=".1%", x_title="Year")
        pad_axis(fig, [R["DY_SQ"][:hold], R["DY_RF"][:hold]], v["DY_Default"])
        chart(fig, "prop_dy")
        tbl = pd.DataFrame({"Year": years, "DSCR": R["DSCR_SQ"][:hold], "Headroom to cash trap": R["DSCR_Headroom_SQ"][:hold],
                            "DSCR status": R["DSCR_Flag_SQ"][:hold], "Debt yield": R["DY_SQ"][:hold],
                            "Debt-yield status": R["DY_Flag_SQ"][:hold]})
    else:
        ten = int(v["Tenor"])
        years = np.arange(1, ten + 1)
        kpis([("Senior debt", fmt_m(S["Debt"]), "Re-sized at close if the case shocks the rate"),
              ("Minimum DSCR, operating", f"{S['Min_DSCR_Op']:.2f}x", None), ("LLCR, operating", f"{S['LLCR_Op']:.2f}x", None),
              ("Years in lock-up", f"{S['Lockup_Years']:.0f}", f"Below {v['DSCR_Lockup']:.2f}x")])
        fig = go.Figure()
        for i, (key, label) in enumerate((("P50", "P50 (sizing)"), ("P90", "P90 (sizing)"), ("Op", f"Operating ({name})"))):
            fig.add_scatter(x=years, y=R[f"DSCR_{key}"][:ten], name=label, mode="lines+markers",
                            line={"color": p["series"][i], "width": 2}, marker={"size": 8, "line": {"color": p["surface"], "width": 2}},
                            hovertemplate="%{y:.2f}x")
        threshold(fig, v["DSCR_Lockup"], f"Lock-up {v['DSCR_Lockup']:.2f}x", "warning")
        threshold(fig, v["DSCR_Default_PF"], f"Default {v['DSCR_Default_PF']:.2f}x", "critical")
        style(fig, f"DSCR by year, {name} case", y_title="DSCR (x)", y_fmt=".2f", x_title="Year from COD")
        pad_axis(fig, [R["DSCR_P50"][:ten], R["DSCR_P90"][:ten], R["DSCR_Op"][:ten]], v["DSCR_Default_PF"])
        chart(fig, "pf_dscr")
        fig = go.Figure(go.Bar(x=years, y=R["Debt_Service"][:ten], name="Scheduled debt service",
                               marker={"color": p["series"][0], "line": {"color": p["surface"], "width": 2}},
                               hovertemplate="$%{y:,.0f}"))
        style(fig, "Sculpted debt service (steps down when the battery toll ends)", y_title="$", y_fmt="$,.0f",
              x_title="Year from COD")
        chart(fig, "pf_ds")
        tbl = pd.DataFrame({"Year": years, "CFADS (operating)": R["CFADS_Op"][:ten], "Debt service": R["Debt_Service"][:ten],
                            "DSCR": R["DSCR_Op"][:ten], "Closing balance": R["End_Balance"][:ten]})
    st.dataframe(tbl, hide_index=True, width="stretch", column_config={
        c: st.column_config.NumberColumn(c, format=("%.2fx" if "DSCR" == c else "percent" if c in ("Headroom to cash trap", "Debt yield")
                                                    else "$%,.0f" if c not in ("Year",) else "%d"))
        for c in tbl.columns if c not in ("DSCR status", "Debt-yield status")})


# ── 3. stress and sensitivity ───────────────────────────────────────────────

def stress() -> None:
    header("Downside analysis", "Stress and sensitivity",
           "Move the levers to re-run the model live; the cases and grids below use the same engine.")
    asset = st.segmented_control("Asset", list(MODELS), default=list(MODELS)[0], key="st_asset")
    model = MODELS[asset or list(MODELS)[0]]
    b = base(model)
    p = pal()
    if model == "property":
        c = st.columns(4)
        vac = c[0].slider("Vacancy (%)", 0.0, 20.0, b["Vacancy_Rate"] * 100, 0.5, format="%.1f%%") / 100
        rg = c[1].slider("Rent growth (%/yr)", -1.0, 5.0, b["Rent_Growth"] * 100, 0.25, format="%.2f%%") / 100
        cap = c[2].slider("Exit cap rate (%)", 4.5, 8.0, b["Exit_Cap"] * 100, 0.25, format="%.2f%%") / 100
        hp = c[3].slider("Heat pump cost per unit ($)", 6000, 20000, int(b["HP_Capex_Per_Unit"]), 500)
        loan = run(model).scalars["Loan"]
        over = (("Vacancy_Rate", vac), ("Rent_Growth", rg), ("Exit_Cap", cap), ("HP_Capex_Per_Unit", float(hp)),
                ("Loan_Override", loan))
        s, s0 = run(model, over).scalars, run(model).scalars
        kpis([("Minimum DSCR", f"{s['Min_DSCR_SQ']:.2f}x", f"Base {s0['Min_DSCR_SQ']:.2f}x; loan held"),
              ("Levered IRR, retrofit", fmt_pct(s["Lev_IRR_RF"]), f"Base {fmt_pct(s0['Lev_IRR_RF'])}"),
              ("Exit value, retrofit", fmt_m(s["Exit_Value_RF"]), f"Base {fmt_m(s0['Exit_Value_RF'])}"),
              ("Covenant flag-years", f"{s['Trap_Years_SQ']:.0f}", f"Base {s0['Trap_Years_SQ']:.0f}")])
        metric, mlabel, mfmt = "Lev_IRR_RF", "levered IRR, retrofit", ".1%"
        g = grid(model, "Exit_Cap", (0.0525, 0.055, 0.0575, 0.06, 0.0625, 0.065, 0.0675),
                 "Vacancy_Rate", (0.04, 0.05, 0.07, 0.10, 0.13), metric)
        x_lab, y_lab, xf, yf = "Exit cap rate", "Vacancy", "{:.2%}", "{:.0%}"
    else:
        c = st.columns(4)
        z = c[0].select_slider("Output, every year", ["P50", "P75", "P90", "P95", "P99"], value="P50")
        zmap = {"P50": 0.0, "P75": 0.6745, "P90": b["Z_P90"], "P95": 1.6449, "P99": b["Z_P99"]}
        ppa = c[1].slider("PPA price ($/MWh)", 35.0, 65.0, b["PPA_Price"], 1.0)
        capex = c[2].slider("EPC overrun (%)", 0.0, 30.0, 0.0, 5.0, format="%.0f%%") / 100
        rate = c[3].slider("Rate shock at close (bp)", 0, 300, 0, 25, format="%d bp") / 1e4
        over = (("Gen_Case_Z", zmap[z]), ("PPA_Price", ppa), ("Capex_Overrun", capex), ("Rate_Shock", rate))
        s, s0 = run(model, over).scalars, run(model).scalars
        kpis([("Senior debt", fmt_m(s["Debt"]), f"Base {fmt_m(s0['Debt'])}"),
              ("Minimum DSCR, operating", f"{s['Min_DSCR_Op']:.2f}x", f"Base {s0['Min_DSCR_Op']:.2f}x"),
              ("Equity IRR, after tax", fmt_pct(s["Equity_IRR_AT"]), f"Base {fmt_pct(s0['Equity_IRR_AT'])}"),
              ("Years in lock-up", f"{s['Lockup_Years']:.0f}", f"Base {s0['Lockup_Years']:.0f}")])
        st.caption("A PPA price change re-sizes the sculpted debt at close, so it moves equity returns, not coverage.")
        metric, mlabel, mfmt = "Equity_IRR_AT", "after-tax equity IRR", ".1%"
        g = grid(model, "PPA_Price", (40.0, 44.0, 48.0, 51.0, 55.0, 60.0), "Gen_Case_Z",
                 (0.0, 0.6745, b["Z_P90"], b["Z_P99"]), metric)
        x_lab, y_lab, xf, yf = "PPA price ($/MWh)", "Output case", "${:.0f}", None
        g.index = ["P50", "P75", "P90", "P99"]

    st.markdown("#### Cases")
    t = case_table(model)
    show = t.copy()
    for cname in ST.CASES:
        show[cname] = [("n/m" if x != x else f"${x / 1e6:,.1f}m" if k == "usd" else f"{x:.2f}x" if k == "x"
                        else f"{x:.1%}" if k == "pct" else f"{x:,.1f} yrs" if k == "yrs" else f"{x:,.1f}" if k == "num1"
                        else f"{x:,.0f}")
                       for x, k in zip(t[cname], t["kind"], strict=True)]
    st.dataframe(show[["metric", *ST.CASES]], hide_index=True, width="stretch", column_config={"metric": "Metric"})

    left, right = st.columns(2)
    sens = sensitivities(model, metric)
    fig = go.Figure(go.Bar(x=sens["change"], y=sens["lever"], orientation="h",
                           marker={"color": p["series"][0], "line": {"color": p["surface"], "width": 2}},
                           text=[f"{v * 1e4:+,.0f} bp" for v in sens["change"]], textposition="outside",
                           textfont={"color": p["ink"], "size": 11}, cliponaxis=False,
                           hovertemplate="%{y}: %{x:+.2%}<extra></extra>", showlegend=False))
    style(fig, f"One factor at a time: change in {mlabel}", height=380, x_title="Change from base")
    lo = float(sens["change"].min())
    fig.update_xaxes(tickformat=".1%", range=[lo * 1.35, max(0.0, float(sens["change"].max())) - lo * 0.05])
    fig.update_layout(hovermode="closest")
    with left:
        chart(fig, "tornado")
    zvals = g.to_numpy(float)
    labels = [[("n/m" if v != v else format(v, mfmt)) for v in row] for row in zvals]
    xs = [xf.format(x) for x in g.columns]
    ys = list(g.index) if yf is None else [yf.format(y) for y in g.index]
    fig = go.Figure(go.Heatmap(z=zvals, x=xs, y=ys, text=labels, texttemplate="%{text}", textfont={"size": 11},
                               colorscale=[[i / (len(p["seq"]) - 1), c] for i, c in enumerate(p["seq"])],
                               colorbar={"title": "", "tickformat": mfmt, "thickness": 10}, xgap=2, ygap=2,
                               hovertemplate=f"{x_lab} %{{x}}<br>{y_lab} %{{y}}<br>{mlabel} %{{text}}<extra></extra>"))
    style(fig, f"Two-way grid: {mlabel}", height=380, x_title=x_lab, y_title=y_lab)
    fig.update_xaxes(type="category")
    fig.update_yaxes(type="category")
    fig.update_layout(hovermode="closest")
    with right:
        chart(fig, "grid")


# ── 4. decarbonization ──────────────────────────────────────────────────────

def decarbonization() -> None:
    header("Sustainability", "Decarbonization KPIs",
           "Energy, emissions and cost per tonne for both assets. Grid factors are eGRID2022 averages held "
           "flat, so a cleaner grid over time is not counted.")
    p = pal()
    pr = run("property").scalars
    pv = run("solar_storage").scalars
    vprop = base("property")
    st.markdown("#### Multifamily retrofit")
    kpis([("Site EUI", f"{pr['EUI_RF']:.1f} kBtu/sf", f"From {pr['EUI_Base']:.1f}; DC BEPS pathway needs a "
                                                     f"{vprop['BEPS_EUI_Cut']:.0%} cut"),
          ("Owner emissions avoided", f"{pr['tCO2e_Avoided']:,.0f} tCO2e/yr", "Scope 1 + 2"),
          ("Net capex per tonne", f"${pr['Cost_Per_tCO2e']:,.0f}", f"Over a {vprop['Measure_Life']:.0f}-year measure life"),
          ("Simple payback", f"{pr['Payback_Years']:.1f} yrs", "On owner utility savings only")])
    left, right = st.columns(2)
    target = pr["EUI_Base"] * (1 - vprop["BEPS_EUI_Cut"])
    fig = go.Figure(go.Bar(x=["Status quo", "Retrofit", "Retrofit, net of solar"],
                           y=[pr["EUI_Base"], pr["EUI_RF"], pr["EUI_RF_Net_Solar"]],
                           marker={"color": [p["neutral"], p["series"][0], p["series"][0]],
                                   "line": {"color": p["surface"], "width": 2}},
                           text=[f"{x:.1f}" for x in (pr["EUI_Base"], pr["EUI_RF"], pr["EUI_RF_Net_Solar"])],
                           textposition="outside", textfont={"color": p["ink"]}, cliponaxis=False,
                           hovertemplate="%{x}: %{y:.1f} kBtu/sf<extra></extra>", showlegend=False))
    threshold(fig, target, f"BEPS pathway {target:.1f}", "good")
    style(fig, "Site EUI (kBtu per square foot)", y_title="kBtu/sf")
    fig.update_layout(hovermode="closest")
    with left:
        chart(fig, "eui")
    cases = ["Status quo", "Retrofit"]
    parts = [("Scope 1, owner gas", [pr["Scope1_SQ"], pr["Scope1_RF"]]),
             ("Scope 2, owner electricity", [pr["Scope2_SQ"], pr["Scope2_RF"]]),
             ("Scope 3, tenant electricity", [pr["Tenant_tCO2e"], pr["Tenant_tCO2e"]])]
    fig = go.Figure()
    for i, (label, vals) in enumerate(parts):
        fig.add_bar(x=cases, y=vals, name=label, marker={"color": p["series"][i], "line": {"color": p["surface"], "width": 2}},
                    text=[f"{x:,.0f}" if x >= 25 else "" for x in vals], textposition="inside",
                    insidetextfont={"color": "#ffffff"}, hovertemplate=f"{label}: %{{y:,.0f}} tCO2e<extra></extra>")
    style(fig, "Emissions by scope (tCO2e per year)", y_title="tCO2e/yr")
    fig.update_layout(barmode="stack", hovermode="closest",
                      legend={"orientation": "h", "y": -0.12, "yanchor": "top", "x": 0, "xanchor": "left",
                              "traceorder": "normal"})
    with right:
        chart(fig, "scopes")

    st.markdown("#### Solar + storage")
    r = run("solar_storage")
    kpis([("Generation, year 1", f"{pv['Gen_Y1_P50'] / 1e3:,.0f} GWh", f"Net capacity factor {pv['Net_CF_Y1']:.1%}"),
          ("Grid emissions displaced, year 1", f"{pv['tCO2e_Avoided_Y1']:,.0f} tCO2e", "eGRID ERCOT average rate"),
          ("Over the project life", f"{pv['tCO2e_Avoided_Life'] / 1e6:,.2f} Mt", None),
          ("Project capex per tonne", f"${pv['Capex_Per_tCO2e']:,.0f}", None)])
    years = np.arange(1, len(r.rows["Gen_P50"]) + 1)
    fig = go.Figure(go.Bar(x=years, y=r.rows["Gen_P50"] / 1e3, name="P50 generation",
                           marker={"color": p["series"][0], "line": {"color": p["surface"], "width": 2}},
                           hovertemplate="Year %{x}: %{y:,.0f} GWh<extra></extra>"))
    style(fig, "Solar generation by year, P50 (GWh; degradation 0.7% a year)", y_title="GWh", x_title="Year from COD")
    chart(fig, "gen")
    st.dataframe(pd.DataFrame([
        {"Asset": "Multifamily retrofit", "Capital": pr["Retrofit_Net"], "tCO2e per year": pr["tCO2e_Avoided"],
         "Capital per annual tonne": pr["Retrofit_Net"] / pr["tCO2e_Avoided"]},
        {"Asset": "Solar + storage", "Capital": pv["Project_Capex"], "tCO2e per year": pv["tCO2e_Avoided_Y1"],
         "Capital per annual tonne": pv["Project_Capex"] / pv["tCO2e_Avoided_Y1"]}]),
        hide_index=True, width="stretch", column_config={
            "Capital": st.column_config.NumberColumn(format="$%,.0f"),
            "tCO2e per year": st.column_config.NumberColumn(format="%,.0f"),
            "Capital per annual tonne": st.column_config.NumberColumn(format="$%,.0f")})
    st.caption("Capital per annual tonne compares very different assets: the retrofit buys compliance and lower "
               "owner emissions; the solar displaces grid generation at an average, not marginal, rate.")


with tabs[0]:
    budget_vs_actual()
with tabs[1]:
    covenants()
with tabs[2]:
    stress()
with tabs[3]:
    decarbonization()
