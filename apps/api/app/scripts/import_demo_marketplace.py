from __future__ import annotations

import argparse
import json
import secrets
import time
from pathlib import Path
from typing import Any

import psycopg
from argon2 import PasswordHasher
from psycopg import sql

from app.core.config import get_settings

TABLE_COLUMNS: dict[str, list[str]] = {
    "categories": [
        "id",
        "name",
        "slug",
        "created_at",
    ],
    "products": [
        "id",
        "category_id",
        "source_product_id",
        "sku",
        "seller_source_id",
        "subcategory",
        "name",
        "slug",
        "description",
        "brand",
        "price",
        "cost",
        "weight_kg",
        "review_count",
        "return_rate",
        "launch_date",
        "average_rating",
        "is_active",
        "is_demo",
        "created_at",
        "updated_at",
    ],
    "product_images": [
        "id",
        "product_id",
        "image_url",
        "alt_text",
        "display_order",
    ],
    "inventory": [
        "product_id",
        "available_quantity",
        "reserved_quantity",
        "updated_at",
    ],
    "users": [
        "id",
        "source_customer_id",
        "email",
        "full_name",
        "region",
        "country_code",
        "segment",
        "signup_channel",
        "account_status",
        "role",
        "is_active",
        "is_demo",
        "created_at",
        "updated_at",
    ],
    "addresses": [
        "id",
        "user_id",
        "full_name",
        "phone",
        "address_line_1",
        "address_line_2",
        "city",
        "state",
        "postal_code",
        "country_code",
        "is_default",
        "created_at",
        "updated_at",
    ],
    "orders": [
        "id",
        "source_order_id",
        "order_number",
        "user_id",
        "shipping_address_id",
        "source_region",
        "order_channel",
        "device_type",
        "status",
        "payment_status",
        "currency_code",
        "subtotal",
        "discount_amount",
        "shipping_amount",
        "tax_amount",
        "total_amount",
        "shipping_full_name",
        "shipping_phone",
        "shipping_address_line_1",
        "shipping_address_line_2",
        "shipping_city",
        "shipping_state",
        "shipping_postal_code",
        "shipping_country_code",
        "customer_note",
        "is_demo",
        "created_at",
        "updated_at",
    ],
    "order_items": [
        "id",
        "source_order_item_id",
        "source_seller_id",
        "source_category",
        "order_id",
        "product_id",
        "product_name",
        "product_slug",
        "product_brand",
        "quantity",
        "unit_price",
        "unit_cost",
        "discount_amount",
        "tax_amount",
        "line_total",
        "created_at",
    ],
    "order_status_history": [
        "id",
        "order_id",
        "status",
        "note",
        "created_by_user_id",
        "created_at",
    ],
    "customer_events": [
        "id",
        "user_id",
        "session_id",
        "event_type",
        "product_id",
        "order_id",
        "properties",
        "occurred_at",
    ],
    "customer_churn_scores": [
        "id",
        "user_id",
        "feature_snapshot_date",
        "days_since_last_order",
        "total_orders",
        "orders_last_30d",
        "orders_last_90d",
        "lifetime_spend",
        "average_order_value",
        "spend_last_90d",
        "account_age_days",
        "is_single_order_customer",
        "churn_probability",
        "predicted_churn_flag",
        "risk_rank",
        "risk_percentile",
        "risk_decile",
        "risk_segment",
        "recommended_action",
        "scoring_population_size",
        "probability_threshold",
        "model_name",
        "model_version",
        "scored_at_utc",
        "created_at",
        "updated_at",
    ],
}


