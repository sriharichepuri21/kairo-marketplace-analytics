"""
Governed Metric Reconciliation

Reconciles the authoritative Gold-layer financial metrics:

1. Gross GMV
2. Net GMV
3. Customer charged amount
4. Customer LTV spend
5. Seller commission revenue
6. Unknown-customer reconciliation
7. Order-component data-quality issues

Run:
    python scripts/reconcile_metrics.py
"""

from decimal import Decimal
from pathlib import Path

import duckdb


DB_PATH = Path("warehouse/kairo.duckdb")
ELIGIBLE_STATUSES = "('cancelled', 'refunded')"


def to_decimal(value) -> Decimal:
    """Convert a database numeric value safely to Decimal."""

    if value is None:
        return Decimal("0")

    return Decimal(str(value))


def format_money(value) -> str:
    """Format a numeric value as currency."""

    return f"${to_decimal(value):,.2f}"


def print_header(title: str) -> None:
    """Print a consistent report header."""

    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def assert_close(
    label: str,
    first_value,
    second_value,
    tolerance: Decimal = Decimal("0.01"),
) -> None:
    """Require two governed totals to reconcile within tolerance."""

    first = to_decimal(first_value)
    second = to_decimal(second_value)
    difference = first - second

    if abs(difference) > tolerance:
        raise AssertionError(
            f"{label} failed reconciliation: "
            f"{format_money(first)} vs {format_money(second)} "
            f"(difference {format_money(difference)})"
        )

    print(
        f"  PASS — {label}: "
        f"difference {format_money(difference)}"
    )


if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Database not found: {DB_PATH}\n"
        "Generate the data and run dbt before reconciliation."
    )


conn = duckdb.connect(str(DB_PATH), read_only=True)
conn.execute("SET preserve_insertion_order = false")
conn.execute("SET threads = 4")


