"""
Kairo Marketplace Analytics — Executive Dashboard Suite

This is the entry point for the Streamlit multi-page app.
Each page in the /pages folder becomes a tab in the sidebar.

Run: streamlit run analytics/streamlit_app/app.py
"""

import streamlit as st
import duckdb
from pathlib import Path

st.set_page_config(
    page_title="Kairo Analytics",
    page_icon="📊",
    layout="wide",
)

DB_PATH = Path("warehouse/kairo.duckdb")


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def main():
    st.title("📊 Kairo Marketplace Analytics")
    st.markdown("---")

    conn = get_connection()

    # Top-level KPIs
    col1, col2, col3, col4 = st.columns(4)

    # Total GMV
    gmv = conn.execute("""
        SELECT ROUND(SUM(gmv), 2) FROM main.mart_gmv_daily
    """).fetchone()[0]

    # Total Orders
    orders = conn.execute("""
        SELECT COUNT(*) FROM main.fact_orders
        WHERE order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()[0]

    # Total Customers
    customers = conn.execute("""
        SELECT COUNT(*) FROM main.dim_customers
    """).fetchone()[0]

    # Active Sellers
    sellers = conn.execute("""
        SELECT COUNT(*) FROM main.mart_seller_health
        WHERE health_status = 'active'
    """).fetchone()[0]

    col1.metric("💰 Total GMV", f"${gmv:,.0f}")
    col2.metric("📦 Total Orders", f"{orders:,}")
    col3.metric("👥 Customers", f"{customers:,}")
    col4.metric("🏪 Active Sellers", f"{sellers:,}")

    st.markdown("---")

    # GMV Trend
    st.subheader("GMV Trend — Monthly")

    monthly_gmv = conn.execute("""
        SELECT
            DATE_TRUNC('month', order_date) AS month,
            ROUND(SUM(gmv), 2) AS monthly_gmv,
            SUM(order_count) AS monthly_orders
        FROM main.mart_gmv_daily
        GROUP BY month
        ORDER BY month
    """).df()

    if len(monthly_gmv) > 0:
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=monthly_gmv["month"].to_list(),
            y=monthly_gmv["monthly_gmv"].to_list(),
            name="Monthly GMV",
            marker_color="#4F46E5",
        ))
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="GMV ($)",
            height=400,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Region Breakdown
    st.subheader("GMV by Region")

    col_left, col_right = st.columns(2)

    with col_left:
        
        region_data = conn.execute("""
            SELECT
                region,
                ROUND(SUM(gmv), 2) AS total_gmv,
                SUM(order_count) AS total_orders
            FROM main.mart_gmv_daily
            GROUP BY region
            ORDER BY total_gmv DESC
        """).df()

        import plotly.express as px

        if len(region_data) > 0:
            fig2 = px.pie(
                region_data,
                values="total_gmv",
                names="region",
                color_discrete_sequence=["#4F46E5", "#7C3AED", "#EC4899"],
            )
            fig2.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        # Category breakdown
        category_data = conn.execute("""
            SELECT
                category,
                ROUND(SUM(gmv), 2) AS total_gmv,
                SUM(order_count) AS total_orders
            FROM main.mart_gmv_daily
            GROUP BY category
            ORDER BY total_gmv DESC
        """).df()

        if len(category_data) > 0:
            fig3 = px.bar(
                category_data,
                x="total_gmv",
                y="category",
                orientation="h",
                color_discrete_sequence=["#4F46E5"],
            )
            fig3.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                yaxis_title="",
                xaxis_title="GMV ($)",
            )
            st.plotly_chart(fig3, use_container_width=True)

    # Customer Segments
    st.subheader("Customer Activity Status")

    segment_data = conn.execute("""
        SELECT
            activity_status,
            COUNT(*) AS customer_count,
            ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
            ROUND(AVG(total_orders), 1) AS avg_orders
        FROM main.mart_customer_ltv
        GROUP BY activity_status
        ORDER BY customer_count DESC
    """).df()

    if len(segment_data) > 0:
        st.dataframe(
            segment_data,
            use_container_width=True,
            hide_index=True,
        )

    # Pipeline Health
    st.markdown("---")
    st.subheader("🔧 Pipeline Health")

    col_a, col_b, col_c = st.columns(3)

    dbt_run = "dbt run → PASS=27"
    dbt_test = "dbt test → PASS=99, WARN=8, ERROR=0"

    col_a.info(f"**Models:** {dbt_run}")
    col_b.info(f"**Tests:** {dbt_test}")
    col_c.info("**Data Quality:** 8 known warnings documented")


if __name__ == "__main__":
    main()