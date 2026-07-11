"""
Chaos injector functions.

Each function takes a Polars DataFrame, applies one type of
data quality issue, and returns the modified DataFrame plus
a manifest of what was changed.

Every injector follows the same contract:
    Input:  df (Polars DataFrame), config, seed
    Output: (modified_df, manifest_records)

Manifest records track every change for ground truth comparison.
"""

import random
from datetime import datetime, timedelta
from uuid import uuid4

import polars as pl


# ─────────────────────────────────────────────────────────
# 1. DUPLICATE INJECTOR
# ─────────────────────────────────────────────────────────


def inject_duplicates(
    df: pl.DataFrame,
    rate: float,
    id_column: str,
    timestamp_columns: list[str],
    drift_seconds: int = 5,
    modify_id: bool = True,
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Inject near-duplicate rows simulating retry logic.

    Real-world cause: payment gateway timeout → service retries →
    two records created with slightly different timestamps and
    potentially different IDs.
    """
    random.seed(seed)
    n_dupes = int(len(df) * rate)
    dupe_indices = random.sample(range(len(df)), min(n_dupes, len(df)))

    manifest = []
    dupe_rows = []

    for idx in dupe_indices:
        row = df.row(idx, named=True)
        new_row = dict(row)

        # Drift timestamps by a few seconds
        for ts_col in timestamp_columns:
            if ts_col in new_row and new_row[ts_col] is not None:
                val = new_row[ts_col]
                if isinstance(val, datetime):
                    drift = random.randint(1, drift_seconds)
                    new_row[ts_col] = val + timedelta(seconds=drift)

        # Optionally change the ID (simulates new transaction ID on retry)
        original_id = new_row[id_column]
        if modify_id:
            new_row[id_column] = str(uuid4())

        dupe_rows.append(new_row)
        manifest.append({
            "chaos_type": "duplicate",
            "table": "",  # filled by caller
            "original_row_id": original_id,
            "new_row_id": new_row[id_column],
            "column_affected": id_column,
            "original_value": str(original_id),
            "new_value": str(new_row[id_column]),
            "description": f"Near-duplicate with {drift_seconds}s max timestamp drift",
        })

    if dupe_rows:
        dupe_df = pl.DataFrame(dupe_rows, schema=df.schema)
        df = pl.concat([df, dupe_df], how="vertical_relaxed")

    return df, manifest


# ─────────────────────────────────────────────────────────
# 2. NULL CHAOS INJECTOR
# ─────────────────────────────────────────────────────────


def inject_null_chaos(
    df: pl.DataFrame,
    rate: float,
    target_columns: list[str],
    representations: list[str],
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Replace values with various null representations.

    Real-world cause: different source systems encode nulls differently.
    Old CRM: "N/A". New API: "". Mobile SDK: "null". Data warehouse: actual NULL.
    """
    random.seed(seed)
    manifest = []

    for col in target_columns:
        if col not in df.columns:
            continue

        n_corrupt = int(len(df) * rate)
        corrupt_indices = random.sample(range(len(df)), min(n_corrupt, len(df)))

        col_values = df[col].to_list()
        for idx in corrupt_indices:
            original_value = col_values[idx]
            null_repr = random.choice(representations)
            col_values[idx] = null_repr

            manifest.append({
                "chaos_type": "null_representation",
                "table": "",
                "original_row_id": "",
                "new_row_id": "",
                "column_affected": col,
                "original_value": str(original_value),
                "new_value": null_repr,
                "description": f"Null represented as '{null_repr}'",
            })

        df = df.with_columns(pl.Series(name=col, values=col_values))

    return df, manifest


# ─────────────────────────────────────────────────────────
# 3. TYPE DRIFT INJECTOR
# ─────────────────────────────────────────────────────────


def inject_type_drift(
    df: pl.DataFrame,
    rate: float,
    numeric_columns: list[str],
    currency_prefixes: list[str],
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Convert numeric values to strings with formatting artifacts.

    Real-world cause: upstream team switches from DB export to CSV export.
    Prices suddenly have dollar signs. Quantities become strings.
    European locale uses comma as decimal separator.
    """
    random.seed(seed)
    manifest = []

    for col in numeric_columns:
        if col not in df.columns:
            continue

        n_corrupt = int(len(df) * rate)
        corrupt_indices = random.sample(range(len(df)), min(n_corrupt, len(df)))

        # Cast entire column to string first
        col_values = [str(v) for v in df[col].to_list()]

        for idx in corrupt_indices:
            original = col_values[idx]
            corruption_type = random.choice([
                "currency_prefix",
                "comma_decimal",
                "extra_spaces",
                "thousands_separator",
            ])

            if corruption_type == "currency_prefix":
                prefix = random.choice(currency_prefixes)
                col_values[idx] = f"{prefix}{original}"
            elif corruption_type == "comma_decimal":
                col_values[idx] = original.replace(".", ",")
            elif corruption_type == "extra_spaces":
                col_values[idx] = f"  {original}  "
            elif corruption_type == "thousands_separator":
                try:
                    num = float(original)
                    if num > 1000:
                        col_values[idx] = f"{num:,.2f}"
                except (ValueError, TypeError):
                    pass

            manifest.append({
                "chaos_type": "type_drift",
                "table": "",
                "original_row_id": "",
                "new_row_id": "",
                "column_affected": col,
                "original_value": original,
                "new_value": col_values[idx],
                "description": f"Numeric to string: {corruption_type}",
            })

        df = df.with_columns(pl.Series(name=col, values=col_values).cast(pl.Utf8))

    return df, manifest


# ─────────────────────────────────────────────────────────
# 4. ENCODING CHAOS INJECTOR
# ─────────────────────────────────────────────────────────


def inject_encoding_chaos(
    df: pl.DataFrame,
    rate: float,
    text_columns: list[str],
    replacements: dict[str, str],
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Corrupt text with encoding mismatches.

    Real-world cause: a microservice reads a UTF-8 database as Latin-1.
    José becomes JosÃ©. García becomes GarcÃ­a. This persists for weeks
    before anyone notices because it only affects non-ASCII names.
    """
    random.seed(seed)
    manifest = []

    for col in text_columns:
        if col not in df.columns:
            continue

        n_corrupt = int(len(df) * rate)
        corrupt_indices = random.sample(range(len(df)), min(n_corrupt, len(df)))

        col_values = df[col].to_list()
        for idx in corrupt_indices:
            original = str(col_values[idx])
            corrupted = original
            for char, replacement in replacements.items():
                corrupted = corrupted.replace(char, replacement)

            if corrupted != original:
                col_values[idx] = corrupted
                manifest.append({
                    "chaos_type": "encoding",
                    "table": "",
                    "original_row_id": "",
                    "new_row_id": "",
                    "column_affected": col,
                    "original_value": original,
                    "new_value": corrupted,
                    "description": "UTF-8 read as Latin-1",
                })

        df = df.with_columns(pl.Series(name=col, values=col_values))

    return df, manifest


# ─────────────────────────────────────────────────────────
# 5. LATE ARRIVAL INJECTOR
# ─────────────────────────────────────────────────────────


def inject_late_arrivals(
    df: pl.DataFrame,
    rate: float,
    date_column: str,
    max_delay_days: int = 90,
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Shift some records' dates forward to simulate late arrival.

    Real-world cause: warehouse in São Paulo had a 3-day network outage.
    Orders placed during the outage arrive in the data pipeline days later
    with their original timestamps, mixed into newer batches.

    We add an _ingestion_delay_days column to track this.
    """
    random.seed(seed)
    manifest = []

    n_late = int(len(df) * rate)
    late_indices = random.sample(range(len(df)), min(n_late, len(df)))

    delay_values = [0] * len(df)

    for idx in late_indices:
        delay = random.randint(7, max_delay_days)
        delay_values[idx] = delay

        manifest.append({
            "chaos_type": "late_arrival",
            "table": "",
            "original_row_id": "",
            "new_row_id": "",
            "column_affected": date_column,
            "original_value": "",
            "new_value": f"+{delay} days",
            "description": f"Record arrived {delay} days late",
        })

    df = df.with_columns(
        pl.Series(name="_ingestion_delay_days", values=delay_values)
    )

    return df, manifest


# ─────────────────────────────────────────────────────────
# 6. ORPHAN RECORD INJECTOR
# ─────────────────────────────────────────────────────────


def inject_orphan_records(
    df: pl.DataFrame,
    rate: float,
    fk_column: str,
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Break foreign key references by replacing valid IDs with fake ones.

    Real-world cause: a nightly cleanup job deletes old customers,
    but their orders remain. Or a CDC event is missed and a product
    update never reaches the warehouse.
    """
    random.seed(seed)
    manifest = []

    n_orphans = int(len(df) * rate)
    orphan_indices = random.sample(range(len(df)), min(n_orphans, len(df)))

    col_values = df[fk_column].to_list()
    for idx in orphan_indices:
        original = col_values[idx]
        fake_id = f"ORPHAN-{uuid4().hex[:12]}"
        col_values[idx] = fake_id

        manifest.append({
            "chaos_type": "orphan_record",
            "table": "",
            "original_row_id": "",
            "new_row_id": "",
            "column_affected": fk_column,
            "original_value": str(original),
            "new_value": fake_id,
            "description": "FK points to non-existent parent record",
        })

    df = df.with_columns(pl.Series(name=fk_column, values=col_values))

    return df, manifest


# ─────────────────────────────────────────────────────────
# 7. BUSINESS LOGIC VIOLATION INJECTOR
# ─────────────────────────────────────────────────────────


def inject_business_logic_violations(
    df: pl.DataFrame,
    rate: float,
    violation_specs: list[dict],
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Inject impossible business states.

    Real-world cause: race conditions, timezone bugs, or
    upstream service bugs creating logically impossible records.

    violation_specs format:
    [
        {"column": "quantity", "violation": "negative", "min": -10, "max": -1},
        {"column": "total_amount", "violation": "zero"},
        {"column": "discount_amount", "violation": "exceeds_subtotal", "ref_column": "subtotal"},
    ]
    """
    random.seed(seed)
    manifest = []

    n_violations = int(len(df) * rate)

    for spec in violation_specs:
        col = spec["column"]
        if col not in df.columns:
            continue

        violation_indices = random.sample(
            range(len(df)),
            min(n_violations // len(violation_specs), len(df)),
        )

        col_values = df[col].to_list()
        violation_type = spec["violation"]

        for idx in violation_indices:
            original = col_values[idx]

            if violation_type == "negative":
                neg_val = random.uniform(spec.get("min", -100), spec.get("max", -1))
                # Preserve integer type if the column is integer
                if isinstance(original, int):
                    neg_val = int(neg_val)
                col_values[idx] = neg_val
            elif violation_type == "zero":
                col_values[idx] = 0
            elif violation_type == "exceeds_subtotal" and spec.get("ref_column"):
                ref_values = df[spec["ref_column"]].to_list()
                col_values[idx] = ref_values[idx] * random.uniform(1.5, 3.0)

            manifest.append({
                "chaos_type": "business_logic_violation",
                "table": "",
                "original_row_id": "",
                "new_row_id": "",
                "column_affected": col,
                "original_value": str(original),
                "new_value": str(col_values[idx]),
                "description": f"Violation: {violation_type}",
            })

        df = df.with_columns(pl.Series(name=col, values=col_values))

    return df, manifest


# ─────────────────────────────────────────────────────────
# 8. ZOMBIE TEST DATA INJECTOR
# ─────────────────────────────────────────────────────────


def inject_zombie_test_data(
    df: pl.DataFrame,
    count: int,
    id_column: str,
    text_columns: list[str],
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Inject obviously fake test records that QA forgot to clean up.

    Real-world cause: QA team creates test orders with names like
    "TEST USER" and emails like "test@test.com". These leak into
    production analytics and inflate metrics.
    """
    random.seed(seed)
    manifest = []

    test_names = [
        "TEST USER", "test test", "ASDF ASDF", "John Doe",
        "Jane Smith", "QA Test", "DELETE ME", "xxxxx",
        "Sample Customer", "Fake Person", "DO NOT USE",
    ]
    test_emails = [
        "test@test.com", "admin@localhost", "asdf@asdf.com",
        "noreply@example.com", "test123@test.com", "qa@internal.co",
        "delete.me@fake.com",
    ]

    zombie_rows = []
    for i in range(count):
        # Take a random existing row as template
        template_idx = random.randint(0, len(df) - 1)
        row = dict(df.row(template_idx, named=True))

        row[id_column] = f"TEST-{uuid4().hex[:8]}"

        for col in text_columns:
            if col in row:
                if "email" in col.lower():
                    row[col] = random.choice(test_emails)
                elif "name" in col.lower():
                    row[col] = random.choice(test_names)

        zombie_rows.append(row)
        manifest.append({
            "chaos_type": "zombie_test_data",
            "table": "",
            "original_row_id": "N/A",
            "new_row_id": row[id_column],
            "column_affected": "multiple",
            "original_value": "N/A",
            "new_value": "test/QA record",
            "description": f"Zombie test record with fake PII",
        })

    if zombie_rows:
        zombie_df = pl.DataFrame(zombie_rows, schema=df.schema)
        df = pl.concat([df, zombie_df], how="vertical_relaxed")

    return df, manifest


# ─────────────────────────────────────────────────────────
# 9. SCHEMA EVOLUTION INJECTOR
# ─────────────────────────────────────────────────────────


def inject_schema_evolution(
    df: pl.DataFrame,
    add_columns: list[str],
    rename_columns: dict[str, str],
    fill_rate: float = 0.3,
    seed: int = 42,
) -> tuple[pl.DataFrame, list[dict]]:
    """
    Simulate schema changes over time.

    Real-world cause: product team adds a 'promo_code' field in month 8.
    Records before month 8 have NULL for this column. Records after
    month 8 are partially filled (not every order uses a promo).

    Column renames simulate a team deciding 'customer_external_id' is
    too long and renaming it to 'cust_ext_id' without updating downstream.
    """
    random.seed(seed)
    manifest = []

    # Add new columns (partially filled — simulates mid-stream addition)
    for col_name in add_columns:
        values = []
        for i in range(len(df)):
            # First 40% of rows: NULL (column didn't exist yet)
            # Remaining 60%: 30% filled, rest NULL
            if i < len(df) * 0.4:
                values.append(None)
            elif random.random() < fill_rate:
                if "promo" in col_name:
                    values.append(random.choice([
                        "SUMMER20", "WELCOME10", "FLASH30", "VIP50",
                        "HOLIDAY25", "NEWUSER", None,
                    ]))
                elif "points" in col_name:
                    values.append(str(random.randint(0, 5000)))
                else:
                    values.append(f"ref_{random.randint(1000, 9999)}")
            else:
                values.append(None)

        df = df.with_columns(pl.Series(name=col_name, values=values))
        manifest.append({
            "chaos_type": "schema_evolution",
            "table": "",
            "original_row_id": "N/A",
            "new_row_id": "N/A",
            "column_affected": col_name,
            "original_value": "column_did_not_exist",
            "new_value": "column_added",
            "description": f"New column '{col_name}' added mid-stream (first 40% null)",
        })

    # Rename columns
    for old_name, new_name in rename_columns.items():
        if old_name in df.columns:
            df = df.rename({old_name: new_name})
            manifest.append({
                "chaos_type": "schema_evolution",
                "table": "",
                "original_row_id": "N/A",
                "new_row_id": "N/A",
                "column_affected": old_name,
                "original_value": old_name,
                "new_value": new_name,
                "description": f"Column renamed from '{old_name}' to '{new_name}'",
            })

    return df, manifest