UPSERT_STATEMENTS: list[tuple[str, str]] = [
    (
        "categories",
        """
        INSERT INTO categories (
            id,
            name,
            slug,
            created_at
        )
        SELECT
            id::uuid,
            name,
            slug,
            created_at::timestamptz
        FROM stg_categories
        ON CONFLICT (slug) DO UPDATE
        SET name = EXCLUDED.name
        """,
    ),
    (
        "products",
        """
        INSERT INTO products (
            id,
            category_id,
            source_product_id,
            sku,
            seller_source_id,
            subcategory,
            name,
            slug,
            description,
            brand,
            price,
            cost,
            weight_kg,
            review_count,
            return_rate,
            launch_date,
            average_rating,
            is_active,
            is_demo,
            created_at,
            updated_at
        )
        SELECT
            staged.id::uuid,
            category.id,
            staged.source_product_id,
            staged.sku,
            NULLIF(staged.seller_source_id, ''),
            NULLIF(staged.subcategory, ''),
            staged.name,
            staged.slug,
            NULLIF(staged.description, ''),
            staged.brand,
            staged.price::numeric,
            NULLIF(staged.cost, '')::numeric,
            NULLIF(staged.weight_kg, '')::numeric,
            staged.review_count::integer,
            NULLIF(staged.return_rate, '')::numeric,
            NULLIF(staged.launch_date, '')::date,
            staged.average_rating::numeric,
            staged.is_active::boolean,
            TRUE,
            staged.created_at::timestamptz,
            staged.updated_at::timestamptz
        FROM stg_products AS staged
        INNER JOIN stg_categories AS staged_category
            ON staged_category.id = staged.category_id
        INNER JOIN categories AS category
            ON category.slug = staged_category.slug
        ON CONFLICT (source_product_id) DO UPDATE
        SET
            category_id = EXCLUDED.category_id,
            sku = EXCLUDED.sku,
            seller_source_id = EXCLUDED.seller_source_id,
            subcategory = EXCLUDED.subcategory,
            name = EXCLUDED.name,
            slug = EXCLUDED.slug,
            description = EXCLUDED.description,
            brand = EXCLUDED.brand,
            price = EXCLUDED.price,
            cost = EXCLUDED.cost,
            weight_kg = EXCLUDED.weight_kg,
            review_count = EXCLUDED.review_count,
            return_rate = EXCLUDED.return_rate,
            launch_date = EXCLUDED.launch_date,
            average_rating = EXCLUDED.average_rating,
            is_active = EXCLUDED.is_active,
            is_demo = TRUE,
            updated_at = EXCLUDED.updated_at
        """,
    ),
    (
        "product_images",
        """
        INSERT INTO product_images (
            id,
            product_id,
            image_url,
            alt_text,
            display_order
        )
        SELECT
            staged_image.id::uuid,
            product.id,
            staged_image.image_url,
            NULLIF(staged_image.alt_text, ''),
            staged_image.display_order::integer
        FROM stg_product_images AS staged_image
        INNER JOIN stg_products AS staged_product
            ON staged_product.id = staged_image.product_id
        INNER JOIN products AS product
            ON product.source_product_id =
               staged_product.source_product_id
        ON CONFLICT (id) DO UPDATE
        SET
            product_id = EXCLUDED.product_id,
            image_url = EXCLUDED.image_url,
            alt_text = EXCLUDED.alt_text,
            display_order = EXCLUDED.display_order
        """,
    ),
    (
        "inventory",
        """
        INSERT INTO inventory (
            product_id,
            available_quantity,
            reserved_quantity,
            updated_at
        )
        SELECT
            product.id,
            staged.available_quantity::integer,
            staged.reserved_quantity::integer,
            staged.updated_at::timestamptz
        FROM stg_inventory AS staged
        INNER JOIN stg_products AS staged_product
            ON staged_product.id = staged.product_id
        INNER JOIN products AS product
            ON product.source_product_id =
               staged_product.source_product_id
        ON CONFLICT (product_id) DO UPDATE
        SET
            available_quantity = EXCLUDED.available_quantity,
            reserved_quantity = EXCLUDED.reserved_quantity,
            updated_at = EXCLUDED.updated_at
        """,
    ),
    (
        "users",
        """
        INSERT INTO users (
            id,
            source_customer_id,
            email,
            full_name,
            password_hash,
            region,
            country_code,
            segment,
            signup_channel,
            account_status,
            role,
            is_active,
            is_demo,
            created_at,
            updated_at
        )
        SELECT
            id::uuid,
            source_customer_id,
            email,
            COALESCE(
                NULLIF(full_name, ''),
                'Demo Customer'
            ),
            %s,
            NULLIF(region, ''),
            NULLIF(country_code, ''),
            NULLIF(segment, ''),
            NULLIF(signup_channel, ''),
            NULLIF(account_status, ''),
            role,
            is_active::boolean,
            TRUE,
            created_at::timestamptz,
            updated_at::timestamptz
        FROM stg_users
        ON CONFLICT (source_customer_id) DO UPDATE
        SET
            email = EXCLUDED.email,
            full_name = EXCLUDED.full_name,
            region = EXCLUDED.region,
            country_code = EXCLUDED.country_code,
            segment = EXCLUDED.segment,
            signup_channel = EXCLUDED.signup_channel,
            account_status = EXCLUDED.account_status,
            role = EXCLUDED.role,
            is_active = EXCLUDED.is_active,
            is_demo = TRUE,
            updated_at = EXCLUDED.updated_at
        """,
    ),
    (
        "addresses",
        """
        INSERT INTO addresses (
            id,
            user_id,
            full_name,
            phone,
            address_line_1,
            address_line_2,
            city,
            state,
            postal_code,
            country_code,
            is_default,
            created_at,
            updated_at
        )
        SELECT
            staged_address.id::uuid,
            app_user.id,
            staged_address.full_name,
            staged_address.phone,
            staged_address.address_line_1,
            NULLIF(staged_address.address_line_2, ''),
            staged_address.city,
            staged_address.state,
            staged_address.postal_code,
            staged_address.country_code,
            staged_address.is_default::boolean,
            staged_address.created_at::timestamptz,
            staged_address.updated_at::timestamptz
        FROM stg_addresses AS staged_address
        INNER JOIN stg_users AS staged_user
            ON staged_user.id = staged_address.user_id
        INNER JOIN users AS app_user
            ON app_user.source_customer_id =
               staged_user.source_customer_id
        ON CONFLICT (id) DO UPDATE
        SET
            user_id = EXCLUDED.user_id,
            full_name = EXCLUDED.full_name,
            phone = EXCLUDED.phone,
            address_line_1 = EXCLUDED.address_line_1,
            address_line_2 = EXCLUDED.address_line_2,
            city = EXCLUDED.city,
            state = EXCLUDED.state,
            postal_code = EXCLUDED.postal_code,
            country_code = EXCLUDED.country_code,
            is_default = EXCLUDED.is_default,
            updated_at = EXCLUDED.updated_at
        """,
    ),
    (
        "orders",
        """
        INSERT INTO orders (
            id,
            source_order_id,
            order_number,
            user_id,
            shipping_address_id,
            source_region,
            order_channel,
            device_type,
            status,
            payment_status,
            currency_code,
            subtotal,
            discount_amount,
            shipping_amount,
            tax_amount,
            total_amount,
            shipping_full_name,
            shipping_phone,
            shipping_address_line_1,
            shipping_address_line_2,
            shipping_city,
            shipping_state,
            shipping_postal_code,
            shipping_country_code,
            customer_note,
            is_demo,
            created_at,
            updated_at
        )
        SELECT
            staged_order.id::uuid,
            staged_order.source_order_id,
            staged_order.order_number,
            app_user.id,
            address.id,
            NULLIF(staged_order.source_region, ''),
            NULLIF(staged_order.order_channel, ''),
            NULLIF(staged_order.device_type, ''),
            staged_order.status,
            staged_order.payment_status,
            staged_order.currency_code,
            staged_order.subtotal::numeric,
            staged_order.discount_amount::numeric,
            staged_order.shipping_amount::numeric,
            staged_order.tax_amount::numeric,
            (
                staged_order.subtotal::numeric
                - staged_order.discount_amount::numeric
                + staged_order.shipping_amount::numeric
                + staged_order.tax_amount::numeric
            ),
            staged_order.shipping_full_name,
            staged_order.shipping_phone,
            staged_order.shipping_address_line_1,
            NULLIF(
                staged_order.shipping_address_line_2,
                ''
            ),
            staged_order.shipping_city,
            staged_order.shipping_state,
            staged_order.shipping_postal_code,
            staged_order.shipping_country_code,
            NULLIF(staged_order.customer_note, ''),
            TRUE,
            staged_order.created_at::timestamptz,
            staged_order.updated_at::timestamptz
        FROM stg_orders AS staged_order
        INNER JOIN stg_users AS staged_user
            ON staged_user.id = staged_order.user_id
        INNER JOIN users AS app_user
            ON app_user.source_customer_id =
               staged_user.source_customer_id
        LEFT JOIN addresses AS address
            ON address.user_id = app_user.id
           AND address.is_default
        ON CONFLICT (source_order_id) DO UPDATE
        SET
            order_number = EXCLUDED.order_number,
            user_id = EXCLUDED.user_id,
            shipping_address_id = EXCLUDED.shipping_address_id,
            source_region = EXCLUDED.source_region,
            order_channel = EXCLUDED.order_channel,
            device_type = EXCLUDED.device_type,
            status = EXCLUDED.status,
            payment_status = EXCLUDED.payment_status,
            currency_code = EXCLUDED.currency_code,
            subtotal = EXCLUDED.subtotal,
            discount_amount = EXCLUDED.discount_amount,
            shipping_amount = EXCLUDED.shipping_amount,
            tax_amount = EXCLUDED.tax_amount,
            total_amount = EXCLUDED.total_amount,
            shipping_full_name = EXCLUDED.shipping_full_name,
            shipping_phone = EXCLUDED.shipping_phone,
            shipping_address_line_1 =
                EXCLUDED.shipping_address_line_1,
            shipping_address_line_2 =
                EXCLUDED.shipping_address_line_2,
            shipping_city = EXCLUDED.shipping_city,
            shipping_state = EXCLUDED.shipping_state,
            shipping_postal_code =
                EXCLUDED.shipping_postal_code,
            shipping_country_code =
                EXCLUDED.shipping_country_code,
            customer_note = EXCLUDED.customer_note,
            is_demo = TRUE,
            updated_at = EXCLUDED.updated_at
        """,
    ),
    (
        "order_items",
        """
        INSERT INTO order_items (
            id,
            source_order_item_id,
            source_seller_id,
            source_category,
            order_id,
            product_id,
            product_name,
            product_slug,
            product_brand,
            quantity,
            unit_price,
            unit_cost,
            discount_amount,
            tax_amount,
            line_total,
            created_at
        )
        SELECT
            staged_item.id::uuid,
            staged_item.source_order_item_id,
            NULLIF(staged_item.source_seller_id, ''),
            NULLIF(staged_item.source_category, ''),
            app_order.id,
            app_product.id,
            staged_item.product_name,
            staged_item.product_slug,
            staged_item.product_brand,
            staged_item.quantity::integer,
            staged_item.unit_price::numeric,
            NULLIF(staged_item.unit_cost, '')::numeric,
            staged_item.discount_amount::numeric,
            staged_item.tax_amount::numeric,
            (
                staged_item.unit_price::numeric
                * staged_item.quantity::integer
                - staged_item.discount_amount::numeric
                + staged_item.tax_amount::numeric
            ),
            staged_item.created_at::timestamptz
        FROM stg_order_items AS staged_item
        INNER JOIN stg_orders AS staged_order
            ON staged_order.id = staged_item.order_id
        INNER JOIN orders AS app_order
            ON app_order.source_order_id =
               staged_order.source_order_id
        INNER JOIN stg_products AS staged_product
            ON staged_product.id = staged_item.product_id
        INNER JOIN products AS app_product
            ON app_product.source_product_id =
               staged_product.source_product_id
        ON CONFLICT (source_order_item_id) DO UPDATE
        SET
            source_seller_id = EXCLUDED.source_seller_id,
            source_category = EXCLUDED.source_category,
            order_id = EXCLUDED.order_id,
            product_id = EXCLUDED.product_id,
            product_name = EXCLUDED.product_name,
            product_slug = EXCLUDED.product_slug,
            product_brand = EXCLUDED.product_brand,
            quantity = EXCLUDED.quantity,
            unit_price = EXCLUDED.unit_price,
            unit_cost = EXCLUDED.unit_cost,
            discount_amount = EXCLUDED.discount_amount,
            tax_amount = EXCLUDED.tax_amount,
            line_total = EXCLUDED.line_total
        """,
    ),
    (
        "order_status_history",
        """
        INSERT INTO order_status_history (
            id,
            order_id,
            status,
            note,
            created_by_user_id,
            created_at
        )
        SELECT
            staged_status.id::uuid,
            app_order.id,
            staged_status.status,
            NULLIF(staged_status.note, ''),
            NULL,
            staged_status.created_at::timestamptz
        FROM stg_order_status_history AS staged_status
        INNER JOIN stg_orders AS staged_order
            ON staged_order.id = staged_status.order_id
        INNER JOIN orders AS app_order
            ON app_order.source_order_id =
               staged_order.source_order_id
        ON CONFLICT (id) DO UPDATE
        SET
            order_id = EXCLUDED.order_id,
            status = EXCLUDED.status,
            note = EXCLUDED.note,
            created_at = EXCLUDED.created_at
        """,
    ),
    (
        "customer_events",
        """
        INSERT INTO customer_events (
            id,
            user_id,
            session_id,
            event_type,
            product_id,
            order_id,
            properties,
            occurred_at
        )
        SELECT
            staged_event.id::uuid,
            app_user.id,
            NULLIF(staged_event.session_id, ''),
            staged_event.event_type,
            app_product.id,
            app_order.id,
            staged_event.properties::jsonb,
            staged_event.occurred_at::timestamptz
        FROM stg_customer_events AS staged_event
        INNER JOIN stg_users AS staged_user
            ON staged_user.id = staged_event.user_id
        INNER JOIN users AS app_user
            ON app_user.source_customer_id =
               staged_user.source_customer_id
        LEFT JOIN stg_products AS staged_product
            ON staged_product.id =
               NULLIF(staged_event.product_id, '')
        LEFT JOIN products AS app_product
            ON app_product.source_product_id =
               staged_product.source_product_id
        LEFT JOIN stg_orders AS staged_order
            ON staged_order.id =
               NULLIF(staged_event.order_id, '')
        LEFT JOIN orders AS app_order
            ON app_order.source_order_id =
               staged_order.source_order_id
        ON CONFLICT (id) DO UPDATE
        SET
            user_id = EXCLUDED.user_id,
            session_id = EXCLUDED.session_id,
            event_type = EXCLUDED.event_type,
            product_id = EXCLUDED.product_id,
            order_id = EXCLUDED.order_id,
            properties = EXCLUDED.properties,
            occurred_at = EXCLUDED.occurred_at
        """,
    ),
    (
        "customer_churn_scores",
        """
        INSERT INTO customer_churn_scores (
            id,
            user_id,
            feature_snapshot_date,
            days_since_last_order,
            total_orders,
            orders_last_30d,
            orders_last_90d,
            lifetime_spend,
            average_order_value,
            spend_last_90d,
            account_age_days,
            is_single_order_customer,
            churn_probability,
            predicted_churn_flag,
            risk_rank,
            risk_percentile,
            risk_decile,
            risk_segment,
            recommended_action,
            scoring_population_size,
            probability_threshold,
            model_name,
            model_version,
            scored_at_utc,
            created_at,
            updated_at
        )
        SELECT
            staged_score.id::uuid,
            app_user.id,
            staged_score.feature_snapshot_date::date,
            staged_score.days_since_last_order::integer,
            staged_score.total_orders::integer,
            staged_score.orders_last_30d::integer,
            staged_score.orders_last_90d::integer,
            staged_score.lifetime_spend::numeric,
            staged_score.average_order_value::numeric,
            staged_score.spend_last_90d::numeric,
            staged_score.account_age_days::integer,
            staged_score.is_single_order_customer::boolean,
            staged_score.churn_probability::numeric,
            staged_score.predicted_churn_flag::boolean,
            staged_score.risk_rank::integer,
            staged_score.risk_percentile::numeric,
            staged_score.risk_decile::integer,
            staged_score.risk_segment,
            staged_score.recommended_action,
            staged_score.scoring_population_size::integer,
            staged_score.probability_threshold::numeric,
            staged_score.model_name,
            staged_score.model_version,
            staged_score.scored_at_utc::timestamptz,
            staged_score.created_at::timestamptz,
            staged_score.updated_at::timestamptz
        FROM stg_customer_churn_scores AS staged_score
        INNER JOIN stg_users AS staged_user
            ON staged_user.id = staged_score.user_id
        INNER JOIN users AS app_user
            ON app_user.source_customer_id =
               staged_user.source_customer_id
        ON CONFLICT (
            user_id,
            feature_snapshot_date,
            model_version
        ) DO UPDATE
        SET
            days_since_last_order =
                EXCLUDED.days_since_last_order,
            total_orders = EXCLUDED.total_orders,
            orders_last_30d = EXCLUDED.orders_last_30d,
            orders_last_90d = EXCLUDED.orders_last_90d,
            lifetime_spend = EXCLUDED.lifetime_spend,
            average_order_value =
                EXCLUDED.average_order_value,
            spend_last_90d = EXCLUDED.spend_last_90d,
            account_age_days = EXCLUDED.account_age_days,
            is_single_order_customer =
                EXCLUDED.is_single_order_customer,
            churn_probability =
                EXCLUDED.churn_probability,
            predicted_churn_flag =
                EXCLUDED.predicted_churn_flag,
            risk_rank = EXCLUDED.risk_rank,
            risk_percentile = EXCLUDED.risk_percentile,
            risk_decile = EXCLUDED.risk_decile,
            risk_segment = EXCLUDED.risk_segment,
            recommended_action =
                EXCLUDED.recommended_action,
            scoring_population_size =
                EXCLUDED.scoring_population_size,
            probability_threshold =
                EXCLUDED.probability_threshold,
            model_name = EXCLUDED.model_name,
            scored_at_utc = EXCLUDED.scored_at_utc,
            updated_at = EXCLUDED.updated_at
        """,
    ),
]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Import the prepared synthetic marketplace dataset into PostgreSQL.")
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("/tmp/kairo_demo_import"),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute all statements and roll back.",
    )

    return parser.parse_args()


