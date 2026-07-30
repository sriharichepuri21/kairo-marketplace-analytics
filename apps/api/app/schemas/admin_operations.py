from datetime import date
from decimal import Decimal

from pydantic import (
    BaseModel,
    Field,
)


class OperationsCurrencySummary(BaseModel):
    currency_code: str = Field(
        pattern=r"^[A-Z]{3}$",
    )
    eligible_orders: int
    gross_sales: Decimal
    average_order_value: Decimal


class OperationsSummaryResponse(BaseModel):
    snapshot_date: date | None

    total_orders: int
    eligible_orders: int
    delivered_orders: int
    cancelled_orders: int
    active_customers: int

    revenue_by_currency: list[
        OperationsCurrencySummary
    ]
