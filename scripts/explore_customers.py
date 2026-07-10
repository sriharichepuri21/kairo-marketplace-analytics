"""
Explore the generated customer data using DuckDB.

This proves the round trip: generator -> Parquet -> SQL query.
Also demonstrates DuckDB's ability to query Parquet files directly.

Run: python scripts/explore_customers.py
"""

from pathlib import Path

import duckdb


PARQUET_PATH = Path("raw_data/customers/customers.parquet")


def main() -> None:
    if not PARQUET_PATH.exists():
        raise FileNotFoundError(
            f"Parquet file not found at {PARQUET_PATH}. "
            "Run 'python scripts/generate_customers.py' first."
        )

    # DuckDB can query Parquet files directly — no import step
    conn = duckdb.connect()

    print("=" * 70)
    print("Query 1: Row count and file overview")
    print("=" * 70)
    result = conn.execute(f"""
        SELECT
            COUNT(*) AS total_customers,
            COUNT(DISTINCT customer_id) AS unique_customer_ids,
            MIN(signup_date) AS earliest_signup,
            MAX(signup_date) AS latest_signup
        FROM '{PARQUET_PATH}'
    """).pl()
    print(result)
    print()

    print("=" * 70)
    print("Query 2: Customers per region + segment")
    print("=" * 70)
    result = conn.execute(f"""
        SELECT
            region,
            segment,
            COUNT(*) AS customer_count,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY region), 2)
                AS pct_within_region
        FROM '{PARQUET_PATH}'
        GROUP BY region, segment
        ORDER BY region, customer_count DESC
    """).pl()
    print(result)
    print()

    print("=" * 70)
    print("Query 3: Signups by month (last 12 months of data)")
    print("=" * 70)
    result = conn.execute(f"""
        SELECT
            DATE_TRUNC('month', signup_date) AS signup_month,
            COUNT(*) AS new_customers
        FROM '{PARQUET_PATH}'
        WHERE signup_date >= (
            SELECT MAX(signup_date) - INTERVAL 12 MONTH
            FROM '{PARQUET_PATH}'
        )
        GROUP BY signup_month
        ORDER BY signup_month
    """).pl()
    print(result)
    print()

    print("=" * 70)
    print("Query 4: Country breakdown within EU region")
    print("=" * 70)
    result = conn.execute(f"""
        SELECT
            country_code,
            COUNT(*) AS customers,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_eu
        FROM '{PARQUET_PATH}'
        WHERE region = 'EU'
        GROUP BY country_code
        ORDER BY customers DESC
    """).pl()
    print(result)
    print()

    print("=" * 70)
    print("Query 5: Signup channel effectiveness (proxy)")
    print("=" * 70)
    result = conn.execute(f"""
        SELECT
            signup_channel,
            COUNT(*) AS customer_count,
            SUM(CASE WHEN segment = 'whale' THEN 1 ELSE 0 END) AS whales,
            ROUND(100.0 * SUM(CASE WHEN segment = 'whale' THEN 1 ELSE 0 END)
                        / COUNT(*), 2) AS whale_pct
        FROM '{PARQUET_PATH}'
        GROUP BY signup_channel
        ORDER BY whale_pct DESC
    """).pl()
    print(result)
    print()

    print("✅ End-to-end round trip complete.")
    print("   Generator -> Parquet -> DuckDB SQL -> analytics results.")


if __name__ == "__main__":
    main()