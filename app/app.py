import pathlib

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics import (
    cohort_index_summary,
    cohort_retention,
    cohort_retention_pivot,
    compute_rfm,
    kpi_summary,
    monthly_revenue,
    revenue_by_category,
    revenue_by_state,
    rfm_segment_summary,
)
from theme import CATEGORICAL, DIVERGING, SEQUENTIAL_BLUE, apply_layout

DATA_PATH = pathlib.Path(__file__).resolve().parent.parent / "dashboard" / "olist_clean_dataset.parquet"

st.set_page_config(page_title="Olist E-Commerce Analytics", page_icon="📊", layout="wide")


@st.cache_data(show_spinner="Loading dataset...")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return df


df = load_data(str(DATA_PATH))

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("Filters")

months = sorted(df["order_month"].dropna().unique())
month_range = st.sidebar.select_slider(
    "Order month range",
    options=months,
    value=(months[0], months[-1]),
)

states = sorted(df["customer_state"].dropna().unique())
selected_states = st.sidebar.multiselect("Customer state", states, default=[])

statuses = sorted(df["order_status"].dropna().unique())
selected_statuses = st.sidebar.multiselect("Order status", statuses, default=["delivered"])

mask = (df["order_month"] >= month_range[0]) & (df["order_month"] <= month_range[1])
if selected_states:
    mask &= df["customer_state"].isin(selected_states)
if selected_statuses:
    mask &= df["order_status"].isin(selected_statuses)

fdf = df[mask].copy()

st.sidebar.caption(f"{fdf['order_id'].nunique():,} orders in current filter")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Olist E-Commerce Analytics")
st.caption("Brazilian marketplace · 2016–2018 · Cohort retention, RFM segmentation & revenue analysis")

tab_overview, tab_revenue, tab_cohort, tab_rfm, tab_geo = st.tabs(
    ["Overview", "Revenue", "Cohort Retention", "RFM Segmentation", "Geography"]
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
with tab_overview:
    kpis = kpi_summary(fdf)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Revenue", f"R$ {kpis['total_revenue']:,.0f}")
    c2.metric("Delivered Orders", f"{kpis['total_orders']:,}")
    c3.metric("Unique Customers", f"{kpis['unique_customers']:,}")
    c4.metric("Avg Order Value", f"R$ {kpis['avg_order_value']:,.2f}")

    st.subheader("Monthly Revenue Trend")
    mr = monthly_revenue(fdf)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=mr["order_month"],
            y=mr["total_revenue"],
            mode="lines+markers",
            line=dict(color=CATEGORICAL[0], width=2),
            marker=dict(size=7),
            name="Revenue",
            hovertemplate="%{x}<br>R$ %{y:,.0f}<extra></extra>",
        )
    )
    apply_layout(fig, height=380, yaxis_title="Revenue (R$)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True, theme=None)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Top 10 Categories by Revenue")
        cat = revenue_by_category(fdf, top_n=10).sort_values("total_revenue")
        fig2 = go.Figure(
            go.Bar(
                x=cat["total_revenue"],
                y=cat["product_category_name"],
                orientation="h",
                marker_color=CATEGORICAL[0],
                hovertemplate="%{y}<br>R$ %{x:,.0f}<extra></extra>",
            )
        )
        apply_layout(fig2, height=380, xaxis_title="Revenue (R$)", margin=dict(l=160, r=30, t=40, b=60))
        st.plotly_chart(fig2, use_container_width=True, theme=None)
    with col_b:
        st.subheader("Payment Type Mix")
        pay = fdf.drop_duplicates("order_id")["payment_type"].value_counts().reset_index()
        pay.columns = ["payment_type", "count"]
        fig3 = go.Figure(
            go.Pie(
                labels=pay["payment_type"],
                values=pay["count"],
                hole=0.55,
                marker=dict(colors=CATEGORICAL),
                sort=False,
            )
        )
        apply_layout(fig3, height=380)
        st.plotly_chart(fig3, use_container_width=True, theme=None)

