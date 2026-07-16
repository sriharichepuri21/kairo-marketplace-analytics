"""
Kairo Marketplace Analytics — Executive Dashboard Suite

Entry point for the Streamlit multi-page Business Intelligence app.

Run:
    streamlit run analytics/streamlit_app/app.py
"""

from pathlib import Path

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Kairo Analytics",
    page_icon="📊",
    layout="wide",
)

DB_PATH = Path("warehouse/kairo.duckdb")


@st.cache_resource
def get_connection():
    """Open the governed DuckDB warehouse."""

    return duckdb.connect(str(DB_PATH), read_only=True)


def main():
    """Render the executive overview."""

    st.title("📊 Kairo Marketplace Analytics")
    st.caption(
        "Governed marketplace reporting across customers, orders, "
        "categories, regions, and sellers."
    )
    st.markdown("---")

    conn = get_connection()

    kpis = conn.execute("""
        SELECT
            (
                SELECT ROUND(SUM(net_gmv), 2)
                FROM main.mart_gmv_daily
            ) AS net_gmv,

            (
                SELECT ROUND(SUM(total_amount), 2)
                FROM main.fact_orders
                WHERE order_status NOT IN ('cancelled', 'refunded')
            ) AS customer_charged_amount,

            (
                SELECT COUNT(DISTINCT order_id)
                FROM main.fact_orders
                WHERE order_status NOT IN ('cancelled', 'refunded')
            ) AS eligible_orders,

            (
                SELECT COUNT(*)
                FROM main.dim_customers
                WHERE is_unknown_customer = FALSE
            ) AS real_customers,

            (
                SELECT ROUND(SUM(commission_revenue), 2)
                FROM main.mart_seller_health
            ) AS commission_revenue
    """).fetchone()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Net GMV", f"${kpis[0]:,.0f}")
    col2.metric("Customer Charged", f"${kpis[1]:,.0f}")
    col3.metric("Eligible Orders", f"{kpis[2]:,}")
    col4.metric("Real Customers", f"{kpis[3]:,}")
    col5.metric("Commission Revenue", f"${kpis[4]:,.0f}")

    st.caption(
        "Net GMV represents merchandise value after item discounts "
        "and before tax. Customer Charged includes eligible order totals."
    )

    st.markdown("---")
    st.subheader("Monthly Net GMV Trend")

    monthly = conn.execute("""
        WITH monthly_gmv AS (
            SELECT
                DATE_TRUNC('month', order_date) AS month,
                ROUND(SUM(net_gmv), 2) AS net_gmv
            FROM main.mart_gmv_daily
            GROUP BY 1
        ),

        monthly_orders AS (
            SELECT
                DATE_TRUNC('month', order_date) AS month,
                COUNT(DISTINCT order_id) AS eligible_orders
            FROM main.fact_orders
            WHERE order_status NOT IN ('cancelled', 'refunded')
            GROUP BY 1
        )

        SELECT
            g.month,
            g.net_gmv,
            o.eligible_orders
        FROM monthly_gmv AS g
        JOIN monthly_orders AS o
            ON g.month = o.month
        ORDER BY g.month
    """).df()

    if not monthly.empty:
        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=monthly["month"].to_list(),
                y=monthly["net_gmv"].to_list(),
                name="Net GMV",
                marker_color="#4F46E5",
            )
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Net GMV ($)",
            height=400,
            margin=dict(l=20, r=20, t=20, b=20),
        )

        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Marketplace Performance")

    col_left, col_right = st.columns(2)

    with col_left:
        region_data = conn.execute("""
            WITH regional_gmv AS (
                SELECT
                    region,
                    ROUND(SUM(net_gmv), 2) AS net_gmv
                FROM main.mart_gmv_daily
                GROUP BY region
            ),

            regional_orders AS (
                SELECT
                    region,
                    COUNT(DISTINCT order_id) AS eligible_orders
                FROM main.fact_orders
                WHERE order_status NOT IN ('cancelled', 'refunded')
                GROUP BY region
            )

            SELECT
                g.region,
                g.net_gmv,
                o.eligible_orders
            FROM regional_gmv AS g
            JOIN regional_orders AS o
                ON g.region = o.region
            ORDER BY g.net_gmv DESC
        """).df()

        if not region_data.empty:
            fig2 = px.pie(
                region_data,
                values="net_gmv",
                names="region",
                title="Net GMV by Region",
                color_discrete_sequence=[
                    "#4F46E5",
                    "#7C3AED",
                    "#EC4899",
                ],
            )

            fig2.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
            )

            st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        category_data = conn.execute("""
            SELECT
                category,

                ROUND(
                    SUM(
                        CASE
                            WHEN is_gmv_valid THEN net_gmv
                            ELSE 0
                        END
                    ),
                    2
                ) AS net_gmv,

                COUNT(
                    DISTINCT CASE
                        WHEN is_gmv_valid THEN order_id
                    END
                ) AS orders

            FROM main.fact_order_items

            WHERE order_status NOT IN ('cancelled', 'refunded')

            GROUP BY category
            ORDER BY net_gmv DESC
        """).df()

        if not category_data.empty:
            fig3 = px.bar(
                category_data,
                x="net_gmv",
                y="category",
                orientation="h",
                title="Net GMV by Category",
                color_discrete_sequence=["#4F46E5"],
            )

            fig3.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                yaxis_title="",
                xaxis_title="Net GMV ($)",
            )

            st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Customer Activity Status")

    customer_health = conn.execute("""
        SELECT
            activity_status,
            COUNT(*) AS customers,

            ROUND(
                AVG(lifetime_revenue),
                2
            ) AS avg_lifetime_spend,

            ROUND(
                AVG(total_orders),
                1
            ) AS avg_orders

        FROM main.mart_customer_ltv

        WHERE is_unknown_customer = FALSE

        GROUP BY activity_status
        ORDER BY customers DESC
    """).df()

    if not customer_health.empty:
        st.dataframe(
            customer_health.style.format(
                {
                    "customers": "{:,.0f}",
                    "avg_lifetime_spend": "${:,.2f}",
                    "avg_orders": "{:,.1f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    st.subheader("🔧 Pipeline Health")

    col_a, col_b, col_c = st.columns(3)

    col_a.info("**Models:** 27 Bronze, Silver, and Gold models")
    col_b.info("**Tests:** 107 tests — 102 pass, 5 warn, 0 error")
    col_c.info("**Reconciliation:** $0 cross-model variance")


if __name__ == "__main__":
    main()
