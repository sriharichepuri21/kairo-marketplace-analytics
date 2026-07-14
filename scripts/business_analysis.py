"""
Business Intelligence Analysis

This script runs analytical queries against the Gold layer
to discover patterns, anomalies, and actionable insights.

The findings feed into:
  - WBR narrative document
  - Ad-hoc deep-dive analyses
  - Dashboard insight annotations

This is what a BIE does AFTER the pipeline is built.
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


def analyze_gmv_trends(conn) -> None:
    """Analyze GMV trends — the #1 executive metric."""

    print_header("ANALYSIS 1: GMV Growth Trajectory")

    # Monthly GMV with MoM and YoY comparisons
    result = conn.execute("""
        WITH monthly AS (
            SELECT
                DATE_TRUNC('month', order_date) AS month,
                ROUND(SUM(gmv)) AS gmv,
                SUM(order_count) AS orders,
                SUM(customer_count) AS customers,
                ROUND(SUM(gmv) / SUM(order_count), 2) AS aov
            FROM main.mart_gmv_daily
            GROUP BY month
            ORDER BY month
        )
        SELECT
            month,
            gmv,
            orders,
            customers,
            aov,
            ROUND(100.0 * (gmv - LAG(gmv) OVER (ORDER BY month))
                / NULLIF(LAG(gmv) OVER (ORDER BY month), 0), 1) AS mom_growth_pct,
            LAG(gmv, 12) OVER (ORDER BY month) AS gmv_year_ago,
            ROUND(100.0 * (gmv - LAG(gmv, 12) OVER (ORDER BY month))
                / NULLIF(LAG(gmv, 12) OVER (ORDER BY month), 0), 1) AS yoy_growth_pct
        FROM monthly
        ORDER BY month
    """).df()

    print("\n  Monthly GMV with Growth Rates:")
    print(result.to_string(index=False))

    # Key finding
    latest = result.iloc[-1]
    earliest = result.iloc[0]
    print(f"\n  📊 KEY FINDING:")
    print(f"     First month GMV:  ${earliest['gmv']:,.0f}")
    print(f"     Latest month GMV: ${latest['gmv']:,.0f}")
    print(f"     Latest MoM growth: {latest['mom_growth_pct']}%")
    if latest['yoy_growth_pct']:
        print(f"     Latest YoY growth: {latest['yoy_growth_pct']}%")


def analyze_customer_segments(conn) -> None:
    """Analyze customer segment economics — who drives value?"""

    print_header("ANALYSIS 2: Customer Segment Economics")

    result = conn.execute("""
        SELECT
            segment,
            COUNT(*) AS customers,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_customers,
            ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
            ROUND(AVG(total_orders), 1) AS avg_orders,
            ROUND(SUM(lifetime_revenue)) AS total_revenue,
            ROUND(100.0 * SUM(lifetime_revenue) / SUM(SUM(lifetime_revenue)) OVER (), 1)
                AS pct_of_revenue
        FROM main.mart_customer_ltv
        GROUP BY segment
        ORDER BY total_revenue DESC
    """).df()

    print("\n  Customer Segment Breakdown:")
    print(result.to_string(index=False))

    # Revenue concentration
    top_segment = result.iloc[0]
    print(f"\n  📊 KEY FINDING:")
    print(f"     '{top_segment['segment']}' customers are {top_segment['pct_of_customers']}% of base")
    print(f"     but drive {top_segment['pct_of_revenue']}% of revenue")
    print(f"     Avg LTV: ${top_segment['avg_ltv']:,.2f}")


def analyze_whale_concentration(conn) -> None:
    """How dependent are we on whale customers?"""

    print_header("ANALYSIS 3: Whale Customer Dependency Risk")

    result = conn.execute("""
        SELECT
            segment,
            COUNT(*) AS customers,
            ROUND(SUM(lifetime_revenue)) AS total_revenue,
            ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
            ROUND(MIN(lifetime_revenue), 2) AS min_ltv,
            ROUND(MAX(lifetime_revenue), 2) AS max_ltv,
            ROUND(AVG(total_orders), 1) AS avg_orders
        FROM main.mart_customer_ltv
        WHERE segment = 'whale'
        GROUP BY segment
    """).df()

    print("\n  Whale Customer Profile:")
    print(result.to_string(index=False))

    # What happens if we lose 5% of whales?
    whale_revenue = result.iloc[0]['total_revenue']
    whale_count = result.iloc[0]['customers']
    churn_impact = whale_revenue * 0.05

    print(f"\n  📊 RISK ANALYSIS:")
    print(f"     Total whale customers: {whale_count:,.0f}")
    print(f"     Total whale revenue: ${whale_revenue:,.0f}")
    print(f"     If 5% of whales churn: -${churn_impact:,.0f} annual revenue at risk")
    print(f"     That's {int(whale_count * 0.05)} customers worth protecting")