def database_connection_string() -> str:
    database_url = get_settings().database_url

    return database_url.replace(
        "postgresql+psycopg://",
        "postgresql://",
        1,
    )


def verify_files(input_directory: Path) -> dict[str, int]:
    summary_path = input_directory / "preparation_summary.json"

    if not summary_path.exists():
        raise FileNotFoundError(f"Missing preparation summary: {summary_path}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    if not summary.get("preparation_passed"):
        raise RuntimeError("Preparation summary does not indicate success.")

    expected_counts = summary["counts"]

    missing = [
        input_directory / f"{table_name}.csv"
        for table_name in TABLE_COLUMNS
        if not (input_directory / f"{table_name}.csv").exists()
    ]

    if missing:
        formatted = "\n".join(f"  - {path}" for path in missing)
        raise FileNotFoundError(f"Missing prepared CSV files:\n{formatted}")

    return {name: int(count) for name, count in expected_counts.items()}


def create_staging_table(
    cursor: psycopg.Cursor[Any],
    table_name: str,
    columns: list[str],
) -> None:
    definitions = sql.SQL(", ").join(
        sql.SQL("{} TEXT").format(sql.Identifier(column)) for column in columns
    )

    query = sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT DROP").format(
        sql.Identifier(f"stg_{table_name}"),
        definitions,
    )

    cursor.execute(query)


