from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    shipping_address_id: UUID

    customer_note: str | None = Field(
        default=None,
        max_length=1000,
    )


class OrderShippingAddressResponse(BaseModel):
    full_name: str
    phone: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    postal_code: str
    country_code: str


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: UUID | None
    product_name: str
    product_slug: str
    product_brand: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    created_at: datetime


class OrderStatusHistoryResponse(BaseModel):
    id: UUID
    status: str
    note: str | None
    created_at: datetime


class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    user_id: UUID
    status: str
    payment_status: str
    currency_code: str
    subtotal: Decimal
    shipping_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    shipping_address: OrderShippingAddressResponse
    customer_note: str | None
    items: list[OrderItemResponse]
    status_history: list[OrderStatusHistoryResponse]
    created_at: datetime
    updated_at: datetime
