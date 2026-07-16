"""
Category Manager Dashboard.

Persona: VP of Category
Cadence: Weekly
"""

from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Category Performance",
    page_icon="🏷️",
    layout="wide",
)

DB_PATH = Path("warehouse/kairo.duckdb")


@st.cache_resource
def get_connection():
    return duckdb.connect(str(DB_PATH), read_only=True)


def main():
    st.title("🏷️ Category Performance Dashboard")
    st.markdown("*For Category Managers — weekly performance review*")
    st.caption("All financial reporting uses tax-exclusive Net GMV.")
    st.markdown("---")

    conn = get_connection()

    categories = conn.execute("""
        SELECT DISTINCT category
        FROM main.fact_order_items
        WHERE category IS NOT NULL
        ORDER BY category
    """).df()["category"].to_list()

    selected_category = st.selectbox(
        "Select Category",
        ["All Categories"] + categories,
    )

    category_filter = ""

    if selected_category != "All Categories":
        safe_category = selected_category.replace("'", "''")
        category_filter = f"AND category = '{safe_category}'"

    kpis = conn.execute(f"""
        SELECT
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
        {category_filter}
    """).fetchone()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Net GMV", f"${(kpis[0] or 0):,.0f}")
    col2.metric("Distinct Orders", f"{(kpis[1] or 0):,}")
    col3.metric("Valid Items Sold", f"{(kpis[2] or 0):,}")
    col4.metric("Weighted Margin", f"{(kpis[3] or 0)}%")

    st.markdown("---")
    st.subheader(f"Monthly Trend — {selected_category}")

    monthly = conn.execute(f"""
        SELECT
            DATE_TRUNC('month', order_date) AS month,

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
        {category_filter}

        GROUP BY 1
        ORDER BY 1
    """).df()

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

    comparison = conn.execute("""
        SELECT
            category,

            ROUND(
                SUM(
                    CASE
                        WHEN is_gmv_valid THEN gross_gmv
                        ELSE 0
                    END
                ),
                2
            ) AS gross_gmv,

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
            ) AS weighted_margin,

            ROUND(
                SUM(
                    CASE
                        WHEN is_gmv_valid THEN discount_amount
                        ELSE 0
                    END
                ),
                2
            ) AS item_discounts

        FROM main.fact_order_items

        WHERE order_status NOT IN ('cancelled', 'refunded')

        GROUP BY category
        ORDER BY net_gmv DESC
    """).df()

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

    segments = conn.execute(f"""
        SELECT
            COALESCE(
                customer_segment,
                'unknown'
            ) AS customer_segment,

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

            ROUND(
                100.0
                * SUM(
                    CASE
                        WHEN is_gmv_valid THEN net_gmv
                        ELSE 0
                    END
                )
                / NULLIF(
                    SUM(
                        SUM(
                            CASE
                                WHEN is_gmv_valid THEN net_gmv
                                ELSE 0
                            END
                        )
                    ) OVER (),
                    0
                ),
                1
            ) AS net_gmv_share_pct

        FROM main.fact_order_items

        WHERE order_status NOT IN ('cancelled', 'refunded')
        {category_filter}

        GROUP BY 1
        ORDER BY net_gmv DESC
    """).df()

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
