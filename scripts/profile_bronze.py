"""
Bronze Layer Data Profiling

This script explores every Bronze table and reports data quality issues.
A real BIE does this BEFORE writing any cleaning logic.

The output of this script becomes the basis for Silver layer design decisions.

Usage:
    python scripts/profile_bronze.py
"""

from pathlib import Path

import duckdb


DB_PATH = Path("warehouse/kairo.duckdb")
RAW_DIR = Path("raw_data")


def get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH))


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_subheader(title: str) -> None:
    print(f"\n  --- {title} ---")


def profile_table(conn: duckdb.DuckDBPyConnection, name: str, path: str) -> None:
    """Run a comprehensive profile on one table."""

    print_header(f"PROFILING: {name.upper()}")

    # Row count
    result = conn.execute(f"SELECT COUNT(*) AS rows FROM read_parquet('{path}')").fetchone()
    total_rows = result[0]
    print(f"\n  Total rows: {total_rows:,}")

    # Column info
    print_subheader("Column types")
    cols = conn.execute(f"""
        SELECT column_name, column_type
        FROM (DESCRIBE SELECT * FROM read_parquet('{path}'))
    """).fetchall()
    for col_name, col_type in cols:
        print(f"    {col_name:<35} {col_type}")

    return total_rows


def profile_customers(conn: duckdb.DuckDBPyConnection) -> None:
    path = f"{RAW_DIR}/customers/customers.parquet"
    total = profile_table(conn, "customers", path)

    # Duplicate check
    print_subheader("Duplicate detection")
    result = conn.execute(f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT customer_id) AS unique_ids,
            COUNT(*) - COUNT(DISTINCT customer_id) AS duplicate_count
        FROM read_parquet('{path}')
    """).fetchone()
    print(f"    Total rows:     {result[0]:,}")
    print(f"    Unique IDs:     {result[1]:,}")
    print(f"    Duplicates:     {result[2]:,}")

    # Null representation scan
    print_subheader("Null representations in 'email' column")
    result = conn.execute(f"""
        SELECT email, COUNT(*) AS occurrences
        FROM read_parquet('{path}')
        WHERE email IN ('N/A', '', 'NULL', 'null', 'None', '-', 'n/a', 'NA', ' ', '  ')
           OR email IS NULL
        GROUP BY email
        ORDER BY occurrences DESC
    """).pl()
    if len(result) > 0:
        print(result)
    else:
        print("    No null representations found in email")

    print_subheader("Null representations in 'first_name' column")
    result = conn.execute(f"""
        SELECT first_name, COUNT(*) AS occurrences
        FROM read_parquet('{path}')
        WHERE first_name IN ('N/A', '', 'NULL', 'null', 'None', '-', 'n/a', 'NA', ' ', '  ')
           OR first_name IS NULL
        GROUP BY first_name
        ORDER BY occurrences DESC
    """).pl()
    if len(result) > 0:
        print(result)
    else:
        print("    No null representations found in first_name")

    print_subheader("Null representations in 'signup_channel' column")
    result = conn.execute(f"""
        SELECT signup_channel, COUNT(*) AS occurrences
        FROM read_parquet('{path}')
        WHERE signup_channel IN ('N/A', '', 'NULL', 'null', 'None', '-', 'n/a', 'NA', ' ', '  ')
           OR signup_channel IS NULL
        GROUP BY signup_channel
        ORDER BY occurrences DESC
    """).pl()
    if len(result) > 0:
        print(result)
    else:
        print("    No null representations found in signup_channel")

    # Zombie test data detection
    print_subheader("Zombie / test data detection")
    result = conn.execute(f"""
        SELECT customer_id, first_name, last_name, email
        FROM read_parquet('{path}')
        WHERE customer_id LIKE 'TEST%'
           OR email LIKE '%test@test%'
           OR email LIKE '%@localhost%'
           OR email LIKE '%asdf%'
           OR first_name IN ('TEST USER', 'test test', 'ASDF ASDF', 'QA Test',
                            'DELETE ME', 'xxxxx', 'DO NOT USE')
        LIMIT 10
    """).pl()
    print(f"    Zombie records found: {len(result)}")
    if len(result) > 0:
        print(result)

    # Schema evolution check
    print_subheader("Schema evolution — extra columns")
    for col in ['promo_code', 'loyalty_points', 'referral_source', 'cust_ext_id']:
        try:
            result = conn.execute(f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT({col}) AS non_null,
                    ROUND(100.0 * COUNT({col}) / COUNT(*), 1) AS fill_rate_pct
                FROM read_parquet('{path}')
            """).fetchone()
            print(f"    Column '{col}': {result[1]:,} / {result[0]:,} filled ({result[2]}%)")
        except Exception:
            print(f"    Column '{col}': does not exist")

    # Check if original column was renamed
    print_subheader("Column rename check")
    try:
        conn.execute(f"SELECT customer_external_id FROM read_parquet('{path}') LIMIT 1")
        print("    'customer_external_id' exists (original name)")
    except Exception:
        print("    'customer_external_id' MISSING — likely renamed")
    try:
        conn.execute(f"SELECT cust_ext_id FROM read_parquet('{path}') LIMIT 1")
        print("    'cust_ext_id' exists (renamed version)")
    except Exception:
        print("    'cust_ext_id' does not exist")


