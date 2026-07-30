from decimal import (
    ROUND_HALF_UP,
    Decimal,
)

from sqlalchemy.orm import Session

from app.repositories.operations_repository import (
    OperationsRepository,
)
from app.schemas.admin_operations import (
    OperationsCurrencySummary,
    OperationsOrderStatusItem,
    OperationsOrderStatusResponse,
    OperationsRevenueTrendPoint,
    OperationsRevenueTrendResponse,
    OperationsSummaryResponse,
)

MONEY_PRECISION = Decimal("0.01")


def decimal_value(
    value: object,
) -> Decimal:
    if value is None:
        return Decimal("0.00")

    return Decimal(
        str(value)
    ).quantize(
        MONEY_PRECISION,
        rounding=ROUND_HALF_UP,
    )


def string_value(
    value: object,
) -> str:
    enum_value = getattr(
        value,
        "value",
        value,
    )

    return str(enum_value)


class OperationsService:
    @staticmethod
    def get_summary(
        database: Session,
        *,
        days: int,
    ) -> OperationsSummaryResponse:
        (
            start_date,
            end_date,
            summary,
            currency_rows,
        ) = OperationsRepository.get_summary(
            database,
            days=days,
        )

        if summary is None:
            return OperationsSummaryResponse(
                days=days,
                start_date=start_date,
                end_date=end_date,
                snapshot_date=end_date,
                total_orders=0,
                eligible_orders=0,
                delivered_orders=0,
                cancelled_orders=0,
                active_customers=0,
                revenue_by_currency=[],
            )

        return OperationsSummaryResponse(
            days=days,
            start_date=start_date,
            end_date=end_date,
            snapshot_date=end_date,
            total_orders=int(
                summary.total_orders or 0
            ),
            eligible_orders=int(
                summary.eligible_orders or 0
            ),
            delivered_orders=int(
                summary.delivered_orders or 0
            ),
            cancelled_orders=int(
                summary.cancelled_orders or 0
            ),
            active_customers=int(
                summary.active_customers or 0
            ),
            revenue_by_currency=[
                OperationsCurrencySummary(
                    currency_code=(
                        row.currency_code
                    ),
                    eligible_orders=int(
                        row.eligible_orders or 0
                    ),
                    gross_sales=decimal_value(
                        row.gross_sales
                    ),
                    average_order_value=(
                        decimal_value(
                            row.average_order_value
                        )
                    ),
                )
                for row in currency_rows
            ],
        )

    @staticmethod
    def get_revenue_trend(
        database: Session,
        *,
        days: int,
    ) -> OperationsRevenueTrendResponse:
        (
            start_date,
            end_date,
            rows,
        ) = OperationsRepository.get_revenue_trend(
            database,
            days=days,
        )

        return OperationsRevenueTrendResponse(
            days=days,
            start_date=start_date,
            end_date=end_date,
            items=[
                OperationsRevenueTrendPoint(
                    order_date=row.order_date,
                    currency_code=(
                        row.currency_code
                    ),
                    eligible_orders=int(
                        row.eligible_orders or 0
                    ),
                    gross_sales=decimal_value(
                        row.gross_sales
                    ),
                    average_order_value=(
                        decimal_value(
                            row.average_order_value
                        )
                    ),
                )
                for row in rows
            ],
        )

    @staticmethod
    def get_order_statuses(
        database: Session,
        *,
        days: int,
    ) -> OperationsOrderStatusResponse:
        (
            start_date,
            end_date,
            rows,
        ) = OperationsRepository.get_order_statuses(
            database,
            days=days,
        )

        total_orders = sum(
            int(row.order_count or 0)
            for row in rows
        )

        return OperationsOrderStatusResponse(
            days=days,
            start_date=start_date,
            end_date=end_date,
            total_orders=total_orders,
            items=[
                OperationsOrderStatusItem(
                    status=string_value(
                        row.status
                    ),
                    order_count=int(
                        row.order_count or 0
                    ),
                    order_percentage=(
                        round(
                            int(
                                row.order_count
                                or 0
                            )
                            / total_orders,
                            4,
                        )
                        if total_orders
                        else 0
                    ),
                )
                for row in rows
            ],
        )
