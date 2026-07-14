"""
Final Reconciliation: Is our $407M GMV actually tax-inclusive?
If so, what's the real GMV and what changes?
"""

from pathlib import Path
import duckdb

conn = duckdb.connect(str(Path("warehouse/kairo.duckdb")), read_only=True)
conn.execute("SET preserve_insertion_order = false")


print("=" * 70)
print("  FINAL METRIC RECONCILIATION")
print("=" * 70)

# Step 1: Understand what line_total actually contains
print("\n--- Step 1: What is line_total? ---")

sample = conn.execute("""
    SELECT
        order_item_id,
        ROUND(unit_price, 2) AS unit_price,
        quantity,
        ROUND(unit_price * quantity, 2) AS gross_merchandise,
        ROUND(discount_amount, 2) AS discount,
        ROUND(tax_amount, 2) AS tax,
        ROUND(line_total, 2) AS line_total,
        ROUND(unit_price * quantity - discount_amount + tax_amount, 2) AS reconstructed,
        ROUND(line_total - (unit_price * quantity - discount_amount + tax_amount), 2) AS residual
    FROM main.fact_order_items
    WHERE quantity > 0
      AND unit_price IS NOT NULL
      AND line_total IS NOT NULL
    LIMIT 10
""").df()
print(sample.to_string(index=False))

print("\n  If residual ≈ 0, then line_total = (price × qty) - discount + tax")
print("  That means our GMV includes tax — which is wrong for a GMV metric.")


# Step 2: Calculate correct metrics
print("\n--- Step 2: Correct Metric Calculations ---")

metrics = conn.execute("""
    SELECT
        ROUND(SUM(line_total)) AS current_gmv_tax_inclusive,
        ROUND(SUM(unit_price * quantity)) AS gross_merchandise_value,
        ROUND(SUM(unit_price * quantity - COALESCE(discount_amount, 0))) AS net_merchandise_value,
        ROUND(SUM(COALESCE(discount_amount, 0))) AS total_item_discounts,
        ROUND(SUM(COALESCE(tax_amount, 0))) AS total_item_tax,
        ROUND(SUM(unit_cost * quantity)) AS total_cogs
    FROM main.fact_order_items
    WHERE quantity > 0
      AND unit_price IS NOT NULL
      AND line_total > 0
      AND order_status NOT IN ('cancelled', 'refunded')
""").fetchone()

print(f"  Current GMV (line_total, tax-inclusive):  ${metrics[0]:,.0f}  ← what we've been reporting")
print(f"  Gross Merchandise Value (price × qty):    ${metrics[1]:,.0f}  ← before any discounts")
print(f"  Net Merchandise Value (gross - discount): ${metrics[2]:,.0f}  ← after discounts")
print(f"  Total Item Discounts:                     ${metrics[3]:,.0f}")
print(f"  Total Item Tax:                           ${metrics[4]:,.0f}")
print(f"  Total COGS:                               ${metrics[5]:,.0f}")

# Step 3: Recalculate margins
print("\n--- Step 3: Corrected Margins ---")

gross_merch = metrics[1]
net_merch = metrics[2]
cogs = metrics[5]
tax_inclusive = metrics[0]

print(f"\n  WRONG (current, tax-inclusive):")
print(f"    GMV:          ${tax_inclusive:,.0f}")
print(f"    COGS:         ${cogs:,.0f}")
print(f"    Gross Profit: ${tax_inclusive - cogs:,.0f}")
print(f"    Margin:       {round(100 * (tax_inclusive - cogs) / tax_inclusive, 1)}%")

print(f"\n  CORRECT (net merchandise, tax-excluded):")
print(f"    Net GMV:      ${net_merch:,.0f}")
print(f"    COGS:         ${cogs:,.0f}")
print(f"    Gross Profit: ${net_merch - cogs:,.0f}")
print(f"    Margin:       {round(100 * (net_merch - cogs) / net_merch, 1)}%")

print(f"\n  ALSO CORRECT (gross merchandise, pre-discount):")
print(f"    Gross GMV:    ${gross_merch:,.0f}")
print(f"    COGS:         ${cogs:,.0f}")
print(f"    Gross Profit: ${gross_merch - cogs:,.0f}")
print(f"    Margin:       {round(100 * (gross_merch - cogs) / gross_merch, 1)}%")


# Step 4: Corrected commission
print("\n--- Step 4: Corrected Commission Revenue ---")

current_commission = conn.execute("""
    SELECT ROUND(SUM(commission_revenue)) FROM main.mart_seller_health
""").fetchone()[0]

corrected_rate = current_commission / tax_inclusive
corrected_commission_net = net_merch * corrected_rate

print(f"  Current commission (on tax-inclusive):    ${current_commission:,.0f}")
print(f"  Effective rate on tax-inclusive GMV:       {round(100 * corrected_rate, 2)}%")
print(f"  If commission on net merchandise instead:  ${corrected_commission_net:,.0f}")
print(f"  Difference:                               ${current_commission - corrected_commission_net:,.0f}")


# Step 5: Corrected category margins
print("\n--- Step 5: Corrected Category Economics ---")

categories = conn.execute("""
    SELECT
        category,
        ROUND(SUM(unit_price * quantity)) AS gross_gmv,
        ROUND(SUM(unit_price * quantity - COALESCE(discount_amount, 0))) AS net_gmv,
        ROUND(SUM(unit_cost * quantity)) AS cogs,
        ROUND(SUM(unit_price * quantity - COALESCE(discount_amount, 0)) 
              - SUM(unit_cost * quantity)) AS gross_profit,
        ROUND(100.0 * (
            SUM(unit_price * quantity - COALESCE(discount_amount, 0)) - SUM(unit_cost * quantity)
        ) / NULLIF(SUM(unit_price * quantity - COALESCE(discount_amount, 0)), 0), 1) AS margin_pct
    FROM main.fact_order_items
    WHERE quantity > 0 AND unit_price IS NOT NULL AND line_total > 0
      AND order_status NOT IN ('cancelled', 'refunded')
    GROUP BY category
    ORDER BY gross_gmv DESC
""").df()
print(categories.to_string(index=False))


# Step 6: Summary
print("\n" + "=" * 70)
print("  FINAL METRIC DEFINITIONS")
print("=" * 70)
print(f"""
  Gross Merchandise Value (Gross GMV):
    Formula: SUM(unit_price × quantity)
    Value:   ${gross_merch:,.0f}
    Meaning: Total merchandise value before discounts, before tax

  Net Merchandise Value (Net GMV):
    Formula: SUM(unit_price × quantity - discount_amount)
    Value:   ${net_merch:,.0f}
    Meaning: Merchandise value after discounts, before tax
    USE THIS as the primary GMV metric.

  Customer Charged Amount:
    Formula: SUM(fact_orders.total_amount)
    Value:   $454,525,513
    Meaning: Total charged to customers (merchandise + tax + shipping)
    USE THIS for customer LTV (rename to lifetime_customer_spend)

  Commission Revenue:
    Formula: Net GMV × seller commission rate
    Corrected Value: ${corrected_commission_net:,.0f}
    Current (incorrect): ${current_commission:,.0f}
    Meaning: What Kairo earns from marketplace transactions

  Previously Published GMV ($406,966,903):
    This was line_total which includes tax — INCORRECT for GMV
    Should not be used as the primary business metric
""")