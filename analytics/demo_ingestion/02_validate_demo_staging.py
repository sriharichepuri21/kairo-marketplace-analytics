from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIRECTORY = (
    PROJECT_ROOT
    / "analytics"
    / "demo_ingestion"
    / "data"
)
REPORT_PATH = DATA_DIRECTORY / "validation_report.json"

FILES = {
    "customers": DATA_DIRECTORY / "customers.parquet",
    "products": DATA_DIRECTORY / "products.parquet",
    "orders": DATA_DIRECTORY / "orders.parquet",
    "order_items": DATA_DIRECTORY / "order_items.parquet",
    "churn_scores": DATA_DIRECTORY / "churn_scores.parquet",
}

ALLOWED_ORDER_STATUSES = {
    "delivered",
    "cancelled",
    "refunded",
    "shipped",
    "in_transit",
    "paid",
    "placed",
}

ALLOWED_RISK_SEGMENTS = {
    "high_risk",
    "medium_risk",
    "low_risk",
}


def sql_path(path: Path) -> str:
    return path.resolve().as_posix().replace("'", "''")


def scalar(
    connection: duckdb.DuckDBPyConnection,
    query: str,
) -> Any:
    result = connection.execute(query).fetchone()

    if result is None:
        return None

    return result[0]


def records(
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


def count_rows(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
) -> int:
    return int(
        scalar(
            connection,
            f"SELECT COUNT(*) FROM {table_name}",
        )
    )


def main() -> None:
    missing_files = [
        path
        for path in FILES.values()
        if not path.exists()
    ]

    if missing_files:
        formatted = "\n".join(
            f"  - {path}"
            for path in missing_files
        )
        raise FileNotFoundError(
            "Missing staging files:\n"
            f"{formatted}"
        )

    connection = duckdb.connect(database=":memory:")
    connection.execute("SET threads = 6")
    connection.execute("SET memory_limit = '6GB'")
    connection.execute(
        "SET preserve_insertion_order = false"
    )

    for name, path in FILES.items():
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW {name} AS
            SELECT *
            FROM read_parquet('{sql_path(path)}')
            """
        )

    counts = {
        name: count_rows(connection, name)
        for name in FILES
    }

    checks: dict[str, int] = {
        # Primary identifiers
        "duplicate_customer_ids": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT customer_id
                    FROM customers
                    GROUP BY customer_id
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "duplicate_product_ids": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT product_id
                    FROM products
                    GROUP BY product_id
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "duplicate_order_ids": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT order_id
                    FROM orders
                    GROUP BY order_id
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "duplicate_order_item_ids": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT order_item_id
                    FROM order_items
                    GROUP BY order_item_id
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        # Relationships
        "orders_without_customers": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM orders AS o
                LEFT JOIN customers AS c
                    ON c.customer_id = o.customer_id
                WHERE c.customer_id IS NULL
                """,
            )
        ),
        "items_without_orders": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM order_items AS oi
                LEFT JOIN orders AS o
                    ON o.order_id = oi.order_id
                WHERE o.order_id IS NULL
                """,
            )
        ),
        "items_without_products": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM order_items AS oi
                LEFT JOIN products AS p
                    ON p.product_id = oi.product_id
                WHERE p.product_id IS NULL
                """,
            )
        ),
        "customers_without_scores": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM customers AS c
                LEFT JOIN churn_scores AS s
                    ON s.customer_id = c.customer_id
                WHERE s.customer_id IS NULL
                """,
            )
        ),
        "scores_without_customers": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM churn_scores AS s
                LEFT JOIN customers AS c
                    ON c.customer_id = s.customer_id
                WHERE c.customer_id IS NULL
                """,
            )
        ),
        # Application constraint compatibility
        "duplicate_order_product_groups": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        order_id,
                        product_id
                    FROM order_items
                    GROUP BY
                        order_id,
                        product_id
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "extra_duplicate_order_product_rows": int(
            scalar(
                connection,
                """
                SELECT COALESCE(
                    SUM(row_count - 1),
                    0
                )
                FROM (
                    SELECT COUNT(*) AS row_count
                    FROM order_items
                    GROUP BY
                        order_id,
                        product_id
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "duplicate_product_skus": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT product_sku
                    FROM products
                    WHERE product_sku IS NOT NULL
                    GROUP BY product_sku
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "duplicate_customer_emails": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT LOWER(email)
                    FROM customers
                    WHERE email IS NOT NULL
                    GROUP BY LOWER(email)
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        # Item financial validation
        "invalid_item_quantities": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM order_items
                WHERE quantity IS NULL
                   OR quantity <= 0
                """,
            )
        ),
        "negative_item_amounts": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM order_items
                WHERE unit_price < 0
                   OR COALESCE(unit_cost, 0) < 0
                   OR COALESCE(discount_amount, 0) < 0
                   OR COALESCE(tax_amount, 0) < 0
                """,
            )
        ),
        "negative_recomputed_item_totals": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM order_items
                WHERE
                    unit_price * quantity
                    - COALESCE(discount_amount, 0)
                    + COALESCE(tax_amount, 0)
                    < 0
                """,
            )
        ),
        "item_total_mismatches": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM order_items
                WHERE ABS(
                    line_total
                    - (
                        unit_price * quantity
                        - COALESCE(discount_amount, 0)
                        + COALESCE(tax_amount, 0)
                    )
                ) > 0.01
                """,
            )
        ),
        # Order financial validation
        "negative_order_amounts": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM orders
                WHERE COALESCE(subtotal, 0) < 0
                   OR COALESCE(discount_amount, 0) < 0
                   OR COALESCE(tax_amount, 0) < 0
                   OR COALESCE(shipping_cost, 0) < 0
                """,
            )
        ),
        "negative_recomputed_order_totals": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM orders
                WHERE
                    COALESCE(subtotal, 0)
                    - COALESCE(discount_amount, 0)
                    + COALESCE(tax_amount, 0)
                    + COALESCE(shipping_cost, 0)
                    < 0
                """,
            )
        ),
        "order_total_mismatches": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM orders
                WHERE ABS(
                    total_amount
                    - (
                        COALESCE(subtotal, 0)
                        - COALESCE(discount_amount, 0)
                        + COALESCE(tax_amount, 0)
                        + COALESCE(shipping_cost, 0)
                    )
                ) > 0.01
                """,
            )
        ),
        # Churn validation
        "duplicate_customer_scores": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT customer_id
                    FROM churn_scores
                    GROUP BY customer_id
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "invalid_churn_probabilities": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM churn_scores
                WHERE churn_probability IS NULL
                   OR churn_probability < 0
                   OR churn_probability > 1
                """,
            )
        ),
        "invalid_risk_deciles": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM churn_scores
                WHERE risk_decile IS NULL
                   OR risk_decile < 1
                   OR risk_decile > 10
                """,
            )
        ),
    }

    unexpected_statuses = records(
        connection,
        """
        SELECT
            order_status,
            COUNT(*) AS orders
        FROM orders
        WHERE order_status NOT IN (
            'delivered',
            'cancelled',
            'refunded',
            'shipped',
            'in_transit',
            'paid',
            'placed'
        )
           OR order_status IS NULL
        GROUP BY order_status
        ORDER BY orders DESC
        """,
    )

    unexpected_risk_segments = records(
        connection,
        """
        SELECT
            risk_segment,
            COUNT(*) AS customers
        FROM churn_scores
        WHERE risk_segment NOT IN (
            'high_risk',
            'medium_risk',
            'low_risk'
        )
           OR risk_segment IS NULL
        GROUP BY risk_segment
        ORDER BY customers DESC
        """,
    )

    invalid_currencies = records(
        connection,
        """
        SELECT
            currency,
            COUNT(*) AS orders
        FROM orders
        WHERE currency IS NULL
           OR LENGTH(currency) != 3
        GROUP BY currency
        ORDER BY orders DESC
        """,
    )

    order_date_range = records(
        connection,
        """
        SELECT
            MIN(order_placed_at) AS minimum_order_at,
            MAX(order_placed_at) AS maximum_order_at
        FROM orders
        """,
    )

    orders_by_currency = records(
        connection,
        """
        SELECT
            currency,
            COUNT(*) AS orders,
            ROUND(
                SUM(
                    subtotal
                    - discount_amount
                    + tax_amount
                    + shipping_cost
                ),
                2
            ) AS recomputed_total
        FROM orders
        GROUP BY currency
        ORDER BY orders DESC
        """,
    )

    products_by_category = records(
        connection,
        """
        SELECT
            category,
            COUNT(*) AS products
        FROM products
        GROUP BY category
        ORDER BY products DESC
        """,
    )

    hard_blocker_names = {
        "duplicate_customer_ids",
        "duplicate_product_ids",
        "duplicate_order_ids",
        "duplicate_order_item_ids",
        "orders_without_customers",
        "items_without_orders",
        "items_without_products",
        "customers_without_scores",
        "scores_without_customers",
        "invalid_item_quantities",
        "negative_item_amounts",
        "negative_recomputed_item_totals",
        "negative_order_amounts",
        "negative_recomputed_order_totals",
        "duplicate_customer_scores",
        "invalid_churn_probabilities",
        "invalid_risk_deciles",
    }

    blockers = {
        name: value
        for name, value in checks.items()
        if name in hard_blocker_names
        and value != 0
    }

    if unexpected_statuses:
        blockers["unexpected_statuses"] = unexpected_statuses

    if unexpected_risk_segments:
        blockers["unexpected_risk_segments"] = (
            unexpected_risk_segments
        )

    if invalid_currencies:
        blockers["invalid_currencies"] = invalid_currencies

    warnings = {
        name: value
        for name, value in checks.items()
        if name not in hard_blocker_names
        and value != 0
    }

    report = {
        "counts": counts,
        "checks": checks,
        "warnings": warnings,
        "blockers": blockers,
        "order_date_range": order_date_range,
        "orders_by_currency": orders_by_currency,
        "products_by_category": products_by_category,
        "planned_transformations": {
            "duplicate_order_product_lines": (
                "Consolidate into one application order item "
                "per order and product."
            ),
            "customer_emails": (
                "Replace with deterministic @demo.kairo.local "
                "addresses to prevent login and email collisions."
            ),
            "product_skus": (
                "Suffix duplicate SKUs with the source product ID."
            ),
            "order_totals": (
                "Recompute using subtotal - discount + shipping + tax."
            ),
            "order_item_totals": (
                "Recompute using unit price × quantity "
                "- discount + tax."
            ),
            "order_statuses": {
                "delivered": "delivered",
                "cancelled": "cancelled",
                "refunded": "cancelled",
                "shipped": "shipped",
                "in_transit": "shipped",
                "paid": "confirmed",
                "placed": "pending",
            },
        },
        "validation_passed": not blockers,
    }

    REPORT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    print("=" * 72)
    print("DEMO STAGING VALIDATION")
    print("=" * 72)

    for name, value in counts.items():
        print(f"{name:20} {value:>12,}")

    print()
    print("Warnings:")
    if warnings:
        for name, value in warnings.items():
            print(f"  {name}: {value:,}")
    else:
        print("  None")

    print()
    print("Blockers:")
    if blockers:
        for name, value in blockers.items():
            print(f"  {name}: {value}")
    else:
        print("  None")

    print()
    print(f"Report: {REPORT_PATH}")

    connection.close()

    if blockers:
        raise SystemExit(
            "VALIDATION FAILED — resolve blockers before ingestion."
        )

    print()
    print("VALIDATION PASSED")


if __name__ == "__main__":
    main()