def profile_orders(conn: duckdb.DuckDBPyConnection) -> None:
    path = f"{RAW_DIR}/orders/orders.parquet"
    total = profile_table(conn, "orders", path)

    # Duplicate check
    print_subheader("Duplicate detection")
    result = conn.execute(f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT order_id) AS unique_ids,
            COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_count
        FROM read_parquet('{path}')
    """).fetchone()
    print(f"    Total rows:     {result[0]:,}")
    print(f"    Unique IDs:     {result[1]:,}")
    print(f"    Duplicates:     {result[2]:,}")

    # Type drift detection — check if numeric columns became strings
    print_subheader("Type drift detection (numeric columns)")
    for col in ['total_amount', 'subtotal', 'discount_amount', 'shipping_cost']:
        try:
            col_type = conn.execute(f"""
                SELECT typeof({col}) FROM read_parquet('{path}') LIMIT 1
            """).fetchone()[0]
            print(f"    {col}: type is {col_type}")

            if 'VARCHAR' in col_type.upper() or 'TEXT' in col_type.upper():
                # Sample corrupted values
                sample = conn.execute(f"""
                    SELECT DISTINCT {col}
                    FROM read_parquet('{path}')
                    WHERE {col} NOT GLOB '[0-9]*'
                      AND {col} NOT GLOB '-[0-9]*'
                    LIMIT 5
                """).fetchall()
                if sample:
                    print(f"      Sample corrupted values: {[s[0] for s in sample]}")
        except Exception as e:
            print(f"    {col}: error — {e}")

    # Null representations in order_number
    print_subheader("Null representations in 'order_number'")
    result = conn.execute(f"""
        SELECT order_number, COUNT(*) AS occurrences
        FROM read_parquet('{path}')
        WHERE order_number IN ('N/A', '', 'NULL', 'null', 'None', '-', 'n/a', 'NA', ' ', '  ')
           OR order_number IS NULL
        GROUP BY order_number
        ORDER BY occurrences DESC
    """).pl()
    if len(result) > 0:
        print(result)
    else:
        print("    No null representations found")

    # Late arrival detection
    print_subheader("Late arrival detection")
    try:
        result = conn.execute(f"""
            SELECT
                COUNT(*) AS total_late,
                MIN(_ingestion_delay_days) AS min_delay,
                MAX(_ingestion_delay_days) AS max_delay,
                ROUND(AVG(_ingestion_delay_days), 1) AS avg_delay
            FROM read_parquet('{path}')
            WHERE _ingestion_delay_days > 0
        """).fetchone()
        print(f"    Late records:   {result[0]:,}")
        print(f"    Delay range:    {result[1]} — {result[2]} days")
        print(f"    Avg delay:      {result[3]} days")
    except Exception:
        print("    No _ingestion_delay_days column found")

    # Business logic violations
    print_subheader("Business logic violations")
    try:
        result = conn.execute(f"""
            SELECT COUNT(*) FROM read_parquet('{path}')
            WHERE CAST(shipping_cost AS DOUBLE) < 0
        """).fetchone()
        print(f"    Negative shipping_cost: {result[0]:,}")
    except Exception:
        print("    Cannot check shipping_cost (may be string type)")


def profile_order_items(conn: duckdb.DuckDBPyConnection) -> None:
    path = f"{RAW_DIR}/order_items/order_items.parquet"
    total = profile_table(conn, "order_items", path)

    # Orphan records
    print_subheader("Orphan record detection")
    orders_path = f"{RAW_DIR}/orders/orders.parquet"
    result = conn.execute(f"""
        SELECT COUNT(*) AS orphan_items
        FROM read_parquet('{path}') oi
        LEFT JOIN read_parquet('{orders_path}') o ON oi.order_id = o.order_id
        WHERE o.order_id IS NULL
    """).fetchone()
    print(f"    Items with no matching order: {result[0]:,}")

    # FK check for orphan-injected IDs
    print_subheader("Orphan ID pattern check")
    result = conn.execute(f"""
        SELECT order_id, COUNT(*) AS cnt
        FROM read_parquet('{path}')
        WHERE order_id LIKE 'ORPHAN%'
        GROUP BY order_id
        LIMIT 5
    """).pl()
    if len(result) > 0:
        print(f"    ORPHAN-prefixed order_ids found: {len(result)}")
        print(result)
    else:
        print("    No ORPHAN-prefixed IDs found")

    # Negative quantities
    print_subheader("Negative quantities")
    result = conn.execute(f"""
        SELECT COUNT(*) AS negative_qty
        FROM read_parquet('{path}')
        WHERE quantity < 0
    """).fetchone()
    print(f"    Rows with negative quantity: {result[0]:,}")

    # Type drift
    print_subheader("Type drift in price columns")
    for col in ['unit_price', 'unit_cost', 'line_total']:
        col_type = conn.execute(f"""
            SELECT typeof({col}) FROM read_parquet('{path}') LIMIT 1
        """).fetchone()[0]
        print(f"    {col}: type is {col_type}")


def profile_payments(conn: duckdb.DuckDBPyConnection) -> None:
    path = f"{RAW_DIR}/payments/payments.parquet"
    total = profile_table(conn, "payments", path)

    # Duplicates (elevated rate for payments)
    print_subheader("Duplicate detection")
    result = conn.execute(f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT payment_id) AS unique_ids,
            COUNT(*) - COUNT(DISTINCT payment_id) AS duplicate_count
        FROM read_parquet('{path}')
    """).fetchone()
    print(f"    Total rows:     {result[0]:,}")
    print(f"    Unique IDs:     {result[1]:,}")
    print(f"    Duplicates:     {result[2]:,}")

    # Orphan orders
    print_subheader("Orphan order references")
    result = conn.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{path}')
        WHERE order_id LIKE 'ORPHAN%'
    """).fetchone()
    print(f"    Payments with ORPHAN order_id: {result[0]:,}")

    # Null representations in card_brand
    print_subheader("Null chaos in 'card_brand'")
    result = conn.execute(f"""
        SELECT card_brand, COUNT(*) AS cnt
        FROM read_parquet('{path}')
        WHERE card_brand IN ('N/A', '', 'NULL', 'null', 'None', '-', 'n/a', 'NA', ' ', '  ')
        GROUP BY card_brand
        ORDER BY cnt DESC
    """).pl()
    if len(result) > 0:
        print(result)
    else:
        print("    No null representations found")


def profile_shipments(conn: duckdb.DuckDBPyConnection) -> None:
    path = f"{RAW_DIR}/shipments/shipments.parquet"
    total = profile_table(conn, "shipments", path)

    # Duplicates
    print_subheader("Duplicate detection")
    result = conn.execute(f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT shipment_id) AS unique_ids,
            COUNT(*) - COUNT(DISTINCT shipment_id) AS duplicate_count
        FROM read_parquet('{path}')
    """).fetchone()
    print(f"    Total rows:     {result[0]:,}")
    print(f"    Unique IDs:     {result[1]:,}")
    print(f"    Duplicates:     {result[2]:,}")

    # Null representations in tracking_number
    print_subheader("Null chaos in 'tracking_number'")
    result = conn.execute(f"""
        SELECT tracking_number, COUNT(*) AS cnt
        FROM read_parquet('{path}')
        WHERE tracking_number IN ('N/A', '', 'NULL', 'null', 'None', '-', 'n/a', 'NA', ' ', '  ')
        GROUP BY tracking_number
        ORDER BY cnt DESC
    """).pl()
    if len(result) > 0:
        print(result)
    else:
        print("    No null representations found")


