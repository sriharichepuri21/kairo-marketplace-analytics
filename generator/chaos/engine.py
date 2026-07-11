"""
Chaos engine — orchestrates applying multiple chaos types
to each table in the data layer.

Each table gets a tailored set of chaos injections based on
what would realistically happen to that type of data.
"""

import shutil
from pathlib import Path

import polars as pl

from generator.chaos.config import ChaosConfig
from generator.chaos.injectors import (
    inject_business_logic_violations,
    inject_duplicates,
    inject_encoding_chaos,
    inject_late_arrivals,
    inject_null_chaos,
    inject_orphan_records,
    inject_schema_evolution,
    inject_type_drift,
    inject_zombie_test_data,
)


RAW_DATA_DIR = Path("raw_data")
CLEAN_BACKUP_DIR = Path("raw_data_clean")
MANIFEST_DIR = Path("chaos_manifest")


def _save_manifest(manifest: list[dict], table_name: str) -> None:
    """Save manifest records to Parquet."""
    if not manifest:
        return
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    for record in manifest:
        record["table"] = table_name
    df = pl.DataFrame(manifest)
    path = MANIFEST_DIR / f"{table_name}_manifest.parquet"
    df.write_parquet(path)
    print(f"    ✓ Manifest: {len(manifest)} changes logged to {path}")


def _backup_clean_data() -> None:
    """Copy raw_data/ to raw_data_clean/ before applying chaos."""
    if CLEAN_BACKUP_DIR.exists():
        shutil.rmtree(CLEAN_BACKUP_DIR)
    shutil.copytree(RAW_DATA_DIR, CLEAN_BACKUP_DIR)
    print(f"  ✓ Clean data backed up to {CLEAN_BACKUP_DIR}/")


def apply_chaos_to_customers(config: ChaosConfig) -> None:
    """Apply chaos to the customers table."""
    print("\n─── Customers ───")
    path = RAW_DATA_DIR / "customers" / "customers.parquet"
    df = pl.read_parquet(path)
    print(f"  Loaded {len(df):,} rows")
    all_manifest: list[dict] = []

    if config.duplicates.enabled:
        df, m = inject_duplicates(
            df, config.duplicates.rate, "customer_id",
            ["created_at", "updated_at"], config.duplicates.timestamp_drift_seconds,
            config.duplicates.modify_id, config.seed,
        )
        all_manifest.extend(m)
        print(f"    + Duplicates: {len(m)} injected")

    if config.null_chaos.enabled:
        df, m = inject_null_chaos(
            df, config.null_chaos.rate,
            ["email", "first_name", "last_name", "signup_channel"],
            config.null_chaos.representations, config.seed + 1,
        )
        all_manifest.extend(m)
        print(f"    + Null chaos: {len(m)} values corrupted")

    if config.encoding.enabled:
        df, m = inject_encoding_chaos(
            df, config.encoding.rate,
            ["first_name", "last_name", "email"],
            config.encoding.replacements, config.seed + 2,
        )
        all_manifest.extend(m)
        print(f"    + Encoding: {len(m)} values corrupted")

    if config.zombie_test_data.enabled:
        df, m = inject_zombie_test_data(
            df, config.zombie_test_data.count, "customer_id",
            ["email", "first_name", "last_name"], config.seed + 3,
        )
        all_manifest.extend(m)
        print(f"    + Zombie test data: {len(m)} records injected")

    if config.schema_evolution.enabled:
        df, m = inject_schema_evolution(
            df, config.schema_evolution.add_columns,
            {"customer_external_id": "cust_ext_id"}, seed=config.seed + 4,
        )
        all_manifest.extend(m)
        print(f"    + Schema evolution: {len(m)} changes")

    df.write_parquet(path)
    print(f"  ✓ Wrote {len(df):,} messy rows back to {path}")
    _save_manifest(all_manifest, "customers")


