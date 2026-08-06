"""
Analytics helpers for the Olist Streamlit app.

Ports the SQL logic from sql/02_cohort_retention.sql, sql/03_rfm_segmentation.sql
and sql/04_revenue_analysis.sql to pandas so the app can run directly off the
cleaned CSV export without a database connection.
"""

import numpy as np
import pandas as pd


def build_orders_view(df: pd.DataFrame) -> pd.DataFrame:
    """One row per order (dedupe the order-items grain) for order-level metrics."""
    order_cols = [
        "order_id",
        "customer_unique_id",
        "order_status",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
        "payment_value",
        "customer_state",
        "customer_city",
        "order_month",
    ]
    orders = df[order_cols].drop_duplicates(subset="order_id").copy()
    return orders


def monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    orders = build_orders_view(df)
    monthly = (
        orders.groupby("order_month")
        .agg(total_revenue=("payment_value", "sum"), total_orders=("order_id", "nunique"))
        .reset_index()
        .sort_values("order_month")
    )
    monthly["prev_month_revenue"] = monthly["total_revenue"].shift(1)
    monthly["growth_pct"] = (
        (monthly["total_revenue"] - monthly["prev_month_revenue"]) / monthly["prev_month_revenue"] * 100
    )
    return monthly


def revenue_by_category(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    cat = (
        df.groupby("product_category_name")
        .agg(total_revenue=("price", "sum"), total_orders=("order_id", "nunique"))
        .reset_index()
        .sort_values("total_revenue", ascending=False)
        .head(top_n)
    )
    return cat


def revenue_by_state(df: pd.DataFrame) -> pd.DataFrame:
    orders = build_orders_view(df)
    state = (
        orders.groupby("customer_state")
        .agg(total_revenue=("payment_value", "sum"), total_orders=("order_id", "nunique"))
        .reset_index()
        .sort_values("total_revenue", ascending=False)
    )
    return state


def compute_rfm(df: pd.DataFrame) -> pd.DataFrame:
    """Recency/Frequency/Monetary scoring + segment labels, mirrors 03_rfm_segmentation.sql."""
    delivered = df[df["order_status"] == "delivered"].copy()
    delivered["order_purchase_timestamp"] = pd.to_datetime(delivered["order_purchase_timestamp"])

    ref_date = delivered["order_purchase_timestamp"].max() + pd.Timedelta(days=1)

    orders = delivered.drop_duplicates(subset="order_id")
    rfm = (
        orders.groupby("customer_unique_id")
        .agg(
            last_purchase=("order_purchase_timestamp", "max"),
            frequency=("order_id", "nunique"),
        )
        .reset_index()
    )
    monetary = orders.groupby("customer_unique_id")["payment_value"].sum().reset_index(name="monetary")
    rfm = rfm.merge(monetary, on="customer_unique_id")
    rfm["recency_days"] = (ref_date - rfm["last_purchase"]).dt.days
    rfm["monetary"] = rfm["monetary"].round(2)

    if len(rfm) < 5:
        rfm["r_score"] = pd.Series(dtype=int)
        rfm["f_score"] = pd.Series(dtype=int)
        rfm["m_score"] = pd.Series(dtype=int)
        rfm["rfm_cell"] = pd.Series(dtype=str)
        rfm["segment"] = pd.Series(dtype=str)
        return rfm.drop(columns=["last_purchase"])

    # ntile(5): higher r_score = more recent (order by recency desc -> rank ascending recency gets low bucket)
    rfm["r_score"] = pd.qcut(rfm["recency_days"].rank(method="first", ascending=False), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["f_score"] = pd.qcut(rfm["frequency"].rank(method="first", ascending=True), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["m_score"] = pd.qcut(rfm["monetary"].rank(method="first", ascending=True), 5, labels=[1, 2, 3, 4, 5]).astype(int)

    rfm["rfm_cell"] = rfm["r_score"].astype(str) + rfm["f_score"].astype(str) + rfm["m_score"].astype(str)

    def segment(row):
        r, f = row["r_score"], row["f_score"]
        if r >= 4 and f >= 4:
            return "Champions"
        if r >= 3 and f >= 3:
            return "Loyal Customers"
        if r >= 4 and f < 3:
            return "Recent Customers"
        if r >= 3 and f < 3:
            return "Potential Loyalists"
        if r < 2 and f >= 3:
            return "Cannot Lose Them"
        if r < 3 and f >= 3:
            return "At Risk"
        if r < 2 and f < 2:
            return "Lost"
        return "Needs Attention"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm.drop(columns=["last_purchase"]).sort_values("monetary", ascending=False)


def rfm_segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    summary = (
        rfm.groupby("segment")
        .agg(
            customer_count=("customer_unique_id", "count"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency=("frequency", "mean"),
            avg_monetary=("monetary", "mean"),
            total_revenue=("monetary", "sum"),
        )
        .reset_index()
    )
    summary["pct_of_customers"] = (summary["customer_count"] / summary["customer_count"].sum() * 100).round(2)
    for c in ["avg_recency_days", "avg_frequency", "avg_monetary", "total_revenue"]:
        summary[c] = summary[c].round(2)
    return summary.sort_values("total_revenue", ascending=False)


def cohort_retention(df: pd.DataFrame) -> pd.DataFrame:
    """Full cohort_month x cohort_index retention table, mirrors 02_cohort_retention.sql."""
    delivered = df[df["order_status"] == "delivered"].copy()
    delivered["order_purchase_timestamp"] = pd.to_datetime(delivered["order_purchase_timestamp"])
    orders = delivered.drop_duplicates(subset="order_id")

    orders["activity_month"] = orders["order_purchase_timestamp"].values.astype("datetime64[M]")
    cohort_month = orders.groupby("customer_unique_id")["activity_month"].min().rename("cohort_month")
    orders = orders.join(cohort_month, on="customer_unique_id")

    orders["cohort_index"] = (
        (orders["activity_month"].dt.year - orders["cohort_month"].dt.year) * 12
        + (orders["activity_month"].dt.month - orders["cohort_month"].dt.month)
    )

    cohort_data = (
        orders.groupby(["cohort_month", "cohort_index"])["customer_unique_id"]
        .nunique()
        .reset_index(name="active_customers")
    )

    cohort_sizes = cohort_data[cohort_data["cohort_index"] == 0][["cohort_month", "active_customers"]].rename(
        columns={"active_customers": "cohort_size"}
    )

    cohort_data = cohort_data.merge(cohort_sizes, on="cohort_month")
    cohort_data["retention_rate_pct"] = (
        cohort_data["active_customers"] / cohort_data["cohort_size"] * 100
    ).round(2)

    return cohort_data.sort_values(["cohort_month", "cohort_index"])


def cohort_retention_pivot(cohort_data: pd.DataFrame) -> pd.DataFrame:
    pivot = cohort_data.pivot(index="cohort_month", columns="cohort_index", values="retention_rate_pct")
    pivot.index = pivot.index.strftime("%Y-%m")
    return pivot


def cohort_index_summary(cohort_data: pd.DataFrame) -> pd.DataFrame:
    summary = (
        cohort_data.groupby("cohort_index")
        .agg(
            num_cohorts=("cohort_month", "nunique"),
            total_active=("active_customers", "sum"),
            avg_retention_pct=("retention_rate_pct", "mean"),
        )
        .reset_index()
        .rename(columns={"cohort_index": "months_since_acquisition"})
    )
    summary["avg_retention_pct"] = summary["avg_retention_pct"].round(2)
    return summary


def kpi_summary(df: pd.DataFrame) -> dict:
    orders = build_orders_view(df)
    delivered = orders[orders["order_status"] == "delivered"]
    total_revenue = delivered["payment_value"].sum()
    total_orders = delivered["order_id"].nunique()
    unique_customers = delivered["customer_unique_id"].nunique()
    aov = total_revenue / total_orders if total_orders else 0
    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "unique_customers": unique_customers,
        "avg_order_value": aov,
    }
