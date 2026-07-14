"""
Metric Verification Script

Queries the Gold layer to establish precise, governed business metrics.
Every number published in project documentation should trace to a query
in this script.

Run:
    python scripts/verify_metrics.py
"""

from datetime import date
from pathlib import Path

import duckdb


DB_PATH = Path("warehouse/kairo.duckdb")
ANALYSIS_AS_OF_DATE = date(2025, 12, 31)


def get_conn() -> duckdb.DuckDBPyConnection:
    """Open the Kairo DuckDB warehouse in read-only mode."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Generate the data and run dbt before running verification."
        )

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    conn.execute("SET preserve_insertion_order = false")
    conn.execute("SET threads = 4")

    return conn


def print_header(title: str) -> None:
    """Print a consistent report header."""

    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def verify_gmv(conn: duckdb.DuckDBPyConnection) -> None:
    """
    Verify governed Gross and Net GMV.

    Net GMV is the primary marketplace metric:
        unit_price × quantity - item discount

    The mart's order_count is not additive across categories, so annual
    order totals are calculated directly from fact_orders.
    """

    print_header("METRIC: Marketplace GMV")

    totals = conn.execute("""
        SELECT
            ROUND(SUM(gross_gmv), 2) AS gross_gmv,
            ROUND(SUM(net_gmv), 2) AS net_gmv,
            ROUND(SUM(total_discounts), 2) AS item_discounts,
            ROUND(SUM(total_item_tax), 2) AS item_tax,
            SUM(invalid_gmv_item_count) AS invalid_gmv_items
        FROM main.mart_gmv_daily
    """).fetchone()

    print(f"\n  Gross GMV: ${totals[0]:,.2f}")
    print(f"  Net GMV:   ${totals[1]:,.2f}  ← primary GMV metric")
    print(f"  Discounts: ${totals[2]:,.2f}")
    print(f"  Item tax:  ${totals[3]:,.2f}")
    print(f"  Financially invalid item rows excluded: {totals[4]:,}")

    yearly = conn.execute("""
        WITH annual_gmv AS (
            SELECT
                CAST(EXTRACT(YEAR FROM order_date) AS INTEGER) AS year,
                ROUND(SUM(gross_gmv), 2) AS gross_gmv,
                ROUND(SUM(net_gmv), 2) AS net_gmv
            FROM main.mart_gmv_daily
            GROUP BY 1
        ),

        annual_orders AS (
            SELECT
                CAST(EXTRACT(YEAR FROM order_date) AS INTEGER) AS year,
                COUNT(DISTINCT order_id) AS eligible_orders
            FROM main.fact_orders
            WHERE order_status NOT IN ('cancelled', 'refunded')
            GROUP BY 1
        )

        SELECT
            g.year,
            g.gross_gmv,
            g.net_gmv,
            o.eligible_orders,
            ROUND(
                g.net_gmv / NULLIF(o.eligible_orders, 0),
                2
            ) AS net_gmv_per_order
        FROM annual_gmv AS g
        JOIN annual_orders AS o
            ON g.year = o.year
        ORDER BY g.year
    """).df()

    print("\n  Annual Marketplace Performance:")
    print(yearly.to_string(index=False))

    date_range = conn.execute("""
        SELECT
            MIN(order_date) AS earliest,
            MAX(order_date) AS latest
        FROM main.fact_orders
        WHERE order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()

    print(f"\n  Eligible order data spans: {date_range[0]} to {date_range[1]}")
    print(
        "  NOTE: mart_gmv_daily.order_count must not be summed across "
        "categories or customer segments."
    )


