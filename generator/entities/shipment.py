"""
Shipment entity model and generator.

Shipments track the delivery lifecycle of non-cancelled orders.
On-time delivery rate (~92-95%) is a key fulfillment SLA metric.
"""

import random
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

from faker import Faker
from pydantic import BaseModel, Field


class ShipmentStatus(str, Enum):
    LABEL_CREATED = "label_created"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED_DELIVERY = "failed_delivery"
    RETURNED_TO_SENDER = "returned_to_sender"


class Carrier(str, Enum):
    FEDEX = "fedex"
    UPS = "ups"
    DHL = "dhl"
    USPS = "usps"
    LOCAL_COURIER = "local_courier"


class ShippingMethod(str, Enum):
    STANDARD = "standard"
    EXPRESS = "express"
    NEXT_DAY = "next_day"
    SAME_DAY = "same_day"


class Shipment(BaseModel):
    shipment_id: str = Field(..., description="Surrogate key (UUID)")
    order_id: str = Field(..., description="FK to fact_orders")
    carrier: Carrier
    tracking_number: str
    shipping_method: ShippingMethod
    status: ShipmentStatus
    shipped_at: datetime
    estimated_delivery_at: datetime
    delivered_at: datetime | None = None
    weight_kg: float = Field(..., ge=0.01)
    shipping_cost: float = Field(..., ge=0)
    is_international: bool
    delay_days: int = Field(default=0, ge=0)
    delivery_attempts: int = Field(default=1, ge=1)
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────

CARRIER_WEIGHTS: dict[Carrier, float] = {
    Carrier.FEDEX: 0.30,
    Carrier.UPS: 0.25,
    Carrier.DHL: 0.20,
    Carrier.USPS: 0.15,
    Carrier.LOCAL_COURIER: 0.10,
}

METHOD_WEIGHTS: dict[ShippingMethod, float] = {
    ShippingMethod.STANDARD: 0.55,
    ShippingMethod.EXPRESS: 0.30,
    ShippingMethod.NEXT_DAY: 0.12,
    ShippingMethod.SAME_DAY: 0.03,
}

# Delivery time in days by method
METHOD_DELIVERY_DAYS: dict[ShippingMethod, tuple[int, int]] = {
    ShippingMethod.STANDARD: (4, 10),
    ShippingMethod.EXPRESS: (2, 5),
    ShippingMethod.NEXT_DAY: (1, 2),
    ShippingMethod.SAME_DAY: (0, 0),
}

# On-time delivery probability by carrier
CARRIER_ON_TIME_RATE: dict[Carrier, float] = {
    Carrier.FEDEX: 0.95,
    Carrier.UPS: 0.94,
    Carrier.DHL: 0.92,
    Carrier.USPS: 0.88,
    Carrier.LOCAL_COURIER: 0.85,
}


class OrderShipmentInfo:
    def __init__(
        self,
        order_id: str,
        order_status: str,
        order_placed_at: datetime,
        total_amount: float,
        region: str,
    ):
        self.order_id = order_id
        self.order_status = order_status
        self.order_placed_at = order_placed_at
        self.total_amount = total_amount
        self.region = region


def generate_shipments(
    orders: list[OrderShipmentInfo],
    seed: int | None = None,
) -> list[Shipment]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    fake = Faker()
    shipments: list[Shipment] = []

    for order in orders:
        # Only ship non-cancelled, non-placed orders
        if order.order_status in ("cancelled", "placed"):
            continue

        carrier = random.choices(
            list(CARRIER_WEIGHTS.keys()),
            weights=list(CARRIER_WEIGHTS.values()),
            k=1,
        )[0]

        method = random.choices(
            list(METHOD_WEIGHTS.keys()),
            weights=list(METHOD_WEIGHTS.values()),
            k=1,
        )[0]

        # Shipped 1-3 days after order placed
        ship_delay_hours = random.randint(4, 72)
        shipped_at = order.order_placed_at + timedelta(hours=ship_delay_hours)

        # Estimated delivery based on method
        day_low, day_high = METHOD_DELIVERY_DAYS[method]
        est_days = random.randint(max(day_low, 1), max(day_high, 1))
        estimated_delivery_at = shipped_at + timedelta(days=est_days)

        # Is it international?
        is_international = order.region != "US"
        if is_international:
            estimated_delivery_at += timedelta(days=random.randint(1, 4))

        # On-time or late?
        on_time_rate = CARRIER_ON_TIME_RATE[carrier]
        if random.random() < on_time_rate:
            # On time or early
            actual_days = est_days + random.randint(-1, 0)
            delay_days = 0
        else:
            # Late
            delay_days = random.randint(1, 7)
            actual_days = est_days + delay_days

        delivered_at = shipped_at + timedelta(days=max(actual_days, 1))

        # Status based on order status
        if order.order_status in ("delivered", "refunded"):
            status = ShipmentStatus.DELIVERED
        elif order.order_status in ("shipped", "in_transit"):
            status = random.choice([
                ShipmentStatus.IN_TRANSIT,
                ShipmentStatus.OUT_FOR_DELIVERY,
            ])
            delivered_at = None
            delay_days = 0
        else:
            status = ShipmentStatus.DELIVERED

        # Delivery attempts
        delivery_attempts = 1
        if delay_days > 3:
            delivery_attempts = random.randint(2, 3)

        # Shipping cost
        base_cost = random.uniform(3.99, 15.99)
        if method == ShippingMethod.EXPRESS:
            base_cost *= 1.5
        elif method == ShippingMethod.NEXT_DAY:
            base_cost *= 2.5
        elif method == ShippingMethod.SAME_DAY:
            base_cost *= 4.0
        if is_international:
            base_cost *= 1.8

        weight_kg = round(random.uniform(0.2, 15.0), 2)

        tracking = f"{carrier.value.upper()}{fake.random_int(1000000000, 9999999999)}"

        shipments.append(Shipment(
            shipment_id=str(uuid4()),
            order_id=order.order_id,
            carrier=carrier,
            tracking_number=tracking,
            shipping_method=method,
            status=status,
            shipped_at=shipped_at,
            estimated_delivery_at=estimated_delivery_at,
            delivered_at=delivered_at,
            weight_kg=weight_kg,
            shipping_cost=round(base_cost, 2),
            is_international=is_international,
            delay_days=delay_days,
            delivery_attempts=delivery_attempts,
            created_at=shipped_at,
            updated_at=delivered_at or shipped_at,
        ))

    return shipments
