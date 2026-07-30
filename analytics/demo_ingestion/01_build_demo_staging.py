from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_PATHS = {
    "customers": (
        PROJECT_ROOT
        / "raw_data_clean"
        / "customers"
        / "customers.parquet"
    ),
    "products": (
        PROJECT_ROOT
        / "raw_data_clean"
        / "products"
        / "products.parquet"
    ),
    "orders": (
        PROJECT_ROOT
        / "raw_data_clean"
        / "orders"
        / "orders.parquet"
    ),
    "order_items": (
        PROJECT_ROOT
        / "raw_data_clean"
        / "order_items"
        / "order_items.parquet"
    ),
    "churn_scores": (
        PROJECT_ROOT
        / "analytics"
        / "churn_model"
        / "data"
        / "customer_churn_scores.parquet"
    ),
}

DEFAULT_OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "analytics"
    / "demo_ingestion"
    / "data"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a coherent synthetic marketplace subset "
            "for PostgreSQL ingestion."
        )
    )

    parser.add_argument(
        "--customers",
        type=int,
        default=5_000,
        help="Number of synthetic customers to select.",
    )

    parser.add_argument(
        "--max-orders",
        type=int,
        default=50_000,
        help="Maximum total orders in the staging dataset.",
    )

    parser.add_argument(
        "--max-orders-per-customer",
        type=int,
        default=20,
        help="Maximum orders retained for each selected customer.",
    )

    parser.add_argument(
        "--output-directory",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Directory where staging Parquet files are written.",
    )

    arguments = parser.parse_args()

    if arguments.customers <= 0:
        parser.error("--customers must be greater than zero.")

    if arguments.max_orders < arguments.customers:
        parser.error(
            "--max-orders must be at least equal to --customers "
            "so every selected customer can retain an order."
        )

    if arguments.max_orders_per_customer <= 0:
        parser.error(
            "--max-orders-per-customer must be greater than zero."
        )

    return arguments


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def verify_source_files() -> None:
    missing_files = [
        path
        for path in SOURCE_PATHS.values()
        if not path.exists()
    ]

    if missing_files:
        formatted = "\n".join(
            f"  - {path}" for path in missing_files
        )
        raise FileNotFoundError(
            "Required source files are missing:\n"
            f"{formatted}"
        )


def fetch_records(
    connection: duckdb.DuckDBPyConnection,
    query: str,
) -> list[dict[str, Any]]:
    cursor = connection.execute(query)
    columns = [
        description[0]
        for description in cursor.description
    ]

    return [
        dict(zip(columns, row, strict=True))
        for row in cursor.fetchall()
    ]


def fetch_integer(
    connection: duckdb.DuckDBPyConnection,
    query: str,
) -> int:
    result = connection.execute(query).fetchone()

    if result is None:
        return 0

    return int(result[0])


