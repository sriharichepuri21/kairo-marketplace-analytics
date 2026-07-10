"""
Generate synthetic customer data and save to Parquet.

Usage:
    python scripts/generate_customers.py

Output:
    raw_data/customers/customers.parquet
"""

from pathlib import Path
from time import perf_counter

from generator.entities.customer import generate_customers
from generator.writers.parquet_writer import write_entities_to_parquet


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

NUM_CUSTOMERS = 200_000
SEED = 42
OUTPUT_PATH = Path("raw_data/customers/customers.parquet")


def main() -> None:
    print(f"Generating {NUM_CUSTOMERS:,} customers (seed={SEED})...")

    start = perf_counter()
    customers = generate_customers(n=NUM_CUSTOMERS, seed=SEED)
    gen_elapsed = perf_counter() - start

    print(f"  ✓ Generation done in {gen_elapsed:.2f}s")
    print(f"  ✓ Writing to {OUTPUT_PATH}")

    start = perf_counter()
    df = write_entities_to_parquet(customers, OUTPUT_PATH)
    write_elapsed = perf_counter() - start

    print(f"  ✓ Wrote {len(df):,} rows in {write_elapsed:.2f}s")
    print()
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")
    print()
    print("Sample rows:")
    print(df.head(5))
    print()
    print("Segment distribution:")
    print(
        df.group_by("segment")
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


if __name__ == "__main__":
    # polars needs to be imported here for the group_by expressions above
    import polars as pl

    main()