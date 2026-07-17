"""Category Performance dashboard."""

from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "warehouse" / "kairo_dashboard.duckdb"

st.set_page_config(
    page_title="Category Performance",
    page_icon="🛍️",
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
    st.title("🛍️ Category Performance Dashboard")
    st.markdown("*For Category Managers — weekly performance review*")
    st.caption("All financial reporting uses tax-exclusive Net GMV.")
    st.markdown("---")

    try:
        conn = get_connection()
    except Exception as error:
        st.error(str(error))
        st.stop()

    categories = conn.execute(
        """
        SELECT category
        FROM dashboard_category_summary
        ORDER BY category
        """
    ).df()["category"].tolist()

    selected_category = st.selectbox(
        "Select Category",
        ["All Categories"] + categories,
    )

    category_parameter = (
        None
        if selected_category == "All Categories"
        else selected_category
    )

    kpis = conn.execute(
        """
        SELECT
            ROUND(SUM(net_gmv), 2) AS net_gmv,
            SUM(orders) AS orders,
            SUM(items) AS items,
            ROUND(
                100.0 * SUM(gross_margin_amount)
                / NULLIF(SUM(margin_net_gmv), 0),
                1
            ) AS weighted_margin
        FROM dashboard_category_summary
        WHERE (? IS NULL OR category = ?)
        """,
        [category_parameter, category_parameter],
    ).fetchone()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Net GMV", f"${(kpis[0] or 0):,.0f}")
    col2.metric("Distinct Orders", f"{(kpis[1] or 0):,}")
    col3.metric("Valid Items Sold", f"{(kpis[2] or 0):,}")
    col4.metric("Weighted Margin", f"{(kpis[3] or 0):.1f}%")

    st.markdown("---")
    st.subheader(f"Monthly Trend — {selected_category}")

    monthly = conn.execute(
        """
        SELECT
            month,
            ROUND(SUM(net_gmv), 2) AS net_gmv,
            SUM(orders) AS orders,
            ROUND(
                100.0 * SUM(gross_margin_amount)
                / NULLIF(SUM(margin_net_gmv), 0),
                1
            ) AS weighted_margin
        FROM dashboard_category_monthly
        WHERE (? IS NULL OR category = ?)
        GROUP BY month
        ORDER BY month
        """,
        [category_parameter, category_parameter],
    ).df()

    if not monthly.empty:
        fig = px.line(
            monthly,
            x="month",
            y="net_gmv",
            markers=True,
            labels={"net_gmv": "Net GMV ($)"},
            color_discrete_sequence=["#4F46E5"],
        )
        fig.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Category Comparison")

    comparison = conn.execute(
        """
        SELECT
            category,
            gross_gmv,
            net_gmv,
            orders,
            items,
            weighted_margin,
            item_discounts
        FROM dashboard_category_summary
        ORDER BY net_gmv DESC
        """
    ).df()

    if not comparison.empty:
        st.dataframe(
            comparison.style.format(
                {
                    "gross_gmv": "${:,.0f}",
                    "net_gmv": "${:,.0f}",
                    "orders": "{:,.0f}",
                    "items": "{:,.0f}",
                    "weighted_margin": "{:.1f}%",
                    "item_discounts": "${:,.0f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader(f"Customer Segments — {selected_category}")

    segments = conn.execute(
        """
        WITH selected AS (
            SELECT
                customer_segment,
                SUM(net_gmv) AS net_gmv,
                SUM(orders) AS orders
            FROM dashboard_category_customer_segment
            WHERE (? IS NULL OR category = ?)
            GROUP BY customer_segment
        )
        SELECT
            customer_segment,
            ROUND(net_gmv, 2) AS net_gmv,
            orders,
            ROUND(
                100.0 * net_gmv
                / NULLIF(SUM(net_gmv) OVER (), 0),
                1
            ) AS net_gmv_share_pct
        FROM selected
        ORDER BY net_gmv DESC
        """,
        [category_parameter, category_parameter],
    ).df()

    if not segments.empty:
        col_l, col_r = st.columns(2)

        with col_l:
            fig2 = px.pie(
                segments,
                values="net_gmv",
                names="customer_segment",
                title="Net GMV by Customer Segment",
            )
            fig2.update_layout(
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig2, use_container_width=True)

        with col_r:
            st.dataframe(
                segments.style.format(
                    {
                        "net_gmv": "${:,.0f}",
                        "orders": "{:,.0f}",
                        "net_gmv_share_pct": "{:.1f}%",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


if __name__ == "__main__":
    main()
