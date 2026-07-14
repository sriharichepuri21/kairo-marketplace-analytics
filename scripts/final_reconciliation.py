"""
Final Governed Metric Audit

Provides a concise final verification of the authoritative marketplace
financial metrics after the dbt Gold layer has been built.

Run:
    python scripts/final_reconciliation.py
"""

from decimal import Decimal
from pathlib import Path

import duckdb


DB_PATH = Path("warehouse/kairo.duckdb")


def money(value) -> str:
    """Format a numeric value as currency."""

    if value is None:
        value = Decimal("0")

    return f"${Decimal(str(value)):,.2f}"


def assert_equal(
    label: str,
    left,
    right,
    tolerance: Decimal = Decimal("0.01"),
) -> None:
    """Require two financial totals to reconcile."""

    left_value = Decimal(str(left or 0))
    right_value = Decimal(str(right or 0))
    difference = left_value - right_value

    if abs(difference) > tolerance:
        raise AssertionError(
            f"{label} failed: "
            f"{money(left_value)} vs {money(right_value)}"
        )

    print(f"  PASS — {label}: {money(difference)} difference")


if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Database not found: {DB_PATH}\n"
        "Generate the data and run dbt first."
    )


conn = duckdb.connect(str(DB_PATH), read_only=True)
conn.execute("SET preserve_insertion_order = false")
conn.execute("SET threads = 4")