def copy_csv(
    cursor: psycopg.Cursor[Any],
    table_name: str,
    columns: list[str],
    csv_path: Path,
) -> int:
    column_sql = sql.SQL(", ").join(sql.Identifier(column) for column in columns)

    copy_query = sql.SQL(
        """
        COPY {} ({})
        FROM STDIN
        WITH (
            FORMAT CSV,
            HEADER TRUE,
            ENCODING 'UTF8'
        )
        """
    ).format(
        sql.Identifier(f"stg_{table_name}"),
        column_sql,
    )

    with (
        csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle,
        cursor.copy(copy_query) as copy,
    ):
        while chunk := handle.read(1024 * 1024):
            copy.write(chunk)

    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(f"stg_{table_name}")))

    result = cursor.fetchone()

    return int(result[0]) if result else 0


def final_counts(
    cursor: psycopg.Cursor[Any],
) -> dict[str, int]:
    queries = {
        "demo_users": """
            SELECT COUNT(*)
            FROM users
            WHERE is_demo
        """,
        "demo_products": """
            SELECT COUNT(*)
            FROM products
            WHERE is_demo
        """,
        "demo_orders": """
            SELECT COUNT(*)
            FROM orders
            WHERE is_demo
        """,
        "demo_order_items": """
            SELECT COUNT(*)
            FROM order_items AS item
            INNER JOIN orders AS app_order
                ON app_order.id = item.order_id
            WHERE app_order.is_demo
        """,
        "demo_events": """
            SELECT COUNT(*)
            FROM customer_events
            WHERE properties->>'source' =
                  'synthetic_demo'
        """,
        "demo_churn_scores": """
            SELECT COUNT(*)
            FROM customer_churn_scores AS score
            INNER JOIN users AS app_user
                ON app_user.id = score.user_id
            WHERE app_user.is_demo
        """,
    }

    counts: dict[str, int] = {}

    for name, query in queries.items():
        cursor.execute(query)
        result = cursor.fetchone()
        counts[name] = int(result[0]) if result else 0

    return counts


