"""
Generate synthetic orders and order items, save to Parquet.

Reads customer and product data from existing Parquet files
so orders have valid foreign keys.

Usage:
    python scripts/generate_orders.py

Output:
    raw_data/orders/orders.parquet
    raw_data/order_items/order_items.parquet
"""

from datetime import date
from pathlib import Path
from time import perf_counter

import duckdb
import polars as pl

from generator.entities.order import (
    CustomerProfile,
    ProductInfo,
    generate_orders,
)
from generator.writers.parquet_writer import write_entities_to_parquet


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

TARGET_ORDERS = 3_000_000  # start small, scale to 3M later
SEED = 42
START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 12, 31)

ORDERS_OUTPUT = Path("raw_data/orders/orders.parquet")
ITEMS_OUTPUT = Path("raw_data/order_items/order_items.parquet")
CUSTOMERS_PATH = Path("raw_data/customers/customers.parquet")
PRODUCTS_PATH = Path("raw_data/products/products.parquet")


def load_customer_profiles(path: Path) -> list[CustomerProfile]:
    """Load customer data from Parquet into lightweight profiles."""
    conn = duckdb.connect()
    rows = conn.execute(f"""
        SELECT customer_id, region, segment, signup_date
        FROM '{path}'
    """).fetchall()

    return [
        CustomerProfile(
            customer_id=r[0],
            region=r[1],
            segment=r[2],
            signup_date=r[3],
        )
        for r in rows
    ]


def load_product_info(path: Path) -> list[ProductInfo]:
    """Load product data from Parquet into lightweight product info."""
    conn = duckdb.connect()
    rows = conn.execute(f"""
        SELECT product_id, seller_id, category, price, cost
        FROM '{path}'
        WHERE is_active = true
    """).fetchall()

    return [
        ProductInfo(
            product_id=r[0],
            seller_id=r[1],
            category=r[2],
            price=r[3],
            cost=r[4],
        )
        for r in rows
    ]


def main() -> None:
    # Load dependencies
    print("Loading customer profiles...")
    customers = load_customer_profiles(CUSTOMERS_PATH)
    print(f"  ✓ Loaded {len(customers):,} customers")

    print("Loading product info...")
    products = load_product_info(PRODUCTS_PATH)
    print(f"  ✓ Loaded {len(products):,} active products")

    # Generate
    print(f"\nGenerating ~{TARGET_ORDERS:,} orders (seed={SEED})...")
    print(f"  Window: {START_DATE} to {END_DATE}")

    start = perf_counter()
    orders, items = generate_orders(
        customers=customers,
        products=products,
        start_date=START_DATE,
        end_date=END_DATE,
        target_orders=TARGET_ORDERS,
        seed=SEED,
    )
    gen_elapsed = perf_counter() - start
    print(f"  ✓ Generated {len(orders):,} orders with {len(items):,} line items in {gen_elapsed:.2f}s")

    # Write orders
    print(f"\nWriting orders to {ORDERS_OUTPUT}...")
    start = perf_counter()
    orders_df = write_entities_to_parquet(orders, ORDERS_OUTPUT)
    print(f"  ✓ Wrote {len(orders_df):,} orders in {perf_counter() - start:.2f}s")
    print(f"  File size: {ORDERS_OUTPUT.stat().st_size / 1024:.1f} KB")

    # Write order items
    print(f"\nWriting order items to {ITEMS_OUTPUT}...")
    start = perf_counter()
    items_df = write_entities_to_parquet(items, ITEMS_OUTPUT)
    print(f"  ✓ Wrote {len(items_df):,} items in {perf_counter() - start:.2f}s")
    print(f"  File size: {ITEMS_OUTPUT.stat().st_size / 1024:.1f} KB")

    # ─────────────────────────────────────────────────────
    # Analytics
    # ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("ORDER ANALYTICS")
    print("=" * 70)

    print("\nOrder status distribution:")
    print(
        orders_df.group_by("order_status")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )

    print("\nOrders by region:")
    print(
        orders_df.group_by("region")
        .agg(
            pl.len().alias("orders"),
            pl.col("total_amount").sum().round(2).alias("total_gmv"),
            pl.col("total_amount").mean().round(2).alias("avg_order_value"),
        )
        .sort("total_gmv", descending=True)
    )

    print("\nOrders by channel:")
    print(
        orders_df.group_by("order_channel")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )

    print("\nMonthly order volume (showing first and last 3 months):")
    monthly = (
        orders_df.with_columns(
            pl.col("order_placed_at").cast(pl.Date).dt.truncate("1mo").alias("month")
        )
        .group_by("month")
        .agg(
            pl.len().alias("orders"),
            pl.col("total_amount").sum().round(2).alias("monthly_gmv"),
        )
        .sort("month")
    )
    print(monthly.head(3))
    print("...")
    print(monthly.tail(3))

    print(f"\nAvg items per order: {len(items) / len(orders):.2f}")
    print(f"Total GMV: ${orders_df['total_amount'].sum():,.2f}")
    print(f"Avg Order Value: ${orders_df['total_amount'].mean():,.2f}")

    print("\n" + "=" * 70)
    print("ORDER ITEM ANALYTICS")
    print("=" * 70)

    print("\nItems by category:")
    print(
        items_df.group_by("category")
        .agg(
            pl.len().alias("items_sold"),
            pl.col("line_total").sum().round(2).alias("category_revenue"),
        )
        .sort("category_revenue", descending=True)
    )


if __name__ == "__main__":
    main()