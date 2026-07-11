"""
Category Manager Dashboard
Persona: VP of Category
Cadence: Weekly
"""

import streamlit as st
import duckdb
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Category Performance", page_icon="🏷️", layout="wide")

DB_PATH = Path("warehouse/kairo.duckdb")


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def main():
    st.title("🏷️ Category Performance Dashboard")
    st.markdown("*For Category Managers — weekly performance review*")
    st.markdown("---")

    conn = get_connection()

    # Category selector
    categories = conn.execute("""
        SELECT DISTINCT category FROM main.mart_gmv_daily ORDER BY category
    """).df()["category"].to_list()

    selected_category = st.selectbox("Select Category", ["All Categories"] + categories)

    where_clause = ""
    if selected_category != "All Categories":
        where_clause = f"WHERE category = '{selected_category}'"

    # KPIs
    kpis = conn.execute(f"""
        SELECT
            ROUND(SUM(gmv)) AS gmv,
            SUM(order_count) AS orders,
            SUM(items_sold) AS items,
            ROUND(AVG(gross_margin_pct), 1) AS margin
        FROM main.mart_gmv_daily
        {where_clause}
    """).fetchone()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("GMV", f"${kpis[0]:,.0f}")
    col2.metric("Orders", f"{kpis[1]:,}")
    col3.metric("Items Sold", f"{kpis[2]:,}")
    col4.metric("Avg Margin", f"{kpis[3]}%")

    st.markdown("---")

    # Monthly trend for selected category
    st.subheader(f"Monthly Trend — {selected_category}")

    monthly = conn.execute(f"""
        SELECT
            DATE_TRUNC('month', order_date) AS month,
            ROUND(SUM(gmv)) AS gmv,
            SUM(order_count) AS orders,
            ROUND(AVG(gross_margin_pct), 1) AS margin
        FROM main.mart_gmv_daily
        {where_clause}
        GROUP BY month
        ORDER BY month
    """).df()

    if len(monthly) > 0:
        fig = px.line(
            monthly,
            x="month", y="gmv",
            markers=True,
            color_discrete_sequence=["#4F46E5"],
        )
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # Category comparison table
    st.subheader("Category Comparison")

    comparison = conn.execute("""
        SELECT
            category,
            ROUND(SUM(gmv)) AS total_gmv,
            SUM(order_count) AS total_orders,
            SUM(items_sold) AS total_items,
            ROUND(AVG(gross_margin_pct), 1) AS avg_margin,
            ROUND(SUM(total_discounts)) AS total_discounts
        FROM main.mart_gmv_daily
        GROUP BY category
        ORDER BY total_gmv DESC
    """).df()

    if len(comparison) > 0:
        st.dataframe(
            comparison.style.format({
                "total_gmv": "${:,.0f}",
                "total_orders": "{:,.0f}",
                "total_items": "{:,.0f}",
                "avg_margin": "{:.1f}%",
                "total_discounts": "${:,.0f}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    # Segment breakdown within category
    st.subheader(f"Customer Segments — {selected_category}")

    segment_filter = f"AND category = '{selected_category}'" if selected_category != "All Categories" else ""

    segments = conn.execute(f"""
        SELECT
            customer_segment,
            ROUND(SUM(gmv)) AS gmv,
            SUM(order_count) AS orders,
            ROUND(SUM(gmv) * 100.0 / SUM(SUM(gmv)) OVER (), 1) AS gmv_share_pct
        FROM main.mart_gmv_daily
        WHERE 1=1 {segment_filter}
        GROUP BY customer_segment
        ORDER BY gmv DESC
    """).df()

    if len(segments) > 0:
        col_l, col_r = st.columns(2)
        with col_l:
            fig2 = px.pie(
                segments,
                values="gmv", names="customer_segment",
                title="GMV by Customer Segment",
            )
            fig2.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig2, use_container_width=True)

        with col_r:
            st.dataframe(
                segments.style.format({
                    "gmv": "${:,.0f}",
                    "orders": "{:,.0f}",
                    "gmv_share_pct": "{:.1f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )


if __name__ == "__main__":
    main()