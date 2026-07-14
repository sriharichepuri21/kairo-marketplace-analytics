"""
Metric Reconciliation — Resolving every dollar of difference.

Gap 1: Items ($407M) vs Orders ($454.5M) — mostly tax+shipping, $9.3M unexplained
Gap 2: Orders ($454.5M) vs LTV mart ($454.0M) — $499K unexplained
"""

from pathlib import Path
import duckdb

conn = duckdb.connect(str(Path("warehouse/kairo.duckdb")), read_only=True)
conn.execute("SET preserve_insertion_order = false")


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


# ── GAP 1: Why don't order components add up to total_amount? ──

print_header("GAP 1: Order Component Reconstruction")

reconstruction = conn.execute("""
    SELECT
        ROUND(SUM(total_amount)) AS actual_total,
        ROUND(SUM(
            COALESCE(subtotal, 0)
            - COALESCE(discount_amount, 0)
            + COALESCE(tax_amount, 0)
            + COALESCE(shipping_cost, 0)
        )) AS reconstructed_total
    FROM main.fact_orders
    WHERE order_status NOT IN ('cancelled', 'refunded')
""").fetchone()

unexplained = reconstruction[0] - reconstruction[1]
print(f"  Actual SUM(total_amount):      ${reconstruction[0]:,.0f}")
print(f"  Reconstructed (sub-disc+tax+ship): ${reconstruction[1]:,.0f}")
print(f"  Unexplained difference:        ${unexplained:,.0f}")

# Check for NULLs in components
print_header("NULL Check in Order Components")

nulls = conn.execute("""
    SELECT
        COUNT(*) AS total_orders,
        SUM(CASE WHEN subtotal IS NULL THEN 1 ELSE 0 END) AS null_subtotal,
        SUM(CASE WHEN discount_amount IS NULL THEN 1 ELSE 0 END) AS null_discount,
        SUM(CASE WHEN tax_amount IS NULL THEN 1 ELSE 0 END) AS null_tax,
        SUM(CASE WHEN shipping_cost IS NULL THEN 1 ELSE 0 END) AS null_shipping,
        SUM(CASE WHEN total_amount IS NULL THEN 1 ELSE 0 END) AS null_total
    FROM main.fact_orders
    WHERE order_status NOT IN ('cancelled', 'refunded')
""").fetchone()

print(f"  Total orders:       {nulls[0]:,}")
print(f"  NULL subtotal:      {nulls[1]:,}")
print(f"  NULL discount:      {nulls[2]:,}")
print(f"  NULL tax:           {nulls[3]:,}")
print(f"  NULL shipping:      {nulls[4]:,}")
print(f"  NULL total_amount:  {nulls[5]:,}")

# Sample rows with discrepancy
print_header("Sample Orders Where Components Don't Add Up")

samples = conn.execute("""
    SELECT
        order_id,
        ROUND(subtotal, 2) AS subtotal,
        ROUND(discount_amount, 2) AS discount,
        ROUND(tax_amount, 2) AS tax,
        ROUND(shipping_cost, 2) AS shipping,
        ROUND(total_amount, 2) AS total,
        ROUND(total_amount - (
            COALESCE(subtotal, 0)
            - COALESCE(discount_amount, 0)
            + COALESCE(tax_amount, 0)
            + COALESCE(shipping_cost, 0)
        ), 2) AS difference
    FROM main.fact_orders
    WHERE order_status NOT IN ('cancelled', 'refunded')
      AND ABS(total_amount - (
            COALESCE(subtotal, 0)
            - COALESCE(discount_amount, 0)
            + COALESCE(tax_amount, 0)
            + COALESCE(shipping_cost, 0)
        )) > 0.01
    ORDER BY ABS(difference) DESC
    LIMIT 10
""").df()

if len(samples) > 0:
    print(f"  Found {len(samples)} sample rows with component mismatch:")
    print(samples.to_string(index=False))
else:
    print("  All orders reconstruct perfectly from components!")

