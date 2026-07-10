"""
Return entity model and generator.

Returns occur on delivered orders. Rate varies by category:
fashion ~27%, books ~2%. Overall ~8% return rate.
"""

import random
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

from faker import Faker
from pydantic import BaseModel, Field


class ReturnStatus(str, Enum):
    INITIATED = "initiated"
    APPROVED = "approved"
    RECEIVED = "received"
    REFUNDED = "refunded"
    REJECTED = "rejected"


class ReturnReason(str, Enum):
    WRONG_ITEM = "wrong_item"
    DEFECTIVE = "defective"
    NOT_AS_DESCRIBED = "not_as_described"
    CHANGED_MIND = "changed_mind"
    DAMAGED_SHIPPING = "damaged_shipping"
    TOO_LATE = "too_late"
    OTHER = "other"


RETURN_REASON_WEIGHTS: dict[ReturnReason, float] = {
    ReturnReason.CHANGED_MIND: 0.30,
    ReturnReason.NOT_AS_DESCRIBED: 0.20,
    ReturnReason.DEFECTIVE: 0.15,
    ReturnReason.WRONG_ITEM: 0.12,
    ReturnReason.DAMAGED_SHIPPING: 0.10,
    ReturnReason.TOO_LATE: 0.08,
    ReturnReason.OTHER: 0.05,
}


class Return(BaseModel):
    return_id: str = Field(..., description="Surrogate key (UUID)")
    order_id: str = Field(..., description="FK to fact_orders")
    order_item_id: str = Field(..., description="FK to fact_order_items")
    customer_id: str
    product_id: str
    category: str
    return_reason: ReturnReason
    return_status: ReturnStatus
    initiated_at: datetime
    received_at: datetime | None = None
    refund_amount: float = Field(..., ge=0)
    is_partial_refund: bool = False
    created_at: datetime
    updated_at: datetime


# Return rate by category
CATEGORY_RETURN_RATE: dict[str, float] = {
    "electronics": 0.05,
    "fashion": 0.27,
    "home_garden": 0.08,
    "beauty": 0.11,
    "sports_outdoors": 0.07,
    "books_media": 0.02,
    "toys_games": 0.09,
}


class DeliveredItemInfo:
    def __init__(
        self,
        order_id: str,
        order_item_id: str,
        customer_id: str,
        product_id: str,
        category: str,
        line_total: float,
        delivered_at: datetime,
    ):
        self.order_id = order_id
        self.order_item_id = order_item_id
        self.customer_id = customer_id
        self.product_id = product_id
        self.category = category
        self.line_total = line_total
        self.delivered_at = delivered_at


def generate_returns(
    delivered_items: list[DeliveredItemInfo],
    seed: int | None = None,
) -> list[Return]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    returns: list[Return] = []

    for item in delivered_items:
        # Check if this item gets returned based on category rate
        rate = CATEGORY_RETURN_RATE.get(item.category, 0.08)
        if random.random() > rate:
            continue

        reason = random.choices(
            list(RETURN_REASON_WEIGHTS.keys()),
            weights=list(RETURN_REASON_WEIGHTS.values()),
            k=1,
        )[0]

        # Initiated 3-30 days after delivery
        days_after = random.randint(3, 30)
        initiated_at = item.delivered_at + timedelta(days=days_after)

        # Status — most returns complete successfully
        status_roll = random.random()
        if status_roll < 0.75:
            status = ReturnStatus.REFUNDED
            received_at = initiated_at + timedelta(days=random.randint(3, 14))
        elif status_roll < 0.90:
            status = ReturnStatus.RECEIVED
            received_at = initiated_at + timedelta(days=random.randint(3, 14))
        elif status_roll < 0.95:
            status = ReturnStatus.APPROVED
            received_at = None
        elif status_roll < 0.98:
            status = ReturnStatus.INITIATED
            received_at = None
        else:
            status = ReturnStatus.REJECTED
            received_at = None

        # Refund amount — usually full, sometimes partial
        is_partial = random.random() < 0.10
        if is_partial:
            refund_amount = round(item.line_total * random.uniform(0.5, 0.9), 2)
        else:
            refund_amount = item.line_total

        if status == ReturnStatus.REJECTED:
            refund_amount = 0.0

        returns.append(Return(
            return_id=str(uuid4()),
            order_id=item.order_id,
            order_item_id=item.order_item_id,
            customer_id=item.customer_id,
            product_id=item.product_id,
            category=item.category,
            return_reason=reason,
            return_status=status,
            initiated_at=initiated_at,
            received_at=received_at,
            refund_amount=refund_amount,
            is_partial_refund=is_partial,
            created_at=initiated_at,
            updated_at=received_at or initiated_at,
        ))

    return returns