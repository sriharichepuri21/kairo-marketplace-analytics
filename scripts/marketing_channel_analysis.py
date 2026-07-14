"""
Marketing Channel Quality Analysis

Compares acquisition channels using equal 90-day observation windows
so customers who signed up at different times are fairly compared.

Key question:
Which channels bring customers who buy repeatedly versus customers
who buy once and disappear?

Important:
This analysis measures correlation, not causation. We cannot conclude
that a channel causes better retention. Causal claims require experiments,
marketing-spend data, and reliable campaign attribution.

Usage:
    python scripts/marketing_channel_analysis.py
"""

from pathlib import Path

import duckdb


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

DB_PATH = Path("warehouse/kairo.duckdb")

ANALYSIS_AS_OF_DATE = "2025-12-31"
OBSERVATION_DAYS = 90

# Customers must sign up by this date to receive a complete
# 90-day observation window before the analysis date.
SIGNUP_CUTOFF = "2025-10-02"


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def get_conn() -> duckdb.DuckDBPyConnection:
    """Open the Kairo DuckDB warehouse in read-only mode."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at: {DB_PATH}\n"
            "Generate the data and run the dbt pipeline first."
        )

    conn = duckdb.connect(str(DB_PATH), read_only=True)

    # Reduces memory requirements for large analytical queries.
    conn.execute("SET preserve_insertion_order = false")
    conn.execute("SET threads = 4")

    return conn


def print_header(title: str) -> None:
    """Print a consistent section header."""

    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def exclude_unknown_channels(dataframe):
    """
    Remove the unknown channel from channel ranking calculations.

    Unknown records are still displayed in the analysis but should not
    be treated as a legitimate acquisition channel.
    """

    if dataframe.empty:
        return dataframe

    return dataframe[
        dataframe["signup_channel"].fillna("unknown") != "unknown"
    ].copy()


# ----------------------------------------------------------------------
# Main analysis
# ----------------------------------------------------------------------

def main() -> None:
    conn = get_conn()

    try:
        print("\n" + "=" * 70)
        print("  MARKETING CHANNEL QUALITY ANALYSIS")
        print(f"  Observation window: {OBSERVATION_DAYS} days from signup")
        print(f"  Analysis as-of date: {ANALYSIS_AS_OF_DATE}")
        print(f"  Eligible signups: on or before {SIGNUP_CUTOFF}")
        print("=" * 70)

        # ==============================================================
        # 1. Channel quality using equal 90-day observation windows
        # ==============================================================

        print_header("1. CHANNEL QUALITY — 90-DAY OBSERVATION WINDOW")

        channel_summary = conn.execute(
            f"""
            WITH eligible_customers AS (
                SELECT
                    customer_id,
                    COALESCE(signup_channel, 'unknown') AS signup_channel,
                    signup_date,
                    segment
                FROM main.dim_customers
                WHERE signup_date <= DATE '{SIGNUP_CUTOFF}'
                  AND is_unknown_customer = FALSE
            ),

            customer_orders AS (
                SELECT
                    c.customer_id,
                    c.signup_channel,
                    c.signup_date,
                    c.segment,
                    o.order_id,
                    o.total_amount,
                    o.order_date

                FROM eligible_customers AS c

                LEFT JOIN main.fact_orders AS o
                    ON c.customer_id = o.customer_id
                    AND o.order_status NOT IN ('cancelled', 'refunded')
                    AND o.order_date >= c.signup_date
                    AND o.order_date
                        <= c.signup_date + INTERVAL '{OBSERVATION_DAYS} days'
                    AND o.order_date <= DATE '{ANALYSIS_AS_OF_DATE}'
            ),

            customer_90d AS (
                SELECT
                    customer_id,
                    signup_channel,
                    segment,

                    COUNT(DISTINCT order_id) AS orders_90d,

                    COALESCE(
                        SUM(total_amount),
                        0
                    ) AS spend_90d

                FROM customer_orders

                GROUP BY
                    customer_id,
                    signup_channel,
                    segment
            )

            SELECT
                signup_channel,

                COUNT(*) AS customers,

                ROUND(
                    100.0 * COUNT(*)
                    / SUM(COUNT(*)) OVER (),
                    1
                ) AS pct_of_total,

                ROUND(
                    AVG(spend_90d),
                    2
                ) AS avg_spend_90d,

                ROUND(
                    MEDIAN(spend_90d),
                    2
                ) AS median_spend_90d,

                ROUND(
                    AVG(orders_90d),
                    1
                ) AS avg_orders_90d,

                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN orders_90d = 0 THEN 1
                            ELSE 0
                        END
                    )
                    / COUNT(*),
                    1
                ) AS no_order_within_90d_pct,

                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN orders_90d = 1 THEN 1
                            ELSE 0
                        END
                    )
                    / COUNT(*),
                    1
                ) AS one_order_within_90d_pct,

                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN orders_90d >= 2 THEN 1
                            ELSE 0
                        END
                    )
                    / COUNT(*),
                    1
                ) AS repeat_within_90d_pct,

                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN segment = 'whale' THEN 1
                            ELSE 0
                        END
                    )
                    / COUNT(*),
                    1
                ) AS synthetic_whale_persona_pct

            FROM customer_90d

            GROUP BY signup_channel

            ORDER BY
                avg_spend_90d DESC,
                signup_channel
            """
        ).df()

        if channel_summary.empty:
            print("  No eligible customer data was found.")
        else:
            print(channel_summary.to_string(index=False))

            ranked_channels = exclude_unknown_channels(channel_summary)

            if not ranked_channels.empty:
                best_channel = ranked_channels.iloc[0]
                worst_channel = ranked_channels.iloc[-1]

                worst_spend = float(worst_channel["avg_spend_90d"])
                best_spend = float(best_channel["avg_spend_90d"])

                spend_ratio = (
                    best_spend / worst_spend
                    if worst_spend > 0
                    else 0
                )

                print("\n  KEY FINDINGS:")
                print(
                    "     Highest average 90-day spend: "
                    f"{best_channel['signup_channel']} "
                    f"(${best_spend:,.2f})"
                )
                print(
                    "     Lowest average 90-day spend:  "
                    f"{worst_channel['signup_channel']} "
                    f"(${worst_spend:,.2f})"
                )
                print(f"     Spend ratio: {spend_ratio:.2f}x")

        # ==============================================================
        # 2. Synthetic whale-persona distribution
        # ==============================================================

        print_header("2. SYNTHETIC WHALE PERSONA DISTRIBUTION BY CHANNEL")

        whale_analysis = conn.execute(
            f"""
            SELECT
                COALESCE(
                    signup_channel,
                    'unknown'
                ) AS signup_channel,

                COUNT(*) AS total_customers,

                SUM(
                    CASE
                        WHEN segment = 'whale' THEN 1
                        ELSE 0
                    END
                ) AS whale_persona_count,

                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN segment = 'whale' THEN 1
                            ELSE 0
                        END
                    )
                    / COUNT(*),
                    2
                ) AS whale_persona_pct,

                ROUND(
                    1000.0
                    * SUM(
                        CASE
                            WHEN segment = 'whale' THEN 1
                            ELSE 0
                        END
                    )
                    / COUNT(*),
                    1
                ) AS whale_personas_per_1000_signups

            FROM main.dim_customers

            WHERE signup_date <= DATE '{SIGNUP_CUTOFF}'
                  AND is_unknown_customer = FALSE

            GROUP BY
                COALESCE(signup_channel, 'unknown')

            ORDER BY
                whale_persona_pct DESC,
                signup_channel
            """
        ).df()

        if whale_analysis.empty:
            print("  No whale-persona data was found.")
        else:
            print(whale_analysis.to_string(index=False))

        # ==============================================================
        # 3. Lifetime purchase behavior by channel
        # ==============================================================

        print_header("3. LIFETIME PURCHASE BEHAVIOR BY CHANNEL")

        purchase_behavior = conn.execute(
            f"""
            WITH customer_order_counts AS (
                SELECT
                    c.customer_id,

                    COALESCE(
                        c.signup_channel,
                        'unknown'
                    ) AS signup_channel,

                    COUNT(
                        DISTINCT o.order_id
                    ) AS lifetime_orders

                FROM main.dim_customers AS c

                LEFT JOIN main.fact_orders AS o
                    ON c.customer_id = o.customer_id
                    AND o.order_status NOT IN ('cancelled', 'refunded')
                    AND o.order_date <= DATE '{ANALYSIS_AS_OF_DATE}'

                WHERE c.signup_date <= DATE '{SIGNUP_CUTOFF}'
                  AND c.is_unknown_customer = FALSE

                GROUP BY
                    c.customer_id,
                    COALESCE(c.signup_channel, 'unknown')
            )

            SELECT
                signup_channel,

                COUNT(*) AS total_customers,

                SUM(
                    CASE
                        WHEN lifetime_orders = 0 THEN 1
                        ELSE 0
                    END
                ) AS never_ordered_lifetime,

                SUM(
                    CASE
                        WHEN lifetime_orders = 1 THEN 1
                        ELSE 0
                    END
                ) AS one_order_only_lifetime,

                SUM(
                    CASE
                        WHEN lifetime_orders >= 2 THEN 1
                        ELSE 0
                    END
                ) AS repeat_buyers_lifetime,

                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN lifetime_orders = 1 THEN 1
                            ELSE 0
                        END
                    )
                    / NULLIF(
                        SUM(
                            CASE
                                WHEN lifetime_orders >= 1 THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    1
                ) AS one_order_rate_among_buyers

            FROM customer_order_counts

            GROUP BY signup_channel

            ORDER BY
                one_order_rate_among_buyers DESC,
                signup_channel
            """
        ).df()

        if purchase_behavior.empty:
            print("  No lifetime purchase-behavior data was found.")
        else:
            print(purchase_behavior.to_string(index=False))

        # ==============================================================
        # 4. First-purchase category by channel
        # ==============================================================

        print_header("4. WHAT DO CUSTOMERS BUY FIRST? (BY CHANNEL)")

        first_purchase = conn.execute(
            f"""
            WITH ranked_orders AS (
                SELECT
                    o.customer_id,

                    COALESCE(
                        c.signup_channel,
                        'unknown'
                    ) AS signup_channel,

                    o.order_id,
                    o.order_date,

                    ROW_NUMBER() OVER (
                        PARTITION BY o.customer_id
                        ORDER BY
                            o.order_date ASC,
                            o.order_id ASC
                    ) AS order_rank

                FROM main.fact_orders AS o

                INNER JOIN main.dim_customers AS c
                    ON o.customer_id = c.customer_id

                WHERE o.order_status NOT IN ('cancelled', 'refunded')
                  AND o.order_date <= DATE '{ANALYSIS_AS_OF_DATE}'
                  AND c.signup_date <= DATE '{SIGNUP_CUTOFF}'
                  AND c.is_unknown_customer = FALSE
            ),

            first_orders AS (
                SELECT
                    customer_id,
                    signup_channel,
                    order_id,
                    order_date

                FROM ranked_orders

                WHERE order_rank = 1
            ),

            ranked_first_order_items AS (
                SELECT
                    fo.customer_id,
                    fo.signup_channel,
                    fo.order_id,
                    oi.order_item_id,
                    oi.category,

                    (
                        COALESCE(oi.unit_price, 0)
                        * COALESCE(oi.quantity, 0)
                        - COALESCE(oi.discount_amount, 0)
                    ) AS net_item_value,

                    ROW_NUMBER() OVER (
                        PARTITION BY fo.customer_id
                        ORDER BY
                            (
                                COALESCE(oi.unit_price, 0)
                                * COALESCE(oi.quantity, 0)
                                - COALESCE(oi.discount_amount, 0)
                            ) DESC,
                            oi.order_item_id ASC
                    ) AS item_rank

                FROM first_orders AS fo

                INNER JOIN main.fact_order_items AS oi
                    ON fo.order_id = oi.order_id

                WHERE COALESCE(oi.quantity, 0) > 0
                  AND oi.unit_price IS NOT NULL
                  AND oi.category IS NOT NULL
            ),

            primary_first_purchase AS (
                SELECT
                    customer_id,
                    signup_channel,
                    category

                FROM ranked_first_order_items

                WHERE item_rank = 1
            ),

            category_summary AS (
                SELECT
                    signup_channel,
                    category,
                    COUNT(*) AS customers

                FROM primary_first_purchase

                GROUP BY
                    signup_channel,
                    category
            )

            SELECT
                signup_channel,
                category AS first_purchase_category,
                customers,

                ROUND(
                    100.0
                    * customers
                    / SUM(customers) OVER (
                        PARTITION BY signup_channel
                    ),
                    1
                ) AS pct_of_channel_customers

            FROM category_summary

            ORDER BY
                signup_channel,
                customers DESC,
                first_purchase_category
            """
        ).df()

        if first_purchase.empty:
            print("  No first-purchase data was found.")
            print("  Check order_id relationships between facts.")
        else:
            channels = first_purchase["signup_channel"].unique()

            for channel in channels:
                channel_data = (
                    first_purchase[
                        first_purchase["signup_channel"] == channel
                    ]
                    .head(3)
                )

                print(f"\n  {channel}:")

                for _, row in channel_data.iterrows():
                    print(
                        f"    {row['first_purchase_category']}: "
                        f"{int(row['customers']):,} customers "
                        f"({row['pct_of_channel_customers']}%)"
                    )

        # ==============================================================
        # 5. Repeat purchase within 90 days of first order
        # ==============================================================

        print_header(
            "5. 90-DAY REPEAT RATE FROM FIRST ORDER BY CHANNEL"
        )

        repeat_90d = conn.execute(
            f"""
            WITH ranked_customer_orders AS (
                SELECT
                    c.customer_id,

                    COALESCE(
                        c.signup_channel,
                        'unknown'
                    ) AS signup_channel,

                    o.order_id,
                    o.order_date,

                    ROW_NUMBER() OVER (
                        PARTITION BY c.customer_id
                        ORDER BY
                            o.order_date ASC,
                            o.order_id ASC
                    ) AS order_rank

                FROM main.dim_customers AS c

                INNER JOIN main.fact_orders AS o
                    ON c.customer_id = o.customer_id

                WHERE c.signup_date <= DATE '{SIGNUP_CUTOFF}'
                  AND c.is_unknown_customer = FALSE
                  AND o.order_status NOT IN ('cancelled', 'refunded')
                  AND o.order_date <= DATE '{ANALYSIS_AS_OF_DATE}'
            ),

            first_and_second_orders AS (
                SELECT
                    customer_id,
                    signup_channel,

                    MIN(
                        CASE
                            WHEN order_rank = 1 THEN order_date
                        END
                    ) AS first_order_date,

                    MIN(
                        CASE
                            WHEN order_rank = 2 THEN order_date
                        END
                    ) AS second_order_date

                FROM ranked_customer_orders

                GROUP BY
                    customer_id,
                    signup_channel
            )

            SELECT
                signup_channel,

                COUNT(*) AS customers_with_first_order,

                SUM(
                    CASE
                        WHEN second_order_date IS NOT NULL
                         AND second_order_date
                             <= first_order_date
                                + INTERVAL '{OBSERVATION_DAYS} days'
                        THEN 1
                        ELSE 0
                    END
                ) AS returned_within_90d,

                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN second_order_date IS NOT NULL
                             AND second_order_date
                                 <= first_order_date
                                    + INTERVAL '{OBSERVATION_DAYS} days'
                            THEN 1
                            ELSE 0
                        END
                    )
                    / COUNT(*),
                    1
                ) AS repeat_rate_90d,

                ROUND(
                    AVG(
                        CASE
                            WHEN second_order_date IS NOT NULL
                             AND second_order_date
                                 <= first_order_date
                                    + INTERVAL '{OBSERVATION_DAYS} days'
                            THEN DATEDIFF(
                                'day',
                                first_order_date,
                                second_order_date
                            )
                        END
                    ),
                    1
                ) AS avg_days_to_second_order

            FROM first_and_second_orders

            WHERE first_order_date IS NOT NULL
              AND first_order_date
                    <= DATE '{ANALYSIS_AS_OF_DATE}'
                        - INTERVAL '{OBSERVATION_DAYS} days'

            GROUP BY signup_channel

            ORDER BY
                repeat_rate_90d DESC,
                signup_channel
            """
        ).df()

        if repeat_90d.empty:
            print("  No repeat-purchase data was found.")
        else:
            print(repeat_90d.to_string(index=False))

            ranked_repeat = exclude_unknown_channels(repeat_90d)

            if not ranked_repeat.empty:
                best_repeat = ranked_repeat.iloc[0]
                worst_repeat = ranked_repeat.iloc[-1]

                repeat_gap = (
                    float(best_repeat["repeat_rate_90d"])
                    - float(worst_repeat["repeat_rate_90d"])
                )

                print("\n  KEY FINDINGS:")
                print(
                    "     Highest 90-day repeat rate: "
                    f"{best_repeat['signup_channel']} "
                    f"({best_repeat['repeat_rate_90d']}%)"
                )
                print(
                    "     Lowest 90-day repeat rate:  "
                    f"{worst_repeat['signup_channel']} "
                    f"({worst_repeat['repeat_rate_90d']}%)"
                )
                print(f"     Difference: {repeat_gap:.1f} percentage points")

        # ==============================================================
        # Summary
        # ==============================================================

        print_header("SUMMARY & CONCLUSIONS")

        named_summary = exclude_unknown_channels(channel_summary)
        named_repeat = exclude_unknown_channels(repeat_90d)

        if not named_summary.empty:
            highest_spend = named_summary.iloc[0]
            lowest_spend = named_summary.iloc[-1]

            print("\n  OBSERVED CHANNEL-QUALITY PATTERNS:")
            print(
                f"  - {highest_spend['signup_channel']} has the highest "
                f"average 90-day customer spend "
                f"(${highest_spend['avg_spend_90d']:,.2f})."
            )
            print(
                f"  - {lowest_spend['signup_channel']} has the lowest "
                f"average 90-day customer spend "
                f"(${lowest_spend['avg_spend_90d']:,.2f})."
            )

        if not named_repeat.empty:
            highest_repeat = named_repeat.iloc[0]
            lowest_repeat = named_repeat.iloc[-1]

            print(
                f"  - {highest_repeat['signup_channel']} has the highest "
                f"90-day repeat rate "
                f"({highest_repeat['repeat_rate_90d']}%)."
            )
            print(
                f"  - {lowest_repeat['signup_channel']} has the lowest "
                f"90-day repeat rate "
                f"({lowest_repeat['repeat_rate_90d']}%)."
            )

        print(
            """
  INTERPRETATION:

  - These are associations, not causal effects.
  - The channel-to-segment relationship is an intentional synthetic
    business assumption in the customer generator.
  - Channel may be useful as a churn-model feature, but it should not
    replace observed behavioral features such as recency, frequency,
    spend, returns, and reviews.

  WHAT THIS ANALYSIS CANNOT PROVE:

  - It cannot prove that a channel causes better retention.
  - It cannot calculate CAC, ROI, or LTV:CAC without marketing spend.
  - It cannot justify a specific budget reallocation percentage.
  - It cannot separate channel effects from customer-selection effects.

  DATA NEEDED FOR STRONGER BUSINESS RECOMMENDATIONS:

  - Marketing spend by channel and campaign
  - Campaign attribution data
  - Customer acquisition cost
  - Promotional and referral-program costs
  - Randomized holdout or A/B test results

  RECOMMENDED NEXT STEP:

  Build the point-in-time churn dataset and compare:

  1. A baseline churn model using behavioral features only
  2. A model using behavioral features plus signup_channel

  Keep signup_channel only if it improves out-of-sample prediction.
            """
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()