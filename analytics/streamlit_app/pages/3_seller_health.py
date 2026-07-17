"""Seller Health dashboard."""

from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "warehouse" / "kairo_dashboard.duckdb"

st.set_page_config(
    page_title="Seller Health",
    page_icon="🏪",
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
    st.title("🏪 Seller Health Dashboard")
    st.markdown(
        "*For Seller Success — monitor seller ecosystem health*"
    )
    st.caption(
        "Seller performance and commissions are calculated from Net GMV."
    )
    st.markdown("---")

    try:
        conn = get_connection()
    except Exception as error:
        st.error(str(error))
        st.stop()

    status = conn.execute(
        """
        SELECT
            COUNT(*) AS total_sellers,
            COUNT(*) FILTER (
                WHERE health_status = 'active'
            ) AS active_sellers,
            COUNT(*) FILTER (
                WHERE health_status = 'at_risk'
            ) AS at_risk_sellers,
            COUNT(*) FILTER (
                WHERE health_status = 'churned'
            ) AS churned_sellers,
            COUNT(*) FILTER (
                WHERE health_status = 'no_sales'
            ) AS no_sales_sellers
        FROM mart_seller_health
        """
    ).fetchone()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Sellers", f"{status[0]:,}")
    col2.metric("✅ Active", f"{status[1]:,}")
    col3.metric("⚠️ At Risk", f"{status[2]:,}")
    col4.metric("❌ Churned", f"{status[3]:,}")
    col5.metric("No Sales", f"{status[4]:,}")

    st.markdown("---")
    st.subheader("Seller Health Distribution")

    health = conn.execute(
        """
        SELECT
            health_status,
            tier,
            COUNT(*) AS sellers,
            ROUND(SUM(net_gmv), 2) AS net_gmv,
            ROUND(AVG(net_gmv), 2) AS avg_net_gmv
        FROM mart_seller_health
        GROUP BY health_status, tier
        ORDER BY health_status, sellers DESC
        """
    ).df()

    if not health.empty:
        col_l, col_r = st.columns(2)

        with col_l:
            fig = px.sunburst(
                health,
                path=["health_status", "tier"],
                values="sellers",
                title="Sellers: Health Status → Tier",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(
                height=450,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            tier_summary = conn.execute(
                """
                SELECT
                    tier,
                    COUNT(*) AS sellers,
                    ROUND(SUM(net_gmv), 2) AS net_gmv,
                    ROUND(
                        SUM(commission_revenue),
                        2
                    ) AS commission_revenue,
                    ROUND(AVG(avg_rating), 2) AS avg_rating,
                    ROUND(
                        AVG(commission_rate) * 100,
                        1
                    ) AS avg_commission_pct
                FROM mart_seller_health
                GROUP BY tier
                ORDER BY net_gmv DESC
                """
            ).df()

            st.dataframe(
                tier_summary.style.format(
                    {
                        "sellers": "{:,}",
                        "net_gmv": "${:,.0f}",
                        "commission_revenue": "${:,.0f}",
                        "avg_rating": "{:.2f}",
                        "avg_commission_pct": "{:.1f}%",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("Top 20 Sellers by Net GMV")

    top_sellers = conn.execute(
        """
        SELECT
            business_name,
            tier,
            region,
            primary_category,
            total_orders,
            total_items_sold,
            ROUND(net_gmv, 2) AS net_gmv,
            ROUND(
                commission_revenue,
                2
            ) AS commission_revenue,
            avg_rating,
            health_status
        FROM mart_seller_health
        ORDER BY net_gmv DESC
        LIMIT 20
        """
    ).df()

    if not top_sellers.empty:
        st.dataframe(
            top_sellers.style.format(
                {
                    "net_gmv": "${:,.0f}",
                    "commission_revenue": "${:,.0f}",
                    "total_orders": "{:,}",
                    "total_items_sold": "{:,}",
                    "avg_rating": "{:.2f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("⚠️ At-Risk Sellers — Intervention Needed")

    at_risk = conn.execute(
        """
        SELECT
            business_name,
            tier,
            region,
            primary_category,
            total_orders,
            ROUND(net_gmv, 2) AS net_gmv,
            days_since_last_sale,
            avg_rating,
            health_status
        FROM mart_seller_health
        WHERE health_status = 'at_risk'
        ORDER BY net_gmv DESC
        LIMIT 15
        """
    ).df()

    if not at_risk.empty:
        st.dataframe(
            at_risk.style.format(
                {
                    "net_gmv": "${:,.0f}",
                    "total_orders": "{:,}",
                    "avg_rating": "{:.2f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No at-risk sellers found.")


if __name__ == "__main__":
    main()
