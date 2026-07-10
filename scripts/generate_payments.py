"""
Generate synthetic payment data from existing orders.

Usage:
    python scripts/generate_payments.py
"""

from pathlib import Path
from time import perf_counter

import duckdb
import polars as pl

from generator.entities.payment import OrderPaymentInfo, generate_payments
from generator.writers.parquet_writer import write_entities_to_parquet


NUM_SEED = 42
OUTPUT_PATH = Path("raw_data/payments/payments.parquet")
ORDERS_PATH = Path("raw_data/orders/orders.parquet")


def load_order_info(path: Path) -> list[OrderPaymentInfo]:
    conn = duckdb.connect()
    rows = conn.execute(f"""
        SELECT order_id, total_amount, currency, region,
               order_status, order_placed_at
        FROM '{path}'
    """).fetchall()

    return [
        OrderPaymentInfo(
            order_id=r[0], total_amount=r[1], currency=r[2],
            region=r[3], order_status=r[4], order_placed_at=r[5],
        )
        for r in rows
    ]


def main() -> None:
    print("Loading orders...")
    orders = load_order_info(ORDERS_PATH)
    print(f"  ✓ Loaded {len(orders):,} orders")

    print(f"\nGenerating payments (seed={NUM_SEED})...")
    start = perf_counter()
    payments = generate_payments(orders, seed=NUM_SEED)
    elapsed = perf_counter() - start
    print(f"  ✓ Generated {len(payments):,} payment records in {elapsed:.2f}s")

    print(f"\nWriting to {OUTPUT_PATH}...")
    start = perf_counter()
    df = write_entities_to_parquet(payments, OUTPUT_PATH)
    print(f"  ✓ Wrote {len(df):,} rows in {perf_counter() - start:.2f}s")
    print(f"  File size: {OUTPUT_PATH.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print("PAYMENT ANALYTICS")
    print("=" * 70)

    print("\nPayment status:")
    print(df.group_by("payment_status").agg(pl.len().alias("count")).sort("count", descending=True))

    print("\nPayment method:")
    print(df.group_by("payment_method").agg(pl.len().alias("count")).sort("count", descending=True))

    print("\nProcessor:")
    print(df.group_by("processor").agg(pl.len().alias("count")).sort("count", descending=True))

    print(f"\nRetries: {df.filter(pl.col('is_retry')).height:,} / {len(df):,}")
    print(f"Failure rate: {100 * df.filter(pl.col('payment_status') == 'failed').height / len(df):.1f}%")

    print("\nFailure reasons:")
    print(
        df.filter(pl.col("failure_reason").is_not_null())
        .group_by("failure_reason")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )


if __name__ == "__main__":
    main()