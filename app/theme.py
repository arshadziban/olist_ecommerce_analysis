"""Shared color palette for Plotly charts (validated categorical/sequential/diverging set)."""

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]

SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]

DIVERGING = ["#e34948", "#f0efec", "#2a78d6"]  # red -> neutral -> blue

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"

PLOTLY_LAYOUT = dict(
    template="plotly_white",
    font=dict(family="Segoe UI, Arial, Helvetica, sans-serif", color=INK_PRIMARY, size=13),
    plot_bgcolor=SURFACE,
    paper_bgcolor=SURFACE,
    margin=dict(l=70, r=30, t=40, b=60),
    xaxis=dict(gridcolor=GRIDLINE, linecolor=GRIDLINE, zerolinecolor=GRIDLINE, color=INK_PRIMARY, tickfont=dict(color=INK_PRIMARY), title_font=dict(color=INK_PRIMARY)),
    yaxis=dict(gridcolor=GRIDLINE, linecolor=GRIDLINE, zerolinecolor=GRIDLINE, color=INK_PRIMARY, tickfont=dict(color=INK_PRIMARY), title_font=dict(color=INK_PRIMARY)),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    hoverlabel=dict(bgcolor="white", font_size=13),
)


def apply_layout(fig, **overrides):
    layout = dict(PLOTLY_LAYOUT)
    layout.update(overrides)
    fig.update_layout(**layout)
    fig.update_xaxes(color=INK_PRIMARY, tickfont=dict(color=INK_PRIMARY))
    fig.update_yaxes(color=INK_PRIMARY, tickfont=dict(color=INK_PRIMARY))
    return fig
