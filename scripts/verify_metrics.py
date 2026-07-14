"""
Metric Verification Script

Queries the Gold layer to establish precise, correct numbers
for the business context document. Every number in our
documentation must trace back to a query in this script.

Run: python scripts/verify_metrics.py
"""

from pathlib import Path
import duckdb

DB_PATH = Path("warehouse/kairo.duckdb")


def get_conn():
    return duckdb.connect(str(DB_PATH), read_only=True)


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def verify_gmv(conn) -> None:
    """Establish the CORRECT GMV numbers."""

    print_header("METRIC: GMV (Gross Merchandise Value)")

    # Total cumulative GMV
    total = conn.execute("""
        SELECT ROUND(SUM(gmv), 2) FROM main.mart_gmv_daily
    """).fetchone()[0]
    print(f"\n  Total cumulative GMV (all time): ${total:,.0f}")

    # By year
    yearly = conn.execute("""
        SELECT
            EXTRACT(YEAR FROM order_date) AS year,
            ROUND(SUM(gmv)) AS annual_gmv,
            SUM(order_count) AS annual_orders
        FROM main.mart_gmv_daily
        GROUP BY year
        ORDER BY year
    """).df()
    print(f"\n  Annual GMV:")
    print(yearly.to_string(index=False))

    # Date range
    date_range = conn.execute("""
        SELECT MIN(order_date) AS earliest, MAX(order_date) AS latest
        FROM main.mart_gmv_daily
    """).fetchone()
    print(f"\n  Data spans: {date_range[0]} to {date_range[1]}")


def verify_customer_segments(conn) -> None:
    """Establish CORRECT customer segment numbers."""

    print_header("METRIC: Customer Segments")

    # Total customers in dim (signed up)
    total_dim = conn.execute("""
        SELECT COUNT(*) FROM main.dim_customers
    """).fetchone()[0]
    print(f"\n  Total customers in dim_customers: {total_dim:,}")

    # Total customers with orders (in LTV mart)
    total_ltv = conn.execute("""
        SELECT COUNT(*) FROM main.mart_customer_ltv
    """).fetchone()[0]
    print(f"  Total customers with orders (in mart_customer_ltv): {total_ltv:,}")
    print(f"  Customers who signed up but never ordered: {total_dim - total_ltv:,}")

    # Segment breakdown from LTV mart
    segments = conn.execute("""
        SELECT
            segment,
            COUNT(*) AS customers,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_customers,
            SUM(CASE WHEN total_orders = 1 THEN 1 ELSE 0 END) AS single_order_count,
            SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) AS repeat_count,
            ROUND(AVG(total_orders), 1) AS avg_orders,
            ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
            ROUND(SUM(lifetime_revenue)) AS total_revenue,
            ROUND(100.0 * SUM(lifetime_revenue) / SUM(SUM(lifetime_revenue)) OVER (), 1)
                AS pct_of_revenue
        FROM main.mart_customer_ltv
        GROUP BY segment
        ORDER BY total_revenue DESC
    """).df()
    print(f"\n  Segment Breakdown:")
    print(segments.to_string(index=False))

    # ACTUAL repeat rate
    repeat_stats = conn.execute("""
        SELECT
            COUNT(*) AS total_customers,
            SUM(CASE WHEN total_orders = 1 THEN 1 ELSE 0 END) AS one_order_only,
            SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) AS repeat_buyers,
            ROUND(100.0 * SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) / COUNT(*), 1)
                AS repeat_rate_pct,
            ROUND(100.0 * SUM(CASE WHEN total_orders = 1 THEN 1 ELSE 0 END) / COUNT(*), 1)
                AS one_time_rate_pct
        FROM main.mart_customer_ltv
    """).df()
    print(f"\n  Repeat vs One-Time (across ALL segments):")
    print(repeat_stats.to_string(index=False))

    # One-time segment specifically
    one_time = conn.execute("""
        SELECT
            COUNT(*) AS customers,
            SUM(CASE WHEN total_orders = 1 THEN 1 ELSE 0 END) AS truly_single_order,
            SUM(CASE WHEN total_orders > 1 THEN 1 ELSE 0 END) AS has_multiple_orders,
            ROUND(AVG(total_orders), 1) AS avg_orders
        FROM main.mart_customer_ltv
        WHERE segment = 'one_time'
    """).df()
    print(f"\n  'one_time' segment deep look:")
    print(one_time.to_string(index=False))
    print(f"  NOTE: 'one_time' is a BEHAVIORAL SEGMENT assigned by the generator,")
    print(f"  not a count of orders. Some 'one_time' segment customers may have >1 orders.")