def analyze_regional_performance(conn) -> None:
    """Compare regions — where to invest, where to cut?"""

    print_header("ANALYSIS 4: Regional Performance Comparison")

    result = conn.execute("""
        SELECT
            region,
            ROUND(SUM(gmv)) AS total_gmv,
            ROUND(100.0 * SUM(gmv) / SUM(SUM(gmv)) OVER (), 1) AS gmv_share_pct,
            SUM(order_count) AS total_orders,
            ROUND(SUM(gmv) / SUM(order_count), 2) AS aov,
            ROUND(AVG(gross_margin_pct), 1) AS avg_margin,
            SUM(customer_count) AS total_customers
        FROM main.mart_gmv_daily
        GROUP BY region
        ORDER BY total_gmv DESC
    """).df()

    print("\n  Regional Breakdown:")
    print(result.to_string(index=False))

    # Find highest and lowest AOV regions
    highest_aov = result.loc[result['aov'].idxmax()]
    lowest_aov = result.loc[result['aov'].idxmin()]

    print(f"\n  📊 KEY FINDING:")
    print(f"     Highest AOV: {highest_aov['region']} at ${highest_aov['aov']}")
    print(f"     Lowest AOV:  {lowest_aov['region']} at ${lowest_aov['aov']}")
    print(f"     AOV gap: ${highest_aov['aov'] - lowest_aov['aov']:.2f}")


def analyze_category_profitability(conn) -> None:
    """Which categories make money vs lose money?"""

    print_header("ANALYSIS 5: Category Profitability Matrix")

    result = conn.execute("""
        SELECT
            category,
            ROUND(SUM(gmv)) AS total_gmv,
            ROUND(100.0 * SUM(gmv) / SUM(SUM(gmv)) OVER (), 1) AS gmv_share_pct,
            ROUND(SUM(gross_profit)) AS total_profit,
            ROUND(AVG(gross_margin_pct), 1) AS avg_margin,
            SUM(order_count) AS total_orders,
            SUM(items_sold) AS total_items,
            ROUND(SUM(total_discounts)) AS total_discounts,
            ROUND(100.0 * SUM(total_discounts) / NULLIF(SUM(gmv), 0), 1) AS discount_rate_pct
        FROM main.mart_gmv_daily
        GROUP BY category
        ORDER BY total_profit DESC
    """).df()

    print("\n  Category Profitability (sorted by profit):")
    print(result.to_string(index=False))

    # Key insight: which category has highest revenue but NOT highest profit?
    top_gmv = result.loc[result['total_gmv'].idxmax()]
    top_profit = result.loc[result['total_profit'].idxmax()]

    print(f"\n  📊 KEY FINDING:")
    print(f"     Highest GMV:    {top_gmv['category']} (${top_gmv['total_gmv']:,.0f})")
    print(f"     Highest Profit: {top_profit['category']} (${top_profit['total_profit']:,.0f})")
    if top_gmv['category'] != top_profit['category']:
        print(f"     ⚠️  Revenue leader ≠ Profit leader!")
        print(f"     {top_profit['category']} generates more profit despite lower GMV")
        print(f"     Consider shifting investment from {top_gmv['category']} to {top_profit['category']}")