def apply_chaos_to_orders(config: ChaosConfig) -> None:
    """Apply chaos to the orders table."""
    print("\n─── Orders ───")
    path = RAW_DATA_DIR / "orders" / "orders.parquet"
    df = pl.read_parquet(path)
    print(f"  Loaded {len(df):,} rows")
    all_manifest: list[dict] = []

    if config.duplicates.enabled:
        df, m = inject_duplicates(
            df, config.duplicates.rate, "order_id",
            ["order_placed_at", "created_at", "updated_at"],
            config.duplicates.timestamp_drift_seconds,
            config.duplicates.modify_id, config.seed + 10,
        )
        all_manifest.extend(m)
        print(f"    + Duplicates: {len(m)} injected")

    if config.null_chaos.enabled:
        df, m = inject_null_chaos(
            df, config.null_chaos.rate,
            ["order_number", "currency"],
            config.null_chaos.representations, config.seed + 11,
        )
        all_manifest.extend(m)
        print(f"    + Null chaos: {len(m)} values corrupted")

    if config.business_logic.enabled:
        df, m = inject_business_logic_violations(
            df, config.business_logic.rate,
            [
                {"column": "shipping_cost", "violation": "negative", "min": -20.0, "max": -0.01},
                {"column": "discount_amount", "violation": "exceeds_subtotal", "ref_column": "subtotal"},
            ],
            config.seed + 14,
        )
        all_manifest.extend(m)
        print(f"    + Business logic violations: {len(m)} injected")
        
    if config.type_drift.enabled:
        df, m = inject_type_drift(
            df, config.type_drift.rate,
            ["total_amount", "subtotal", "discount_amount", "shipping_cost"],
            config.type_drift.currency_prefixes, config.seed + 12,
        )
        all_manifest.extend(m)
        print(f"    + Type drift: {len(m)} values corrupted")

    if config.late_arrival.enabled:
        df, m = inject_late_arrivals(
            df, config.late_arrival.rate, "order_placed_at",
            config.late_arrival.max_delay_days, config.seed + 13,
        )
        all_manifest.extend(m)
        print(f"    + Late arrivals: {len(m)} records delayed")


    df.write_parquet(path)
    print(f"  ✓ Wrote {len(df):,} messy rows back to {path}")
    _save_manifest(all_manifest, "orders")


def apply_chaos_to_order_items(config: ChaosConfig) -> None:
    """Apply chaos to the order_items table."""
    print("\n─── Order Items ───")
    path = RAW_DATA_DIR / "order_items" / "order_items.parquet"
    df = pl.read_parquet(path)
    print(f"  Loaded {len(df):,} rows")
    all_manifest: list[dict] = []

    if config.orphan_records.enabled:
        df, m = inject_orphan_records(
            df, config.orphan_records.rate, "order_id", config.seed + 20,
        )
        all_manifest.extend(m)
        print(f"    + Orphan records: {len(m)} broken FKs")

    if config.business_logic.enabled:
        df, m = inject_business_logic_violations(
            df, config.business_logic.rate,
            [
                {"column": "quantity", "violation": "negative", "min": -5, "max": -1},
            ],
            config.seed + 22,
        )
        all_manifest.extend(m)
        print(f"    + Business logic violations: {len(m)} injected")

    if config.type_drift.enabled:
        df, m = inject_type_drift(
            df, config.type_drift.rate,
            ["unit_price", "unit_cost", "line_total"],
            config.type_drift.currency_prefixes, config.seed + 21,
        )
        all_manifest.extend(m)
        print(f"    + Type drift: {len(m)} values corrupted")


    df.write_parquet(path)
    print(f"  ✓ Wrote {len(df):,} messy rows back to {path}")
    _save_manifest(all_manifest, "order_items")


def apply_chaos_to_payments(config: ChaosConfig) -> None:
    """Apply chaos to the payments table."""
    print("\n─── Payments ───")
    path = RAW_DATA_DIR / "payments" / "payments.parquet"
    df = pl.read_parquet(path)
    print(f"  Loaded {len(df):,} rows")
    all_manifest: list[dict] = []

    if config.duplicates.enabled:
        df, m = inject_duplicates(
            df, config.duplicates.rate * 2,  # payments have HIGHER dupe rate
            "payment_id", ["attempted_at", "created_at"],
            drift_seconds=3, modify_id=True, seed=config.seed + 30,
        )
        all_manifest.extend(m)
        print(f"    + Duplicates: {len(m)} injected (elevated rate — payment retries)")

    if config.null_chaos.enabled:
        df, m = inject_null_chaos(
            df, config.null_chaos.rate,
            ["card_brand", "failure_reason"],
            config.null_chaos.representations, config.seed + 31,
        )
        all_manifest.extend(m)
        print(f"    + Null chaos: {len(m)} values corrupted")

    if config.orphan_records.enabled:
        df, m = inject_orphan_records(
            df, config.orphan_records.rate, "order_id", config.seed + 32,
        )
        all_manifest.extend(m)
        print(f"    + Orphan records: {len(m)} broken FKs")

    df.write_parquet(path)
    print(f"  ✓ Wrote {len(df):,} messy rows back to {path}")
    _save_manifest(all_manifest, "payments")


