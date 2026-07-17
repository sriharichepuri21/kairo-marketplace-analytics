#!/usr/bin/env python3
"""Build a compact DuckDB warehouse for the Kairo Streamlit deployment.

Run from the repository root:

    python scripts/build_dashboard_warehouse.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


MAX_GITHUB_FILE_MB = 95.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a compact dashboard-only DuckDB database from the "
            "full local Kairo warehouse."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("warehouse/kairo.duckdb"),
        help="Full local DuckDB warehouse.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("warehouse/kairo_dashboard.duckdb"),
        help="Compact deployment DuckDB warehouse.",
    )
    return parser.parse_args()


def sql_literal(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def create_compact_warehouse(
    source: Path,
    output: Path,
) -> None:
    source = source.resolve()
    output = output.resolve()

    if not source.exists():
        raise FileNotFoundError(
            f"Full warehouse was not found: {source}"
        )

    if source == output:
        raise ValueError(
            "The compact output path cannot equal the source warehouse path."
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        output.unlink()

    conn = duckdb.connect(str(output))

    try:
        conn.execute("PRAGMA threads=4")
        conn.execute("PRAGMA preserve_insertion_order=false")

        conn.execute(
            f"ATTACH '{sql_literal(source)}' "
            "AS source_db (READ_ONLY)"
        )

        conn.execute(
            """
            CREATE TABLE dashboard_kpis AS
            WITH marketplace AS (
                SELECT
                    ROUND(SUM(net_gmv), 2) AS net_gmv
                FROM source_db.main.mart_gmv_daily
            ),
            orders AS (
                SELECT
                    ROUND(SUM(total_amount), 2)
                        AS customer_charged_amount,
                    COUNT(DISTINCT order_id)
                        AS eligible_orders
                FROM source_db.main.fact_orders
                WHERE order_status
                    NOT IN ('cancelled', 'refunded')
            ),
            customers AS (
                SELECT
                    COUNT(*) AS real_customers
                FROM source_db.main.dim_customers
                WHERE is_unknown_customer = FALSE
            ),
            sellers AS (
                SELECT
                    ROUND(SUM(commission_revenue), 2)
                        AS commission_revenue
                FROM source_db.main.mart_seller_health
            ),
            customer_health AS (
                SELECT
                    ROUND(
                        100.0
                        * SUM(
                            CASE
                                WHEN total_orders >= 2 THEN 1
                                ELSE 0
                            END
                        )
                        / NULLIF(
                            SUM(
                                CASE
                                    WHEN total_orders > 0 THEN 1
                                    ELSE 0
                                END
                            ),
                            0
                        ),
                        1
                    ) AS repeat_buyer_rate
                FROM source_db.main.mart_customer_ltv
                WHERE is_unknown_customer = FALSE
            ),
            margin AS (
                SELECT
                    ROUND(
                        100.0
                        * SUM(
                            CASE
                                WHEN is_margin_valid
                                THEN net_gmv - merchandise_cost
                                ELSE 0
                            END
                        )
                        / NULLIF(
                            SUM(
                                CASE
                                    WHEN is_margin_valid
                                    THEN net_gmv
                                    ELSE 0
                                END
                            ),
                            0
                        ),
                        1
                    ) AS weighted_margin
                FROM source_db.main.fact_order_items
                WHERE order_status
                    NOT IN ('cancelled', 'refunded')
            )
            SELECT
                marketplace.net_gmv,
                orders.customer_charged_amount,
                orders.eligible_orders,
                customers.real_customers,
                sellers.commission_revenue,
                ROUND(
                    marketplace.net_gmv
                    / NULLIF(orders.eligible_orders, 0),
                    2
                ) AS net_gmv_per_order,
                customer_health.repeat_buyer_rate,
                margin.weighted_margin
            FROM marketplace
            CROSS JOIN orders
            CROSS JOIN customers
            CROSS JOIN sellers
            CROSS JOIN customer_health
            CROSS JOIN margin
            """
        )

        conn.execute(
            """
            CREATE TABLE dashboard_monthly_marketplace AS
            WITH monthly_gmv AS (
                SELECT
                    DATE_TRUNC('month', order_date) AS month,
                    ROUND(SUM(net_gmv), 2) AS net_gmv
                FROM source_db.main.mart_gmv_daily
                GROUP BY 1
            ),
            monthly_orders AS (
                SELECT
                    DATE_TRUNC('month', order_date) AS month,
                    COUNT(DISTINCT order_id)
                        AS eligible_orders
                FROM source_db.main.fact_orders
                WHERE order_status
                    NOT IN ('cancelled', 'refunded')
                GROUP BY 1
            )
            SELECT
                g.month,
                g.net_gmv,
                o.eligible_orders
            FROM monthly_gmv AS g
            JOIN monthly_orders AS o
                USING (month)
            ORDER BY month
            """
        )

        conn.execute(
            """
            CREATE TABLE dashboard_region_performance AS
            WITH financials AS (
                SELECT
                    region,
                    ROUND(
                        SUM(
                            CASE
                                WHEN is_gmv_valid
                                THEN net_gmv
                                ELSE 0
                            END
                        ),
                        2
                    ) AS net_gmv,
                    SUM(
                        CASE
                            WHEN is_margin_valid
                            THEN net_gmv - merchandise_cost
                            ELSE 0
                        END
                    ) AS gross_margin_amount,
                    SUM(
                        CASE
                            WHEN is_margin_valid
                            THEN net_gmv
                            ELSE 0
                        END
                    ) AS margin_net_gmv
                FROM source_db.main.fact_order_items
                WHERE order_status
                    NOT IN ('cancelled', 'refunded')
                GROUP BY region
            ),
            orders AS (
                SELECT
                    region,
                    COUNT(DISTINCT order_id)
                        AS eligible_orders,
                    COUNT(DISTINCT customer_id)
                        AS customers
                FROM source_db.main.fact_orders
                WHERE order_status
                    NOT IN ('cancelled', 'refunded')
                GROUP BY region
            )
            SELECT
                f.region,
                f.net_gmv,
                o.eligible_orders,
                o.customers,
                f.gross_margin_amount,
                f.margin_net_gmv,
                ROUND(
                    100.0
                    * f.gross_margin_amount
                    / NULLIF(f.margin_net_gmv, 0),
                    1
                ) AS weighted_margin
            FROM financials AS f
            JOIN orders AS o
                USING (region)
            ORDER BY f.net_gmv DESC
            """
        )

        conn.execute(
            """
            CREATE TABLE dashboard_category_summary AS
            SELECT
                category,
                ROUND(
                    SUM(
                        CASE
                            WHEN is_gmv_valid
                            THEN gross_gmv
                            ELSE 0
                        END
                    ),
                    2
                ) AS gross_gmv,
                ROUND(
                    SUM(
                        CASE
                            WHEN is_gmv_valid
                            THEN net_gmv
                            ELSE 0
                        END
                    ),
                    2
                ) AS net_gmv,
                COUNT(
                    DISTINCT CASE
                        WHEN is_gmv_valid
                        THEN order_id
                    END
                ) AS orders,
                SUM(
                    CASE
                        WHEN is_gmv_valid
                        THEN quantity
                        ELSE 0
                    END
                ) AS items,
                SUM(
                    CASE
                        WHEN is_margin_valid
                        THEN net_gmv - merchandise_cost
                        ELSE 0
                    END
                ) AS gross_margin_amount,
                SUM(
                    CASE
                        WHEN is_margin_valid
                        THEN net_gmv
                        ELSE 0
                    END
                ) AS margin_net_gmv,
                ROUND(
                    100.0
                    * SUM(
                        CASE
                            WHEN is_margin_valid
                            THEN net_gmv - merchandise_cost
                            ELSE 0
                        END
                    )
                    / NULLIF(
                        SUM(
                            CASE
                                WHEN is_margin_valid
                                THEN net_gmv
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    1
                ) AS weighted_margin,
                ROUND(
                    SUM(
                        CASE
                            WHEN is_gmv_valid
                            THEN discount_amount
                            ELSE 0
                        END
                    ),
                    2
                ) AS item_discounts
            FROM source_db.main.fact_order_items
            WHERE order_status
                NOT IN ('cancelled', 'refunded')
              AND category IS NOT NULL
            GROUP BY category
            ORDER BY net_gmv DESC
            """
        )

        conn.execute(
            """
            CREATE TABLE dashboard_category_monthly AS
            SELECT
                DATE_TRUNC('month', order_date) AS month,
                category,
                ROUND(
                    SUM(
                        CASE
                            WHEN is_gmv_valid
                            THEN net_gmv
                            ELSE 0
                        END
                    ),
                    2
                ) AS net_gmv,
                COUNT(
                    DISTINCT CASE
                        WHEN is_gmv_valid
                        THEN order_id
                    END
                ) AS orders,
                SUM(
                    CASE
                        WHEN is_gmv_valid
                        THEN quantity
                        ELSE 0
                    END
                ) AS items,
                SUM(
                    CASE
                        WHEN is_margin_valid
                        THEN net_gmv - merchandise_cost
                        ELSE 0
                    END
                ) AS gross_margin_amount,
                SUM(
                    CASE
                        WHEN is_margin_valid
                        THEN net_gmv
                        ELSE 0
                    END
                ) AS margin_net_gmv
            FROM source_db.main.fact_order_items
            WHERE order_status
                NOT IN ('cancelled', 'refunded')
              AND category IS NOT NULL
            GROUP BY 1, 2
            ORDER BY month, category
            """
        )

        conn.execute(
            """
            CREATE TABLE dashboard_category_customer_segment AS
            SELECT
                category,
                COALESCE(
                    customer_segment,
                    'unknown'
                ) AS customer_segment,
                ROUND(
                    SUM(
                        CASE
                            WHEN is_gmv_valid
                            THEN net_gmv
                            ELSE 0
                        END
                    ),
                    2
                ) AS net_gmv,
                COUNT(
                    DISTINCT CASE
                        WHEN is_gmv_valid
                        THEN order_id
                    END
                ) AS orders
            FROM source_db.main.fact_order_items
            WHERE order_status
                NOT IN ('cancelled', 'refunded')
              AND category IS NOT NULL
            GROUP BY 1, 2
            ORDER BY category, net_gmv DESC
            """
        )

        conn.execute(
            """
            CREATE TABLE dashboard_customer_health AS
            SELECT
                activity_status,
                COUNT(*) AS customers,
                ROUND(
                    AVG(lifetime_revenue),
                    2
                ) AS avg_lifetime_spend,
                ROUND(
                    AVG(total_orders),
                    1
                ) AS avg_orders
            FROM source_db.main.mart_customer_ltv
            WHERE is_unknown_customer = FALSE
            GROUP BY activity_status
            ORDER BY customers DESC
            """
        )

        conn.execute(
            """
            CREATE TABLE mart_seller_health AS
            SELECT *
            FROM source_db.main.mart_seller_health
            """
        )

        conn.execute(
            """
            CREATE TABLE mart_customer_churn_scores AS
            SELECT *
            FROM source_db.main.mart_customer_churn_scores
            """
        )

        conn.execute(
            """
            CREATE TABLE dashboard_model_metrics AS
            SELECT
                'behavioral_only'::VARCHAR AS model_name,
                0.7757::DOUBLE AS roc_auc,
                0.4865::DOUBLE AS pr_auc,
                0.7873::DOUBLE AS recall,
                0.5154::DOUBLE AS f1,
                2.51::DOUBLE AS top_10_pct_lift,
                0.30::DOUBLE AS probability_threshold,
                'Promoted because signup channel added negligible '
                'out-of-time predictive value.'::VARCHAR
                    AS selection_reason
            """
        )

        conn.execute(
            """
            CREATE TABLE dashboard_metadata AS
            SELECT
                CURRENT_TIMESTAMP AS built_at_utc,
                'kairo_dashboard.duckdb'::VARCHAR
                    AS warehouse_name,
                28::INTEGER AS dbt_models,
                130::INTEGER AS dbt_tests,
                125::INTEGER AS passing_tests,
                5::INTEGER AS documented_warnings,
                0::INTEGER AS errors
            """
        )

        conn.execute("DETACH source_db")
        conn.execute("CHECKPOINT")

        tables = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchall()

        print()
        print("Created compact dashboard warehouse")
        print(f"Path: {output}")
        print()
        print("Tables:")

        for (table_name,) in tables:
            row_count = conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]

            print(
                f"  {table_name}: {row_count:,} rows"
            )

    finally:
        conn.close()

    size_mb = output.stat().st_size / (1024 * 1024)

    print()
    print(f"File size: {size_mb:,.1f} MB")

    if size_mb >= MAX_GITHUB_FILE_MB:
        raise RuntimeError(
            f"The compact warehouse is {size_mb:,.1f} MB. "
            f"It must remain below {MAX_GITHUB_FILE_MB:.0f} MB "
            "before it is committed."
        )

    print(
        f"PASS: compact warehouse is below "
        f"{MAX_GITHUB_FILE_MB:.0f} MB."
    )


def main() -> None:
    args = parse_args()

    create_compact_warehouse(
        source=args.source,
        output=args.output,
    )


if __name__ == "__main__":
    main()