def analyze_seller_concentration(conn) -> None:
    """How concentrated is GMV across sellers?"""

    print_header("ANALYSIS 6: Seller Concentration Risk")

    # Top 10 sellers by GMV
    top_sellers = conn.execute("""
        SELECT
            business_name,
            tier,
            region,
            primary_category,
            total_orders,
            ROUND(total_gmv) AS total_gmv,
            ROUND(commission_revenue) AS commission_revenue,
            avg_rating,
            health_status
        FROM main.mart_seller_health
        ORDER BY total_gmv DESC
        LIMIT 10
    """).df()

    print("\n  Top 10 Sellers by GMV:")
    print(top_sellers.to_string(index=False))

    # Concentration analysis
    concentration = conn.execute("""
        WITH ranked AS (
            SELECT
                total_gmv,
                NTILE(10) OVER (ORDER BY total_gmv DESC) AS decile
            FROM main.mart_seller_health
        )
        SELECT
            decile,
            COUNT(*) AS sellers,
            ROUND(SUM(total_gmv)) AS total_gmv,
            ROUND(100.0 * SUM(total_gmv) / SUM(SUM(total_gmv)) OVER (), 1) AS gmv_share_pct
        FROM ranked
        GROUP BY decile
        ORDER BY decile
    """).df()

    print("\n  Seller GMV Concentration by Decile:")
    print(concentration.to_string(index=False))

    top_decile_share = concentration.iloc[0]['gmv_share_pct']
    print(f"\n  📊 KEY FINDING:")
    print(f"     Top 10% of sellers generate {top_decile_share}% of GMV")
    print(f"     Classic 80/20 pattern — seller retention is critical")


def analyze_one_time_conversion_opportunity(conn) -> None:
    """Can we convert one-time customers to repeat?"""

    print_header("ANALYSIS 7: One-Time Customer Conversion Opportunity")

    result = conn.execute("""
        SELECT
            segment,
            activity_status,
            COUNT(*) AS customers,
            ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
            ROUND(AVG(total_orders), 1) AS avg_orders
        FROM main.mart_customer_ltv
        WHERE segment = 'one_time'
        GROUP BY segment, activity_status
        ORDER BY customers DESC
    """).df()

    print("\n  One-Time Customer Status:")
    print(result.to_string(index=False))

    total_one_time = result['customers'].sum()
    avg_ltv_one_time = conn.execute("""
        SELECT ROUND(AVG(lifetime_revenue), 2)
        FROM main.mart_customer_ltv WHERE segment = 'one_time'
    """).fetchone()[0]

    avg_ltv_regular = conn.execute("""
        SELECT ROUND(AVG(lifetime_revenue), 2)
        FROM main.mart_customer_ltv WHERE segment = 'regular'
    """).fetchone()[0]

    conversion_target = int(total_one_time * 0.10)
    revenue_opportunity = conversion_target * (avg_ltv_regular - avg_ltv_one_time)

    print(f"\n  📊 OPPORTUNITY:")
    print(f"     Total one-time customers: {total_one_time:,}")
    print(f"     Avg LTV (one-time): ${avg_ltv_one_time:,.2f}")
    print(f"     Avg LTV (regular):  ${avg_ltv_regular:,.2f}")
    print(f"     If we convert 10% ({conversion_target:,}) to regular:")
    print(f"     Additional revenue: ${revenue_opportunity:,.0f}")


def analyze_monthly_seasonality(conn) -> None:
    """Understand the seasonal patterns for planning."""

    print_header("ANALYSIS 8: Seasonality Patterns")

    result = conn.execute("""
        SELECT
            EXTRACT(MONTH FROM order_date) AS month_num,
            CASE EXTRACT(MONTH FROM order_date)
                WHEN 1 THEN 'January'    WHEN 2 THEN 'February'
                WHEN 3 THEN 'March'      WHEN 4 THEN 'April'
                WHEN 5 THEN 'May'        WHEN 6 THEN 'June'
                WHEN 7 THEN 'July'       WHEN 8 THEN 'August'
                WHEN 9 THEN 'September'  WHEN 10 THEN 'October'
                WHEN 11 THEN 'November'  WHEN 12 THEN 'December'
            END AS month_name,
            ROUND(SUM(gmv)) AS total_gmv,
            SUM(order_count) AS total_orders,
            ROUND(AVG(gross_margin_pct), 1) AS avg_margin
        FROM main.mart_gmv_daily
        GROUP BY month_num, month_name
        ORDER BY month_num
    """).df()

    print("\n  GMV by Calendar Month (all years combined):")
    print(result.to_string(index=False))

    peak_month = result.loc[result['total_gmv'].idxmax()]
    low_month = result.loc[result['total_gmv'].idxmin()]

    print(f"\n  📊 KEY FINDING:")
    print(f"     Peak month: {peak_month['month_name']} (${peak_month['total_gmv']:,.0f})")
    print(f"     Lowest month: {low_month['month_name']} (${low_month['total_gmv']:,.0f})")
    print(f"     Peak-to-trough ratio: {peak_month['total_gmv'] / low_month['total_gmv']:.1f}x")
    print(f"     Q4 concentration needs fulfillment capacity planning")


