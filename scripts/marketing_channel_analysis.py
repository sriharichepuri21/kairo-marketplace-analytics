"""
Marketing Channel Quality Analysis

Compares acquisition channels using equal 90-day observation windows
so that customers who signed up at different times are fairly compared.

Key question: Which channels bring customers who buy repeatedly
vs customers who buy once and disappear?

NOTE: This is correlation, not causation. We cannot conclude that a
channel CAUSES better retention — only that it is ASSOCIATED with it.
Causal claims require experimental data (A/B tests).

Usage: python scripts/marketing_channel_analysis.py
"""

from pathlib import Path
import duckdb

DB_PATH = Path("warehouse/kairo.duckdb")
ANALYSIS_AS_OF_DATE = "2025-12-31"

# Only include customers who signed up early enough to have a full 90-day window
# If as_of_date is 2025-12-31, last eligible signup is 2025-10-02
SIGNUP_CUTOFF = "2025-10-02"


def get_conn():
    return duckdb.connect(str(DB_PATH), read_only=True)


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def main():
    conn = get_conn()
    conn.execute("SET preserve_insertion_order = false")

    print("\n" + "=" * 70)
    print("  MARKETING CHANNEL QUALITY ANALYSIS")
    print(f"  Observation window: 90 days from each customer's signup")
    print(f"  Analysis as-of date: {ANALYSIS_AS_OF_DATE}")
    print(f"  Eligible signups: before {SIGNUP_CUTOFF}")
    print("=" * 70)

    # ── Analysis 1: Channel-level summary with 90-day windows ──

    print_header("1. CHANNEL QUALITY — 90-DAY OBSERVATION WINDOW")

    channel_summary = conn.execute(f"""
        WITH customer_orders AS (
            SELECT
                c.customer_id,
                c.signup_channel,
                c.signup_date,
                c.segment,
                o.order_id,
                o.total_amount,
                o.order_date,
                DATEDIFF('day', c.signup_date, o.order_date) AS days_since_signup
            FROM main.dim_customers c
            LEFT JOIN main.fact_orders o
                ON c.customer_id = o.customer_id
                AND o.order_status NOT IN ('cancelled', 'refunded')
                AND o.order_date <= c.signup_date + INTERVAL '90 days'
            WHERE c.signup_date <= DATE '{SIGNUP_CUTOFF}'
        ),

        customer_90d AS (
            SELECT
                customer_id,
                signup_channel,
                segment,
                COUNT(DISTINCT order_id) AS orders_90d,
                COALESCE(SUM(total_amount), 0) AS spend_90d
            FROM customer_orders
            GROUP BY customer_id, signup_channel, segment
        )

        SELECT
            signup_channel,
            COUNT(*) AS customers,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_total,

            -- Spend metrics (90-day window)
            ROUND(AVG(spend_90d), 2) AS avg_spend_90d,
            ROUND(MEDIAN(spend_90d), 2) AS median_spend_90d,

            -- Order metrics (90-day window)
            ROUND(AVG(orders_90d), 1) AS avg_orders_90d,

            -- Behavior rates
            ROUND(100.0 * SUM(CASE WHEN orders_90d = 0 THEN 1 ELSE 0 END)
                / COUNT(*), 1) AS never_ordered_pct,
            ROUND(100.0 * SUM(CASE WHEN orders_90d = 1 THEN 1 ELSE 0 END)
                / COUNT(*), 1) AS one_order_pct,
            ROUND(100.0 * SUM(CASE WHEN orders_90d >= 2 THEN 1 ELSE 0 END)
                / COUNT(*), 1) AS repeat_pct,

            -- Whale rate
            ROUND(100.0 * SUM(CASE WHEN segment = 'whale' THEN 1 ELSE 0 END)
                / COUNT(*), 1) AS whale_pct

        FROM customer_90d
        GROUP BY signup_channel
        ORDER BY avg_spend_90d DESC
    """).df()

    print(channel_summary.to_string(index=False))

    # Key findings
    best_channel = channel_summary.iloc[0]
    worst_channel = channel_summary.iloc[-1]
    print(f"\n  📊 KEY FINDINGS:")
    print(f"     Highest avg 90-day spend: {best_channel['signup_channel']} (${best_channel['avg_spend_90d']:,.2f})")
    print(f"     Lowest avg 90-day spend:  {worst_channel['signup_channel']} (${worst_channel['avg_spend_90d']:,.2f})")
    spend_ratio = best_channel['avg_spend_90d'] / worst_channel['avg_spend_90d'] if worst_channel['avg_spend_90d'] > 0 else 0
    print(f"     Ratio: {spend_ratio:.1f}x")

    # ── Analysis 2: Which channels produce whales? ──

    print_header("2. WHALE PRODUCTION BY CHANNEL")

    whale_analysis = conn.execute(f"""
        SELECT
            c.signup_channel,
            COUNT(*) AS total_customers,
            SUM(CASE WHEN c.segment = 'whale' THEN 1 ELSE 0 END) AS whale_count,
            ROUND(100.0 * SUM(CASE WHEN c.segment = 'whale' THEN 1 ELSE 0 END)
                / COUNT(*), 2) AS whale_pct,
            ROUND(1000.0 * SUM(CASE WHEN c.segment = 'whale' THEN 1 ELSE 0 END)
                / COUNT(*), 1) AS whales_per_1000_signups
        FROM main.dim_customers c
        WHERE c.signup_date <= DATE '{SIGNUP_CUTOFF}'
        GROUP BY c.signup_channel
        ORDER BY whale_pct DESC
    """).df()

    print(whale_analysis.to_string(index=False))

    # ── Analysis 3: One-order customer distribution by channel ──

    print_header("3. SINGLE-ORDER CUSTOMERS BY CHANNEL")

    single_order = conn.execute(f"""
        WITH customer_order_counts AS (
            SELECT
                c.customer_id,
                c.signup_channel,
                COUNT(DISTINCT o.order_id) AS total_orders
            FROM main.dim_customers c
            LEFT JOIN main.fact_orders o
                ON c.customer_id = o.customer_id
                AND o.order_status NOT IN ('cancelled', 'refunded')
            WHERE c.signup_date <= DATE '{SIGNUP_CUTOFF}'
            GROUP BY c.customer_id, c.signup_channel
        )

        SELECT
            signup_channel,
            COUNT(*) AS total_customers,
            SUM(CASE WHEN total_orders = 0 THEN 1 ELSE 0 END) AS never_ordered,
            SUM(CASE WHEN total_orders = 1 THEN 1 ELSE 0 END) AS one_order_only,
            SUM(CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END) AS repeat_buyers,
            ROUND(100.0 * SUM(CASE WHEN total_orders = 1 THEN 1 ELSE 0 END)
                / NULLIF(SUM(CASE WHEN total_orders >= 1 THEN 1 ELSE 0 END), 0), 1)
                AS one_order_rate_of_buyers
        FROM customer_order_counts
        GROUP BY signup_channel
        ORDER BY one_order_rate_of_buyers DESC
    """).df()

    print(single_order.to_string(index=False))

    # ── Analysis 4: First purchase category by channel ──

    print_header("4. WHAT DO CUSTOMERS BUY FIRST? (by channel)")

    first_purchase = conn.execute(f"""
        WITH first_orders AS (
            SELECT
                o.customer_id,
                c.signup_channel,
                o.order_date,
                ROW_NUMBER() OVER (
                    PARTITION BY o.customer_id
                    ORDER BY o.order_date ASC, o.order_id ASC
                ) AS order_rank
            FROM main.fact_orders o
            JOIN main.dim_customers c ON o.customer_id = c.customer_id
            WHERE o.order_status NOT IN ('cancelled', 'refunded')
              AND c.signup_date <= DATE '{SIGNUP_CUTOFF}'
        ),

        first_order_items AS (
            SELECT
                fo.customer_id,
                fo.signup_channel,
                oi.category,
                ROW_NUMBER() OVER (
                    PARTITION BY fo.customer_id
                    ORDER BY oi.line_total DESC
                ) AS item_rank
            FROM first_orders fo
            JOIN main.fact_order_items oi ON fo.customer_id = oi.order_id
            WHERE fo.order_rank = 1
        )

        SELECT
            signup_channel,
            category,
            COUNT(*) AS customers,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY signup_channel), 1)
                AS pct_of_channel
        FROM first_order_items
        WHERE item_rank = 1
        GROUP BY signup_channel, category
        ORDER BY signup_channel, customers DESC
    """).df()

    if len(first_purchase) > 0:
        # Show top 3 categories per channel
        for channel in first_purchase['signup_channel'].unique():
            channel_data = first_purchase[first_purchase['signup_channel'] == channel].head(3)
            print(f"\n  {channel}:")
            for _, row in channel_data.iterrows():
                print(f"    {row['category']}: {row['customers']:,} ({row['pct_of_channel']}%)")
    else:
        print("  No first-purchase data available (possible join issue)")

    # ── Analysis 5: 90-day repeat rate by channel ──

    print_header("5. 90-DAY REPEAT RATE BY CHANNEL (fairest comparison)")

    repeat_90d = conn.execute(f"""
        WITH customer_first_order AS (
            SELECT
                c.customer_id,
                c.signup_channel,
                MIN(o.order_date) AS first_order_date
            FROM main.dim_customers c
            JOIN main.fact_orders o
                ON c.customer_id = o.customer_id
                AND o.order_status NOT IN ('cancelled', 'refunded')
            WHERE c.signup_date <= DATE '{SIGNUP_CUTOFF}'
            GROUP BY c.customer_id, c.signup_channel
        ),

        customer_second_order AS (
            SELECT
                cfo.customer_id,
                cfo.signup_channel,
                cfo.first_order_date,
                MIN(o.order_date) AS second_order_date
            FROM customer_first_order cfo
            JOIN main.fact_orders o
                ON cfo.customer_id = o.customer_id
                AND o.order_date > cfo.first_order_date
                AND o.order_date <= cfo.first_order_date + INTERVAL '90 days'
                AND o.order_status NOT IN ('cancelled', 'refunded')
            GROUP BY cfo.customer_id, cfo.signup_channel, cfo.first_order_date
        )

        SELECT
            cfo.signup_channel,
            COUNT(DISTINCT cfo.customer_id) AS customers_with_first_order,
            COUNT(DISTINCT cso.customer_id) AS returned_within_90d,
            ROUND(100.0 * COUNT(DISTINCT cso.customer_id)
                / COUNT(DISTINCT cfo.customer_id), 1) AS repeat_rate_90d,
            ROUND(AVG(DATEDIFF('day', cfo.first_order_date,
                cso.second_order_date)), 1) AS avg_days_to_second_order
        FROM customer_first_order cfo
        LEFT JOIN customer_second_order cso
            ON cfo.customer_id = cso.customer_id
        GROUP BY cfo.signup_channel
        ORDER BY repeat_rate_90d DESC
    """).df()

    print(repeat_90d.to_string(index=False))

    best_repeat = repeat_90d.iloc[0]
    worst_repeat = repeat_90d.iloc[-1]
    print(f"\n  📊 KEY FINDING:")
    print(f"     Highest 90-day repeat: {best_repeat['signup_channel']} ({best_repeat['repeat_rate_90d']}%)")
    print(f"     Lowest 90-day repeat:  {worst_repeat['signup_channel']} ({worst_repeat['repeat_rate_90d']}%)")
    print(f"     Gap: {best_repeat['repeat_rate_90d'] - worst_repeat['repeat_rate_90d']}pp")

    # ── Summary ──

    print_header("SUMMARY & CONCLUSIONS")

    print("""
  WHAT WE FOUND (correlation, not causation):
  
  [Findings will be filled after seeing the data]

  WHAT WE CANNOT CONCLUDE:
  
  - We cannot say any channel CAUSES better retention
  - Referral customers may have higher spend because loyal people
    are more likely to use referrals — not because referrals create loyalty
  - We cannot recommend budget reallocation without spend data
  - We cannot calculate ROI, CAC, or LTV:CAC without marketing spend

  WHAT WOULD BE NEEDED FOR CAUSAL CLAIMS:
  
  - A/B test: randomly assign new visitors to different channels
  - Marketing spend data by channel by month
  - Attribution model connecting campaigns to signups
  - Holdout experiments for each channel

  RECOMMENDED NEXT STEP:
  
  Use signup_channel as a FEATURE in the churn prediction model.
  If it improves prediction accuracy, it's useful regardless of
  whether the relationship is causal.
    """)


if __name__ == "__main__":
    main()