def main() -> None:
    arguments = parse_arguments()
    input_directory = arguments.input_dir.resolve()

    expected_counts = verify_files(input_directory)

    demo_password_hash = PasswordHasher().hash(secrets.token_urlsafe(48))

    connection = psycopg.connect(
        database_connection_string(),
        autocommit=False,
    )

    started_at = time.monotonic()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")
            cursor.execute("SET statement_timeout = 0")
            cursor.execute("SET lock_timeout = '30s'")
            cursor.execute("SET synchronous_commit = off")

            print("=" * 72)
            print("LOADING CSV FILES INTO TEMPORARY STAGING TABLES")
            print("=" * 72)

            for table_name, columns in TABLE_COLUMNS.items():
                create_staging_table(
                    cursor,
                    table_name,
                    columns,
                )

                actual_count = copy_csv(
                    cursor,
                    table_name,
                    columns,
                    input_directory / f"{table_name}.csv",
                )

                expected_count = expected_counts[table_name]

                if actual_count != expected_count:
                    raise RuntimeError(
                        f"{table_name}: expected "
                        f"{expected_count:,} rows but copied "
                        f"{actual_count:,}."
                    )

                print(f"{table_name:24} {actual_count:>12,}")

            print()
            print("=" * 72)
            print("UPSERTING APPLICATION TABLES")
            print("=" * 72)

            for table_name, statement in UPSERT_STATEMENTS:
                if table_name == "users":
                    cursor.execute(
                        statement,
                        (demo_password_hash,),
                    )
                else:
                    cursor.execute(statement)

                print(f"{table_name:24} {cursor.rowcount:>12,}")

            cursor.execute("ANALYZE")

            counts = final_counts(cursor)

            print()
            print("=" * 72)
            print("FINAL DEMO POPULATION")
            print("=" * 72)

            for name, count in counts.items():
                print(f"{name:24} {count:>12,}")

        elapsed_seconds = time.monotonic() - started_at

        if arguments.dry_run:
            connection.rollback()

            print()
            print("DRY RUN PASSED — transaction rolled back.")
        else:
            connection.commit()

            print()
            print("DEMO MARKETPLACE IMPORT COMMITTED.")

        print(f"Elapsed: {elapsed_seconds:.2f} seconds")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()