try:
    print("\n" + "🔎" * 35)
    print("  GOVERNED METRIC RECONCILIATION")
    print("  Financial measures must reconcile across Gold models")
    print("🔎" * 35)

    # ------------------------------------------------------------------
    # 1. Marketplace merchandise metrics
    # ------------------------------------------------------------------

    print_header("1. Marketplace Merchandise Metrics")

    marketplace = conn.execute("""
        SELECT
            ROUND(SUM(gross_gmv), 2) AS gross_gmv,
            ROUND(SUM(net_gmv), 2) AS net_gmv,
            ROUND(SUM(total_discounts), 2) AS item_discounts,
            ROUND(SUM(total_item_tax), 2) AS item_tax,
            SUM(invalid_gmv_item_count) AS invalid_gmv_items
        FROM main.mart_gmv_daily
    """).fetchone()

    item_quality = conn.execute("""
        SELECT
            COUNT(*) AS eligible_item_rows,

            COUNT(*) FILTER (
                WHERE is_gmv_valid = TRUE
            ) AS valid_gmv_item_rows,

            COUNT(*) FILTER (
                WHERE is_gmv_valid = FALSE
            ) AS invalid_gmv_item_rows

        FROM main.fact_order_items

        WHERE order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()

    gross_gmv = marketplace[0]
    net_gmv = marketplace[1]
    item_discounts = marketplace[2]
    item_tax = marketplace[3]
    invalid_gmv_items = marketplace[4]

    print(f"\n  Gross GMV:       {format_money(gross_gmv)}")
    print(f"  Net GMV:         {format_money(net_gmv)}")
    print(f"  Item discounts:  {format_money(item_discounts)}")
    print(f"  Item tax:        {format_money(item_tax)}")
    print(f"\n  Eligible item rows: {item_quality[0]:,}")
    print(f"  Valid GMV rows:     {item_quality[1]:,}")
    print(f"  Invalid GMV rows:   {item_quality[2]:,}")

    assert_close(
        "Gross GMV minus discounts equals Net GMV",
        to_decimal(gross_gmv) - to_decimal(item_discounts),
        net_gmv,
    )

    if item_quality[2] != invalid_gmv_items:
        raise AssertionError(
            "Invalid item count differs between fact_order_items "
            "and mart_gmv_daily."
        )

    print(
        "  PASS — Invalid item counts agree between fact and mart: "
        f"{invalid_gmv_items:,}"
    )

    # ------------------------------------------------------------------
    # 2. Seller financial reconciliation
    # ------------------------------------------------------------------

    print_header("2. Seller Financial Reconciliation")

    seller_totals = conn.execute("""
        SELECT
            ROUND(SUM(gross_gmv), 2) AS gross_gmv,
            ROUND(SUM(net_gmv), 2) AS net_gmv,
            ROUND(SUM(commission_revenue), 2)
                AS commission_revenue,

            ROUND(
                100.0 * SUM(commission_revenue)
                / NULLIF(SUM(net_gmv), 0),
                2
            ) AS effective_take_rate_pct

        FROM main.mart_seller_health
    """).fetchone()

    seller_gross_gmv = seller_totals[0]
    seller_net_gmv = seller_totals[1]
    commission_revenue = seller_totals[2]
    effective_take_rate = seller_totals[3]

    print(
        f"\n  Seller mart Gross GMV: "
        f"{format_money(seller_gross_gmv)}"
    )
    print(
        f"  Seller mart Net GMV:   "
        f"{format_money(seller_net_gmv)}"
    )
    print(
        f"  Commission revenue:    "
        f"{format_money(commission_revenue)}"
    )
    print(
        f"  Effective take rate:   "
        f"{effective_take_rate}%"
    )

    assert_close(
        "Gross GMV across marketplace and seller marts",
        gross_gmv,
        seller_gross_gmv,
    )

    assert_close(
        "Net GMV across marketplace and seller marts",
        net_gmv,
        seller_net_gmv,
    )

    # ------------------------------------------------------------------
    # 3. Customer charged amount
    # ------------------------------------------------------------------

    print_header("3. Customer Charged Amount Reconciliation")

    order_totals = conn.execute("""
        SELECT
            COUNT(DISTINCT order_id) AS eligible_orders,

            COUNT(*) FILTER (
                WHERE total_amount IS NULL
            ) AS null_total_amount_orders,

            ROUND(SUM(total_amount), 2)
                AS customer_charged_amount

        FROM main.fact_orders

        WHERE order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()

    eligible_orders = order_totals[0]
    null_total_orders = order_totals[1]
    customer_charged_amount = order_totals[2]

    ltv_totals = conn.execute("""
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

    real_customer_spend = ltv_totals[0]
    orphan_reconciliation_spend = ltv_totals[1]
    platform_customer_spend = ltv_totals[2]
    invalid_financial_orders = ltv_totals[3]

    print(f"\n  Eligible orders: {eligible_orders:,}")
    print(
        f"  Orders with null total_amount: "
        f"{null_total_orders:,}"
    )
    print(
        f"  fact_orders customer charged amount: "
        f"{format_money(customer_charged_amount)}"
    )
    print(
        f"\n  Real-customer lifetime spend: "
        f"{format_money(real_customer_spend)}"
    )
    print(
        f"  Orphan-order reconciliation spend: "
        f"{format_money(orphan_reconciliation_spend)}"
    )
    print(
        f"  Platform customer spend: "
        f"{format_money(platform_customer_spend)}"
    )
    print(
        f"  Invalid financial orders tracked by LTV: "
        f"{invalid_financial_orders:,}"
    )

    assert_close(
        "fact_orders charged amount vs LTV platform spend",
        customer_charged_amount,
        platform_customer_spend,
    )

    assert_close(
        "Real plus orphan spend vs platform spend",
        to_decimal(real_customer_spend)
        + to_decimal(orphan_reconciliation_spend),
        platform_customer_spend,
    )

    if null_total_orders != invalid_financial_orders:
        raise AssertionError(
            "Null total_amount order count does not agree with "
            "mart_customer_ltv.invalid_financial_orders."
        )

    print(
        "  PASS — Invalid financial order counts agree: "
        f"{invalid_financial_orders:,}"
    )

    # ------------------------------------------------------------------
    # 4. Customer referential integrity
    # ------------------------------------------------------------------

    print_header("4. Customer Referential Integrity")

    customer_integrity = conn.execute("""
        SELECT
            COUNT(*) FILTER (
                WHERE c.customer_id IS NULL
            ) AS unmatched_orders,

            COUNT(*) FILTER (
                WHERE o.is_unknown_customer = TRUE
            ) AS orders_mapped_to_unknown,

            ROUND(
                SUM(
                    CASE
                        WHEN o.is_unknown_customer = TRUE
                        THEN o.total_amount
                        ELSE 0
                    END
                ),
                2
            ) AS unknown_customer_spend

        FROM main.fact_orders AS o

        LEFT JOIN main.dim_customers AS c
            ON o.customer_id = c.customer_id

        WHERE o.order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()

    unmatched_orders = customer_integrity[0]
    orders_mapped_to_unknown = customer_integrity[1]
    unknown_customer_spend = customer_integrity[2]

    print(f"\n  Unmatched fact orders: {unmatched_orders:,}")
    print(
        f"  Eligible orders mapped to unknown member: "
        f"{orders_mapped_to_unknown:,}"
    )
    print(
        f"  Unknown-member charged amount: "
        f"{format_money(unknown_customer_spend)}"
    )

    if unmatched_orders != 0:
        raise AssertionError(
            f"Found {unmatched_orders:,} unmatched fact orders."
        )

    print("  PASS — Every fact order matches dim_customers.")

    assert_close(
        "Unknown-member spend vs orphan reconciliation spend",
        unknown_customer_spend,
        orphan_reconciliation_spend,
    )

    # ------------------------------------------------------------------
    # 5. Order-component data-quality diagnostics
    # ------------------------------------------------------------------

    print_header("5. Order Component Data-Quality Diagnostics")

    component_quality = conn.execute("""
        SELECT
            COUNT(*) AS eligible_orders,

            COUNT(*) FILTER (
                WHERE subtotal IS NULL
                   OR discount_amount IS NULL
                   OR tax_amount IS NULL
                   OR shipping_cost IS NULL
                   OR total_amount IS NULL
            ) AS orders_with_missing_components,

            COUNT(*) FILTER (
                WHERE subtotal IS NOT NULL
                  AND discount_amount IS NOT NULL
                  AND tax_amount IS NOT NULL
                  AND shipping_cost IS NOT NULL
                  AND total_amount IS NOT NULL
                  AND ABS(
                      total_amount
                      - (
                          subtotal
                          - discount_amount
                          + tax_amount
                          + shipping_cost
                      )
                  ) > 0.01
            ) AS complete_orders_with_mismatch,

            ROUND(
                SUM(
                    CASE
                        WHEN subtotal IS NOT NULL
                         AND discount_amount IS NOT NULL
                         AND tax_amount IS NOT NULL
                         AND shipping_cost IS NOT NULL
                         AND total_amount IS NOT NULL
                        THEN total_amount
                    END
                ),
                2
            ) AS complete_order_actual_total,

            ROUND(
                SUM(
                    CASE
                        WHEN subtotal IS NOT NULL
                         AND discount_amount IS NOT NULL
                         AND tax_amount IS NOT NULL
                         AND shipping_cost IS NOT NULL
                         AND total_amount IS NOT NULL
                        THEN
                            subtotal
                            - discount_amount
                            + tax_amount
                            + shipping_cost
                    END
                ),
                2
            ) AS complete_order_reconstructed_total

        FROM main.fact_orders

        WHERE order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()

    component_gap = (
        to_decimal(component_quality[3])
        - to_decimal(component_quality[4])
    )

    print(f"\n  Eligible orders: {component_quality[0]:,}")
    print(
        f"  Orders with one or more missing components: "
        f"{component_quality[1]:,}"
    )
    print(
        f"  Complete orders with component mismatch: "
        f"{component_quality[2]:,}"
    )
    print(
        f"  Complete-order actual charged amount: "
        f"{format_money(component_quality[3])}"
    )
    print(
        f"  Complete-order reconstructed amount: "
        f"{format_money(component_quality[4])}"
    )
    print(
        f"  Complete-order reconstruction gap: "
        f"{format_money(component_gap)}"
    )

    print(
        "\n  NOTE: Component reconstruction is a data-quality diagnostic."
    )
    print(
        "  It is not used to define GMV because synthetic chaos can "
        "corrupt individual order components."
    )

    mismatch_samples = conn.execute("""
        SELECT
            order_id,
            ROUND(subtotal, 2) AS subtotal,
            ROUND(discount_amount, 2) AS discount,
            ROUND(tax_amount, 2) AS tax,
            ROUND(shipping_cost, 2) AS shipping,
            ROUND(total_amount, 2) AS total_amount,

            ROUND(
                total_amount
                - (
                    subtotal
                    - discount_amount
                    + tax_amount
                    + shipping_cost
                ),
                2
            ) AS difference

        FROM main.fact_orders

        WHERE order_status NOT IN ('cancelled', 'refunded')
          AND subtotal IS NOT NULL
          AND discount_amount IS NOT NULL
          AND tax_amount IS NOT NULL
          AND shipping_cost IS NOT NULL
          AND total_amount IS NOT NULL
          AND ABS(
              total_amount
              - (
                  subtotal
                  - discount_amount
                  + tax_amount
                  + shipping_cost
              )
          ) > 0.01

        ORDER BY ABS(difference) DESC
        LIMIT 5
    """).df()

    if len(mismatch_samples) > 0:
        print("\n  Largest component mismatches:")
        print(mismatch_samples.to_string(index=False))
    else:
        print("\n  No complete-order component mismatches found.")

    # ------------------------------------------------------------------
    # 6. Governed metric summary
    # ------------------------------------------------------------------

    print_header("6. Governed Metric Summary")

    print(
        f"\n  Gross GMV\n"
        f"    Value:   {format_money(gross_gmv)}\n"
        f"    Meaning: Merchandise value before item discounts and tax"
    )

    print(
        f"\n  Net GMV — PRIMARY GMV METRIC\n"
        f"    Value:   {format_money(net_gmv)}\n"
        f"    Meaning: Merchandise value after item discounts, before tax"
    )

    print(
        f"\n  Customer Charged Amount\n"
        f"    Value:   {format_money(customer_charged_amount)}\n"
        f"    Meaning: Eligible order total charged to customers\n"
        f"    Use:     Customer LTV and payment reconciliation"
    )

    print(
        f"\n  Commission Revenue\n"
        f"    Value:   {format_money(commission_revenue)}\n"
        f"    Meaning: Marketplace earnings calculated from Net GMV\n"
        f"    Effective take rate: {effective_take_rate}%"
    )

    print(
        "\n  Do not use fact_order_items.line_total as GMV."
    )
    print(
        "  line_total includes item tax and is therefore not a "
        "tax-exclusive merchandise metric."
    )

    print("\n" + "=" * 78)
    print("  RECONCILIATION COMPLETE")
    print("=" * 78)
    print("\n  All governed cross-model reconciliation checks passed.")

finally:
    conn.close()
