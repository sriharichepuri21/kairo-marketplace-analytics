"""
Step 1: Point-in-Time Feature Engineering for Churn Prediction

Builds customer feature snapshots at multiple historical dates for
proper out-of-time model validation.

Snapshot design
---------------
Training:
    2024-12-31
    2025-03-31

Validation:
    2025-06-30

Test:
    2025-09-30

Feature windows include data through the snapshot date.

For a snapshot dated 2025-09-30:
    Feature window:
        All eligible information through 2025-09-30

    Prediction window:
        2025-10-01 through 2025-12-29

Churn definition:
    A customer is churned when they place no eligible order during
    the 90-day prediction window following the snapshot date.

Important design decisions
--------------------------
1. Uses temporal rather than random train/validation/test splits.
2. Includes customers with at least one historical eligible order.
3. Keeps one row per customer_id × snapshot_date.
4. Allows the same customer to appear across different snapshots.
5. Does not use customer_id as a model feature.
6. Excludes the warehouse unknown/reconciliation customer member.
7. Keeps real customers with missing categorical attributes.
8. Excludes synthetic segment from the primary behavioral models.
9. Filters returns, reviews, and deliveries using their own timestamps.
10. Leaves unavailable averages as missing values for model imputation.
11. Uses governed item-level discount information.
12. Validates all generated datasets before saving.

Usage
-----
python analytics/churn_model/01_feature_engineering.py
"""

import json
from datetime import date, datetime, timedelta

import duckdb
import pandas as pd

from config import (
    DB_PATH,
    DATA_DIR,
    ARTIFACTS_DIR,
    TRAIN_SNAPSHOTS,
    VALIDATION_SNAPSHOT,
    TEST_SNAPSHOT,
    ALL_SNAPSHOTS,
    CHURN_WINDOW_DAYS,
    MIN_ORDERS_FOR_ELIGIBILITY,
    BEHAVIORAL_NUMERIC_FEATURES,
    BEHAVIORAL_BINARY_FEATURES,
    CHANNEL_FEATURES,
    SEGMENT_FEATURES,
)


ELIGIBLE_ORDER_STATUSES_SQL = """
    order_status NOT IN ('cancelled', 'refunded')
"""