def verify_customer_segments(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify real-customer personas and observed purchasing behavior."""

    print_header("METRIC: Customer Segments")

    counts = conn.execute("""
        SELECT
            COUNT(*) FILTER (
                WHERE is_unknown_customer = FALSE
            ) AS registered_customers,

            COUNT(*) FILTER (
                WHERE is_unknown_customer = TRUE
            ) AS unknown_dimension_members,

            COUNT(*) FILTER (
                WHERE is_unknown_customer = FALSE
                  AND total_orders > 0
            ) AS customers_with_orders,

            COUNT(*) FILTER (
                WHERE is_unknown_customer = FALSE
                  AND total_orders = 0
            ) AS never_ordered

        FROM main.mart_customer_ltv
    """).fetchone()

    print(f"\n  Registered customers: {counts[0]:,}")
    print(f"  Unknown reconciliation members: {counts[1]:,}")
    print(f"  Real customers with orders: {counts[2]:,}")
    print(f"  Real customers who never ordered: {counts[3]:,}")

    segments = conn.execute("""
        SELECT
            segment,
            COUNT(*) AS customers,

            ROUND(
                100.0 * COUNT(*)
                / SUM(COUNT(*)) OVER (),
                1
            ) AS pct_of_customers,

            SUM(
                CASE WHEN total_orders = 0 THEN 1 ELSE 0 END
            ) AS never_ordered_count,

            SUM(
                CASE WHEN total_orders = 1 THEN 1 ELSE 0 END
            ) AS single_order_count,

            SUM(
                CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END
            ) AS repeat_count,

            ROUND(AVG(total_orders), 1) AS avg_orders,

            ROUND(
                AVG(lifetime_customer_spend),
                2
            ) AS avg_lifetime_spend,

            ROUND(
                SUM(lifetime_customer_spend),
                2
            ) AS total_customer_spend,

            ROUND(
                100.0 * SUM(lifetime_customer_spend)
                / NULLIF(
                    SUM(SUM(lifetime_customer_spend)) OVER (),
                    0
                ),
                1
            ) AS pct_of_real_customer_spend

        FROM main.mart_customer_ltv

        WHERE is_unknown_customer = FALSE

        GROUP BY segment
        ORDER BY total_customer_spend DESC
    """).df()

    print("\n  Synthetic Persona Breakdown — Real Customers Only:")
    print(segments.to_string(index=False))

    repeat_behavior = conn.execute("""
        SELECT
            COUNT(*) AS registered_customers,

            SUM(
                CASE WHEN total_orders = 0 THEN 1 ELSE 0 END
            ) AS never_ordered,

            SUM(
                CASE WHEN total_orders = 1 THEN 1 ELSE 0 END
            ) AS one_order_only,

            SUM(
                CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END
            ) AS repeat_buyers,

            SUM(
                CASE WHEN total_orders > 0 THEN 1 ELSE 0 END
            ) AS total_buyers,

            ROUND(
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
            ) AS repeat_rate_among_buyers_pct,

            ROUND(
                100.0
                * SUM(
                    CASE WHEN total_orders = 1 THEN 1 ELSE 0 END
                )
                / NULLIF(
                    SUM(
                        CASE WHEN total_orders > 0 THEN 1 ELSE 0 END
                    ),
                    0
                ),
                1
            ) AS one_order_rate_among_buyers_pct

        FROM main.mart_customer_ltv

        WHERE is_unknown_customer = FALSE
    """).df()

    print("\n  Observed Purchase Behavior — Real Customers Only:")
    print(repeat_behavior.to_string(index=False))

    low_frequency = conn.execute("""
        SELECT
            COUNT(*) AS customers,

            SUM(
                CASE WHEN total_orders = 0 THEN 1 ELSE 0 END
            ) AS never_ordered,

            SUM(
                CASE WHEN total_orders = 1 THEN 1 ELSE 0 END
            ) AS truly_single_order,

            SUM(
                CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END
            ) AS has_multiple_orders,

            ROUND(AVG(total_orders), 1) AS avg_orders

        FROM main.mart_customer_ltv

        WHERE is_unknown_customer = FALSE
          AND segment = 'low_frequency'
    """).df()

    print("\n  'low_frequency' Synthetic Persona Deep Look:")
    print(low_frequency.to_string(index=False))
    print(
        "  NOTE: low_frequency is a generated customer persona, "
        "not a literal order-count label."
    )


def verify_customer_spend_reconciliation(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Reconcile real-customer spend, orphan spend, and platform spend."""

    print_header("METRIC: Customer Charged Amount Reconciliation")

    mart_totals = conn.execute("""
        SELECT
            ROUND(
                SUM(
                    CASE
                        WHEN is_unknown_customer = FALSE
                        THEN lifetime_customer_spend
                        ELSE 0
                    END
                ),
                2
            ) AS real_customer_spend,

            ROUND(
                SUM(
                    CASE
                        WHEN is_unknown_customer = TRUE
                        THEN lifetime_customer_spend
                        ELSE 0
                    END
                ),
                2
            ) AS orphan_reconciliation_spend,

            ROUND(
                SUM(lifetime_customer_spend),
                2
            ) AS platform_customer_spend,

            SUM(invalid_financial_orders)
                AS invalid_financial_orders

        FROM main.mart_customer_ltv
    """).fetchone()

    fact_totals = conn.execute("""
        SELECT
            COUNT(DISTINCT order_id) AS eligible_orders,

            COUNT(*) FILTER (
                WHERE total_amount IS NULL
            ) AS null_total_amount_orders,

            ROUND(SUM(total_amount), 2)
                AS fact_order_customer_spend

        FROM main.fact_orders

        WHERE order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()

    reconciliation_gap = (
        float(fact_totals[2] or 0)
        - float(mart_totals[2] or 0)
    )

    print(
        f"\n  Real-customer lifetime spend: "
        f"${mart_totals[0]:,.2f}"
    )
    print(
        f"  Orphan-order reconciliation spend: "
        f"${mart_totals[1]:,.2f}"
    )
    print(
        f"  Platform customer charged amount: "
        f"${mart_totals[2]:,.2f}"
    )
    print(
        f"  fact_orders customer charged amount: "
        f"${fact_totals[2]:,.2f}"
    )
    print(f"  Reconciliation gap: ${reconciliation_gap:,.2f}")
    print(f"  Eligible orders: {fact_totals[0]:,}")
    print(
        f"  Orders with null total_amount: "
        f"{fact_totals[1]:,}"
    )
    print(
        f"  Invalid financial orders tracked in LTV mart: "
        f"{mart_totals[3]:,}"
    )


def verify_whale_economics(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify whale-customer economics using real customers only."""

    print_header("METRIC: Whale Customer Economics")

    whale_stats = conn.execute("""
        SELECT
            COUNT(*) AS whale_count,
            ROUND(SUM(lifetime_customer_spend), 2)
                AS total_whale_spend,
            ROUND(AVG(lifetime_customer_spend), 2)
                AS avg_whale_spend,
            ROUND(MIN(lifetime_customer_spend), 2)
                AS min_whale_spend,
            ROUND(MAX(lifetime_customer_spend), 2)
                AS max_whale_spend,
            ROUND(AVG(total_orders), 1) AS avg_orders,
            ROUND(AVG(customer_lifespan_days))
                AS avg_lifespan_days

        FROM main.mart_customer_ltv

        WHERE is_unknown_customer = FALSE
          AND segment = 'whale'
    """).fetchone()

    total_real_customer_spend = conn.execute("""
        SELECT
            ROUND(SUM(lifetime_customer_spend), 2)
        FROM main.mart_customer_ltv
        WHERE is_unknown_customer = FALSE
    """).fetchone()[0]

    whale_spend = whale_stats[1] or 0

    whale_pct = (
        round(
            100 * float(whale_spend)
            / float(total_real_customer_spend),
            1,
        )
        if total_real_customer_spend
        else 0
    )

    print(f"\n  Whale count: {whale_stats[0]:,}")
    print(f"  Total whale spend: ${whale_spend:,.2f}")
    print(
        f"  Total real-customer spend: "
        f"${total_real_customer_spend:,.2f}"
    )
    print(f"  Whale share of real-customer spend: {whale_pct}%")

    non_whale_spend = (
        float(total_real_customer_spend)
        - float(whale_spend)
    )

    print(
        f"  Non-whale real-customer spend: "
        f"${non_whale_spend:,.2f} "
        f"({100 - whale_pct:.1f}%)"
    )

    print(
        f"\n  Average whale lifetime spend: "
        f"${whale_stats[2]:,.2f}"
    )
    print(
        f"  Minimum whale lifetime spend: "
        f"${whale_stats[3]:,.2f}"
    )
    print(
        f"  Maximum whale lifetime spend: "
        f"${whale_stats[4]:,.2f}"
    )
    print(f"  Average orders per whale: {whale_stats[5]}")

    avg_lifespan_days = whale_stats[6] or 0
    avg_lifespan_years = float(avg_lifespan_days) / 365

    print(
        f"  Average whale lifespan: "
        f"{avg_lifespan_days:,.0f} days "
        f"({avg_lifespan_years:.1f} years)"
    )

    annual_spend_per_whale = (
        float(whale_stats[2]) / avg_lifespan_years
        if avg_lifespan_years > 0
        else 0
    )

    five_pct_whale_count = int(whale_stats[0] * 0.05)

    print("\n  FIVE-PERCENT WHALE SCENARIO:")
    print(
        f"     Five percent of whales: "
        f"{five_pct_whale_count:,} customers"
    )
    print(
        f"     Historical annualized spend represented: "
        f"${five_pct_whale_count * annual_spend_per_whale:,.0f}"
    )
    print(
        f"     Historical lifetime spend represented: "
        f"${five_pct_whale_count * float(whale_stats[2]):,.0f}"
    )
    print(
        "     NOTE: These are historical spend measures, "
        "not forecasts of future Kairo revenue."
    )


def verify_regional(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify regional Net GMV and distinct order performance."""

    print_header("METRIC: Regional Performance")

    result = conn.execute("""
        WITH regional_items AS (
            SELECT
                region,

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

                ROUND(
                    SUM(
                        CASE
                            WHEN is_margin_valid
                            THEN net_gmv - merchandise_cost
                            ELSE 0
                        END
                    ),
                    2
                ) AS merchandise_profit,

                ROUND(
                    SUM(
                        CASE
                            WHEN is_margin_valid THEN net_gmv
                            ELSE 0
                        END
                    ),
                    2
                ) AS margin_eligible_net_gmv

            FROM main.fact_order_items

            WHERE order_status NOT IN ('cancelled', 'refunded')

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
            i.region,
            ROUND(i.net_gmv, 2) AS net_gmv,

            ROUND(
                100.0 * i.net_gmv
                / SUM(i.net_gmv) OVER (),
                1
            ) AS net_gmv_share,

            o.eligible_orders,

            ROUND(
                i.net_gmv / NULLIF(o.eligible_orders, 0),
                2
            ) AS net_gmv_per_order,

            ROUND(
                100.0 * i.merchandise_profit
                / NULLIF(i.margin_eligible_net_gmv, 0),
                1
            ) AS merchandise_margin_pct

        FROM regional_items AS i

        JOIN regional_orders AS o
            ON i.region = o.region

        ORDER BY i.net_gmv DESC
    """).df()

    print(result.to_string(index=False))


def verify_category(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify category-level marketplace economics."""

    print_header("METRIC: Category Economics")

    result = conn.execute("""
        WITH category_metrics AS (
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

                ROUND(
                    SUM(
                        CASE
                            WHEN is_margin_valid
                            THEN net_gmv - merchandise_cost
                            ELSE 0
                        END
                    ),
                    2
                ) AS merchandise_profit,

                ROUND(
                    SUM(
                        CASE
                            WHEN is_margin_valid THEN net_gmv
                            ELSE 0
                        END
                    ),
                    2
                ) AS margin_eligible_net_gmv,

                COUNT(
                    DISTINCT CASE
                        WHEN is_gmv_valid THEN order_id
                    END
                ) AS orders,

                SUM(
                    CASE
                        WHEN NOT is_gmv_valid THEN 1
                        ELSE 0
                    END
                ) AS invalid_financial_items

            FROM main.fact_order_items

            WHERE order_status NOT IN ('cancelled', 'refunded')

            GROUP BY category
        )

        SELECT
            category,
            gross_gmv,
            net_gmv,

            ROUND(
                100.0 * net_gmv
                / SUM(net_gmv) OVER (),
                1
            ) AS net_gmv_share,

            merchandise_profit,

            ROUND(
                100.0 * merchandise_profit
                / NULLIF(margin_eligible_net_gmv, 0),
                1
            ) AS merchandise_margin_pct,

            orders,
            invalid_financial_items

        FROM category_metrics

        ORDER BY net_gmv DESC
    """).df()

    print(result.to_string(index=False))


def verify_seller_tiers(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify seller-tier Net GMV and commission economics."""

    print_header("METRIC: Seller Tier Economics")

    result = conn.execute("""
        SELECT
            tier,
            COUNT(*) AS sellers,
            ROUND(SUM(gross_gmv), 2) AS gross_gmv,
            ROUND(SUM(net_gmv), 2) AS net_gmv,

            ROUND(
                AVG(commission_rate) * 100,
                1
            ) AS avg_commission_pct,

            ROUND(
                SUM(commission_revenue),
                2
            ) AS commission_revenue,

            ROUND(
                100.0 * SUM(commission_revenue)
                / NULLIF(SUM(net_gmv), 0),
                2
            ) AS effective_take_rate_pct,

            ROUND(AVG(net_gmv), 2)
                AS avg_net_gmv_per_seller

        FROM main.mart_seller_health

        GROUP BY tier
        ORDER BY net_gmv DESC
    """).df()

    print(result.to_string(index=False))

    total = conn.execute("""
        SELECT
            ROUND(SUM(net_gmv), 2),
            ROUND(SUM(commission_revenue), 2),
            ROUND(
                100.0 * SUM(commission_revenue)
                / NULLIF(SUM(net_gmv), 0),
                2
            )
        FROM main.mart_seller_health
    """).fetchone()

    print(f"\n  Total seller Net GMV: ${total[0]:,.2f}")
    print(f"  Commission revenue:   ${total[1]:,.2f}")
    print(f"  Effective take rate:  {total[2]}%")


def verify_activity_status(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify real-customer activity-status distribution."""

    print_header("METRIC: Customer Activity Status")

    result = conn.execute("""
        SELECT
            activity_status,
            COUNT(*) AS customers,

            ROUND(
                100.0 * COUNT(*)
                / SUM(COUNT(*)) OVER (),
                1
            ) AS pct,

            ROUND(
                AVG(lifetime_customer_spend),
                2
            ) AS avg_lifetime_spend,

            ROUND(
                AVG(days_since_last_order)
            ) AS avg_days_since_last_order

        FROM main.mart_customer_ltv

        WHERE is_unknown_customer = FALSE

        GROUP BY activity_status
        ORDER BY customers DESC
    """).df()

    print(result.to_string(index=False))

    max_order_date = conn.execute("""
        SELECT MAX(order_date)
        FROM main.fact_orders
    """).fetchone()[0]

    gap_days = (
        ANALYSIS_AS_OF_DATE - max_order_date
    ).days

    print(f"\n  Latest order date in data: {max_order_date}")
    print(
        f"  Analysis reference date: "
        f"{ANALYSIS_AS_OF_DATE}"
    )
    print(
        f"  Difference between reference date and latest order: "
        f"{gap_days} days"
    )


def verify_return_rate(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """
    Verify return incidence among eligible sold items.

    Eligible items exclude cancelled and refunded orders. This definition
    avoids using post-chaos delivered statuses that no longer represent the
    original population from which returns were generated.
    """

    print_header("METRIC: Return Rates")

    category_rates = conn.execute("""
        WITH eligible_items AS (
            SELECT
                category,
                COUNT(DISTINCT order_item_id) AS eligible_items
            FROM main.fact_order_items
            WHERE order_status NOT IN ('cancelled', 'refunded')
              AND NOT COALESCE(_had_negative_quantity, FALSE)
            GROUP BY category
        ),

        returned_items AS (
            SELECT
                category,
                COUNT(DISTINCT return_id) AS returned_items
            FROM main.silver__returns
            GROUP BY category
        )

        SELECT
            e.category,
            e.eligible_items,
            COALESCE(r.returned_items, 0) AS returned_items,

            ROUND(
                100.0 * COALESCE(r.returned_items, 0)
                / NULLIF(e.eligible_items, 0),
                2
            ) AS return_rate_pct

        FROM eligible_items AS e

        LEFT JOIN returned_items AS r
            ON e.category = r.category

        ORDER BY return_rate_pct DESC
    """).df()

    print("\n  Return Incidence by Category:")
    print(category_rates.to_string(index=False))

    totals = conn.execute("""
        SELECT
            (
                SELECT COUNT(DISTINCT return_id)
                FROM main.silver__returns
            ) AS total_returns,

            (
                SELECT COUNT(DISTINCT order_item_id)
                FROM main.fact_order_items
                WHERE order_status NOT IN ('cancelled', 'refunded')
                  AND NOT COALESCE(_had_negative_quantity, FALSE)
            ) AS eligible_items
    """).fetchone()

    overall_rate = (
        round(100 * totals[0] / totals[1], 1)
        if totals[1]
        else 0
    )

    print(f"\n  Total returns: {totals[0]:,}")
    print(f"  Eligible items sold: {totals[1]:,}")
    print(f"  Overall return incidence: {overall_rate}%")

    reasons = conn.execute("""
        SELECT
            return_reason,
            COUNT(DISTINCT return_id) AS return_count,

            ROUND(
                100.0 * COUNT(DISTINCT return_id)
                / SUM(COUNT(DISTINCT return_id)) OVER (),
                1
            ) AS pct_of_returns

        FROM main.silver__returns

        GROUP BY return_reason
        ORDER BY return_count DESC
    """).df()

    print("\n  Return Reasons:")
    print(reasons.to_string(index=False))


def verify_on_time_delivery(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify delivered-shipment performance."""

    print_header("METRIC: On-Time Delivery")

    result = conn.execute("""
        SELECT
            COUNT(*) AS total_shipments,

            SUM(
                CASE WHEN delay_days = 0 THEN 1 ELSE 0 END
            ) AS on_time,

            SUM(
                CASE WHEN delay_days > 0 THEN 1 ELSE 0 END
            ) AS late,

            ROUND(
                100.0
                * SUM(
                    CASE WHEN delay_days = 0 THEN 1 ELSE 0 END
                )
                / NULLIF(COUNT(*), 0),
                1
            ) AS on_time_pct

        FROM main.silver__shipments

        WHERE status = 'delivered'
    """).fetchone()

    print(f"\n  Total delivered shipments: {result[0]:,}")
    print(f"  On-time shipments: {result[1]:,}")
    print(f"  Late shipments: {result[2]:,}")
    print(f"  On-time delivery rate: {result[3]}%")


def main() -> None:
    """Run all governed metric-verification checks."""

    conn = get_conn()

    try:
        print("\n" + "📐" * 35)
        print(
            "  METRIC VERIFICATION — GOVERNED BUSINESS NUMBERS"
        )
        print(
            "  Every published number must trace to this script"
        )
        print("📐" * 35)

        verify_gmv(conn)
        verify_customer_segments(conn)
        verify_customer_spend_reconciliation(conn)
        verify_whale_economics(conn)
        verify_regional(conn)
        verify_category(conn)
        verify_seller_tiers(conn)
        verify_activity_status(conn)
        verify_return_rate(conn)
        verify_on_time_delivery(conn)

        print("\n" + "=" * 78)
        print("  VERIFICATION COMPLETE")
        print("=" * 78)
        print(
            "\n  Use these governed numbers in project documentation."
        )
        print(
            "  Real-customer analytics exclude the unknown dimension member."
        )
        print(
            "  Platform-wide spend includes the unknown member for reconciliation."
        )
        print(
            "  Net GMV excludes tax and is the primary marketplace GMV metric."
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
