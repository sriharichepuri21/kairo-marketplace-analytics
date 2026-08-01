"""Run operational data-quality checks and persist their results.

Usage:
    python -m app.scripts.run_data_quality_checks
    python -m app.scripts.run_data_quality_checks \
        --triggered-by manual \
        --freshness-warning-hours 168 \
        --freshness-failure-hours 720
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    DataQualityCheckResult,
    DataQualityRun,
)

CheckStatus = Literal["passed", "warning", "failed"]


@dataclass(frozen=True)
class CountCheck:
    name: str
    category: str
    target_name: str
    sql: str
    nonzero_status: Literal["warning", "failed"]
    success_message: str
    issue_message: str


COUNT_CHECKS = (
    CountCheck(
        name="order_items_missing_orders",
        category="relationships",
        target_name="order_items",
        sql="""
            SELECT COUNT(*)
            FROM order_items AS item
            LEFT JOIN orders AS customer_order
              ON customer_order.id = item.order_id
            WHERE customer_order.id IS NULL
        """,
        nonzero_status="failed",
        success_message="Every order item references an existing order.",
        issue_message="Order items reference orders that do not exist.",
    ),
    CountCheck(
        name="order_items_missing_products",
        category="relationships",
        target_name="order_items",
        sql="""
            SELECT COUNT(*)
            FROM order_items
            WHERE product_id IS NULL
        """,
        nonzero_status="warning",
        success_message="Every order item currently references a product.",
        issue_message=(
            "Some order items no longer reference products. "
            "This can occur after product deletion because the "
            "foreign key uses ON DELETE SET NULL."
        ),
    ),
    CountCheck(
        name="active_products_missing_inventory",
        category="relationships",
        target_name="products",
        sql="""
            SELECT COUNT(*)
            FROM products AS product
            LEFT JOIN inventory
              ON inventory.product_id = product.id
            WHERE product.is_active = TRUE
              AND inventory.product_id IS NULL
        """,
        nonzero_status="failed",
        success_message="Every active product has an inventory record.",
        issue_message="Active products are missing inventory records.",
    ),
    CountCheck(
        name="customer_events_missing_actor",
        category="completeness",
        target_name="customer_events",
        sql="""
            SELECT COUNT(*)
            FROM customer_events
            WHERE user_id IS NULL
              AND session_id IS NULL
        """,
        nonzero_status="failed",
        success_message="Every customer event has a user or session actor.",
        issue_message="Customer events exist without a user or session.",
    ),
    CountCheck(
        name="order_events_missing_order_id",
        category="completeness",
        target_name="customer_events",
        sql="""
            SELECT COUNT(*)
            FROM customer_events
            WHERE event_type = 'order_placed'
              AND order_id IS NULL
        """,
        nonzero_status="failed",
        success_message="Every order-placed event references an order.",
        issue_message="Order-placed events exist without an order ID.",
    ),
    CountCheck(
        name="critical_orders_missing_order_event",
        category="reconciliation",
        target_name="orders",
        sql="""
            SELECT COUNT(*)
            FROM orders AS customer_order
            LEFT JOIN customer_events AS customer_event
              ON customer_event.order_id = customer_order.id
             AND customer_event.event_type = 'order_placed'
            WHERE customer_event.id IS NULL
              AND (
                  customer_order.payment_status = 'paid'
                  OR customer_order.status IN (
                      'confirmed',
                      'processing',
                      'shipped',
                      'delivered'
                  )
              )
        """,
        nonzero_status="failed",
        success_message=("Every paid or progressed order has an order-placed event."),
        issue_message=("Paid or progressed orders are missing order-placed events."),
    ),
    CountCheck(
        name="pending_orders_missing_order_event",
        category="reconciliation",
        target_name="orders",
        sql="""
            SELECT COUNT(*)
            FROM orders AS customer_order
            LEFT JOIN customer_events AS customer_event
              ON customer_event.order_id = customer_order.id
             AND customer_event.event_type = 'order_placed'
            WHERE customer_event.id IS NULL
              AND customer_order.status = 'pending'
              AND customer_order.payment_status = 'pending'
        """,
        nonzero_status="warning",
        success_message=("No pending unpaid orders are missing order-placed events."),
        issue_message=(
            "Pending unpaid orders are missing order-placed events. "
            "These may represent incomplete checkouts or historical "
            "orders created before event tracking."
        ),
    ),
    CountCheck(
        name="duplicate_order_events",
        category="uniqueness",
        target_name="customer_events",
        sql="""
            SELECT COALESCE(
                SUM(duplicate_group.event_count - 1),
                0
            )
            FROM (
                SELECT
                    order_id,
                    COUNT(*) AS event_count
                FROM customer_events
                WHERE event_type = 'order_placed'
                  AND order_id IS NOT NULL
                GROUP BY order_id
                HAVING COUNT(*) > 1
            ) AS duplicate_group
        """,
        nonzero_status="failed",
        success_message="Each order has at most one order-placed event.",
        issue_message="Orders have duplicate order-placed events.",
    ),
    CountCheck(
        name="duplicate_order_numbers",
        category="uniqueness",
        target_name="orders",
        sql="""
            SELECT COALESCE(
                SUM(duplicate_group.record_count - 1),
                0
            )
            FROM (
                SELECT
                    order_number,
                    COUNT(*) AS record_count
                FROM orders
                GROUP BY order_number
                HAVING COUNT(*) > 1
            ) AS duplicate_group
        """,
        nonzero_status="failed",
        success_message="Order numbers are unique.",
        issue_message="Duplicate order numbers were detected.",
    ),
    CountCheck(
        name="duplicate_customer_emails",
        category="uniqueness",
        target_name="users",
        sql="""
            SELECT COALESCE(
                SUM(duplicate_group.record_count - 1),
                0
            )
            FROM (
                SELECT
                    LOWER(email) AS normalized_email,
                    COUNT(*) AS record_count
                FROM users
                GROUP BY LOWER(email)
                HAVING COUNT(*) > 1
            ) AS duplicate_group
        """,
        nonzero_status="failed",
        success_message="Customer email addresses are unique.",
        issue_message="Duplicate customer email addresses were detected.",
    ),
    CountCheck(
        name="invalid_order_amounts",
        category="business_rule",
        target_name="orders",
        sql="""
            SELECT COUNT(*)
            FROM orders
            WHERE subtotal < 0
               OR discount_amount < 0
               OR shipping_amount < 0
               OR tax_amount < 0
               OR total_amount < 0
        """,
        nonzero_status="failed",
        success_message="All order monetary values are nonnegative.",
        issue_message="Orders contain negative monetary values.",
    ),
    CountCheck(
        name="invalid_inventory_quantities",
        category="business_rule",
        target_name="inventory",
        sql="""
            SELECT COUNT(*)
            FROM inventory
            WHERE available_quantity < 0
               OR reserved_quantity < 0
        """,
        nonzero_status="failed",
        success_message="All inventory quantities are nonnegative.",
        issue_message="Inventory contains negative quantities.",
    ),
    CountCheck(
        name="invalid_order_item_line_totals",
        category="reconciliation",
        target_name="order_items",
        sql="""
            SELECT COUNT(*)
            FROM order_items
            WHERE ABS(
                line_total
                - (
                    unit_price * quantity
                    - discount_amount
                    + tax_amount
                )
            ) > 0.01
        """,
        nonzero_status="failed",
        success_message=("Every order-item line total reconciles to its components."),
        issue_message=(
            "Order-item line totals do not reconcile to quantity, price, discount, and tax."
        ),
    ),
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def severity_for_status(status: CheckStatus) -> str:
    if status == "failed":
        return "error"

    if status == "warning":
        return "warning"

    return "info"


def create_run(
    database: Session,
    triggered_by: str,
    warning_hours: int,
    failure_hours: int,
) -> UUID:
    total_checks = len(COUNT_CHECKS) + 3

    run = DataQualityRun(
        run_type="operational",
        status="running",
        triggered_by=triggered_by,
        total_checks=total_checks,
        run_metadata={
            "freshness_warning_hours": warning_hours,
            "freshness_failure_hours": failure_hours,
            "runner_version": "1.0.0",
        },
    )

    database.add(run)
    database.commit()
    database.refresh(run)

    return run.id


def save_result(
    database: Session,
    *,
    run_id: UUID,
    check_name: str,
    category: str,
    target_name: str,
    status: CheckStatus,
    observed_value: object,
    expected_value: object,
    failure_count: int,
    message: str,
    details: dict[str, object] | None = None,
    started_at: datetime,
) -> None:
    result = DataQualityCheckResult(
        run_id=run_id,
        check_name=check_name,
        check_category=category,
        check_source="operational_sql",
        target_name=target_name,
        status=status,
        severity=severity_for_status(status),
        observed_value=observed_value,
        expected_value=expected_value,
        failure_count=failure_count,
        message=message,
        details=details or {},
        started_at=started_at,
        finished_at=utc_now(),
    )

    database.add(result)
    database.commit()


def run_connectivity_check(
    database: Session,
    run_id: UUID,
) -> CheckStatus:
    started_at = utc_now()

    try:
        observed = int(database.execute(text("SELECT 1")).scalar_one())

        status: CheckStatus = "passed" if observed == 1 else "failed"

        message = (
            "Database connection is available."
            if status == "passed"
            else "Database connectivity check returned an unexpected value."
        )

        save_result(
            database,
            run_id=run_id,
            check_name="database_connectivity",
            category="availability",
            target_name="postgresql",
            status=status,
            observed_value=observed,
            expected_value=1,
            failure_count=0 if status == "passed" else 1,
            message=message,
            started_at=started_at,
        )

        return status

    except SQLAlchemyError as error:
        database.rollback()

        save_result(
            database,
            run_id=run_id,
            check_name="database_connectivity",
            category="availability",
            target_name="postgresql",
            status="failed",
            observed_value=None,
            expected_value=1,
            failure_count=1,
            message="Database connectivity check failed.",
            details={
                "error_type": type(error).__name__,
                "error": str(error),
            },
            started_at=started_at,
        )

        return "failed"


def run_freshness_check(
    database: Session,
    *,
    run_id: UUID,
    check_name: str,
    target_name: str,
    timestamp_sql: str,
    warning_hours: int,
    failure_hours: int,
) -> CheckStatus:
    started_at = utc_now()

    try:
        latest_timestamp = database.execute(text(timestamp_sql)).scalar_one_or_none()

        if latest_timestamp is None:
            status: CheckStatus = "failed"
            age_hours = None
            failure_count = 1
            message = f"{target_name} contains no timestamped records."

        else:
            normalized_timestamp = normalize_datetime(latest_timestamp)

            age_hours = max(
                (utc_now() - normalized_timestamp).total_seconds() / 3600,
                0,
            )

            if age_hours > failure_hours:
                status = "failed"
                failure_count = 1
                message = f"{target_name} is critically stale."

            elif age_hours > warning_hours:
                status = "warning"
                failure_count = 1
                message = f"{target_name} is older than the freshness warning threshold."

            else:
                status = "passed"
                failure_count = 0
                message = f"{target_name} is within the freshness threshold."

        observed_value = {
            "latest_timestamp": (
                normalize_datetime(latest_timestamp).isoformat()
                if latest_timestamp is not None
                else None
            ),
            "age_hours": (round(age_hours, 2) if age_hours is not None else None),
        }

        save_result(
            database,
            run_id=run_id,
            check_name=check_name,
            category="freshness",
            target_name=target_name,
            status=status,
            observed_value=observed_value,
            expected_value={
                "warning_after_hours": warning_hours,
                "failure_after_hours": failure_hours,
            },
            failure_count=failure_count,
            message=message,
            started_at=started_at,
        )

        return status

    except SQLAlchemyError as error:
        database.rollback()

        save_result(
            database,
            run_id=run_id,
            check_name=check_name,
            category="freshness",
            target_name=target_name,
            status="failed",
            observed_value=None,
            expected_value={
                "warning_after_hours": warning_hours,
                "failure_after_hours": failure_hours,
            },
            failure_count=1,
            message=f"Unable to evaluate freshness for {target_name}.",
            details={
                "error_type": type(error).__name__,
                "error": str(error),
            },
            started_at=started_at,
        )

        return "failed"


def run_count_check(
    database: Session,
    run_id: UUID,
    check: CountCheck,
) -> CheckStatus:
    started_at = utc_now()

    try:
        failure_count = int(database.execute(text(check.sql)).scalar_one() or 0)

        status: CheckStatus = "passed" if failure_count == 0 else check.nonzero_status

        message = check.success_message if status == "passed" else check.issue_message

        save_result(
            database,
            run_id=run_id,
            check_name=check.name,
            category=check.category,
            target_name=check.target_name,
            status=status,
            observed_value=failure_count,
            expected_value=0,
            failure_count=failure_count,
            message=message,
            started_at=started_at,
        )

        return status

    except SQLAlchemyError as error:
        database.rollback()

        save_result(
            database,
            run_id=run_id,
            check_name=check.name,
            category=check.category,
            target_name=check.target_name,
            status="failed",
            observed_value=None,
            expected_value=0,
            failure_count=1,
            message=f"Unable to execute check: {check.name}.",
            details={
                "error_type": type(error).__name__,
                "error": str(error),
            },
            started_at=started_at,
        )

        return "failed"


def finalize_run(
    database: Session,
    run_id: UUID,
    statuses: list[CheckStatus],
) -> DataQualityRun:
    passed_checks = statuses.count("passed")
    warning_checks = statuses.count("warning")
    failed_checks = statuses.count("failed")

    if failed_checks:
        final_status = "failed"
    elif warning_checks:
        final_status = "warning"
    else:
        final_status = "passed"

    run = database.get(
        DataQualityRun,
        run_id,
    )

    if run is None:
        raise RuntimeError(f"Data-quality run was not found: {run_id}")

    run.status = final_status
    run.finished_at = utc_now()
    run.passed_checks = passed_checks
    run.warning_checks = warning_checks
    run.failed_checks = failed_checks

    database.commit()
    database.refresh(run)

    return run


def run_checks(
    *,
    triggered_by: str,
    warning_hours: int,
    failure_hours: int,
) -> DataQualityRun:
    if warning_hours <= 0:
        raise ValueError("Freshness warning hours must be positive.")

    if failure_hours <= warning_hours:
        raise ValueError("Freshness failure hours must be greater than warning hours.")

    database = SessionLocal()

    try:
        run_id = create_run(
            database,
            triggered_by,
            warning_hours,
            failure_hours,
        )

        statuses: list[CheckStatus] = []

        statuses.append(
            run_connectivity_check(
                database,
                run_id,
            )
        )

        statuses.append(
            run_freshness_check(
                database,
                run_id=run_id,
                check_name="orders_freshness",
                target_name="orders",
                timestamp_sql=("SELECT MAX(created_at) FROM orders"),
                warning_hours=warning_hours,
                failure_hours=failure_hours,
            )
        )

        statuses.append(
            run_freshness_check(
                database,
                run_id=run_id,
                check_name="customer_events_freshness",
                target_name="customer_events",
                timestamp_sql=("SELECT MAX(occurred_at) FROM customer_events"),
                warning_hours=warning_hours,
                failure_hours=failure_hours,
            )
        )

        for check in COUNT_CHECKS:
            statuses.append(
                run_count_check(
                    database,
                    run_id,
                    check,
                )
            )

        return finalize_run(
            database,
            run_id,
            statuses,
        )

    finally:
        database.close()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run operational data-quality checks and persist the results.")
    )

    parser.add_argument(
        "--triggered-by",
        default="manual",
        help="Source that initiated the quality run.",
    )

    parser.add_argument(
        "--freshness-warning-hours",
        type=int,
        default=168,
        help="Age in hours after which freshness becomes a warning.",
    )

    parser.add_argument(
        "--freshness-failure-hours",
        type=int,
        default=720,
        help="Age in hours after which freshness becomes a failure.",
    )

    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()

    run = run_checks(
        triggered_by=arguments.triggered_by,
        warning_hours=arguments.freshness_warning_hours,
        failure_hours=arguments.freshness_failure_hours,
    )

    print()
    print("Data-quality run completed")
    print(f"  Run ID:   {run.id}")
    print(f"  Status:   {run.status}")
    print(f"  Total:    {run.total_checks}")
    print(f"  Passed:   {run.passed_checks}")
    print(f"  Warnings: {run.warning_checks}")
    print(f"  Failed:   {run.failed_checks}")


if __name__ == "__main__":
    main()
