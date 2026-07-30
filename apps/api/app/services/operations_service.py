from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.repositories.operations_repository import (
    OperationsRepository,
)
from app.schemas.admin_operations import (
    OperationsCurrencySummary,
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


class OperationsService:
    @staticmethod
    def get_summary(
        database: Session,
    ) -> OperationsSummaryResponse:
        summary, currency_rows = (
            OperationsRepository.get_summary(
                database
            )
        )

        return OperationsSummaryResponse(
            snapshot_date=summary.snapshot_date,
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