# If no discrepancy per-row, the gap must come from NULLs
if len(samples) == 0:
    print("\n  Since per-row components add up, the $9.3M gap must come from")
    print("  NULL values in subtotal/discount/shipping that COALESCE to 0")
    print("  but are included differently in total_amount generation.")

    # Check: what do NULL-subtotal orders look like?
    null_orders = conn.execute("""
        SELECT
            COUNT(*) AS orders_with_null_subtotal,
            ROUND(SUM(total_amount)) AS total_amount_of_null_rows
        FROM main.fact_orders
        WHERE order_status NOT IN ('cancelled', 'refunded')
          AND subtotal IS NULL
    """).fetchone()
    print(f"\n  Orders with NULL subtotal: {null_orders[0]:,}")
    print(f"  Their total_amount sum: ${null_orders[1]:,.0f}" if null_orders[1] else "  $0")

    null_ship = conn.execute("""
        SELECT
            COUNT(*) AS orders_with_null_shipping,
            ROUND(SUM(total_amount)) AS total_amount_sum,
            ROUND(SUM(COALESCE(subtotal, 0))) AS subtotal_sum
        FROM main.fact_orders
        WHERE order_status NOT IN ('cancelled', 'refunded')
          AND shipping_cost IS NULL
    """).fetchone()
    print(f"\n  Orders with NULL shipping_cost: {null_ship[0]:,}")
    print(f"  Their total_amount sum: ${null_ship[1]:,.0f}" if null_ship[1] else "  $0")


# ── GAP 2: Orders vs LTV mart ──

print_header("GAP 2: fact_orders vs mart_customer_ltv")

order_total = conn.execute("""
    SELECT ROUND(SUM(total_amount)) FROM main.fact_orders
    WHERE order_status NOT IN ('cancelled', 'refunded')
""").fetchone()[0]

ltv_total = conn.execute("""
    SELECT ROUND(SUM(lifetime_revenue)) FROM main.mart_customer_ltv
""").fetchone()[0]

gap2 = order_total - ltv_total
print(f"  fact_orders SUM(total_amount):     ${order_total:,.0f}")
print(f"  mart_customer_ltv SUM(revenue):    ${ltv_total:,.0f}")
print(f"  Gap:                               ${gap2:,.0f}")

# Check: orders with customer_ids not in dim_customers
orphan_orders = conn.execute("""
    SELECT
        COUNT(*) AS orphan_orders,
        ROUND(SUM(o.total_amount)) AS orphan_revenue
    FROM main.fact_orders o
    LEFT JOIN main.dim_customers c ON o.customer_id = c.customer_id
    WHERE c.customer_id IS NULL
      AND o.order_status NOT IN ('cancelled', 'refunded')
""").fetchone()

print(f"\n  Orders with no matching customer: {orphan_orders[0]:,}")
print(f"  Their revenue: ${orphan_orders[1]:,.0f}" if orphan_orders[1] else "  $0")
print(f"  → This likely explains the ${gap2:,.0f} gap")

# ── SUMMARY ──

print_header("RECONCILIATION SUMMARY")

item_gmv = conn.execute("""
    SELECT ROUND(SUM(line_total))
    FROM main.fact_order_items
    WHERE order_status NOT IN ('cancelled', 'refunded')
      AND quantity > 0 AND line_total > 0
""").fetchone()[0]

print(f"  METRIC 1 — GMV (merchandise value)")
print(f"    Source: fact_order_items.line_total")
print(f"    Value: ${item_gmv:,.0f}")
print(f"    Excludes: tax, shipping, cancelled, refunded")
print(f"    Use for: Business reporting, category analysis, margin calculation")

print(f"\n  METRIC 2 — Customer Spend (total charged)")
print(f"    Source: fact_orders.total_amount")
print(f"    Value: ${order_total:,.0f}")
print(f"    Includes: merchandise + tax + shipping - discounts")
print(f"    Use for: Customer LTV calculation, payment reconciliation")

print(f"\n  METRIC 3 — Commission Revenue (platform earnings)")
commission = conn.execute("""
    SELECT ROUND(SUM(commission_revenue)) FROM main.mart_seller_health
""").fetchone()[0]
print(f"    Source: mart_seller_health.commission_revenue")
print(f"    Value: ${commission:,.0f}")
print(f"    Formula: GMV × seller commission rate")
print(f"    Use for: Kairo P&L, marketplace revenue reporting")

print(f"\n  RELATIONSHIP:")
print(f"    GMV:              ${item_gmv:,.0f}  (what customers paid for products)")
print(f"    + Tax:            ${nulls[0] and reconstruction[0]:,.0f}")
print(f"    + Shipping:        included in total_amount")
print(f"    - Discounts:       included in total_amount")
print(f"    = Customer Spend: ${order_total:,.0f}  (what customers were charged)")
print(f"    × ~12% commission")
print(f"    = Commission Rev: ${commission:,.0f}  (what Kairo earns)")