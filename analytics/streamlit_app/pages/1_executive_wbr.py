"""
Executive Weekly Business Review Dashboard
"""

import streamlit as st
import duckdb
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="Executive WBR", page_icon="📈", layout="wide")

DB_PATH = Path("warehouse/kairo.duckdb")


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def main():
    st.title("📈 Executive Weekly Business Review")
    st.markdown("---")

    conn = get_connection()

    # Top KPIs
    col1, col2, col3, col4, col5 = st.columns(5)

    total_gmv = conn.execute("SELECT ROUND(SUM(gmv)) FROM main.mart_gmv_daily").fetchone()[0]
    total_orders = conn.execute("SELECT SUM(order_count) FROM main.mart_gmv_daily").fetchone()[0]
    avg_order_value = conn.execute("SELECT ROUND(SUM(gmv) / SUM(order_count), 2) FROM main.mart_gmv_daily").fetchone()[0]
    repeat_rate = conn.execute("""
        SELECT ROUND(100.0 * SUM(CASE WHEN is_repeat_customer THEN 1 ELSE 0 END) / COUNT(*), 1)
        FROM main.mart_customer_ltv
    """).fetchone()[0]
    avg_margin = conn.execute("""
        SELECT ROUND(AVG(gross_margin_pct), 1) FROM main.mart_gmv_daily WHERE gross_margin_pct IS NOT NULL
    """).fetchone()[0]

    col1.metric("Total GMV", f"${total_gmv:,.0f}")
    col2.metric("Total Orders", f"{total_orders:,.0f}")
    col3.metric("Avg Order Value", f"${avg_order_value:,.2f}")
    col4.metric("Repeat Customer %", f"{repeat_rate}%")
    col5.metric("Avg Margin %", f"{avg_margin}%")

    st.markdown("---")

    # Monthly GMV Trend
    st.subheader("Monthly GMV Trend")

    monthly = conn.execute("""
        SELECT
            DATE_TRUNC('month', order_date) AS month,
            ROUND(SUM(gmv)) AS gmv,
            SUM(order_count) AS orders
        FROM main.mart_gmv_daily
        GROUP BY month
        ORDER BY month
    """).df()

    if len(monthly) > 0:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly["month"].to_list(),
            y=monthly["gmv"].to_list(),
            name="GMV",
            marker_color="#4F46E5",
        ))
        fig.add_trace(go.Scatter(
            x=monthly["month"].to_list(),
            y=monthly["orders"].to_list(),
            name="Orders",
            yaxis="y2",
            line=dict(color="#EC4899", width=2),
        ))
        fig.update_layout(
            yaxis=dict(title="GMV ($)", side="left"),
            yaxis2=dict(title="Order Count", side="right", overlaying="y"),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Region Performance
    st.subheader("Region Performance")

    region = conn.execute("""
        SELECT
            region,
            ROUND(SUM(gmv)) AS gmv,
            SUM(order_count) AS orders,
            SUM(customer_count) AS customers,
            ROUND(AVG(gross_margin_pct), 1) AS avg_margin
        FROM main.mart_gmv_daily
        GROUP BY region
        ORDER BY gmv DESC
    """).df()

    if len(region) > 0:
        col_l, col_r = st.columns(2)
        with col_l:
            fig2 = px.pie(
                region, values="gmv", names="region",
                title="GMV Share by Region",
                color_discrete_sequence=["#4F46E5", "#7C3AED", "#EC4899"],
            )
            fig2.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig2, use_container_width=True)
        with col_r:
            st.dataframe(region, use_container_width=True, hide_index=True)

    # Category Performance
    st.subheader("Category Performance")

    category = conn.execute("""
        SELECT
            category,
            ROUND(SUM(gmv)) AS gmv,
            SUM(order_count) AS orders,
            SUM(items_sold) AS items,
            ROUND(AVG(gross_margin_pct), 1) AS avg_margin
        FROM main.mart_gmv_daily
        GROUP BY category
        ORDER BY gmv DESC
    """).df()

    if len(category) > 0:
        fig3 = px.bar(
            category, x="category", y="gmv",
            color="avg_margin",
            color_continuous_scale="RdYlGn",
            title="GMV by Category (colored by margin %)",
        )
        fig3.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig3, use_container_width=True)

    # Customer Health
    st.subheader("Customer Health Distribution")

    health = conn.execute("""
        SELECT
            activity_status,
            COUNT(*) AS customers,
            ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
            ROUND(AVG(total_orders), 1) AS avg_orders
        FROM main.mart_customer_ltv
        GROUP BY activity_status
        ORDER BY customers DESC
    """).df()

    if len(health) > 0:
        st.dataframe(health, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()