def get_conn() -> duckdb.DuckDBPyConnection:
    """Open the Kairo DuckDB warehouse in read-only mode."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB warehouse was not found at: {DB_PATH}"
        )

    conn = duckdb.connect(
        str(DB_PATH),
        read_only=True,
    )

    conn.execute(
        "SET preserve_insertion_order = false"
    )

    return conn


def normalize_date(value) -> date:
    """Convert DuckDB/Pandas date-like values to datetime.date."""

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, pd.Timestamp):
        return value.date()

    if isinstance(value, date):
        return value

    return pd.to_datetime(value).date()


def validate_label_window(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """
    Confirm the warehouse contains the complete prediction window
    required for the latest snapshot.
    """

    maximum_order_date = conn.execute("""
        SELECT MAX(order_date)
        FROM main.fact_orders
    """).fetchone()[0]

    if maximum_order_date is None:
        raise ValueError(
            "fact_orders contains no order dates."
        )

    maximum_order_date = normalize_date(
        maximum_order_date
    )

    latest_snapshot = max(ALL_SNAPSHOTS)

    required_label_end = (
        latest_snapshot
        + timedelta(days=CHURN_WINDOW_DAYS)
    )

    print("\n  Label-window validation:")
    print(
        f"    Latest warehouse order: "
        f"{maximum_order_date.isoformat()}"
    )
    print(
        f"    Required label data through: "
        f"{required_label_end.isoformat()}"
    )

    if maximum_order_date < required_label_end:
        raise ValueError(
            "The warehouse does not contain the complete "
            "test prediction window. "
            f"Required through {required_label_end}, "
            f"but fact_orders ends on {maximum_order_date}."
        )

    print(
        "    PASS — complete prediction window is available"
    )


def build_order_features(
    conn: duckdb.DuckDBPyConnection,
    snapshot_date: date,
) -> pd.DataFrame:
    """Build recency, frequency, and monetary features."""

    sd = snapshot_date.isoformat()

    query = f"""
        WITH customer_orders AS (

            SELECT
                customer_id,
                order_id,
                order_date,
                total_amount

            FROM main.fact_orders

            WHERE {ELIGIBLE_ORDER_STATUSES_SQL}
              AND order_date <= DATE '{sd}'

        ),

        order_agg AS (

            SELECT
                customer_id,

                DATEDIFF(
                    'day',
                    MAX(order_date),
                    DATE '{sd}'
                ) AS days_since_last_order,

                DATEDIFF(
                    'day',
                    MIN(order_date),
                    DATE '{sd}'
                ) AS days_since_first_order,

                COUNT(
                    DISTINCT order_id
                ) AS total_orders,

                COUNT(
                    DISTINCT CASE
                        WHEN order_date
                             > DATE '{sd}'
                               - INTERVAL '30 days'
                        THEN order_id
                    END
                ) AS orders_last_30d,

                COUNT(
                    DISTINCT CASE
                        WHEN order_date
                             > DATE '{sd}'
                               - INTERVAL '90 days'
                        THEN order_id
                    END
                ) AS orders_last_90d,

                CASE
                    WHEN COUNT(DISTINCT order_id) > 1
                    THEN
                        DATEDIFF(
                            'day',
                            MIN(order_date),
                            MAX(order_date)
                        )
                        / (
                            COUNT(DISTINCT order_id)
                            - 1.0
                        )
                    ELSE NULL
                END AS avg_days_between_orders,

                SUM(
                    total_amount
                ) AS lifetime_spend,

                AVG(
                    total_amount
                ) AS avg_order_value,

                SUM(
                    CASE
                        WHEN order_date
                             > DATE '{sd}'
                               - INTERVAL '90 days'
                        THEN total_amount
                        ELSE 0
                    END
                ) AS spend_last_90d,

                CASE
                    WHEN
                        SUM(total_amount) > 0
                        AND DATEDIFF(
                            'day',
                            MIN(order_date),
                            DATE '{sd}'
                        ) > 90
                    THEN
                        SUM(
                            CASE
                                WHEN order_date
                                     > DATE '{sd}'
                                       - INTERVAL '90 days'
                                THEN total_amount
                                ELSE 0
                            END
                        )
                        / NULLIF(
                            SUM(total_amount)
                            / (
                                DATEDIFF(
                                    'day',
                                    MIN(order_date),
                                    DATE '{sd}'
                                )
                                / 90.0
                            ),
                            0
                        )
                    ELSE 1.0
                END AS spend_trend,

                CASE
                    WHEN COUNT(DISTINCT order_id) = 1
                    THEN 1
                    ELSE 0
                END AS is_single_order_customer

            FROM customer_orders

            GROUP BY customer_id

            HAVING
                COUNT(DISTINCT order_id)
                >= {MIN_ORDERS_FOR_ELIGIBILITY}

        )

        SELECT *
        FROM order_agg
    """

    return conn.execute(query).df()


def build_item_features(
    conn: duckdb.DuckDBPyConnection,
    snapshot_date: date,
) -> pd.DataFrame:
    """
    Build category, item-count, and governed discount features.

    Discount behavior is calculated from financially valid item data
    rather than potentially corrupted order-header discount amounts.
    """

    sd = snapshot_date.isoformat()

    query = f"""
        SELECT
            o.customer_id,

            COUNT(
                DISTINCT CASE
                    WHEN oi.quantity > 0
                    THEN oi.category
                END
            ) AS category_count,

            COUNT(
                DISTINCT CASE
                    WHEN oi.quantity > 0
                    THEN oi.order_item_id
                END
            ) AS historical_item_count,

            COUNT(
                DISTINCT CASE
                    WHEN
                        COALESCE(
                            oi.is_gmv_valid,
                            FALSE
                        ) = TRUE
                        AND COALESCE(
                            oi.discount_amount,
                            0
                        ) > 0
                    THEN o.order_id
                END
            ) * 1.0
            / NULLIF(
                COUNT(
                    DISTINCT CASE
                        WHEN
                            COALESCE(
                                oi.is_gmv_valid,
                                FALSE
                            ) = TRUE
                        THEN o.order_id
                    END
                ),
                0
            ) AS discount_order_rate

        FROM main.fact_orders AS o

        INNER JOIN main.fact_order_items AS oi
            ON o.order_id = oi.order_id

        WHERE o.order_status
              NOT IN ('cancelled', 'refunded')
          AND o.order_date <= DATE '{sd}'

        GROUP BY o.customer_id
    """

    return conn.execute(query).df()


def build_return_features(
    conn: duckdb.DuckDBPyConnection,
    snapshot_date: date,
) -> pd.DataFrame:
    """
    Build return features using return initiation timestamps.

    The numerator and denominator are aligned to the same eligible
    historical order population.
    """

    sd = snapshot_date.isoformat()

    query = f"""
        WITH customer_orders AS (

            SELECT
                customer_id,
                COUNT(
                    DISTINCT order_id
                ) AS total_orders

            FROM main.fact_orders

            WHERE order_date <= DATE '{sd}'
              AND order_status
                  NOT IN ('cancelled', 'refunded')

            GROUP BY customer_id

        ),

        customer_items AS (

            SELECT
                o.customer_id,

                COUNT(
                    DISTINCT CASE
                        WHEN oi.quantity > 0
                        THEN oi.order_item_id
                    END
                ) AS eligible_item_rows

            FROM main.fact_orders AS o

            INNER JOIN main.fact_order_items AS oi
                ON o.order_id = oi.order_id

            WHERE o.order_date <= DATE '{sd}'
              AND o.order_status
                  NOT IN ('cancelled', 'refunded')

            GROUP BY o.customer_id

        ),

        customer_returns AS (

            SELECT
                o.customer_id,

                COUNT(
                    DISTINCT r.return_id
                ) AS return_count,

                COUNT(
                    DISTINCT r.order_id
                ) AS orders_with_returns

            FROM main.silver__returns AS r

            INNER JOIN main.fact_orders AS o
                ON r.order_id = o.order_id

            WHERE
                CAST(
                    r.initiated_at AS DATE
                ) <= DATE '{sd}'

                AND o.order_date <= DATE '{sd}'

                AND o.order_status
                    NOT IN ('cancelled', 'refunded')

            GROUP BY o.customer_id

        )

        SELECT
            co.customer_id,

            COALESCE(
                cr.return_count,
                0
            ) AS return_count,

            CASE
                WHEN COALESCE(
                    cr.return_count,
                    0
                ) > 0
                THEN 1
                ELSE 0
            END AS has_return,

            LEAST(
                COALESCE(
                    cr.orders_with_returns,
                    0
                ) * 1.0
                / NULLIF(
                    co.total_orders,
                    0
                ),
                1.0
            ) AS return_order_rate,

            LEAST(
                COALESCE(
                    cr.return_count,
                    0
                ) * 1.0
                / NULLIF(
                    ci.eligible_item_rows,
                    0
                ),
                1.0
            ) AS return_item_rate

        FROM customer_orders AS co

        LEFT JOIN customer_returns AS cr
            ON co.customer_id = cr.customer_id

        LEFT JOIN customer_items AS ci
            ON co.customer_id = ci.customer_id
    """

    return conn.execute(query).df()


def build_review_features(
    conn: duckdb.DuckDBPyConnection,
    snapshot_date: date,
) -> pd.DataFrame:
    """
    Build review features using review submission timestamps.

    avg_rating_given remains missing for customers with no reviews.
    """

    sd = snapshot_date.isoformat()

    query = f"""
        SELECT
            customer_id,

            COUNT(*) AS review_count,

            ROUND(
                AVG(rating),
                2
            ) AS avg_rating_given,

            1 AS has_review

        FROM main.silver__reviews

        WHERE
            CAST(
                submitted_at AS DATE
            ) <= DATE '{sd}'

        GROUP BY customer_id
    """

    return conn.execute(query).df()


def build_delivery_features(
    conn: duckdb.DuckDBPyConnection,
    snapshot_date: date,
) -> pd.DataFrame:
    """
    Build delivery features using actual delivery timestamps.

    avg_delivery_delay remains missing for customers without a
    completed historical delivery.
    """

    sd = snapshot_date.isoformat()

    query = f"""
        SELECT
            o.customer_id,

            SUM(
                CASE
                    WHEN s.delay_days > 0
                    THEN 1
                    ELSE 0
                END
            ) AS late_delivery_count,

            ROUND(
                AVG(s.delay_days),
                2
            ) AS avg_delivery_delay,

            1 AS has_completed_delivery

        FROM main.silver__shipments AS s

        INNER JOIN main.fact_orders AS o
            ON s.order_id = o.order_id

        WHERE
            CAST(
                s.delivered_at AS DATE
            ) <= DATE '{sd}'

            AND s.status = 'delivered'

            AND o.order_date <= DATE '{sd}'

            AND o.order_status
                NOT IN ('cancelled', 'refunded')

        GROUP BY o.customer_id
    """

    return conn.execute(query).df()


def build_customer_attributes(
    conn: duckdb.DuckDBPyConnection,
    snapshot_date: date,
) -> pd.DataFrame:
    """
    Build customer attributes.

    Excludes only the warehouse reconciliation member. Real customers
    with missing categorical attributes remain in the modeling data.
    """

    sd = snapshot_date.isoformat()

    query = f"""
        SELECT
            customer_id,

            COALESCE(
                NULLIF(
                    TRIM(signup_channel),
                    ''
                ),
                'missing'
            ) AS signup_channel,

            COALESCE(
                NULLIF(
                    TRIM(segment),
                    ''
                ),
                'missing'
            ) AS segment,

            COALESCE(
                NULLIF(
                    TRIM(region),
                    ''
                ),
                'missing'
            ) AS region,

            signup_date,

            DATEDIFF(
                'day',
                signup_date,
                DATE '{sd}'
            ) AS customer_tenure_days

        FROM main.dim_customers

        WHERE is_unknown_customer = FALSE
          AND signup_date <= DATE '{sd}'
    """

    return conn.execute(query).df()


def build_churn_labels(
    conn: duckdb.DuckDBPyConnection,
    snapshot_date: date,
) -> pd.DataFrame:
    """
    Build the 90-day future-purchase churn label.

    churned = 1:
        No eligible order after the snapshot date and through the
        inclusive end of the prediction window.

    churned = 0:
        At least one eligible order in the prediction window.
    """

    sd = snapshot_date.isoformat()

    churn_end = (
        snapshot_date
        + timedelta(days=CHURN_WINDOW_DAYS)
    ).isoformat()

    query = f"""
        WITH future_orders AS (

            SELECT
                customer_id,
                order_id

            FROM main.fact_orders

            WHERE order_status
                  NOT IN ('cancelled', 'refunded')

              AND order_date > DATE '{sd}'

              AND order_date <= DATE '{churn_end}'

        )

        SELECT
            c.customer_id,

            COUNT(
                DISTINCT f.order_id
            ) AS orders_in_prediction_window,

            CASE
                WHEN COUNT(
                    DISTINCT f.order_id
                ) = 0
                THEN 1
                ELSE 0
            END AS churned

        FROM main.dim_customers AS c

        LEFT JOIN future_orders AS f
            ON c.customer_id = f.customer_id

        WHERE c.is_unknown_customer = FALSE
          AND c.signup_date <= DATE '{sd}'

        GROUP BY c.customer_id
    """

    return conn.execute(query).df()


def build_snapshot(
    conn: duckdb.DuckDBPyConnection,
    snapshot_date: date,
) -> pd.DataFrame:
    """
    Build one point-in-time customer feature snapshot.

    Output grain:
        customer_id × snapshot_date
    """

    sd = snapshot_date.isoformat()

    churn_end = (
        snapshot_date
        + timedelta(days=CHURN_WINDOW_DAYS)
    ).isoformat()

    print(f"\n  ── Snapshot: {sd} ──")
    print(
        f"     Features: data through {sd}"
    )
    print(
        f"     Labels: after {sd} through {churn_end}"
    )

    print("     Building order features...")
    order_features = build_order_features(
        conn,
        snapshot_date,
    )
    print(
        f"       → {len(order_features):,} "
        "eligible customers"
    )

    print("     Building item features...")
    item_features = build_item_features(
        conn,
        snapshot_date,
    )
    print(
        f"       → {len(item_features):,} "
        "customers"
    )

    print("     Building return features...")
    return_features = build_return_features(
        conn,
        snapshot_date,
    )
    print(
        f"       → {len(return_features):,} "
        "customers"
    )

    print("     Building review features...")
    review_features = build_review_features(
        conn,
        snapshot_date,
    )
    print(
        f"       → {len(review_features):,} "
        "customers"
    )

    print("     Building delivery features...")
    delivery_features = build_delivery_features(
        conn,
        snapshot_date,
    )
    print(
        f"       → {len(delivery_features):,} "
        "customers"
    )

    print("     Building customer attributes...")
    customer_attrs = build_customer_attributes(
        conn,
        snapshot_date,
    )
    print(
        f"       → {len(customer_attrs):,} "
        "customers"
    )

    print("     Building churn labels...")
    churn_labels = build_churn_labels(
        conn,
        snapshot_date,
    )
    print(
        f"       → {len(churn_labels):,} "
        "customers"
    )

    print("     Joining feature domains...")

    dataset = order_features.copy()

    dataset = dataset.merge(
        item_features,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        return_features,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        review_features,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        delivery_features,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        customer_attrs,
        on="customer_id",
        how="inner",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        churn_labels[
            [
                "customer_id",
                "orders_in_prediction_window",
                "churned",
            ]
        ],
        on="customer_id",
        how="inner",
        validate="one_to_one",
    )

    count_columns = [
        "category_count",
        "historical_item_count",
        "return_count",
        "review_count",
        "late_delivery_count",
        "orders_in_prediction_window",
    ]

    for column in count_columns:
        dataset[column] = (
            dataset[column]
            .fillna(0)
            .astype(int)
        )

    rate_columns = [
        "discount_order_rate",
        "return_order_rate",
        "return_item_rate",
    ]

    for column in rate_columns:
        dataset[column] = (
            dataset[column]
            .fillna(0.0)
            .clip(lower=0.0, upper=1.0)
        )

    binary_columns = [
        "is_single_order_customer",
        "has_return",
        "has_review",
        "has_completed_delivery",
    ]

    for column in binary_columns:
        dataset[column] = (
            dataset[column]
            .fillna(0)
            .astype(int)
        )

    dataset["churned"] = (
        dataset["churned"]
        .astype(int)
    )

    # Keep these as missing when unavailable:
    #
    # avg_days_between_orders:
    #     Missing for single-order customers.
    #
    # avg_rating_given:
    #     Missing for customers without reviews.
    #
    # avg_delivery_delay:
    #     Missing for customers without completed deliveries.
    #
    # The model preprocessing pipeline will impute them.

    dataset["snapshot_date"] = sd

    preferred_column_order = [
        "customer_id",
        "snapshot_date",
        "signup_channel",
        "segment",
        "region",
        "signup_date",
        "customer_tenure_days",
        "days_since_last_order",
        "days_since_first_order",
        "total_orders",
        "orders_last_30d",
        "orders_last_90d",
        "avg_days_between_orders",
        "lifetime_spend",
        "avg_order_value",
        "spend_last_90d",
        "spend_trend",
        "category_count",
        "historical_item_count",
        "discount_order_rate",
        "return_count",
        "return_order_rate",
        "return_item_rate",
        "has_return",
        "review_count",
        "avg_rating_given",
        "has_review",
        "late_delivery_count",
        "avg_delivery_delay",
        "has_completed_delivery",
        "is_single_order_customer",
        "orders_in_prediction_window",
        "churned",
    ]

    existing_preferred_columns = [
        column
        for column in preferred_column_order
        if column in dataset.columns
    ]

    remaining_columns = [
        column
        for column in dataset.columns
        if column not in existing_preferred_columns
    ]

    dataset = dataset[
        existing_preferred_columns
        + remaining_columns
    ]

    churn_rate = (
        100.0
        * dataset["churned"].mean()
    )

    print(
        f"     ✅ Snapshot {sd}: "
        f"{len(dataset):,} rows, "
        f"{churn_rate:.1f}% churn"
    )

    return dataset


def validate_snapshot(
    dataset: pd.DataFrame,
    expected_snapshot: date,
    dataset_name: str,
) -> None:
    """Validate one customer snapshot before saving."""

    expected_date = expected_snapshot.isoformat()

    if dataset.empty:
        raise ValueError(
            f"{dataset_name} is empty."
        )

    if dataset["customer_id"].isna().any():
        raise ValueError(
            f"{dataset_name} contains null customer IDs."
        )

    duplicate_count = dataset.duplicated(
        subset=[
            "customer_id",
            "snapshot_date",
        ]
    ).sum()

    if duplicate_count:
        raise ValueError(
            f"{dataset_name} contains "
            f"{duplicate_count:,} duplicate "
            "customer-snapshot keys."
        )

    actual_snapshot_dates = set(
        dataset["snapshot_date"]
        .astype(str)
        .unique()
    )

    if actual_snapshot_dates != {expected_date}:
        raise ValueError(
            f"{dataset_name} contains unexpected "
            f"snapshot dates: {actual_snapshot_dates}"
        )

    if not dataset["churned"].isin(
        [0, 1]
    ).all():
        raise ValueError(
            f"{dataset_name} contains invalid "
            "churn labels."
        )

    if dataset["customer_tenure_days"].lt(0).any():
        invalid_count = (
            dataset["customer_tenure_days"]
            .lt(0)
            .sum()
        )

        raise ValueError(
            f"{dataset_name} contains "
            f"{invalid_count:,} customers with "
            "negative tenure."
        )

    if dataset["days_since_last_order"].lt(0).any():
        invalid_count = (
            dataset["days_since_last_order"]
            .lt(0)
            .sum()
        )

        raise ValueError(
            f"{dataset_name} contains "
            f"{invalid_count:,} customers with "
            "negative order recency."
        )

    if (
        dataset["total_orders"]
        < MIN_ORDERS_FOR_ELIGIBILITY
    ).any():
        invalid_count = (
            dataset["total_orders"]
            < MIN_ORDERS_FOR_ELIGIBILITY
        ).sum()

        raise ValueError(
            f"{dataset_name} contains "
            f"{invalid_count:,} customers below "
            "the minimum order requirement."
        )

    rate_columns = [
        "return_order_rate",
        "return_item_rate",
        "discount_order_rate",
    ]

    for column in rate_columns:
        invalid_mask = ~dataset[column].between(
            0,
            1,
            inclusive="both",
        )

        if invalid_mask.any():
            raise ValueError(
                f"{dataset_name}: {column} contains "
                f"{invalid_mask.sum():,} values "
                "outside the range [0, 1]."
            )

    expected_single_order_flag = (
        dataset["total_orders"] == 1
    ).astype(int)

    mismatched_single_order_flags = (
        dataset["is_single_order_customer"]
        != expected_single_order_flag
    ).sum()

    if mismatched_single_order_flags:
        raise ValueError(
            f"{dataset_name} contains "
            f"{mismatched_single_order_flags:,} "
            "incorrect single-order flags."
        )

    missing_interval_for_multi_order = (
        (dataset["total_orders"] > 1)
        & dataset[
            "avg_days_between_orders"
        ].isna()
    ).sum()

    if missing_interval_for_multi_order:
        raise ValueError(
            f"{dataset_name} contains "
            f"{missing_interval_for_multi_order:,} "
            "multi-order customers without an "
            "average order interval."
        )

    print(
        f"  PASS — {dataset_name}: "
        f"{len(dataset):,} valid rows"
    )


def validate_combined_data(
    dataset: pd.DataFrame,
    dataset_name: str,
) -> None:
    """Validate uniqueness for a multi-snapshot dataset."""

    if dataset.empty:
        raise ValueError(
            f"{dataset_name} is empty."
        )

    duplicate_count = dataset.duplicated(
        subset=[
            "customer_id",
            "snapshot_date",
        ]
    ).sum()

    if duplicate_count:
        raise ValueError(
            f"{dataset_name} contains "
            f"{duplicate_count:,} duplicate "
            "customer-snapshot rows."
        )

    print(
        f"  PASS — {dataset_name}: "
        f"{len(dataset):,} unique "
        "customer-snapshot rows"
    )


def print_dataset_summary(
    dataset: pd.DataFrame,
    name: str,
) -> None:
    """Print summary statistics for a modeling dataset."""

    print(f"\n  {name}")
    print(
        f"  Rows: {len(dataset):,}"
    )

    unique_customers = (
        dataset["customer_id"]
        .nunique()
    )

    print(
        f"  Unique customers: "
        f"{unique_customers:,}"
    )

    churn_rate = (
        100.0
        * dataset["churned"].mean()
    )

    print(
        f"  Churn rate: "
        f"{churn_rate:.1f}%"
    )

    snapshot_values = sorted(
        dataset["snapshot_date"]
        .astype(str)
        .unique()
        .tolist()
    )

    print(
        f"  Snapshots: "
        f"{snapshot_values}"
    )

    if "segment" in dataset.columns:
        print("\n  Churn rate by segment:")

        segment_summary = (
            dataset
            .groupby(
                "segment",
                dropna=False,
            )["churned"]
            .agg(
                customers="count",
                churn_rate="mean",
            )
        )

        segment_summary["churn_rate"] = (
            100.0
            * segment_summary["churn_rate"]
        ).round(1)

        print(
            segment_summary.to_string()
        )

    if "signup_channel" in dataset.columns:
        print("\n  Churn rate by channel:")

        channel_summary = (
            dataset
            .groupby(
                "signup_channel",
                dropna=False,
            )["churned"]
            .agg(
                customers="count",
                churn_rate="mean",
            )
        )

        channel_summary["churn_rate"] = (
            100.0
            * channel_summary["churn_rate"]
        ).round(1)

        print(
            channel_summary.to_string()
        )

    if "is_single_order_customer" in dataset.columns:
        single_order = dataset[
            dataset[
                "is_single_order_customer"
            ] == 1
        ]

        multi_order = dataset[
            dataset[
                "is_single_order_customer"
            ] == 0
        ]

        single_share = (
            100.0
            * len(single_order)
            / len(dataset)
        )

        multi_share = (
            100.0
            * len(multi_order)
            / len(dataset)
        )

        print("\n  Purchase-history groups:")

        print(
            f"    Single-order rows: "
            f"{len(single_order):,} "
            f"({single_share:.1f}%)"
        )

        if len(single_order):
            print(
                f"      Churn rate: "
                f"{100.0 * single_order['churned'].mean():.1f}%"
            )

        print(
            f"    Multi-order rows: "
            f"{len(multi_order):,} "
            f"({multi_share:.1f}%)"
        )

        if len(multi_order):
            print(
                f"      Churn rate: "
                f"{100.0 * multi_order['churned'].mean():.1f}%"
            )

    print("\n  Feature distributions:")

    for column in BEHAVIORAL_NUMERIC_FEATURES:
        if column not in dataset.columns:
            continue

        non_null = dataset[column].dropna()

        if non_null.empty:
            print(
                f"    {column}: all values missing"
            )
            continue

        print(
            f"    {column}: "
            f"mean={non_null.mean():.2f}  "
            f"median={non_null.median():.2f}  "
            f"min={non_null.min():.2f}  "
            f"max={non_null.max():.2f}  "
            f"nulls={dataset[column].isna().sum():,}"
        )


def save_datasets(
    train_data: pd.DataFrame,
    validation_data: pd.DataFrame,
    test_data: pd.DataFrame,
) -> pd.DataFrame:
    """Save feature datasets to Parquet."""

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARTIFACTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_data = pd.concat(
        [
            train_data,
            validation_data,
            test_data,
        ],
        ignore_index=True,
    )

    validate_combined_data(
        all_data,
        "ALL SNAPSHOTS",
    )

    all_data.to_parquet(
        DATA_DIR
        / "customer_snapshots.parquet",
        index=False,
    )

    train_data.to_parquet(
        DATA_DIR
        / "train_dataset.parquet",
        index=False,
    )

    validation_data.to_parquet(
        DATA_DIR
        / "validation_dataset.parquet",
        index=False,
    )

    test_data.to_parquet(
        DATA_DIR
        / "test_dataset.parquet",
        index=False,
    )

    return all_data


def save_feature_metadata(
    train_data: pd.DataFrame,
    validation_data: pd.DataFrame,
    test_data: pd.DataFrame,
) -> None:
    """Save feature definitions and split metadata."""

    metadata = {
        "behavioral_numeric_features": (
            BEHAVIORAL_NUMERIC_FEATURES
        ),
        "behavioral_binary_features": (
            BEHAVIORAL_BINARY_FEATURES
        ),
        "channel_features": (
            CHANNEL_FEATURES
        ),
        "segment_features": (
            SEGMENT_FEATURES
        ),
        "primary_model_excludes_segment": True,
        "label": "churned",
        "id_column": "customer_id",
        "snapshot_column": "snapshot_date",
        "prediction_count_column": (
            "orders_in_prediction_window"
        ),
        "train_snapshots": [
            snapshot.isoformat()
            for snapshot in TRAIN_SNAPSHOTS
        ],
        "validation_snapshot": (
            VALIDATION_SNAPSHOT.isoformat()
        ),
        "test_snapshot": (
            TEST_SNAPSHOT.isoformat()
        ),
        "churn_window_days": (
            CHURN_WINDOW_DAYS
        ),
        "churn_definition": (
            "No eligible order after the snapshot "
            "date and through the inclusive end of "
            "the prediction window."
        ),
        "minimum_historical_orders": (
            MIN_ORDERS_FOR_ELIGIBILITY
        ),
        "train_rows": int(
            len(train_data)
        ),
        "train_unique_customers": int(
            train_data["customer_id"].nunique()
        ),
        "validation_rows": int(
            len(validation_data)
        ),
        "validation_unique_customers": int(
            validation_data[
                "customer_id"
            ].nunique()
        ),
        "test_rows": int(
            len(test_data)
        ),
        "test_unique_customers": int(
            test_data["customer_id"].nunique()
        ),
        "train_churn_rate": round(
            float(
                train_data["churned"].mean()
            ),
            6,
        ),
        "validation_churn_rate": round(
            float(
                validation_data[
                    "churned"
                ].mean()
            ),
            6,
        ),
        "test_churn_rate": round(
            float(
                test_data["churned"].mean()
            ),
            6,
        ),
    }

    metadata_path = (
        ARTIFACTS_DIR
        / "feature_columns.json"
    )

    with metadata_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
        )

    print(
        f"  ✅ Feature metadata saved to "
        f"{metadata_path}"
    )


def main() -> None:
    """Build, validate, summarize, and save churn snapshots."""

    if MIN_ORDERS_FOR_ELIGIBILITY != 1:
        raise ValueError(
            "MIN_ORDERS_FOR_ELIGIBILITY must be 1 "
            "so single-order customers remain in "
            "the churn population. Update config.py."
        )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARTIFACTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    conn = get_conn()

    try:
        print("=" * 68)
        print(
            "  POINT-IN-TIME FEATURE ENGINEERING "
            "FOR CHURN PREDICTION"
        )
        print("=" * 68)

        train_snapshot_labels = [
            snapshot.isoformat()
            for snapshot in TRAIN_SNAPSHOTS
        ]

        print()
        print(
            "  Training snapshots:  "
            f"{train_snapshot_labels}"
        )
        print(
            "  Validation snapshot: "
            f"{VALIDATION_SNAPSHOT.isoformat()}"
        )
        print(
            "  Test snapshot:       "
            f"{TEST_SNAPSHOT.isoformat()}"
        )
        print(
            "  Churn window:        "
            f"{CHURN_WINDOW_DAYS} days"
        )
        print(
            "  Minimum orders:      "
            f"{MIN_ORDERS_FOR_ELIGIBILITY}"
        )

        validate_label_window(conn)

        print("\n" + "=" * 68)
        print("  BUILDING TRAINING SNAPSHOTS")
        print("=" * 68)

        train_snapshots = []

        for snapshot_date in TRAIN_SNAPSHOTS:
            snapshot_data = build_snapshot(
                conn,
                snapshot_date,
            )

            validate_snapshot(
                snapshot_data,
                snapshot_date,
                (
                    "TRAIN "
                    f"{snapshot_date.isoformat()}"
                ),
            )

            train_snapshots.append(
                snapshot_data
            )

        train_data = pd.concat(
            train_snapshots,
            ignore_index=True,
        )

        validate_combined_data(
            train_data,
            "STACKED TRAINING DATA",
        )

        print("\n" + "=" * 68)
        print("  BUILDING VALIDATION SNAPSHOT")
        print("=" * 68)

        validation_data = build_snapshot(
            conn,
            VALIDATION_SNAPSHOT,
        )

        validate_snapshot(
            validation_data,
            VALIDATION_SNAPSHOT,
            "VALIDATION",
        )

        print("\n" + "=" * 68)
        print("  BUILDING TEST SNAPSHOT")
        print("=" * 68)

        test_data = build_snapshot(
            conn,
            TEST_SNAPSHOT,
        )

        validate_snapshot(
            test_data,
            TEST_SNAPSHOT,
            "TEST",
        )

        print("\n" + "=" * 68)
        print("  DATASET SUMMARIES")
        print("=" * 68)

        print_dataset_summary(
            train_data,
            "TRAINING",
        )

        print_dataset_summary(
            validation_data,
            "VALIDATION",
        )

        print_dataset_summary(
            test_data,
            "TEST",
        )

        print("\n" + "=" * 68)
        print("  SAVING DATASETS")
        print("=" * 68)

        all_data = save_datasets(
            train_data,
            validation_data,
            test_data,
        )

        print(
            f"\n  Training rows:   "
            f"{len(train_data):,}"
        )

        print(
            f"  Validation rows: "
            f"{len(validation_data):,}"
        )

        print(
            f"  Test rows:       "
            f"{len(test_data):,}"
        )

        print(
            f"  Total rows:      "
            f"{len(all_data):,}"
        )

        print(
            f"\n  ✅ Datasets saved to "
            f"{DATA_DIR}"
        )

        save_feature_metadata(
            train_data,
            validation_data,
            test_data,
        )

        print("\n" + "=" * 68)
        print("  FEATURE ENGINEERING COMPLETE")
        print("=" * 68)

        print(
            "\n  Next step:\n"
            "  python "
            "analytics/churn_model/"
            "02_train_model.py"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