def verify_whale_economics(conn) -> None:
    """Establish CORRECT whale numbers."""

    print_header("METRIC: Whale Customer Economics")

    whale_stats = conn.execute("""
        SELECT
            COUNT(*) AS whale_count,
            ROUND(SUM(lifetime_revenue)) AS total_whale_revenue,
            ROUND(AVG(lifetime_revenue), 2) AS avg_whale_ltv,
            ROUND(MIN(lifetime_revenue), 2) AS min_whale_ltv,
            ROUND(MAX(lifetime_revenue), 2) AS max_whale_ltv,
            ROUND(AVG(total_orders), 1) AS avg_orders,
            MIN(first_order_date) AS earliest_first_order,
            MAX(last_order_date) AS latest_last_order,
            ROUND(AVG(customer_lifespan_days)) AS avg_lifespan_days
        FROM main.mart_customer_ltv
        WHERE segment = 'whale'
    """).fetchone()

    total_revenue = conn.execute("""
        SELECT ROUND(SUM(lifetime_revenue)) FROM main.mart_customer_ltv
    """).fetchone()[0]

    whale_revenue = whale_stats[1]
    whale_pct = round(100 * whale_revenue / total_revenue, 1)

    print(f"\n  Whale count: {whale_stats[0]:,}")
    print(f"  Total whale lifetime revenue: ${whale_revenue:,.0f}")
    print(f"  Total ALL customer revenue: ${total_revenue:,.0f}")
    print(f"  Whale share of revenue: {whale_pct}%")
    print(f"  Non-whale revenue: ${total_revenue - whale_revenue:,.0f} ({100 - whale_pct}%)")
    print(f"\n  Avg whale LTV: ${whale_stats[2]:,.2f}")
    print(f"  Min whale LTV: ${whale_stats[3]:,.2f}")
    print(f"  Max whale LTV: ${whale_stats[4]:,.2f}")
    print(f"  Avg orders per whale: {whale_stats[5]}")
    print(f"  Avg whale lifespan: {whale_stats[8]:,.0f} days ({whale_stats[8]/365:.1f} years)")

    # Annual revenue per whale (LTV / lifespan in years)
    avg_lifespan_years = whale_stats[8] / 365
    annual_per_whale = whale_stats[2] / avg_lifespan_years if avg_lifespan_years > 0 else 0
    print(f"\n  📊 CORRECTED CALCULATION:")
    print(f"     Avg whale LTV: ${whale_stats[2]:,.2f} over {avg_lifespan_years:.1f} years")
    print(f"     Avg whale ANNUAL revenue: ${annual_per_whale:,.2f}")
    print(f"     If 5% of whales churn ({int(whale_stats[0] * 0.05)} customers):")
    print(f"       Annual revenue at risk: ${int(whale_stats[0] * 0.05) * annual_per_whale:,.0f}")
    print(f"       Lifetime revenue at risk: ${int(whale_stats[0] * 0.05) * whale_stats[2]:,.0f}")


def verify_regional(conn) -> None:
    """Verify regional numbers."""

    print_header("METRIC: Regional Performance")

    result = conn.execute("""
        SELECT
            region,
            ROUND(SUM(gmv)) AS total_gmv,
            ROUND(100.0 * SUM(gmv) / SUM(SUM(gmv)) OVER (), 1) AS gmv_share,
            SUM(order_count) AS orders,
            ROUND(SUM(gmv) / SUM(order_count), 2) AS aov,
            ROUND(AVG(gross_margin_pct), 1) AS avg_margin
        FROM main.mart_gmv_daily
        GROUP BY region
        ORDER BY total_gmv DESC
    """).df()
    print(result.to_string(index=False))


def verify_category(conn) -> None:
    """Verify category numbers."""

    print_header("METRIC: Category Economics")

    result = conn.execute("""
        SELECT
            category,
            ROUND(SUM(gmv)) AS total_gmv,
            ROUND(100.0 * SUM(gmv) / SUM(SUM(gmv)) OVER (), 1) AS gmv_share,
            ROUND(SUM(gross_profit)) AS total_profit,
            ROUND(AVG(gross_margin_pct), 1) AS avg_margin,
            SUM(order_count) AS orders
        FROM main.mart_gmv_daily
        GROUP BY category
        ORDER BY total_gmv DESC
    """).df()
    print(result.to_string(index=False))


