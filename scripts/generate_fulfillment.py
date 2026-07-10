"""
Generate shipments, returns, and reviews from existing orders.

All three depend on delivered orders, so we generate them together.

Usage:
    python scripts/generate_fulfillment.py
"""

from datetime import datetime
from pathlib import Path
from time import perf_counter

import duckdb
import polars as pl

from generator.entities.shipment import OrderShipmentInfo, generate_shipments
from generator.entities.returns import DeliveredItemInfo, generate_returns
from generator.entities.review import DeliveredItemReviewInfo, generate_reviews
from generator.writers.parquet_writer import write_entities_to_parquet


SEED = 42
ORDERS_PATH = Path("raw_data/orders/orders.parquet")
ITEMS_PATH = Path("raw_data/order_items/order_items.parquet")

SHIPMENTS_OUTPUT = Path("raw_data/shipments/shipments.parquet")
RETURNS_OUTPUT = Path("raw_data/returns/returns.parquet")
REVIEWS_OUTPUT = Path("raw_data/reviews/reviews.parquet")


def main() -> None:
    conn = duckdb.connect()

    # ─────────────────────────────────────────────────────
    # 1. SHIPMENTS
    # ─────────────────────────────────────────────────────
    print("Loading orders for shipments...")
    rows = conn.execute(f"""
        SELECT order_id, order_status, order_placed_at, total_amount, region
        FROM '{ORDERS_PATH}'
    """).fetchall()

    order_infos = [
        OrderShipmentInfo(
            order_id=r[0], order_status=r[1], order_placed_at=r[2],
            total_amount=r[3], region=r[4],
        )
        for r in rows
    ]
    print(f"  ✓ Loaded {len(order_infos):,} orders")

    print(f"\nGenerating shipments (seed={SEED})...")
    start = perf_counter()
    shipments = generate_shipments(order_infos, seed=SEED)
    elapsed = perf_counter() - start
    print(f"  ✓ Generated {len(shipments):,} shipments in {elapsed:.2f}s")

    df_ship = write_entities_to_parquet(shipments, SHIPMENTS_OUTPUT)
    print(f"  ✓ Wrote to {SHIPMENTS_OUTPUT} ({SHIPMENTS_OUTPUT.stat().st_size / 1024:.1f} KB)")

    # Build a lookup of delivered order dates for returns and reviews
    delivered_dates: dict[str, datetime] = {}
    for s in shipments:
        if s.delivered_at is not None:
            delivered_dates[s.order_id] = s.delivered_at

    # ─────────────────────────────────────────────────────
    # 2. RETURNS (need delivered items)
    # ─────────────────────────────────────────────────────
    print("\nLoading delivered order items for returns...")
    item_rows = conn.execute(f"""
        SELECT
            oi.order_id,
            oi.order_item_id,
            o.customer_id,
            oi.product_id,
            oi.category,
            oi.line_total
        FROM '{ITEMS_PATH}' oi
        JOIN '{ORDERS_PATH}' o ON oi.order_id = o.order_id
        WHERE o.order_status = 'delivered'
    """).fetchall()

    delivered_items = []
    for r in item_rows:
        delivery_dt = delivered_dates.get(r[0])
        if delivery_dt:
            delivered_items.append(DeliveredItemInfo(
                order_id=r[0], order_item_id=r[1], customer_id=r[2],
                product_id=r[3], category=r[4], line_total=r[5],
                delivered_at=delivery_dt,
            ))

    print(f"  ✓ Found {len(delivered_items):,} delivered items")

    print(f"\nGenerating returns (seed={SEED})...")
    start = perf_counter()
    returns = generate_returns(delivered_items, seed=SEED)
    elapsed = perf_counter() - start
    print(f"  ✓ Generated {len(returns):,} returns in {elapsed:.2f}s")

    df_ret = write_entities_to_parquet(returns, RETURNS_OUTPUT)
    print(f"  ✓ Wrote to {RETURNS_OUTPUT} ({RETURNS_OUTPUT.stat().st_size / 1024:.1f} KB)")

    # ─────────────────────────────────────────────────────
    # 3. REVIEWS (need delivered items with seller_id)
    # ─────────────────────────────────────────────────────
    print("\nLoading delivered items for reviews...")
    review_rows = conn.execute(f"""
        SELECT
            oi.order_id,
            oi.order_item_id,
            oi.product_id,
            o.customer_id,
            oi.seller_id
        FROM '{ITEMS_PATH}' oi
        JOIN '{ORDERS_PATH}' o ON oi.order_id = o.order_id
        WHERE o.order_status = 'delivered'
    """).fetchall()

    review_items = []
    for r in review_rows:
        delivery_dt = delivered_dates.get(r[0])
        if delivery_dt:
            review_items.append(DeliveredItemReviewInfo(
                order_id=r[0], order_item_id=r[1], product_id=r[2],
                customer_id=r[3], seller_id=r[4],
                delivered_at=delivery_dt,
            ))

    print(f"  ✓ Found {len(review_items):,} items eligible for review")

    print(f"\nGenerating reviews (seed={SEED})...")
    start = perf_counter()
    reviews = generate_reviews(review_items, seed=SEED)
    elapsed = perf_counter() - start
    print(f"  ✓ Generated {len(reviews):,} reviews in {elapsed:.2f}s")

    df_rev = write_entities_to_parquet(reviews, REVIEWS_OUTPUT)
    print(f"  ✓ Wrote to {REVIEWS_OUTPUT} ({REVIEWS_OUTPUT.stat().st_size / 1024:.1f} KB)")

    # ─────────────────────────────────────────────────────
    # ANALYTICS
    # ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SHIPMENT ANALYTICS")
    print("=" * 70)

    print("\nCarrier distribution:")
    print(df_ship.group_by("carrier").agg(pl.len().alias("count")).sort("count", descending=True))

    print("\nShipping method:")
    print(df_ship.group_by("shipping_method").agg(pl.len().alias("count")).sort("count", descending=True))

    delivered_ships = df_ship.filter(pl.col("status") == "delivered")
    on_time = delivered_ships.filter(pl.col("delay_days") == 0).height
    total_delivered = delivered_ships.height
    print(f"\nOn-time delivery rate: {100 * on_time / total_delivered:.1f}% ({on_time:,} / {total_delivered:,})")

    print("\n" + "=" * 70)
    print("RETURN ANALYTICS")
    print("=" * 70)

    print(f"\nTotal returns: {len(df_ret):,}")
    print(f"Overall return rate: {100 * len(df_ret) / len(delivered_items):.1f}%")

    print("\nReturn rate by category:")
    print(
        df_ret.group_by("category")
        .agg(pl.len().alias("returns"))
        .sort("returns", descending=True)
    )

    print("\nReturn reason:")
    print(df_ret.group_by("return_reason").agg(pl.len().alias("count")).sort("count", descending=True))

    print("\n" + "=" * 70)
    print("REVIEW ANALYTICS")
    print("=" * 70)

    print(f"\nTotal reviews: {len(df_rev):,}")
    print(f"Review rate: {100 * len(df_rev) / len(review_items):.1f}%")

    print("\nRating distribution:")
    print(df_rev.group_by("rating").agg(pl.len().alias("count")).sort("rating", descending=True))

    print(f"\nAvg rating: {df_rev['rating'].mean():.2f}")


if __name__ == "__main__":
    main()