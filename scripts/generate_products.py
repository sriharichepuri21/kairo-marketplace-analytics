"""
Generate synthetic product data and save to Parquet.

Reads seller IDs from the existing sellers Parquet file
so products have valid foreign keys.

Usage:
    python scripts/generate_products.py

Output:
    raw_data/products/products.parquet
"""

from pathlib import Path
from time import perf_counter

import duckdb
import polars as pl

from generator.entities.product import generate_products
from generator.writers.parquet_writer import write_entities_to_parquet


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

NUM_PRODUCTS = 50_000
SEED = 42
OUTPUT_PATH = Path("raw_data/products/products.parquet")
SELLERS_PATH = Path("raw_data/sellers/sellers.parquet")


def main() -> None:
    # Load seller IDs from existing Parquet
    if not SELLERS_PATH.exists():
        raise FileNotFoundError(
            f"Sellers file not found at {SELLERS_PATH}. "
            "Run 'python scripts/generate_sellers.py' first."
        )

    conn = duckdb.connect()
    seller_ids = (
        conn.execute(f"SELECT seller_id FROM '{SELLERS_PATH}'")
        .pl()["seller_id"]
        .to_list()
    )
    print(f"Loaded {len(seller_ids):,} seller IDs from {SELLERS_PATH}")

    print(f"Generating {NUM_PRODUCTS:,} products (seed={SEED})...")

    start = perf_counter()
    products = generate_products(n=NUM_PRODUCTS, seller_ids=seller_ids, seed=SEED)
    gen_elapsed = perf_counter() - start

    print(f"  ✓ Generation done in {gen_elapsed:.2f}s")
    print(f"  ✓ Writing to {OUTPUT_PATH}")

    start = perf_counter()
    df = write_entities_to_parquet(products, OUTPUT_PATH)
    write_elapsed = perf_counter() - start

    print(f"  ✓ Wrote {len(df):,} rows in {write_elapsed:.2f}s")
    print()
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")
    print()
    print("Sample rows:")
    print(df.select(
        "product_sku", "product_name", "category",
        "price", "cost", "avg_rating", "return_rate"
    ).head(10))
    print()
    print("Category distribution:")
    print(
        df.group_by("category")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print()
    print("Avg price by category:")
    print(
        df.group_by("category")
        .agg(pl.col("price").mean().round(2).alias("avg_price"))
        .sort("avg_price", descending=True)
    )
    print()
    print("Avg return rate by category:")
    print(
        df.group_by("category")
        .agg(pl.col("return_rate").mean().round(4).alias("avg_return_rate"))
        .sort("avg_return_rate", descending=True)
    )
    print()
    print("Products per seller (top 10 most prolific):")
    print(
        df.group_by("seller_id")
        .agg(pl.len().alias("product_count"))
        .sort("product_count", descending=True)
        .head(10)
    )
    print()
    print(f"Active products: {df.filter(pl.col('is_active')).height:,} / {len(df):,}")
    print(f"  ({100 * df.filter(pl.col('is_active')).height / len(df):.1f}%)")


if __name__ == "__main__":
    main()