from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

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
    days: int
    start_date: date | None
    end_date: date | None
    snapshot_date: date | None

    total_orders: int
    eligible_orders: int
    delivered_orders: int
    cancelled_orders: int
    active_customers: int

    revenue_by_currency: list[
        OperationsCurrencySummary
    ]


class OperationsRevenueTrendPoint(BaseModel):
    order_date: date
    currency_code: str = Field(
        pattern=r"^[A-Z]{3}$",
    )
    eligible_orders: int
    gross_sales: Decimal
    average_order_value: Decimal


class OperationsRevenueTrendResponse(BaseModel):
    days: int
    start_date: date | None
    end_date: date | None
    items: list[
        OperationsRevenueTrendPoint
    ]


class OperationsOrderStatusItem(BaseModel):
    status: str
    order_count: int
    order_percentage: float = Field(
        ge=0,
        le=1,
    )


class OperationsOrderStatusResponse(BaseModel):
    days: int
    start_date: date | None
    end_date: date | None
    total_orders: int
    items: list[
        OperationsOrderStatusItem
    ]


class OperationsCategoryCurrencySummary(BaseModel):
    currency_code: str = Field(
        pattern=r"^[A-Z]{3}$",
    )
    units_sold: int
    gross_sales: Decimal
    average_unit_revenue: Decimal
    revenue_share: float = Field(
        ge=0,
        le=1,
    )


class OperationsCategoryPerformanceItem(BaseModel):
    category_id: UUID
    category_name: str
    products_sold: int
    eligible_orders: int
    units_sold: int
    revenue_by_currency: list[
        OperationsCategoryCurrencySummary
    ]


class OperationsCategoryPerformanceResponse(
    BaseModel
):
    days: int
    start_date: date | None
    end_date: date | None
    items: list[
        OperationsCategoryPerformanceItem
    ]


InventoryStatus = Literal[
    "untracked",
    "out_of_stock",
    "critical_stock",
    "low_stock",
]


class OperationsInventoryAlertItem(BaseModel):
    product_id: UUID
    product_name: str
    sku: str | None
    brand: str
    category_name: str
    available_quantity: int | None
    reserved_quantity: int | None
    inventory_status: InventoryStatus


class OperationsInventoryAlertsResponse(BaseModel):
    low_stock_threshold: int

    total_products: int
    tracked_products: int
    untracked_products: int
    out_of_stock_products: int
    critical_stock_products: int
    low_stock_products: int
    healthy_stock_products: int

    page: int
    page_size: int
    total_items: int
    total_pages: int

    items: list[
        OperationsInventoryAlertItem
    ]