# ---------------------------------------------------------------------------
# Revenue
# ---------------------------------------------------------------------------
with tab_revenue:
    st.subheader("Monthly Revenue & Month-over-Month Growth")
    mr = monthly_revenue(fdf)

    fig = go.Figure(
        go.Bar(
            x=mr["order_month"],
            y=mr["total_revenue"],
            marker_color=CATEGORICAL[0],
            name="Revenue",
            hovertemplate="%{x}<br>R$ %{y:,.0f}<extra></extra>",
        )
    )
    apply_layout(fig, height=380, yaxis_title="Revenue (R$)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True, theme=None)

    fig_g = go.Figure(
        go.Bar(
            x=mr["order_month"],
            y=mr["growth_pct"],
            marker_color=[CATEGORICAL[2] if v is not None and v >= 0 else CATEGORICAL[1] for v in mr["growth_pct"]],
            hovertemplate="%{x}<br>%{y:.1f}%<extra></extra>",
        )
    )
    apply_layout(fig_g, height=300, yaxis_title="MoM Growth (%)", title="Month-over-Month Revenue Growth")
    st.plotly_chart(fig_g, use_container_width=True, theme=None)

    st.subheader("Revenue by Category")
    top_n = st.slider("Number of categories", 5, 30, 10)
    cat = revenue_by_category(fdf, top_n=top_n).sort_values("total_revenue")
    fig_c = go.Figure(
        go.Bar(
            x=cat["total_revenue"],
            y=cat["product_category_name"],
            orientation="h",
            marker_color=CATEGORICAL[0],
            hovertemplate="%{y}<br>R$ %{x:,.0f} · %{customdata} orders<extra></extra>",
            customdata=cat["total_orders"],
        )
    )
    apply_layout(fig_c, height=max(300, top_n * 28), xaxis_title="Revenue (R$)", margin=dict(l=160, r=30, t=40, b=60))
    st.plotly_chart(fig_c, use_container_width=True, theme=None)

    with st.expander("Show revenue table"):
        st.dataframe(mr, use_container_width=True)

# ---------------------------------------------------------------------------
# Cohort Retention
# ---------------------------------------------------------------------------
with tab_cohort:
    st.subheader("Monthly Cohort Retention")
    st.caption("Share of each acquisition cohort still purchasing N months after their first order.")

    cohort_data = cohort_retention(fdf)
    pivot = cohort_retention_pivot(cohort_data)
    pivot_display = pivot.loc[:, pivot.columns <= 11] if len(pivot.columns) > 12 else pivot

    fig_h = go.Figure(
        go.Heatmap(
            z=pivot_display.values,
            x=[f"M+{c}" for c in pivot_display.columns],
            y=pivot_display.index,
            colorscale=[[i / (len(SEQUENTIAL_BLUE) - 1), c] for i, c in enumerate(SEQUENTIAL_BLUE)],
            zmin=0,
            zmax=100,
            colorbar=dict(title="Retention %"),
            hovertemplate="Cohort %{y}<br>%{x}<br>%{z:.1f}%<extra></extra>",
        )
    )
    apply_layout(fig_h, height=480, xaxis_title="Months since acquisition", yaxis_title="Cohort month")
    fig_h.update_yaxes(autorange="reversed")
    st.plotly_chart(fig_h, use_container_width=True, theme=None)

    st.subheader("Average Retention by Months Since Acquisition")
    idx_summary = cohort_index_summary(cohort_data)
    fig_avg = go.Figure(
        go.Bar(
            x=idx_summary["months_since_acquisition"],
            y=idx_summary["avg_retention_pct"],
            marker_color=CATEGORICAL[0],
            hovertemplate="Month +%{x}<br>%{y:.2f}%<extra></extra>",
        )
    )
    apply_layout(fig_avg, height=340, xaxis_title="Months since acquisition", yaxis_title="Avg retention (%)")
    st.plotly_chart(fig_avg, use_container_width=True, theme=None)

    m1 = idx_summary[idx_summary["months_since_acquisition"] == 1]
    if not m1.empty:
        st.warning(
            f"Month-1 retention averages **{m1['avg_retention_pct'].iloc[0]:.1f}%** across cohorts "
            "(industry benchmark: 20–25%). Olist behaves largely as a one-time-purchase marketplace."
        )

    with st.expander("Show cohort retention table"):
        st.dataframe(pivot, use_container_width=True)

# ---------------------------------------------------------------------------
# RFM Segmentation
# ---------------------------------------------------------------------------
with tab_rfm:
    st.subheader("RFM Customer Segmentation")
    st.caption("Recency / Frequency / Monetary scoring (quintiles) on delivered orders — segment definitions mirror sql/03_rfm_segmentation.sql.")

    rfm = compute_rfm(fdf)

    if len(rfm) < 5:
        st.info("Not enough delivered customers in the current filter selection to compute RFM quintiles (need at least 5). Try widening the filters.")
    else:
        summary = rfm_segment_summary(rfm)

        col_a, col_b = st.columns([1, 1])
        with col_a:
            st.markdown("**Customers by segment**")
            fig_seg = go.Figure(
                go.Bar(
                    x=summary["customer_count"],
                    y=summary["segment"],
                    orientation="h",
                    marker_color=CATEGORICAL[0],
                    hovertemplate="%{y}<br>%{x:,} customers<extra></extra>",
                )
            )
            apply_layout(fig_seg, height=380, xaxis_title="Customers", margin=dict(l=140, r=30, t=40, b=60))
            fig_seg.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_seg, use_container_width=True, theme=None)
        with col_b:
            st.markdown("**Revenue by segment**")
            fig_rev = go.Figure(
                go.Bar(
                    x=summary["total_revenue"],
                    y=summary["segment"],
                    orientation="h",
                    marker_color=CATEGORICAL[1],
                    hovertemplate="%{y}<br>R$ %{x:,.0f}<extra></extra>",
                )
            )
            apply_layout(fig_rev, height=380, xaxis_title="Revenue (R$)", margin=dict(l=140, r=30, t=40, b=60))
            fig_rev.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_rev, use_container_width=True, theme=None)

        st.markdown("**Recency vs. Frequency** (bubble size = monetary value, sampled for readability)")
        sample = rfm.sample(min(3000, len(rfm)), random_state=42)
        fig_scatter = px.scatter(
            sample,
            x="recency_days",
            y="frequency",
            size="monetary",
            color="segment",
            color_discrete_sequence=CATEGORICAL,
            hover_data={"monetary": ":,.2f", "recency_days": True, "frequency": True, "segment": True},
        )
        apply_layout(fig_scatter, height=460, xaxis_title="Recency (days)", yaxis_title="Frequency (orders)")
        st.plotly_chart(fig_scatter, use_container_width=True, theme=None)

        st.subheader("Segment Summary")
        st.dataframe(
            summary.rename(
                columns={
                    "segment": "Segment",
                    "customer_count": "Customers",
                    "avg_recency_days": "Avg Recency (days)",
                    "avg_frequency": "Avg Frequency",
                    "avg_monetary": "Avg Monetary (R$)",
                    "total_revenue": "Total Revenue (R$)",
                    "pct_of_customers": "% of Customers",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        with st.expander("Show customer-level RFM table"):
            st.dataframe(rfm, use_container_width=True)

# ---------------------------------------------------------------------------
# Geography
# ---------------------------------------------------------------------------
with tab_geo:
    st.subheader("Revenue by State")
    state_rev = revenue_by_state(fdf)

    fig_state = go.Figure(
        go.Bar(
            x=state_rev["customer_state"],
            y=state_rev["total_revenue"],
            marker_color=CATEGORICAL[0],
            hovertemplate="%{x}<br>R$ %{y:,.0f} · %{customdata} orders<extra></extra>",
            customdata=state_rev["total_orders"],
        )
    )
    apply_layout(fig_state, height=420, xaxis_title="State", yaxis_title="Revenue (R$)", showlegend=False)
    st.plotly_chart(fig_state, use_container_width=True, theme=None)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Top 10 cities by order volume**")
        city = fdf.drop_duplicates("order_id")["customer_city"].value_counts().head(10).sort_values()
        fig_city = go.Figure(
            go.Bar(
                x=city.values,
                y=city.index,
                orientation="h",
                marker_color=CATEGORICAL[2],
                hovertemplate="%{y}<br>%{x:,} orders<extra></extra>",
            )
        )
        apply_layout(fig_city, height=380, xaxis_title="Orders", margin=dict(l=140, r=30, t=40, b=60))
        st.plotly_chart(fig_city, use_container_width=True, theme=None)
    with col_b:
        st.markdown("**Revenue concentration (top 10 states)**")
        top_states = state_rev.head(10)
        fig_pie = go.Figure(
            go.Pie(
                labels=top_states["customer_state"],
                values=top_states["total_revenue"],
                hole=0.5,
                marker=dict(colors=CATEGORICAL),
                sort=False,
            )
        )
        apply_layout(fig_pie, height=380)
        st.plotly_chart(fig_pie, use_container_width=True, theme=None)

    with st.expander("Show state revenue table"):
        st.dataframe(state_rev, use_container_width=True)

st.divider()
st.caption("Source: Olist Brazilian E-Commerce Public Dataset (Kaggle)")
