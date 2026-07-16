"""
Executive Weekly Business Review Dashboard.
"""

from pathlib import Path

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="Executive WBR",
    page_icon="📈",
    layout="wide",
)

DB_PATH = Path("warehouse/kairo.duckdb")


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def main():
    st.title("📈 Executive Weekly Business Review")
    st.caption(
        "Governed marketplace performance using tax-exclusive Net GMV."
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
                SELECT COUNT(DISTINCT order_id)
                FROM main.fact_orders
                WHERE order_status NOT IN ('cancelled', 'refunded')
            ) AS eligible_orders,

            (
                SELECT ROUND(
                    SUM(net_gmv)
                    / NULLIF(
                        (
                            SELECT COUNT(DISTINCT order_id)
                            FROM main.fact_orders
                            WHERE order_status
                                NOT IN ('cancelled', 'refunded')
                        ),
                        0
                    ),
                    2
                )
                FROM main.mart_gmv_daily
            ) AS net_gmv_per_order,

            (
                SELECT ROUND(
                    100.0
                    * SUM(
                        CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END
                    )
                    / NULLIF(
                        SUM(
                            CASE WHEN total_orders > 0 THEN 1 ELSE 0 END
                        ),
                        0
                    ),
                    1
                )
                FROM main.mart_customer_ltv
                WHERE is_unknown_customer = FALSE
            ) AS repeat_rate,

            (
                SELECT ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN is_margin_valid
                            THEN net_gmv - merchandise_cost
                            ELSE 0
                        END
                    )
                    / NULLIF(
                        SUM(
                            CASE
                                WHEN is_margin_valid THEN net_gmv
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    1
                )
                FROM main.fact_order_items
                WHERE order_status NOT IN ('cancelled', 'refunded')
            ) AS weighted_margin
    """).fetchone()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Net GMV", f"${kpis[0]:,.0f}")
    col2.metric("Eligible Orders", f"{kpis[1]:,}")
    col3.metric("Net GMV / Order", f"${kpis[2]:,.2f}")
    col4.metric("Repeat Buyer Rate", f"{kpis[3]}%")
    col5.metric("Weighted Margin", f"{kpis[4]}%")

    st.markdown("---")
    st.subheader("Monthly Net GMV and Order Trend")

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
                COUNT(DISTINCT order_id) AS orders
            FROM main.fact_orders
            WHERE order_status NOT IN ('cancelled', 'refunded')
            GROUP BY 1
        )

        SELECT
            g.month,
            g.net_gmv,
            o.orders
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

        fig.add_trace(
            go.Scatter(
                x=monthly["month"].to_list(),
                y=monthly["orders"].to_list(),
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

    region = conn.execute("""
        WITH financials AS (
            SELECT
                region,

                ROUND(
                    SUM(
                        CASE
                            WHEN is_gmv_valid THEN net_gmv
                            ELSE 0
                        END
                    ),
                    2
                ) AS net_gmv,

                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN is_margin_valid
                            THEN net_gmv - merchandise_cost
                            ELSE 0
                        END
                    )
                    / NULLIF(
                        SUM(
                            CASE
                                WHEN is_margin_valid THEN net_gmv
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    1
                ) AS weighted_margin

            FROM main.fact_order_items
            WHERE order_status NOT IN ('cancelled', 'refunded')
            GROUP BY region
        ),

        orders AS (
            SELECT
                region,
                COUNT(DISTINCT order_id) AS orders,
                COUNT(DISTINCT customer_id) AS customers
            FROM main.fact_orders
            WHERE order_status NOT IN ('cancelled', 'refunded')
            GROUP BY region
        )

        SELECT
            f.region,
            f.net_gmv,
            o.orders,
            o.customers,
            f.weighted_margin
        FROM financials AS f
        JOIN orders AS o
            ON f.region = o.region
        ORDER BY f.net_gmv DESC
    """).df()

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

    category = conn.execute("""
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
            ) AS orders,

            SUM(
                CASE
                    WHEN is_gmv_valid THEN quantity
                    ELSE 0
                END
            ) AS items,

            ROUND(
                100.0
                * SUM(
                    CASE
                        WHEN is_margin_valid
                        THEN net_gmv - merchandise_cost
                        ELSE 0
                    END
                )
                / NULLIF(
                    SUM(
                        CASE
                            WHEN is_margin_valid THEN net_gmv
                            ELSE 0
                        END
                    ),
                    0
                ),
                1
            ) AS weighted_margin

        FROM main.fact_order_items

        WHERE order_status NOT IN ('cancelled', 'refunded')

        GROUP BY category
        ORDER BY net_gmv DESC
    """).df()

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
                    "avg_orders": "{:.1f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


if __name__ == "__main__":
    main()
