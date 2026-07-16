"""
Generate synthetic seller data and save to Parquet.

Usage:
    python scripts/generate_sellers.py

Output:
    raw_data/sellers/sellers.parquet
"""

from pathlib import Path
from time import perf_counter

import polars as pl

from generator.entities.seller import generate_sellers
from generator.writers.parquet_writer import write_entities_to_parquet


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

NUM_SELLERS = 5_000
SEED = 42
OUTPUT_PATH = Path("raw_data/sellers/sellers.parquet")


def main() -> None:
    print(f"Generating {NUM_SELLERS:,} sellers (seed={SEED})...")

    start = perf_counter()
    sellers = generate_sellers(n=NUM_SELLERS, seed=SEED)
    gen_elapsed = perf_counter() - start

    print(f"  ✓ Generation done in {gen_elapsed:.2f}s")
    print(f"  ✓ Writing to {OUTPUT_PATH}")

    start = perf_counter()
    df = write_entities_to_parquet(sellers, OUTPUT_PATH)
    write_elapsed = perf_counter() - start

    print(f"  ✓ Wrote {len(df):,} rows in {write_elapsed:.2f}s")
    print()
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")
    print()
    print("Sample rows:")
    print(df.select(
        "seller_external_id", "business_name", "seller_type",
        "tier", "region", "primary_category", "avg_rating", "commission_rate"
    ).head(10))
    print()
    print("Seller type distribution:")
    print(
        df.group_by("seller_type")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print()
    print("Sales-profile distribution:")
    print(
        df.group_by("sales_profile")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print()
    print("Tier distribution:")
    print(
        df.group_by("tier")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print()
    print("Region distribution:")
    print(
        df.group_by("region")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print()
    print("Category distribution:")
    print(
        df.group_by("primary_category")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )
    print()
    print("Avg commission rate by tier:")
    print(
        df.group_by("tier")
        .agg(pl.col("commission_rate").mean().round(4).alias("avg_commission"))
        .sort("avg_commission", descending=True)
    )


if __name__ == "__main__":
    main()