def write_parquet(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    escaped_destination = sql_path(destination)

    connection.execute(
        f"""
        COPY (
            {query}
        )
        TO '{escaped_destination}'
        (
            FORMAT PARQUET,
            COMPRESSION ZSTD
        )
        """
    )


def main() -> None:
    arguments = parse_arguments()
    verify_source_files()

    output_directory = arguments.output_directory.resolve()
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = duckdb.connect(database=":memory:")

    connection.execute("SET threads = 6")
    connection.execute("SET memory_limit = '6GB'")
    connection.execute(
        "SET preserve_insertion_order = false"
    )

    for name, path in SOURCE_PATHS.items():
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW source_{name} AS
            SELECT *
            FROM read_parquet('{sql_path(path)}')
            """
        )

    print("Selecting customers with historical churn scores...")

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE selected_customers AS
        SELECT
            c.customer_id,
            c.customer_external_id,
            c.email,
            c.first_name,
            c.last_name,
            c.region,
            c.country_code,
            c.segment,
            c.signup_date,
            c.signup_channel,
            c.account_status,
            c.created_at,
            c.updated_at,
            s.score_date,
            s.churn_probability,
            s.predicted_churn_flag,
            s.risk_decile,
            s.risk_segment,
            s.recommended_action,
            s.model_name,
            s.model_version
        FROM source_customers AS c
        INNER JOIN source_churn_scores AS s
            ON s.customer_id = c.customer_id
        WHERE COALESCE(s.total_orders, 0) >= 1
        ORDER BY md5(c.customer_id)
        LIMIT {arguments.customers}
        """
    )

    selected_customer_count = fetch_integer(
        connection,
        "SELECT COUNT(*) FROM selected_customers",
    )

    if selected_customer_count == 0:
        raise RuntimeError(
            "No eligible customers were selected."
        )

    print(
        f"Selected customers: {selected_customer_count:,}"
    )

    print("Selecting linked historical orders...")

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE ranked_orders AS
        SELECT
            o.*,
            ROW_NUMBER() OVER (
                PARTITION BY o.customer_id
                ORDER BY
                    o.order_placed_at DESC,
                    o.order_id
            ) AS customer_order_rank
        FROM source_orders AS o
        INNER JOIN selected_customers AS c
            ON c.customer_id = o.customer_id
        """
    )

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE selected_orders AS
        SELECT * EXCLUDE (customer_order_rank)
        FROM ranked_orders
        WHERE
            customer_order_rank
            <= {arguments.max_orders_per_customer}
        ORDER BY
            CASE
                WHEN customer_order_rank = 1 THEN 0
                ELSE 1
            END,
            order_placed_at DESC,
            order_id
        LIMIT {arguments.max_orders}
        """
    )

    selected_order_count = fetch_integer(
        connection,
        "SELECT COUNT(*) FROM selected_orders",
    )

    customers_with_orders = fetch_integer(
        connection,
        """
        SELECT COUNT(DISTINCT customer_id)
        FROM selected_orders
        """,
    )

    if customers_with_orders != selected_customer_count:
        raise RuntimeError(
            "The selected data does not preserve at least one "
            "order for every selected customer. "
            f"Customers selected: {selected_customer_count:,}; "
            f"customers with orders: {customers_with_orders:,}."
        )

    print(f"Selected orders: {selected_order_count:,}")

    print("Selecting linked order items...")

    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE selected_order_items AS
        SELECT oi.*
        FROM source_order_items AS oi
        INNER JOIN selected_orders AS o
            ON o.order_id = oi.order_id
        """
    )

    selected_item_count = fetch_integer(
        connection,
        "SELECT COUNT(*) FROM selected_order_items",
    )

    print(f"Selected order items: {selected_item_count:,}")

    print("Selecting products referenced by order items...")

    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE selected_products AS
        SELECT p.*
        FROM source_products AS p
        INNER JOIN (
            SELECT DISTINCT product_id
            FROM selected_order_items
        ) AS selected_product_ids
            ON selected_product_ids.product_id = p.product_id
        """
    )

    selected_product_count = fetch_integer(
        connection,
        "SELECT COUNT(*) FROM selected_products",
    )

    missing_product_count = fetch_integer(
        connection,
        """
        SELECT COUNT(DISTINCT oi.product_id)
        FROM selected_order_items AS oi
        LEFT JOIN selected_products AS p
            ON p.product_id = oi.product_id
        WHERE p.product_id IS NULL
        """,
    )

    if missing_product_count > 0:
        raise RuntimeError(
            "Some selected order items reference products "
            "that do not exist in the clean product dataset. "
            f"Missing products: {missing_product_count:,}."
        )

    print(f"Selected products: {selected_product_count:,}")

    output_files = {
        "customers": output_directory / "customers.parquet",
        "products": output_directory / "products.parquet",
        "orders": output_directory / "orders.parquet",
        "order_items": (
            output_directory
            / "order_items.parquet"
        ),
        "churn_scores": (
            output_directory
            / "churn_scores.parquet"
        ),
    }

    print("Writing staging Parquet files...")

    write_parquet(
        connection,
        "SELECT * FROM selected_customers",
        output_files["customers"],
    )

    write_parquet(
        connection,
        "SELECT * FROM selected_products",
        output_files["products"],
    )

    write_parquet(
        connection,
        "SELECT * FROM selected_orders",
        output_files["orders"],
    )

    write_parquet(
        connection,
        "SELECT * FROM selected_order_items",
        output_files["order_items"],
    )

    write_parquet(
        connection,
        """
        SELECT s.*
        FROM source_churn_scores AS s
        INNER JOIN selected_customers AS c
            ON c.customer_id = s.customer_id
        """,
        output_files["churn_scores"],
    )

    summary: dict[str, Any] = {
        "requested": {
            "customers": arguments.customers,
            "max_orders": arguments.max_orders,
            "max_orders_per_customer": (
                arguments.max_orders_per_customer
            ),
        },
        "selected": {
            "customers": selected_customer_count,
            "customers_with_orders": customers_with_orders,
            "orders": selected_order_count,
            "order_items": selected_item_count,
            "products": selected_product_count,
        },
        "risk_segments": fetch_records(
            connection,
            """
            SELECT
                risk_segment,
                COUNT(*) AS customers
            FROM selected_customers
            GROUP BY risk_segment
            ORDER BY risk_segment
            """,
        ),
        "customer_segments": fetch_records(
            connection,
            """
            SELECT
                segment,
                COUNT(*) AS customers
            FROM selected_customers
            GROUP BY segment
            ORDER BY customers DESC
            """,
        ),
        "regions": fetch_records(
            connection,
            """
            SELECT
                region,
                COUNT(*) AS customers
            FROM selected_customers
            GROUP BY region
            ORDER BY customers DESC
            """,
        ),
        "order_statuses": fetch_records(
            connection,
            """
            SELECT
                order_status,
                COUNT(*) AS orders
            FROM selected_orders
            GROUP BY order_status
            ORDER BY orders DESC
            """,
        ),
        "currencies": fetch_records(
            connection,
            """
            SELECT
                currency,
                COUNT(*) AS orders
            FROM selected_orders
            GROUP BY currency
            ORDER BY orders DESC
            """,
        ),
        "categories": fetch_records(
            connection,
            """
            SELECT
                category,
                COUNT(*) AS products
            FROM selected_products
            GROUP BY category
            ORDER BY products DESC
            """,
        ),
        "output_files": {
            name: {
                "path": str(path),
                "size_mb": round(
                    path.stat().st_size
                    / (1024 * 1024),
                    2,
                ),
            }
            for name, path in output_files.items()
        },
    }

    summary_path = (
        output_directory
        / "import_summary.json"
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 72)
    print("DEMO STAGING DATASET CREATED")
    print("=" * 72)
    print(
        json.dumps(
            summary["selected"],
            indent=2,
        )
    )
    print()
    print(f"Summary: {summary_path}")
    print(f"Output directory: {output_directory}")

    connection.close()


if __name__ == "__main__":
    main()