def verify_seller_tiers(conn) -> None:
    """Verify seller tier numbers."""

    print_header("METRIC: Seller Tier Economics")

    result = conn.execute("""
        SELECT
            tier,
            COUNT(*) AS sellers,
            ROUND(SUM(total_gmv)) AS total_gmv,
            ROUND(AVG(commission_rate) * 100, 1) AS avg_commission_pct,
            ROUND(SUM(commission_revenue)) AS total_commission,
            ROUND(AVG(total_gmv)) AS avg_gmv_per_seller
        FROM main.mart_seller_health
        GROUP BY tier
        ORDER BY total_gmv DESC
    """).df()
    print(result.to_string(index=False))


def verify_activity_status(conn) -> None:
    """Verify activity status distribution."""

    print_header("METRIC: Customer Activity Status")

    result = conn.execute("""
        SELECT
            activity_status,
            COUNT(*) AS customers,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct,
            ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
            ROUND(AVG(days_since_last_order)) AS avg_days_since_last
        FROM main.mart_customer_ltv
        GROUP BY activity_status
        ORDER BY customers DESC
    """).df()
    print(result.to_string(index=False))

    # Reference date issue
    max_order = conn.execute("""
        SELECT MAX(order_date) FROM main.fact_orders
    """).fetchone()[0]
    print(f"\n  Latest order date in data: {max_order}")
    print(f"  Current date used by metric: CURRENT_DATE (2026-07-13)")
    print(f"  Gap: ~{(2026 - 2025) * 365 + 195} days")
    print(f"  ⚠️  This is why all customers show as 'churned'")
    print(f"  FIX: Use MAX(order_date) as reference instead of CURRENT_DATE")


def verify_return_rate(conn) -> None:
    """Verify return rate numbers."""

    print_header("METRIC: Return Rates")

    # Simple return count by category
    simple = conn.execute("""
        SELECT
            category,
            COUNT(*) AS return_count
        FROM main.silver__returns
        GROUP BY category
        ORDER BY return_count DESC
    """).df()
    print(f"\n  Returns by Category:")
    print(simple.to_string(index=False))

    total_returns = conn.execute("SELECT COUNT(*) FROM main.silver__returns").fetchone()[0]
    total_items = conn.execute("SELECT COUNT(*) FROM main.fact_order_items WHERE quantity > 0").fetchone()[0]
    overall_rate = round(100 * total_returns / total_items, 1)
    print(f"\n  Total returns: {total_returns:,}")
    print(f"  Total items sold: {total_items:,}")
    print(f"  Overall return rate: {overall_rate}%")

    # Return reasons
    reasons = conn.execute("""
        SELECT
            return_reason,
            COUNT(*) AS count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM main.silver__returns
        GROUP BY return_reason
        ORDER BY count DESC
    """).df()
    print(f"\n  Return Reasons:")
    print(reasons.to_string(index=False))

    total_returns = conn.execute("SELECT COUNT(*) FROM main.silver__returns").fetchone()[0]
    total_items = conn.execute("SELECT COUNT(*) FROM main.fact_order_items WHERE quantity > 0").fetchone()[0]
    overall_rate = round(100 * total_returns / total_items, 1)
    print(f"\n  Total returns: {total_returns:,}")
    print(f"  Total delivered items: {total_items:,}")
    print(f"  Overall return rate: {overall_rate}%")


def verify_on_time_delivery(conn) -> None:
    """Verify delivery numbers."""

    print_header("METRIC: On-Time Delivery")

    result = conn.execute("""
        SELECT
            COUNT(*) AS total_shipments,
            SUM(CASE WHEN delay_days = 0 THEN 1 ELSE 0 END) AS on_time,
            SUM(CASE WHEN delay_days > 0 THEN 1 ELSE 0 END) AS late,
            ROUND(100.0 * SUM(CASE WHEN delay_days = 0 THEN 1 ELSE 0 END) / COUNT(*), 1)
                AS on_time_pct
        FROM main.silver__shipments
        WHERE status = 'delivered'
    """).fetchone()

    print(f"\n  Total delivered shipments: {result[0]:,}")
    print(f"  On time (delay_days = 0): {result[1]:,}")
    print(f"  Late (delay_days > 0): {result[2]:,}")
    print(f"  On-time rate: {result[3]}%")


def main() -> None:
    conn = get_conn()

    print("\n" + "📐" * 35)
    print("  METRIC VERIFICATION — ESTABLISHING CORRECT NUMBERS")
    print("  Every number in our documentation must trace to this script")
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
    print("\n  Use these EXACT numbers in all documentation.")
    print("  If a document says a different number, the document is wrong.")
    print("  This script is the source of truth.")


if __name__ == "__main__":
    main()