def apply_chaos_to_shipments(config: ChaosConfig) -> None:
    """Apply chaos to the shipments table."""
    print("\n─── Shipments ───")
    path = RAW_DATA_DIR / "shipments" / "shipments.parquet"
    df = pl.read_parquet(path)
    print(f"  Loaded {len(df):,} rows")
    all_manifest: list[dict] = []

    if config.duplicates.enabled:
        df, m = inject_duplicates(
            df, config.duplicates.rate, "shipment_id",
            ["shipped_at", "created_at"], seed=config.seed + 40,
        )
        all_manifest.extend(m)
        print(f"    + Duplicates: {len(m)} injected")

    if config.null_chaos.enabled:
        df, m = inject_null_chaos(
            df, config.null_chaos.rate,
            ["tracking_number", "carrier"],
            config.null_chaos.representations, config.seed + 41,
        )
        all_manifest.extend(m)
        print(f"    + Null chaos: {len(m)} values corrupted")

    df.write_parquet(path)
    print(f"  ✓ Wrote {len(df):,} messy rows back to {path}")
    _save_manifest(all_manifest, "shipments")


def apply_chaos_to_reviews(config: ChaosConfig) -> None:
    """Apply chaos to the reviews table."""
    print("\n─── Reviews ───")
    path = RAW_DATA_DIR / "reviews" / "reviews.parquet"
    df = pl.read_parquet(path)
    print(f"  Loaded {len(df):,} rows")
    all_manifest: list[dict] = []

    if config.encoding.enabled:
        df, m = inject_encoding_chaos(
            df, config.encoding.rate,
            ["title", "review_text"],
            config.encoding.replacements, config.seed + 50,
        )
        all_manifest.extend(m)
        print(f"    + Encoding: {len(m)} values corrupted")

    if config.orphan_records.enabled:
        df, m = inject_orphan_records(
            df, config.orphan_records.rate, "product_id", config.seed + 51,
        )
        all_manifest.extend(m)
        print(f"    + Orphan records: {len(m)} broken FKs")

    df.write_parquet(path)
    print(f"  ✓ Wrote {len(df):,} messy rows back to {path}")
    _save_manifest(all_manifest, "reviews")


def run_chaos_engine(config: ChaosConfig | None = None) -> None:
    """
    Run the full chaos engine across all tables.

    Steps:
    1. Back up clean data to raw_data_clean/
    2. Apply table-specific chaos to raw_data/
    3. Write manifests to chaos_manifest/
    """
    if config is None:
        config = ChaosConfig()

    print("=" * 70)
    print("CHAOS ENGINE — Injecting production-realistic data quality issues")
    print("=" * 70)

    print(f"\nSeed: {config.seed}")
    print(f"Backing up clean data...")
    _backup_clean_data()

    apply_chaos_to_customers(config)
    apply_chaos_to_orders(config)
    apply_chaos_to_order_items(config)
    apply_chaos_to_payments(config)
    apply_chaos_to_shipments(config)
    apply_chaos_to_reviews(config)

    print("\n" + "=" * 70)
    print("CHAOS ENGINE COMPLETE")
    print("=" * 70)
    print(f"\n  Clean backup:  {CLEAN_BACKUP_DIR}/")
    print(f"  Messy data:    {RAW_DATA_DIR}/")
    print(f"  Manifests:     {MANIFEST_DIR}/")
    print(f"\n  Your dbt pipeline should now read from {RAW_DATA_DIR}/")
    print(f"  Ground truth for scoring lives in {CLEAN_BACKUP_DIR}/")