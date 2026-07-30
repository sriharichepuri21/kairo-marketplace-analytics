from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_DIRECTORY = (
    PROJECT_ROOT
    / "analytics"
    / "demo_ingestion"
    / "data"
)

OUTPUT_DIRECTORY = SOURCE_DIRECTORY / "prepared"

SOURCE_FILES = {
    "customers": SOURCE_DIRECTORY / "customers.parquet",
    "products": SOURCE_DIRECTORY / "products.parquet",
    "orders": SOURCE_DIRECTORY / "orders.parquet",
    "order_items": SOURCE_DIRECTORY / "order_items.parquet",
    "churn_scores": SOURCE_DIRECTORY / "churn_scores.parquet",
}

OUTPUT_FILES = {
    "categories": OUTPUT_DIRECTORY / "categories.csv",
    "products": OUTPUT_DIRECTORY / "products.csv",
    "product_images": OUTPUT_DIRECTORY / "product_images.csv",
    "inventory": OUTPUT_DIRECTORY / "inventory.csv",
    "users": OUTPUT_DIRECTORY / "users.csv",
    "addresses": OUTPUT_DIRECTORY / "addresses.csv",
    "orders": OUTPUT_DIRECTORY / "orders.csv",
    "order_items": OUTPUT_DIRECTORY / "order_items.csv",
    "order_status_history": (
        OUTPUT_DIRECTORY / "order_status_history.csv"
    ),
    "customer_events": OUTPUT_DIRECTORY / "customer_events.csv",
    "customer_churn_scores": (
        OUTPUT_DIRECTORY / "customer_churn_scores.csv"
    ),
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


def write_csv(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    destination: Path,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection.execute(
        f"""
        COPY (
            {query}
        )
        TO '{sql_path(destination)}'
        (
            FORMAT CSV,
            HEADER TRUE,
            DELIMITER ',',
            QUOTE '"',
            ESCAPE '"'
        )
        """
    )


def main() -> None:
    missing_files = [
        path
        for path in SOURCE_FILES.values()
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

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = duckdb.connect(database=":memory:")

    connection.execute("SET threads = 6")
    connection.execute("SET memory_limit = '6GB'")
    connection.execute(
        "SET preserve_insertion_order = false"
    )

    connection.execute(
        """
        CREATE OR REPLACE MACRO stable_uuid(input_text) AS (
            substr(md5(CAST(input_text AS VARCHAR)), 1, 8)
            || '-'
            || substr(md5(CAST(input_text AS VARCHAR)), 9, 4)
            || '-'
            || substr(md5(CAST(input_text AS VARCHAR)), 13, 4)
            || '-'
            || substr(md5(CAST(input_text AS VARCHAR)), 17, 4)
            || '-'
            || substr(md5(CAST(input_text AS VARCHAR)), 21, 12)
        )
        """
    )

    for name, path in SOURCE_FILES.items():
        connection.execute(
            f"""
            CREATE OR REPLACE TEMP VIEW source_{name} AS
            SELECT *
            FROM read_parquet('{sql_path(path)}')
            """
        )

    # ------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_categories AS
        SELECT
            stable_uuid(
                'kairo-demo-category:' || category
            ) AS id,
            upper(substr(category, 1, 1))
                || replace(substr(category, 2), '_', ' ')
                AS name,
            replace(lower(category), '_', '-') AS slug,
            MIN(created_at) AS created_at
        FROM source_products
        GROUP BY category
        """
    )

    # ------------------------------------------------------------
    # Products
    # ------------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_products AS
        SELECT
            stable_uuid(
                'kairo-demo-product:' || p.product_id
            ) AS id,
            stable_uuid(
                'kairo-demo-category:' || p.category
            ) AS category_id,
            p.product_id AS source_product_id,
            substr(
                upper(
                    coalesce(
                        nullif(trim(p.product_sku), ''),
                        'SKU'
                    )
                ),
                1,
                65
            )
                || '-'
                || substr(md5(p.product_id), 1, 12)
                AS sku,
            p.seller_id AS seller_source_id,
            p.subcategory,
            p.product_name AS name,
            substr(
                regexp_replace(
                    lower(p.product_name),
                    '[^a-z0-9]+',
                    '-',
                    'g'
                ),
                1,
                220
            )
                || '-'
                || substr(md5(p.product_id), 1, 12)
                AS slug,
            'Synthetic demo product from '
                || coalesce(
                    nullif(trim(p.brand), ''),
                    'Kairo'
                )
                || ' in the '
                || replace(p.category, '_', ' ')
                || ' category.'
                AS description,
            coalesce(
                nullif(trim(p.brand), ''),
                'Kairo'
            ) AS brand,
            round(p.price, 2) AS price,
            round(p.cost, 2) AS cost,
            round(p.weight_kg, 3) AS weight_kg,
            p.review_count,
            round(p.return_rate, 6) AS return_rate,
            p.launch_date,
            round(
                greatest(
                    least(
                        coalesce(p.avg_rating, 0),
                        5
                    ),
                    0
                ),
                2
            ) AS average_rating,
            p.is_active,
            TRUE AS is_demo,
            p.created_at,
            p.updated_at
        FROM source_products AS p
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_product_images AS
        SELECT
            stable_uuid(
                'kairo-demo-product-image:' || source_product_id
            ) AS id,
            id AS product_id,
            '/product-placeholder.svg' AS image_url,
            name || ' product image' AS alt_text,
            0 AS display_order
        FROM prepared_products
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_inventory AS
        SELECT
            id AS product_id,
            CASE
                WHEN is_active
                THEN CAST(
                    (hash(source_product_id) % 196) + 5
                    AS INTEGER
                )
                ELSE 0
            END AS available_quantity,
            0 AS reserved_quantity,
            updated_at
        FROM prepared_products
        """
    )

    # ------------------------------------------------------------
    # Users and addresses
    # ------------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_users AS
        SELECT
            stable_uuid(
                'kairo-demo-user:' || customer_id
            ) AS id,
            customer_id AS source_customer_id,
            'demo+'
                || replace(customer_id, '-', '')
                || '@demo.kairo.local'
                AS email,
            trim(
                coalesce(first_name, '')
                || ' '
                || coalesce(last_name, '')
            ) AS full_name,
            region,
            CASE
                WHEN length(country_code) = 2
                THEN upper(country_code)
                ELSE 'US'
            END AS country_code,
            segment,
            signup_channel,
            account_status,
            'customer' AS role,
            CASE
                WHEN lower(
                    coalesce(account_status, 'active')
                ) = 'active'
                THEN TRUE
                ELSE FALSE
            END AS is_active,
            TRUE AS is_demo,
            created_at,
            updated_at
        FROM source_customers
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_addresses AS
        SELECT
            stable_uuid(
                'kairo-demo-address:' || source_customer_id
            ) AS id,
            id AS user_id,
            full_name,
            '+10000000000' AS phone,
            'Synthetic Demo Address' AS address_line_1,
            NULL::VARCHAR AS address_line_2,
            CASE region
                WHEN 'EU' THEN 'Berlin'
                WHEN 'LATAM' THEN 'São Paulo'
                ELSE 'Seattle'
            END AS city,
            CASE region
                WHEN 'EU' THEN 'Berlin'
                WHEN 'LATAM' THEN 'São Paulo'
                ELSE 'Washington'
            END AS state,
            CASE region
                WHEN 'EU' THEN '10115'
                WHEN 'LATAM' THEN '01000-000'
                ELSE '98101'
            END AS postal_code,
            country_code,
            TRUE AS is_default,
            created_at,
            updated_at
        FROM prepared_users
        """
    )

    # ------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_orders AS
        SELECT
            stable_uuid(
                'kairo-demo-order:' || o.order_id
            ) AS id,
            o.order_id AS source_order_id,
            'DEMO-'
                || substr(
                    replace(o.order_id, '-', ''),
                    1,
                    32
                )
                AS order_number,
            u.id AS user_id,
            a.id AS shipping_address_id,
            o.region AS source_region,
            o.order_channel,
            o.device_type,
            CASE o.order_status
                WHEN 'delivered' THEN 'delivered'
                WHEN 'cancelled' THEN 'cancelled'
                WHEN 'refunded' THEN 'cancelled'
                WHEN 'shipped' THEN 'shipped'
                WHEN 'in_transit' THEN 'shipped'
                WHEN 'paid' THEN 'confirmed'
                WHEN 'placed' THEN 'pending'
            END AS status,
            CASE o.order_status
                WHEN 'refunded' THEN 'refunded'
                WHEN 'cancelled' THEN 'failed'
                WHEN 'placed' THEN 'pending'
                ELSE 'paid'
            END AS payment_status,
            upper(o.currency) AS currency_code,
            round(o.subtotal, 2) AS subtotal,
            round(o.discount_amount, 2) AS discount_amount,
            round(o.shipping_cost, 2) AS shipping_amount,
            round(o.tax_amount, 2) AS tax_amount,
            round(
                o.subtotal
                - o.discount_amount
                + o.shipping_cost
                + o.tax_amount,
                2
            ) AS total_amount,
            u.full_name AS shipping_full_name,
            a.phone AS shipping_phone,
            a.address_line_1 AS shipping_address_line_1,
            a.address_line_2 AS shipping_address_line_2,
            a.city AS shipping_city,
            a.state AS shipping_state,
            a.postal_code AS shipping_postal_code,
            a.country_code AS shipping_country_code,
            'Synthetic marketplace order' AS customer_note,
            TRUE AS is_demo,
            o.created_at,
            o.updated_at,
            o.order_placed_at
        FROM source_orders AS o
        INNER JOIN prepared_users AS u
            ON u.source_customer_id = o.customer_id
        INNER JOIN prepared_addresses AS a
            ON a.user_id = u.id
        """
    )

    # ------------------------------------------------------------
    # Consolidate repeated order/product lines
    # ------------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW grouped_order_items AS
        SELECT
            order_id,
            product_id,
            min(seller_id) AS seller_id,
            min(category) AS category,
            sum(quantity) AS quantity,
            round(
                sum(unit_price * quantity)
                / sum(quantity),
                2
            ) AS unit_price,
            round(
                sum(unit_cost * quantity)
                / sum(quantity),
                2
            ) AS unit_cost,
            round(
                sum(coalesce(discount_amount, 0)),
                2
            ) AS discount_amount,
            round(
                sum(coalesce(tax_amount, 0)),
                2
            ) AS tax_amount
        FROM source_order_items
        GROUP BY
            order_id,
            product_id
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_order_items AS
        SELECT
            stable_uuid(
                'kairo-demo-order-item:'
                || i.order_id
                || ':'
                || i.product_id
            ) AS id,
            'GROUP-'
                || md5(
                    i.order_id
                    || ':'
                    || i.product_id
                )
                AS source_order_item_id,
            i.seller_id AS source_seller_id,
            i.category AS source_category,
            o.id AS order_id,
            p.id AS product_id,
            p.name AS product_name,
            p.slug AS product_slug,
            p.brand AS product_brand,
            i.quantity,
            i.unit_price,
            i.unit_cost,
            i.discount_amount,
            i.tax_amount,
            round(
                i.unit_price * i.quantity
                - i.discount_amount
                + i.tax_amount,
                2
            ) AS line_total,
            o.created_at
        FROM grouped_order_items AS i
        INNER JOIN prepared_orders AS o
            ON o.source_order_id = i.order_id
        INNER JOIN prepared_products AS p
            ON p.source_product_id = i.product_id
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_order_status_history AS
        SELECT
            stable_uuid(
                'kairo-demo-order-status:' || source_order_id
            ) AS id,
            id AS order_id,
            status,
            'Imported synthetic marketplace history'
                AS note,
            NULL::VARCHAR AS created_by_user_id,
            created_at
        FROM prepared_orders
        """
    )

    # ------------------------------------------------------------
    # Customer events
    # ------------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_customer_events AS
        SELECT
            stable_uuid(
                'kairo-demo-event:view:' || oi.source_order_item_id
            ) AS id,
            o.user_id,
            'demo-session-' || o.source_order_id AS session_id,
            'product_view' AS event_type,
            oi.product_id,
            NULL::VARCHAR AS order_id,
            '{"source":"synthetic_demo","funnel_stage":"discovery"}'
                AS properties,
            o.order_placed_at - INTERVAL '30 minutes'
                AS occurred_at
        FROM prepared_order_items AS oi
        INNER JOIN prepared_orders AS o
            ON o.id = oi.order_id

        UNION ALL

        SELECT
            stable_uuid(
                'kairo-demo-event:cart:' || oi.source_order_item_id
            ),
            o.user_id,
            'demo-session-' || o.source_order_id,
            'add_to_cart',
            oi.product_id,
            NULL::VARCHAR,
            '{"source":"synthetic_demo","funnel_stage":"consideration"}',
            o.order_placed_at - INTERVAL '10 minutes'
        FROM prepared_order_items AS oi
        INNER JOIN prepared_orders AS o
            ON o.id = oi.order_id

        UNION ALL

        SELECT
            stable_uuid(
                'kairo-demo-event:checkout:' || source_order_id
            ),
            user_id,
            'demo-session-' || source_order_id,
            'checkout_started',
            NULL::VARCHAR,
            id,
            '{"source":"synthetic_demo","funnel_stage":"checkout"}',
            order_placed_at - INTERVAL '2 minutes'
        FROM prepared_orders

        UNION ALL

        SELECT
            stable_uuid(
                'kairo-demo-event:order:' || source_order_id
            ),
            user_id,
            'demo-session-' || source_order_id,
            'order_placed',
            NULL::VARCHAR,
            id,
            '{"source":"synthetic_demo","funnel_stage":"conversion"}',
            order_placed_at
        FROM prepared_orders
        """
    )

    # ------------------------------------------------------------
    # Churn scores
    # ------------------------------------------------------------

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW staged_customer_spend AS
        SELECT
            u.source_customer_id,
            sum(
                CASE
                    WHEN o.order_placed_at >=
                        CAST(s.score_date AS DATE)
                        - INTERVAL '90 days'
                    THEN o.total_amount
                    ELSE 0
                END
            ) AS spend_last_90d,
            sum(
                CASE
                    WHEN o.order_placed_at >=
                        CAST(s.score_date AS DATE)
                        - INTERVAL '30 days'
                    THEN 1
                    ELSE 0
                END
            ) AS orders_last_30d
        FROM prepared_orders AS o
        INNER JOIN prepared_users AS u
            ON u.id = o.user_id
        INNER JOIN source_churn_scores AS s
            ON s.customer_id = u.source_customer_id
        GROUP BY
            u.source_customer_id
        """
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP VIEW prepared_customer_churn_scores AS
        WITH ranked_scores AS (
            SELECT
                s.*,
                row_number() OVER (
                    ORDER BY
                        s.churn_probability DESC,
                        s.customer_id
                ) AS risk_rank,
                count(*) OVER () AS population_size
            FROM source_churn_scores AS s
        )
        SELECT
            stable_uuid(
                'kairo-demo-churn-score:'
                || s.customer_id
                || ':'
                || s.score_date
                || ':'
                || s.model_version
            ) AS id,
            u.id AS user_id,
            CAST(s.score_date AS DATE)
                AS feature_snapshot_date,
            s.days_since_last_order,
            s.total_orders,
            coalesce(sp.orders_last_30d, 0)
                AS orders_last_30d,
            s.orders_last_90d,
            round(s.lifetime_spend, 2)
                AS lifetime_spend,
            round(
                s.lifetime_spend
                / greatest(s.total_orders, 1),
                2
            ) AS average_order_value,
            round(
                coalesce(sp.spend_last_90d, 0),
                2
            ) AS spend_last_90d,
            greatest(
                date_diff(
                    'day',
                    u.created_at::DATE,
                    CAST(s.score_date AS DATE)
                ),
                0
            ) AS account_age_days,
            CAST(s.is_single_order_customer AS BOOLEAN)
                AS is_single_order_customer,
            round(s.churn_probability, 10)
                AS churn_probability,
            CAST(s.predicted_churn_flag AS BOOLEAN)
                AS predicted_churn_flag,
            s.risk_rank,
            round(
                CASE
                    WHEN s.population_size <= 1 THEN 1
                    ELSE
                        1
                        - (
                            (s.risk_rank - 1)::DOUBLE
                            / (s.population_size - 1)
                        )
                END,
                10
            ) AS risk_percentile,
            s.risk_decile,
            s.risk_segment,
            substr(s.recommended_action, 1, 80)
                AS recommended_action,
            s.population_size
                AS scoring_population_size,
            round(s.probability_threshold, 10)
                AS probability_threshold,
            s.model_name,
            s.model_version,
            s.scored_at_utc,
            s.scored_at_utc AS created_at,
            s.scored_at_utc AS updated_at
        FROM ranked_scores AS s
        INNER JOIN prepared_users AS u
            ON u.source_customer_id = s.customer_id
        LEFT JOIN staged_customer_spend AS sp
            ON sp.source_customer_id = s.customer_id
        """
    )

    exports = {
        "categories": "SELECT * FROM prepared_categories",
        "products": "SELECT * FROM prepared_products",
        "product_images": (
            "SELECT * FROM prepared_product_images"
        ),
        "inventory": "SELECT * FROM prepared_inventory",
        "users": "SELECT * FROM prepared_users",
        "addresses": "SELECT * FROM prepared_addresses",
        "orders": """
            SELECT * EXCLUDE (order_placed_at)
            FROM prepared_orders
        """,
        "order_items": """
            SELECT *
            FROM prepared_order_items
        """,
        "order_status_history": """
            SELECT *
            FROM prepared_order_status_history
        """,
        "customer_events": """
            SELECT *
            FROM prepared_customer_events
        """,
        "customer_churn_scores": """
            SELECT *
            FROM prepared_customer_churn_scores
        """,
    }

    for name, query in exports.items():
        print(f"Writing {name}.csv...")
        write_csv(
            connection,
            query,
            OUTPUT_FILES[name],
        )

    counts = {
        name: int(
            scalar(
                connection,
                f"SELECT COUNT(*) FROM prepared_{name}",
            )
        )
        for name in exports
    }

    expected_counts = {
        "categories": 7,
        "products": 37_722,
        "product_images": 37_722,
        "inventory": 37_722,
        "users": 5_000,
        "addresses": 5_000,
        "orders": 50_000,
        "order_items": 108_932,
        "order_status_history": 50_000,
        "customer_events": 317_864,
        "customer_churn_scores": 5_000,
    }

    mismatches = {
        name: {
            "expected": expected_counts[name],
            "actual": actual,
        }
        for name, actual in counts.items()
        if actual != expected_counts[name]
    }

    duplicate_checks = {
        "duplicate_user_ids": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT id
                    FROM prepared_users
                    GROUP BY id
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
                    SELECT id
                    FROM prepared_products
                    GROUP BY id
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
                    SELECT sku
                    FROM prepared_products
                    GROUP BY sku
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "duplicate_order_numbers": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT order_number
                    FROM prepared_orders
                    GROUP BY order_number
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
        "duplicate_order_product_groups": int(
            scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        order_id,
                        product_id
                    FROM prepared_order_items
                    GROUP BY
                        order_id,
                        product_id
                    HAVING COUNT(*) > 1
                )
                """,
            )
        ),
    }

    failures = {
        **mismatches,
        **{
            name: value
            for name, value in duplicate_checks.items()
            if value != 0
        },
    }

    summary = {
        "counts": counts,
        "expected_counts": expected_counts,
        "duplicate_checks": duplicate_checks,
        "failures": failures,
        "output_directory": str(OUTPUT_DIRECTORY),
        "total_size_mb": round(
            sum(
                path.stat().st_size
                for path in OUTPUT_FILES.values()
            )
            / (1024 * 1024),
            2,
        ),
        "preparation_passed": not failures,
    }

    summary_path = (
        OUTPUT_DIRECTORY
        / "preparation_summary.json"
    )

    summary_path.write_text(
        json.dumps(
            summary,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    connection.close()

    print()
    print("=" * 72)
    print("APPLICATION IMPORT FILES PREPARED")
    print("=" * 72)

    for name, count in counts.items():
        print(f"{name:24} {count:>12,}")

    print()
    print(f"Total size: {summary['total_size_mb']} MB")
    print(f"Summary: {summary_path}")

    if failures:
        print()
        print(json.dumps(failures, indent=2))

        raise SystemExit(
            "PREPARATION FAILED — review the reported mismatches."
        )

    print()
    print("PREPARATION PASSED")


if __name__ == "__main__":
    main()