def profile_reviews(conn: duckdb.DuckDBPyConnection) -> None:
    path = f"{RAW_DIR}/reviews/reviews.parquet"
    total = profile_table(conn, "reviews", path)

    # Orphan products
    print_subheader("Orphan product references")
    result = conn.execute(f"""
        SELECT COUNT(*) FROM read_parquet('{path}')
        WHERE product_id LIKE 'ORPHAN%'
    """).fetchone()
    print(f"    Reviews with ORPHAN product_id: {result[0]:,}")

    # Rating distribution (should still be J-curve)
    print_subheader("Rating distribution")
    result = conn.execute(f"""
        SELECT rating, COUNT(*) AS cnt,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
        FROM read_parquet('{path}')
        GROUP BY rating
        ORDER BY rating DESC
    """).pl()
    print(result)


def main() -> None:
    conn = get_conn()

    print("=" * 70)
    print("  BRONZE LAYER DATA PROFILING")
    print("  Discovering data quality issues before building Silver")
    print("=" * 70)

    profile_customers(conn)
    profile_orders(conn)
    profile_order_items(conn)
    profile_payments(conn)
    profile_shipments(conn)
    profile_reviews(conn)

    print("\n" + "=" * 70)
    print("  PROFILING COMPLETE")
    print("=" * 70)
    print("\n  Use these findings to design Silver layer cleaning logic.")
    print("  Document each decision in docs/data_quality_assessment.md")


if __name__ == "__main__":
    main()