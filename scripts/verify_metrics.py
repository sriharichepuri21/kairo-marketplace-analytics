"""
Metric Verification Script

Queries the Gold layer to establish precise, correct numbers
for the business context document. Every number in the
documentation must trace back to a query in this script.

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

    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def verify_gmv(conn: duckdb.DuckDBPyConnection) -> None:
    """Establish current GMV numbers from the Gold mart."""

    print_header("METRIC: GMV")

    total = conn.execute("""
        SELECT
            ROUND(SUM(gmv), 2)
        FROM main.mart_gmv_daily
    """).fetchone()[0]

    print(f"\n  Total cumulative GMV: ${total:,.0f}")

    yearly = conn.execute("""
        SELECT
            EXTRACT(YEAR FROM order_date) AS year,
            ROUND(SUM(gmv)) AS annual_gmv,
            SUM(order_count) AS annual_orders
        FROM main.mart_gmv_daily
        GROUP BY year
        ORDER BY year
    """).df()

    print("\n  Annual GMV:")
    print(yearly.to_string(index=False))

    date_range = conn.execute("""
        SELECT
            MIN(order_date) AS earliest,
            MAX(order_date) AS latest
        FROM main.mart_gmv_daily
    """).fetchone()

    print(f"\n  Data spans: {date_range[0]} to {date_range[1]}")


def verify_customer_segments(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Establish customer persona and observed purchase behavior numbers."""

    print_header("METRIC: Customer Segments")

    total_dim = conn.execute("""
        SELECT COUNT(*)
        FROM main.dim_customers
    """).fetchone()[0]

    print(
        f"\n  Total customers in dim_customers: "
        f"{total_dim:,}"
    )

    total_ltv = conn.execute("""
        SELECT COUNT(*)
        FROM main.mart_customer_ltv
    """).fetchone()[0]

    print(
        "  Total customers with orders in mart_customer_ltv: "
        f"{total_ltv:,}"
    )
    print(
        "  Customers who signed up but never ordered: "
        f"{total_dim - total_ltv:,}"
    )

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
                CASE
                    WHEN total_orders = 1 THEN 1
                    ELSE 0
                END
            ) AS single_order_count,

            SUM(
                CASE
                    WHEN total_orders >= 2 THEN 1
                    ELSE 0
                END
            ) AS repeat_count,

            ROUND(
                AVG(total_orders),
                1
            ) AS avg_orders,

            ROUND(
                AVG(lifetime_revenue),
                2
            ) AS avg_lifetime_spend,

            ROUND(
                SUM(lifetime_revenue)
            ) AS total_customer_spend,

            ROUND(
                100.0 * SUM(lifetime_revenue)
                / SUM(SUM(lifetime_revenue)) OVER (),
                1
            ) AS pct_of_customer_spend

        FROM main.mart_customer_ltv

        GROUP BY segment

        ORDER BY total_customer_spend DESC
    """).df()

    print("\n  Synthetic Persona Breakdown:")
    print(segments.to_string(index=False))

    # Observed purchase behavior across all synthetic personas.
    repeat_behavior = conn.execute("""
        SELECT
            COUNT(*) AS total_customers,

            SUM(
                CASE
                    WHEN total_orders = 1 THEN 1
                    ELSE 0
                END
            ) AS one_order_only,

            SUM(
                CASE
                    WHEN total_orders >= 2 THEN 1
                    ELSE 0
                END
            ) AS repeat_buyers,

            ROUND(
                100.0
                * SUM(
                    CASE
                        WHEN total_orders >= 2 THEN 1
                        ELSE 0
                    END
                )
                / COUNT(*),
                1
            ) AS repeat_rate_pct,

            ROUND(
                100.0
                * SUM(
                    CASE
                        WHEN total_orders = 1 THEN 1
                        ELSE 0
                    END
                )
                / COUNT(*),
                1
            ) AS one_order_rate_pct

        FROM main.mart_customer_ltv
    """).df()

    print(
        "\n  Repeat vs One-Order Customers "
        "(across ALL synthetic personas):"
    )
    print(repeat_behavior.to_string(index=False))

    # Inspect the low-frequency synthetic persona separately.
    low_frequency_segment = conn.execute("""
        SELECT
            COUNT(*) AS customers,

            SUM(
                CASE
                    WHEN total_orders = 1 THEN 1
                    ELSE 0
                END
            ) AS truly_single_order,

            SUM(
                CASE
                    WHEN total_orders >= 2 THEN 1
                    ELSE 0
                END
            ) AS has_multiple_orders,

            ROUND(
                AVG(total_orders),
                1
            ) AS avg_orders

        FROM main.mart_customer_ltv

        WHERE segment = 'low_frequency'
    """).df()

    print("\n  'low_frequency' synthetic persona deep look:")
    print(low_frequency_segment.to_string(index=False))
    print(
        "  NOTE: 'low_frequency' is a synthetic customer persona "
        "assigned by the generator."
    )
    print(
        "  It is not a literal order count. Actual purchase behavior "
        "must be derived from total_orders."
    )


def verify_whale_economics(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Establish whale-customer economics."""

    print_header("METRIC: Whale Customer Economics")

    whale_stats = conn.execute("""
        SELECT
            COUNT(*) AS whale_count,
            ROUND(SUM(lifetime_revenue)) AS total_whale_spend,
            ROUND(AVG(lifetime_revenue), 2) AS avg_whale_spend,
            ROUND(MIN(lifetime_revenue), 2) AS min_whale_spend,
            ROUND(MAX(lifetime_revenue), 2) AS max_whale_spend,
            ROUND(AVG(total_orders), 1) AS avg_orders,
            MIN(first_order_date) AS earliest_first_order,
            MAX(last_order_date) AS latest_last_order,
            ROUND(AVG(customer_lifespan_days))
                AS avg_lifespan_days
        FROM main.mart_customer_ltv
        WHERE segment = 'whale'
    """).fetchone()

    total_customer_spend = conn.execute("""
        SELECT
            ROUND(SUM(lifetime_revenue))
        FROM main.mart_customer_ltv
    """).fetchone()[0]

    whale_spend = whale_stats[1]

    whale_pct = (
        round(
            100 * whale_spend / total_customer_spend,
            1,
        )
        if total_customer_spend
        else 0
    )

    print(f"\n  Whale count: {whale_stats[0]:,}")
    print(
        f"  Total whale lifetime spend: "
        f"${whale_spend:,.0f}"
    )
    print(
        f"  Total customer lifetime spend: "
        f"${total_customer_spend:,.0f}"
    )
    print(f"  Whale share of customer spend: {whale_pct}%")
    print(
        f"  Non-whale customer spend: "
        f"${total_customer_spend - whale_spend:,.0f} "
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

    avg_lifespan_days = whale_stats[8] or 0
    avg_lifespan_years = avg_lifespan_days / 365

    print(
        f"  Average whale lifespan: "
        f"{avg_lifespan_days:,.0f} days "
        f"({avg_lifespan_years:.1f} years)"
    )

    annual_spend_per_whale = (
        whale_stats[2] / avg_lifespan_years
        if avg_lifespan_years > 0
        else 0
    )

    churned_whale_count = int(whale_stats[0] * 0.05)

    print("\n  FIVE-PERCENT WHALE SCENARIO:")
    print(
        f"     Average whale lifetime spend: "
        f"${whale_stats[2]:,.2f}"
    )
    print(
        f"     Approximate annual spend per whale: "
        f"${annual_spend_per_whale:,.2f}"
    )
    print(
        f"     Five percent of whales: "
        f"{churned_whale_count:,} customers"
    )
    print(
        f"     Historical annualized spend represented: "
        f"${churned_whale_count * annual_spend_per_whale:,.0f}"
    )
    print(
        f"     Historical lifetime spend represented: "
        f"${churned_whale_count * whale_stats[2]:,.0f}"
    )
    print(
        "     NOTE: These are historical customer-spend measures, "
        "not forecasts of future Kairo revenue."
    )


def verify_regional(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify regional performance numbers."""

    print_header("METRIC: Regional Performance")

    result = conn.execute("""
        SELECT
            region,
            ROUND(SUM(gmv)) AS total_gmv,

            ROUND(
                100.0 * SUM(gmv)
                / SUM(SUM(gmv)) OVER (),
                1
            ) AS gmv_share,

            SUM(order_count) AS orders,

            ROUND(
                SUM(gmv)
                / NULLIF(SUM(order_count), 0),
                2
            ) AS average_order_value,

            ROUND(
                AVG(gross_margin_pct),
                1
            ) AS avg_merchandise_margin

        FROM main.mart_gmv_daily

        GROUP BY region

        ORDER BY total_gmv DESC
    """).df()

    print(result.to_string(index=False))


def verify_category(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify category economics."""

    print_header("METRIC: Category Economics")

    result = conn.execute("""
        SELECT
            category,
            ROUND(SUM(gmv)) AS total_gmv,

            ROUND(
                100.0 * SUM(gmv)
                / SUM(SUM(gmv)) OVER (),
                1
            ) AS gmv_share,

            ROUND(
                SUM(gross_profit)
            ) AS merchandise_profit,

            ROUND(
                AVG(gross_margin_pct),
                1
            ) AS merchandise_margin,

            SUM(order_count) AS orders

        FROM main.mart_gmv_daily

        GROUP BY category

        ORDER BY total_gmv DESC
    """).df()

    print(result.to_string(index=False))


def verify_seller_tiers(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify seller-tier economics."""

    print_header("METRIC: Seller Tier Economics")

    result = conn.execute("""
        SELECT
            tier,
            COUNT(*) AS sellers,
            ROUND(SUM(total_gmv)) AS total_gmv,

            ROUND(
                AVG(commission_rate) * 100,
                1
            ) AS avg_commission_pct,

            ROUND(
                SUM(commission_revenue)
            ) AS total_commission,

            ROUND(
                AVG(total_gmv)
            ) AS avg_gmv_per_seller

        FROM main.mart_seller_health

        GROUP BY tier

        ORDER BY total_gmv DESC
    """).df()

    print(result.to_string(index=False))


def verify_activity_status(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify customer activity-status distribution."""

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
                AVG(lifetime_revenue),
                2
            ) AS avg_lifetime_spend,

            ROUND(
                AVG(days_since_last_order)
            ) AS avg_days_since_last_order

        FROM main.mart_customer_ltv

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
        "  Required analysis reference date: "
        f"{ANALYSIS_AS_OF_DATE}"
    )
    print(
        f"  Difference between reference date and latest order: "
        f"{gap_days} days"
    )
    print(
        "  Activity-status models must use the centralized "
        "analysis_as_of_date, not CURRENT_DATE."
    )


def verify_return_rate(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Verify overall and category return-rate numbers."""

    print_header("METRIC: Return Rates")

    category_rates = conn.execute("""
        WITH sold_items AS (
            SELECT
                category,
                COUNT(*) AS items_sold
            FROM main.fact_order_items
            WHERE quantity > 0
              AND order_status NOT IN ('cancelled', 'refunded')
            GROUP BY category
        ),

        returned_items AS (
            SELECT
                category,
                COUNT(*) AS items_returned
            FROM main.silver__returns
            GROUP BY category
        )

        SELECT
            s.category,
            s.items_sold,
            COALESCE(r.items_returned, 0)
                AS items_returned,

            ROUND(
                100.0
                * COALESCE(r.items_returned, 0)
                / NULLIF(s.items_sold, 0),
                2
            ) AS return_rate_pct

        FROM sold_items AS s

        LEFT JOIN returned_items AS r
            ON s.category = r.category

        ORDER BY return_rate_pct DESC
    """).df()

    print("\n  Return Rates by Category:")
    print(category_rates.to_string(index=False))

    total_returns = conn.execute("""
        SELECT COUNT(*)
        FROM main.silver__returns
    """).fetchone()[0]

    total_items = conn.execute("""
        SELECT COUNT(*)
        FROM main.fact_order_items
        WHERE quantity > 0
          AND order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()[0]

    overall_rate = (
        round(
            100 * total_returns / total_items,
            1,
        )
        if total_items
        else 0
    )

    print(f"\n  Total returns: {total_returns:,}")
    print(f"  Total eligible items sold: {total_items:,}")
    print(f"  Overall return rate: {overall_rate}%")

    reasons = conn.execute("""
        SELECT
            return_reason,
            COUNT(*) AS return_count,

            ROUND(
                100.0 * COUNT(*)
                / SUM(COUNT(*)) OVER (),
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
    """Verify on-time delivery numbers."""

    print_header("METRIC: On-Time Delivery")

    result = conn.execute("""
        SELECT
            COUNT(*) AS total_shipments,

            SUM(
                CASE
                    WHEN delay_days = 0 THEN 1
                    ELSE 0
                END
            ) AS on_time,

            SUM(
                CASE
                    WHEN delay_days > 0 THEN 1
                    ELSE 0
                END
            ) AS late,

            ROUND(
                100.0
                * SUM(
                    CASE
                        WHEN delay_days = 0 THEN 1
                        ELSE 0
                    END
                )
                / COUNT(*),
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
    """Run all metric-verification checks."""

    conn = get_conn()

    try:
        print("\n" + "📐" * 35)
        print(
            "  METRIC VERIFICATION — ESTABLISHING CORRECT NUMBERS"
        )
        print(
            "  Every number in the documentation must trace "
            "to this script"
        )
        print("📐" * 35)

        verify_gmv(conn)
        verify_customer_segments(conn)
        verify_whale_economics(conn)
        verify_regional(conn)
        verify_category(conn)
        verify_seller_tiers(conn)
        verify_activity_status(conn)
        verify_return_rate(conn)
        verify_on_time_delivery(conn)

        print("\n" + "=" * 70)
        print("  VERIFICATION COMPLETE")
        print("=" * 70)
        print(
            "\n  Use these verified numbers in the documentation."
        )
        print(
            "  If another document contains a different number, "
            "investigate and reconcile the difference."
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()