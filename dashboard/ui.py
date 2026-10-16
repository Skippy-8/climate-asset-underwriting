"""Dashboard helpers: palette, Plotly styling, KPI rows and cached model runs.

Colours are the validated data-viz reference palette (categorical slots 1-3, a one-hue ordinal ramp
for Base / Downside / Severe, reserved status colours for covenant levels), selected per theme rather
than inverted. Covenant and status colours always ship with a text label.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from cau.engine import property as P
from cau.engine import solar_storage as SS
from cau.engine import stress as ST
from cau.inputs import load_inputs, values

LIGHT = {"surface": "#fcfcfb", "ink": "#0b0b0b", "muted": "#52514e", "grid": "#e9e8e4", "axis": "#c9c8c3",
         "series": ["#2a78d6", "#eb6834", "#1baf7a"], "ordinal": ["#6da7ec", "#2a78d6", "#104281"],
         "good": "#0ca30c", "warning": "#fab219", "critical": "#d03b3b", "neutral": "#9f9e98",
         "seq": ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]}
DARK = {"surface": "#1a1a19", "ink": "#f0efec", "muted": "#c3c2b7", "grid": "#2c2c2a", "axis": "#4a4a46",
        "series": ["#3987e5", "#d95926", "#199e70"], "ordinal": ["#86b6ef", "#3987e5", "#1c5cab"],
        "good": "#0ca30c", "warning": "#fab219", "critical": "#d03b3b", "neutral": "#6f6e69",
        "seq": ["#0d366b", "#1c5cab", "#3987e5", "#86b6ef", "#cde2fb"]}
FONT = "IBM Plex Sans, system-ui, sans-serif"


def pal() -> dict:
    try:
        return DARK if st.context.theme.type == "dark" else LIGHT
    except Exception:
        return LIGHT


def style(fig: go.Figure, title: str, height: int = 320, y_title: str = "", y_fmt: str | None = None,
          x_title: str = "") -> go.Figure:
    """Recessive grid and axes, one y-axis, a legend whenever there are two or more series, and
    hover on every mark."""
    p = pal()
    n_series = sum(1 for t in fig.data if t.showlegend is not False)
    fig.update_layout(
        title={"text": title, "font": {"size": 14, "color": p["ink"]}, "x": 0, "xanchor": "left"},
        height=height, margin={"l": 8, "r": 16, "t": 48, "b": 8}, font={"family": FONT, "color": p["muted"], "size": 12},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", hovermode="x unified",
        hoverlabel={"font": {"family": FONT}}, showlegend=n_series >= 2,
        legend={"orientation": "h", "y": 1.02, "yanchor": "bottom", "x": 1, "xanchor": "right", "title": None},
    )
    fig.update_xaxes(showgrid=False, linecolor=p["axis"], tickcolor=p["axis"], title=x_title, automargin=True)
    fig.update_yaxes(gridcolor=p["grid"], zeroline=False, linecolor=p["axis"], title=y_title, automargin=True,
                     **({"tickformat": y_fmt} if y_fmt else {}))
    return fig


def threshold(fig: go.Figure, y: float, label: str, kind: str) -> None:
    """A labelled covenant level in a reserved status colour (never colour alone)."""
    p = pal()
    fig.add_hline(y=y, line={"color": p[kind], "width": 1.5, "dash": "dash"},
                  annotation={"text": label, "font": {"color": p["ink"], "size": 11}, "bgcolor": p["surface"]},
                  annotation_position="top left")


def chart(fig: go.Figure, key: str) -> None:
    st.plotly_chart(fig, width="stretch", theme=None, key=key, config={"displayModeBar": False})


def header(kicker: str, title: str, blurb: str) -> None:
    st.caption(kicker.upper())
    st.markdown(f"## {title}")
    st.markdown(blurb)


def kpis(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, help_) in zip(cols, items, strict=True):
        col.metric(label, value, help=help_, border=True)


def fmt_m(x: float) -> str:
    return f"${x / 1e6:,.1f}m"


def fmt_pct(x: float, d: int = 1) -> str:
    return "n/m" if x != x else f"{x * 100:.{d}f}%"


@st.cache_data(show_spinner=False)
def base(model: str) -> dict:
    return values(load_inputs(model))


@st.cache_data(show_spinner=False)
def run(model: str, overrides: tuple = ()):
    """A model run with input overrides (a tuple of pairs so it can be cached)."""
    engine = P if model == "property" else SS
    return engine.run(dict(base(model), **dict(overrides)))


@st.cache_data(show_spinner=False)
def case(model: str, name: str):
    return ST.run_case(model, name)


@st.cache_data(show_spinner=False)
def case_table(model: str):
    return ST.case_table(model)


@st.cache_data(show_spinner=False)
def sensitivities(model: str, metric: str):
    return ST.sensitivities(model, metric)


@st.cache_data(show_spinner=False)
def grid(model: str, x_key: str, xs: tuple, y_key: str, ys: tuple, metric: str):
    return ST.grid(model, x_key, list(xs), y_key, list(ys), metric)