try:
    print("\n" + "=" * 78)
    print("  FINAL GOVERNED METRIC AUDIT")
    print("=" * 78)

    # ------------------------------------------------------------------
    # Marketplace GMV
    # ------------------------------------------------------------------

    marketplace = conn.execute("""
        SELECT
            ROUND(SUM(gross_gmv), 2) AS gross_gmv,
            ROUND(SUM(net_gmv), 2) AS net_gmv,
            ROUND(SUM(total_discounts), 2) AS discounts,
            ROUND(SUM(total_item_tax), 2) AS item_tax,
            ROUND(SUM(gross_profit), 2) AS merchandise_profit,
            SUM(invalid_gmv_item_count) AS invalid_items
        FROM main.mart_gmv_daily
    """).fetchone()

    gross_gmv = marketplace[0]
    net_gmv = marketplace[1]
    discounts = marketplace[2]
    item_tax = marketplace[3]
    merchandise_profit = marketplace[4]
    invalid_items = marketplace[5]

    print("\n  MARKETPLACE MERCHANDISE METRICS")
    print(f"    Gross GMV:           {money(gross_gmv)}")
    print(f"    Item discounts:      {money(discounts)}")
    print(f"    Net GMV:             {money(net_gmv)}")
    print(f"    Item tax:            {money(item_tax)}")
    print(f"    Merchandise profit:  {money(merchandise_profit)}")
    print(f"    Invalid item rows:   {invalid_items:,}")

    assert_equal(
        "Gross GMV minus discounts equals Net GMV",
        Decimal(str(gross_gmv)) - Decimal(str(discounts)),
        net_gmv,
    )

    # ------------------------------------------------------------------
    # Seller and commission metrics
    # ------------------------------------------------------------------

    seller = conn.execute("""
        SELECT
            ROUND(SUM(gross_gmv), 2) AS gross_gmv,
            ROUND(SUM(net_gmv), 2) AS net_gmv,
            ROUND(SUM(commission_revenue), 2)
                AS commission_revenue,

            ROUND(
                100.0 * SUM(commission_revenue)
                / NULLIF(SUM(net_gmv), 0),
                2
            ) AS effective_take_rate

        FROM main.mart_seller_health
    """).fetchone()

    seller_gross_gmv = seller[0]
    seller_net_gmv = seller[1]
    commission_revenue = seller[2]
    effective_take_rate = seller[3]

    print("\n  SELLER AND PLATFORM METRICS")
    print(f"    Seller Gross GMV:    {money(seller_gross_gmv)}")
    print(f"    Seller Net GMV:      {money(seller_net_gmv)}")
    print(f"    Commission revenue:  {money(commission_revenue)}")
    print(f"    Effective take rate: {effective_take_rate}%")

    assert_equal(
        "Marketplace and seller Gross GMV",
        gross_gmv,
        seller_gross_gmv,
    )

    assert_equal(
        "Marketplace and seller Net GMV",
        net_gmv,
        seller_net_gmv,
    )

    # ------------------------------------------------------------------
    # Customer charged amount
    # ------------------------------------------------------------------

    customer = conn.execute("""
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
            ) AS orphan_spend,

            ROUND(
                SUM(lifetime_customer_spend),
                2
            ) AS platform_customer_spend

        FROM main.mart_customer_ltv
    """).fetchone()

    real_customer_spend = customer[0]
    orphan_spend = customer[1]
    platform_customer_spend = customer[2]

    fact_order_spend = conn.execute("""
        SELECT ROUND(SUM(total_amount), 2)
        FROM main.fact_orders
        WHERE order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()[0]

    print("\n  CUSTOMER CHARGED AMOUNT")
    print(f"    Real-customer spend: {money(real_customer_spend)}")
    print(f"    Orphan-order spend:  {money(orphan_spend)}")
    print(f"    Platform spend:      {money(platform_customer_spend)}")
    print(f"    fact_orders spend:   {money(fact_order_spend)}")

    assert_equal(
        "Real plus orphan spend equals platform spend",
        Decimal(str(real_customer_spend))
        + Decimal(str(orphan_spend)),
        platform_customer_spend,
    )

    assert_equal(
        "fact_orders equals customer LTV platform spend",
        fact_order_spend,
        platform_customer_spend,
    )

    # ------------------------------------------------------------------
    # Referential integrity
    # ------------------------------------------------------------------

    integrity = conn.execute("""
        SELECT
            COUNT(*) FILTER (
                WHERE c.customer_id IS NULL
            ) AS unmatched_orders,

            COUNT(*) FILTER (
                WHERE o.is_unknown_customer = TRUE
            ) AS unknown_member_orders

        FROM main.fact_orders AS o

        LEFT JOIN main.dim_customers AS c
            ON o.customer_id = c.customer_id

        WHERE o.order_status NOT IN ('cancelled', 'refunded')
    """).fetchone()

    print("\n  CUSTOMER REFERENTIAL INTEGRITY")
    print(f"    Unmatched orders:       {integrity[0]:,}")
    print(f"    Unknown-member orders:  {integrity[1]:,}")

    if integrity[0] != 0:
        raise AssertionError(
            f"Found {integrity[0]:,} unmatched fact orders."
        )

    print("  PASS — Every fact order matches dim_customers.")

    # ------------------------------------------------------------------
    # line_total diagnostic
    # ------------------------------------------------------------------

    line_total = conn.execute("""
        SELECT ROUND(SUM(line_total), 2)
        FROM main.fact_order_items
        WHERE order_status NOT IN ('cancelled', 'refunded')
          AND line_total IS NOT NULL
    """).fetchone()[0]

    print("\n  LINE-TOTAL DIAGNOSTIC")
    print(f"    Tax-inclusive line_total: {money(line_total)}")
    print(
        "    This value is not GMV because line_total includes item tax."
    )

    # ------------------------------------------------------------------
    # Final definitions
    # ------------------------------------------------------------------

    print("\n" + "=" * 78)
    print("  FINAL AUTHORITATIVE DEFINITIONS")
    print("=" * 78)

    print(
        f"""
  Gross GMV
    Formula: unit_price × quantity
    Value:   {money(gross_gmv)}
    Meaning: Merchandise value before discounts and tax

  Net GMV — PRIMARY GMV METRIC
    Formula: Gross GMV - item discounts
    Value:   {money(net_gmv)}
    Meaning: Merchandise value after discounts, before tax

  Customer Charged Amount
    Source:  fact_orders.total_amount
    Value:   {money(platform_customer_spend)}
    Meaning: Total eligible amount charged to customers
    Use:     Customer LTV and payment reconciliation

  Commission Revenue
    Source:  mart_seller_health.commission_revenue
    Value:   {money(commission_revenue)}
    Meaning: Kairo marketplace earnings based on Net GMV
    Effective take rate: {effective_take_rate}%

  Real-Customer Spend
    Value:   {money(real_customer_spend)}

  Orphan-Order Reconciliation Spend
    Value:   {money(orphan_spend)}
"""
    )

    print("=" * 78)
    print("  FINAL AUDIT COMPLETE — ALL RECONCILIATIONS PASSED")
    print("=" * 78)

finally:
    conn.close()