def analyze_discount_effectiveness(conn) -> None:
    """Are discounts driving revenue or eroding margin?"""

    print_header("ANALYSIS 9: Discount Impact Analysis")

    result = conn.execute("""
        SELECT
            category,
            ROUND(SUM(gmv)) AS total_gmv,
            ROUND(SUM(total_discounts)) AS total_discounts,
            ROUND(100.0 * SUM(total_discounts) / NULLIF(SUM(gmv), 0), 1) AS discount_rate,
            ROUND(AVG(gross_margin_pct), 1) AS margin_after_discount,
            ROUND(SUM(gross_profit)) AS net_profit
        FROM main.mart_gmv_daily
        GROUP BY category
        ORDER BY discount_rate DESC
    """).df()

    print("\n  Discount Rate by Category:")
    print(result.to_string(index=False))

    total_discounts = result['total_discounts'].sum()
    total_gmv = result['total_gmv'].sum()

    print(f"\n  📊 KEY FINDING:")
    print(f"     Total discounts given: ${total_discounts:,.0f}")
    print(f"     As % of GMV: {100 * total_discounts / total_gmv:.1f}%")
    print(f"     Question: Are these discounts creating incremental revenue?")
    print(f"     Or are customers buying what they would have bought anyway?")
    print(f"     Recommendation: Run an A/B test — holdout group with no discounts")


def analyze_commission_revenue(conn) -> None:
    """How much does the platform earn from each seller tier?"""

    print_header("ANALYSIS 10: Platform Commission Revenue by Seller Tier")

    result = conn.execute("""
        SELECT
            tier,
            COUNT(*) AS sellers,
            ROUND(SUM(total_gmv)) AS total_gmv,
            ROUND(AVG(commission_rate) * 100, 1) AS avg_commission_pct,
            ROUND(SUM(commission_revenue)) AS commission_revenue,
            ROUND(SUM(commission_revenue) / NULLIF(COUNT(*), 0)) AS revenue_per_seller
        FROM main.mart_seller_health
        GROUP BY tier
        ORDER BY commission_revenue DESC
    """).df()

    print("\n  Commission Revenue by Tier:")
    print(result.to_string(index=False))

    total_commission = result['commission_revenue'].sum()
    top_tier = result.iloc[0]

    print(f"\n  📊 KEY FINDING:")
    print(f"     Total platform commission revenue: ${total_commission:,.0f}")
    print(f"     Top contributor: {top_tier['tier']} tier (${top_tier['commission_revenue']:,.0f})")
    print(f"     Revenue per seller varies {result['revenue_per_seller'].min():,.0f} to {result['revenue_per_seller'].max():,.0f}")
    print(f"     New sellers pay highest rate (16.5%) but contribute least per seller")
    print(f"     Consider: lower new seller rates to improve retention?")


def main() -> None:
    conn = get_conn()

    print("\n" + "🔍" * 35)
    print("  KAIRO MARKETPLACE — BUSINESS INTELLIGENCE ANALYSIS")
    print("  Analyzing Gold layer data to extract actionable insights")
    print("🔍" * 35)

    analyze_gmv_trends(conn)
    analyze_customer_segments(conn)
    analyze_whale_concentration(conn)
    analyze_regional_performance(conn)
    analyze_category_profitability(conn)
    analyze_seller_concentration(conn)
    analyze_one_time_conversion_opportunity(conn)
    analyze_monthly_seasonality(conn)
    analyze_discount_effectiveness(conn)
    analyze_commission_revenue(conn)

    print("\n" + "=" * 70)
    print("  ANALYSIS COMPLETE")
    print("=" * 70)
    print("\n  Next steps:")
    print("  1. Use these findings to write the WBR narrative")
    print("  2. Pick the most impactful finding for a deep-dive doc")
    print("  3. Add insight annotations to each dashboard page")
    print("  4. Present findings with specific $ impact and recommendations")


if __name__ == "__main__":
    main()
    