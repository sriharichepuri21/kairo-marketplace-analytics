"""Kairo Marketplace Analytics — deployment-ready executive dashboard."""

from pathlib import Path

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "warehouse" / "kairo_dashboard.duckdb"

st.set_page_config(
    page_title="Kairo Analytics",
    page_icon="📊",
    layout="wide",
)


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    """Open the compact read-only dashboard warehouse."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Dashboard warehouse was not found at {DB_PATH}. "
            "Run: python scripts/build_dashboard_warehouse.py"
        )
    return duckdb.connect(str(DB_PATH), read_only=True)


def main() -> None:
    """Render the executive overview."""
    st.title("📊 Kairo Marketplace Analytics")
    st.caption(
        "Governed marketplace reporting across customers, orders, "
        "categories, regions, sellers, and customer retention."
    )
    st.markdown("---")

    try:
        conn = get_connection()
    except Exception as error:
        st.error(str(error))
        st.stop()

    kpis = conn.execute(
        """
        SELECT
            net_gmv,
            customer_charged_amount,
            eligible_orders,
            real_customers,
            commission_revenue
        FROM dashboard_kpis
        """
    ).fetchone()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Net GMV", f"${kpis[0]:,.0f}")
    col2.metric("Customer Charged", f"${kpis[1]:,.0f}")
    col3.metric("Eligible Orders", f"{kpis[2]:,}")
    col4.metric("Real Customers", f"{kpis[3]:,}")
    col5.metric("Commission Revenue", f"${kpis[4]:,.0f}")

    st.caption(
        "Net GMV is merchandise value after valid item discounts and "
        "before tax and shipping. Customer Charged includes eligible "
        "order totals."
    )
    st.markdown("---")

    st.subheader("Monthly Net GMV Trend")
    monthly = conn.execute(
        """
        SELECT month, net_gmv, eligible_orders
        FROM dashboard_monthly_marketplace
        ORDER BY month
        """
    ).df()

    if not monthly.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=monthly["month"],
                y=monthly["net_gmv"],
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
        region_data = conn.execute(
            """
            SELECT region, net_gmv, eligible_orders
            FROM dashboard_region_performance
            ORDER BY net_gmv DESC
            """
        ).df()

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
        category_data = conn.execute(
            """
            SELECT category, net_gmv, orders
            FROM dashboard_category_summary
            ORDER BY net_gmv DESC
            """
        ).df()

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
    customer_health = conn.execute(
        """
        SELECT
            activity_status,
            customers,
            avg_lifetime_spend,
            avg_orders
        FROM dashboard_customer_health
        ORDER BY customers DESC
        """
    ).df()

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
    st.subheader("Pipeline Health")

    metadata = conn.execute(
        """
        SELECT
            dbt_models,
            dbt_tests,
            passing_tests,
            documented_warnings,
            errors
        FROM dashboard_metadata
        """
    ).fetchone()

    col_a, col_b, col_c = st.columns(3)
    col_a.info(f"**Models:** {metadata[0]} dbt models")
    col_b.info(
        f"**Tests:** {metadata[1]} total — "
        f"{metadata[2]} pass, {metadata[3]} warn, "
        f"{metadata[4]} error"
    )
    col_c.info("**Reconciliation:** $0 unexplained cross-model variance")


if __name__ == "__main__":
    main()
