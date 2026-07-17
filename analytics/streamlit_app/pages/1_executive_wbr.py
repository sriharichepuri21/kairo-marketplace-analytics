"""Executive Weekly Business Review dashboard."""

from pathlib import Path

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "warehouse" / "kairo_dashboard.duckdb"

st.set_page_config(
    page_title="Executive WBR",
    page_icon="📈",
    layout="wide",
)


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Dashboard warehouse was not found at {DB_PATH}."
        )
    return duckdb.connect(str(DB_PATH), read_only=True)


def main() -> None:
    st.title("📈 Executive Weekly Business Review")
    st.caption(
        "Governed marketplace performance using tax-exclusive Net GMV."
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
            eligible_orders,
            net_gmv_per_order,
            repeat_buyer_rate,
            weighted_margin
        FROM dashboard_kpis
        """
    ).fetchone()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Net GMV", f"${kpis[0]:,.0f}")
    col2.metric("Eligible Orders", f"{kpis[1]:,}")
    col3.metric("Net GMV / Order", f"${kpis[2]:,.2f}")
    col4.metric("Repeat Buyer Rate", f"{kpis[3]:.1f}%")
    col5.metric("Weighted Margin", f"{kpis[4]:.1f}%")

    st.markdown("---")
    st.subheader("Monthly Net GMV and Order Trend")

    monthly = conn.execute(
        """
        SELECT
            month,
            net_gmv,
            eligible_orders AS orders
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
        fig.add_trace(
            go.Scatter(
                x=monthly["month"],
                y=monthly["orders"],
                name="Orders",
                yaxis="y2",
                line=dict(color="#EC4899", width=2),
            )
        )
        fig.update_layout(
            yaxis=dict(title="Net GMV ($)", side="left"),
            yaxis2=dict(
                title="Eligible Orders",
                side="right",
                overlaying="y",
            ),
            height=400,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
            ),
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Regional Performance")

    region = conn.execute(
        """
        SELECT
            region,
            net_gmv,
            eligible_orders AS orders,
            customers,
            weighted_margin
        FROM dashboard_region_performance
        ORDER BY net_gmv DESC
        """
    ).df()

    if not region.empty:
        col_l, col_r = st.columns(2)

        with col_l:
            fig2 = px.pie(
                region,
                values="net_gmv",
                names="region",
                title="Net GMV Share by Region",
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

        with col_r:
            st.dataframe(
                region.style.format(
                    {
                        "net_gmv": "${:,.0f}",
                        "orders": "{:,.0f}",
                        "customers": "{:,.0f}",
                        "weighted_margin": "{:.1f}%",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("Category Performance")

    category = conn.execute(
        """
        SELECT
            category,
            net_gmv,
            orders,
            items,
            weighted_margin
        FROM dashboard_category_summary
        ORDER BY net_gmv DESC
        """
    ).df()

    if not category.empty:
        fig3 = px.bar(
            category,
            x="category",
            y="net_gmv",
            color="weighted_margin",
            color_continuous_scale="RdYlGn",
            title="Net GMV by Category",
        )
        fig3.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis_title="Net GMV ($)",
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Customer Health Distribution")

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
                    "avg_orders": "{:.1f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
