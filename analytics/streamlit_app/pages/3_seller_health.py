"""
Seller Health Dashboard
Persona: Head of Seller Success
Cadence: Weekly
"""

import streamlit as st
import duckdb
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Seller Health", page_icon="🏪", layout="wide")

DB_PATH = Path("warehouse/kairo.duckdb")


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def main():
    st.title("🏪 Seller Health Dashboard")
    st.markdown("*For Seller Success Team — monitor seller ecosystem health*")
    st.markdown("---")

    conn = get_connection()

    # Top KPIs
    col1, col2, col3, col4 = st.columns(4)

    total_sellers = conn.execute("SELECT COUNT(*) FROM main.mart_seller_health").fetchone()[0]
    active_sellers = conn.execute("""
        SELECT COUNT(*) FROM main.mart_seller_health WHERE health_status = 'active'
    """).fetchone()[0]
    at_risk = conn.execute("""
        SELECT COUNT(*) FROM main.mart_seller_health WHERE health_status = 'at_risk'
    """).fetchone()[0]
    churned = conn.execute("""
        SELECT COUNT(*) FROM main.mart_seller_health WHERE health_status = 'churned'
    """).fetchone()[0]

    col1.metric("Total Sellers", f"{total_sellers:,}")
    col2.metric("✅ Active", f"{active_sellers:,}")
    col3.metric("⚠️ At Risk", f"{at_risk:,}")
    col4.metric("❌ Churned", f"{churned:,}")

    st.markdown("---")

    # Health distribution
    st.subheader("Seller Health Distribution")

    health = conn.execute("""
        SELECT
            health_status,
            tier,
            COUNT(*) AS sellers,
            ROUND(SUM(total_gmv)) AS total_gmv,
            ROUND(AVG(total_gmv)) AS avg_gmv
        FROM main.mart_seller_health
        GROUP BY health_status, tier
        ORDER BY health_status, sellers DESC
    """).df()

    if len(health) > 0:
        col_l, col_r = st.columns(2)
        with col_l:
            fig = px.sunburst(
                health,
                path=["health_status", "tier"],
                values="sellers",
                title="Sellers: Health Status → Tier",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(height=450, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            # Health by tier table
            tier_summary = conn.execute("""
                SELECT
                    tier,
                    COUNT(*) AS sellers,
                    ROUND(SUM(total_gmv)) AS total_gmv,
                    ROUND(AVG(avg_rating), 2) AS avg_rating,
                    ROUND(AVG(commission_rate) * 100, 1) AS avg_commission_pct
                FROM main.mart_seller_health
                GROUP BY tier
                ORDER BY total_gmv DESC
            """).df()

            st.dataframe(
                tier_summary.style.format({
                    "sellers": "{:,}",
                    "total_gmv": "${:,.0f}",
                    "avg_rating": "{:.2f}",
                    "avg_commission_pct": "{:.1f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )

    # Top sellers
    st.subheader("Top 20 Sellers by GMV")

    top_sellers = conn.execute("""
        SELECT
            business_name,
            tier,
            region,
            primary_category,
            total_orders,
            total_items_sold,
            ROUND(total_gmv) AS total_gmv,
            ROUND(commission_revenue) AS commission_revenue,
            avg_rating,
            health_status
        FROM main.mart_seller_health
        ORDER BY total_gmv DESC
        LIMIT 20
    """).df()

    if len(top_sellers) > 0:
        st.dataframe(
            top_sellers.style.format({
                "total_gmv": "${:,.0f}",
                "commission_revenue": "${:,.0f}",
                "total_orders": "{:,}",
                "total_items_sold": "{:,}",
                "avg_rating": "{:.2f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # At-risk sellers
    st.subheader("⚠️ At-Risk Sellers — Intervention Needed")

    at_risk_sellers = conn.execute("""
        SELECT
            business_name,
            tier,
            region,
            primary_category,
            total_orders,
            ROUND(total_gmv) AS total_gmv,
            days_since_last_sale,
            avg_rating,
            health_status
        FROM main.mart_seller_health
        WHERE health_status = 'at_risk'
        ORDER BY total_gmv DESC
        LIMIT 15
    """).df()

    if len(at_risk_sellers) > 0:
        st.dataframe(
            at_risk_sellers.style.format({
                "total_gmv": "${:,.0f}",
                "total_orders": "{:,}",
                "avg_rating": "{:.2f}",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("No at-risk sellers found!")


if __name__ == "__main__":
    main()