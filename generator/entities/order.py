"""
Order and OrderItem entity models and generators.

Orders connect customers to products and generate the GMV
that powers every executive metric. OrderItems represent
individual products within an order.

Business rules:
- Whale customers order frequently; low-frequency customers order infrequently
- AOV varies by segment (whales spend more per order)
- Q4 has +40% volume, Black Friday week has +150%
- Items per order follows log-normal (median 2, long tail)
"""

import math
import random
from datetime import date, datetime, timedelta
from enum import Enum
from uuid import uuid4

from faker import Faker
from pydantic import BaseModel, Field

from generator.entities.customer import CustomerSegment, Region


# ─────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────


class OrderStatus(str, Enum):
    """Order lifecycle status."""

    PLACED = "placed"
    PAID = "paid"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class OrderChannel(str, Enum):
    """How the order was placed."""

    WEB = "web"
    MOBILE_APP = "mobile_app"
    MARKETPLACE_API = "marketplace_api"


class DeviceType(str, Enum):
    """Device used to place the order."""

    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"


# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────


class OrderItem(BaseModel):
    """A single product line within an order."""

    order_item_id: str = Field(..., description="Surrogate key (UUID)")
    order_id: str = Field(..., description="FK to fact_orders")
    product_id: str = Field(..., description="FK to dim_products")
    seller_id: str = Field(..., description="FK to dim_sellers (denormalized)")
    category: str = Field(..., description="Product category (denormalized)")
    quantity: int = Field(..., ge=1)
    unit_price: float = Field(..., gt=0)
    unit_cost: float = Field(..., gt=0)
    discount_amount: float = Field(..., ge=0)
    tax_amount: float = Field(..., ge=0)
    line_total: float


class Order(BaseModel):
    """
    A marketplace order placed by a customer.

    Contains header-level info. Line items are in OrderItem.
    """

    order_id: str = Field(..., description="Surrogate key (UUID)")
    order_number: str = Field(..., description="Human-readable order number")
    customer_id: str = Field(..., description="FK to dim_customers")
    region: str
    order_status: OrderStatus
    order_channel: OrderChannel
    device_type: DeviceType
    order_placed_at: datetime
    currency: str = Field(default="USD")
    subtotal: float = Field(..., ge=0)
    discount_amount: float = Field(..., ge=0)
    tax_amount: float = Field(..., ge=0)
    shipping_cost: float = Field(..., ge=0)
    total_amount: float = Field(..., ge=0)
    item_count: int = Field(..., ge=1)
    is_first_order: bool
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────


# Status distribution for completed orders (3-year historical)
STATUS_WEIGHTS: dict[OrderStatus, float] = {
    OrderStatus.DELIVERED: 0.72,
    OrderStatus.SHIPPED: 0.05,
    OrderStatus.IN_TRANSIT: 0.03,
    OrderStatus.PAID: 0.02,
    OrderStatus.PLACED: 0.01,
    OrderStatus.CANCELLED: 0.12,
    OrderStatus.REFUNDED: 0.05,
}

# Channel distribution
CHANNEL_WEIGHTS: dict[OrderChannel, float] = {
    OrderChannel.WEB: 0.40,
    OrderChannel.MOBILE_APP: 0.55,
    OrderChannel.MARKETPLACE_API: 0.05,
}

# Device distribution
DEVICE_WEIGHTS: dict[DeviceType, float] = {
    DeviceType.DESKTOP: 0.30,
    DeviceType.MOBILE: 0.60,
    DeviceType.TABLET: 0.10,
}

# How many orders each customer segment generates per year (avg)
SEGMENT_ANNUAL_ORDERS: dict[str, tuple[int, int]] = {
    "whale": (15, 40),
    "regular": (3, 8),
    "bargain_hunter": (2, 6),
    "low_frequency": (1, 2),
}

# Currency by region
REGION_CURRENCY: dict[str, str] = {
    "US": "USD",
    "EU": "EUR",
    "LATAM": "BRL",
}

# Tax rate by region
REGION_TAX_RATE: dict[str, float] = {
    "US": 0.08,
    "EU": 0.20,
    "LATAM": 0.15,
}

# Shipping cost range
SHIPPING_COST_RANGE: tuple[float, float] = (3.99, 15.99)

# Monthly seasonality multipliers (Jan=1 ... Dec=12)
MONTHLY_SEASONALITY: dict[int, float] = {
    1: 0.75,   # post-holiday slump
    2: 0.80,
    3: 0.90,
    4: 0.95,
    5: 1.00,
    6: 1.00,
    7: 0.90,   # summer dip
    8: 0.90,
    9: 1.05,   # back to school
    10: 1.15,  # Q4 ramp
    11: 1.40,  # Black Friday month
    12: 1.35,  # holiday shopping
}


# ─────────────────────────────────────────────────────────
# Helper: customer data structure for generation
# ─────────────────────────────────────────────────────────


class CustomerProfile:
    """Lightweight holder for customer data needed during order generation."""

    def __init__(
        self,
        customer_id: str,
        region: str,
        segment: str,
        signup_date: date,
    ):
        self.customer_id = customer_id
        self.region = region
        self.segment = segment
        self.signup_date = signup_date
        self.order_count = 0


class ProductInfo:
    """Lightweight holder for product data needed during order generation."""

    def __init__(
        self,
        product_id: str,
        seller_id: str,
        category: str,
        price: float,
        cost: float,
        seller_onboarding_date: date,
        seller_sales_profile: str,
        seller_sales_end_date: date | None,
    ):
        self.product_id = product_id
        self.seller_id = seller_id
        self.category = category
        self.price = price
        self.cost = cost
        self.seller_onboarding_date = seller_onboarding_date
        self.seller_sales_profile = seller_sales_profile
        self.seller_sales_end_date = seller_sales_end_date


# ─────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────


def _pick_order_date(
    customer: CustomerProfile,
    start_date: date,
    end_date: date,
) -> datetime:
    """Pick a random order date between start and end, after customer signup."""
    earliest = max(start_date, customer.signup_date)
    if earliest >= end_date:
        earliest = end_date - timedelta(days=1)

    days_range = (end_date - earliest).days
    if days_range <= 0:
        days_range = 1

    order_date = earliest + timedelta(days=random.randint(0, days_range))

    # Add time of day — peak hours 10am-10pm
    hour = random.choices(
        list(range(24)),
        weights=[
            1, 1, 1, 1, 1, 1,       # 0-5: very low
            3, 5, 7, 8, 9, 10,      # 6-11: morning ramp
            10, 9, 8, 8, 9, 10,     # 12-17: afternoon
            10, 10, 9, 7, 4, 2,     # 18-23: evening peak then drop
        ],
        k=1,
    )[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    return datetime(
        order_date.year, order_date.month, order_date.day,
        hour, minute, second,
    )


def _is_product_available(
    product: ProductInfo,
    order_date: date,
) -> bool:
    """Check whether the seller can receive a sale on this date."""

    if product.seller_sales_profile == "no_sales":
        return False

    if order_date < product.seller_onboarding_date:
        return False

    if product.seller_sales_end_date is None:
        return False

    return order_date <= product.seller_sales_end_date


def _select_available_products(
    products: list[ProductInfo],
    order_date: date,
    item_count: int,
) -> list[ProductInfo]:
    """
    Select products whose sellers are available on the order date.

    Rejection sampling avoids rebuilding a 50K-product pool for every
    generated order while preserving random product selection.
    """

    selected: list[ProductInfo] = []
    attempts = 0
    max_attempts = max(500, item_count * 100)

    while len(selected) < item_count and attempts < max_attempts:
        product = random.choice(products)
        attempts += 1

        if _is_product_available(product, order_date):
            selected.append(product)

    if len(selected) != item_count:
        raise RuntimeError(
            "Unable to find enough products from sellers available "
            f"on {order_date}. Selected {len(selected)} of {item_count}."
        )

    return selected


def _generate_order_items(
    order_id: str,
    products: list[ProductInfo],
    segment: str,
    order_dt: datetime,
) -> list[OrderItem]:
    """Generate 1-N order items for a single order."""

    # Items per order: log-normal, median ~2
    num_items = max(1, int(random.lognormvariate(0.7, 0.6)))
    num_items = min(num_items, 10)  # cap at 10

    # Whales tend to buy more items
    if segment == "whale":
        num_items = max(2, int(num_items * 1.5))
        num_items = min(num_items, 15)

    selected_products = _select_available_products(
        products=products,
        order_date=order_dt.date(),
        item_count=num_items,
    )
    items = []

    for product in selected_products:
        quantity = random.choices(
            [1, 2, 3, 4, 5],
            weights=[0.70, 0.18, 0.07, 0.03, 0.02],
            k=1,
        )[0]

        # Discount: 20% of items get a discount
        if random.random() < 0.20:
            discount_pct = random.choice([0.05, 0.10, 0.15, 0.20, 0.25])
            discount_amount = round(product.price * quantity * discount_pct, 2)
        else:
            discount_amount = 0.0

        line_subtotal = round(product.price * quantity, 2)
        tax_amount = round((line_subtotal - discount_amount) * 0.10, 2)
        line_total = round(line_subtotal - discount_amount + tax_amount, 2)

        items.append(OrderItem(
            order_item_id=str(uuid4()),
            order_id=order_id,
            product_id=product.product_id,
            seller_id=product.seller_id,
            category=product.category,
            quantity=quantity,
            unit_price=product.price,
            unit_cost=product.cost,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            line_total=line_total,
        ))

    return items


def generate_orders(
    customers: list[CustomerProfile],
    products: list[ProductInfo],
    start_date: date = date(2023, 1, 1),
    end_date: date = date(2025, 12, 31),
    target_orders: int = 100_000,
    seed: int | None = None,
) -> tuple[list[Order], list[OrderItem]]:
    """
    Generate synthetic orders and order items.

    Parameters
    ----------
    customers : list[CustomerProfile]
        Customer profiles loaded from Parquet.
    products : list[ProductInfo]
        Product info loaded from Parquet.
    start_date : date
        Start of the order generation window.
    end_date : date
        End of the order generation window.
    target_orders : int
        Approximate number of orders to generate.
    seed : int, optional
        Random seed for reproducibility.

    Returns
    -------
    tuple[list[Order], list[OrderItem]]
        Orders and their line items.
    """
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    fake = Faker()

    # Group customers by segment for weighted selection
    segment_customers: dict[str, list[CustomerProfile]] = {}
    for c in customers:
        segment_customers.setdefault(c.segment, []).append(c)

    # Calculate how many orders each segment contributes
    # Based on segment frequency × segment size
    segment_order_share: dict[str, float] = {}
    total_weight = 0.0
    for seg, custs in segment_customers.items():
        low, high = SEGMENT_ANNUAL_ORDERS.get(seg, (1, 3))
        avg_orders = (low + high) / 2
        weight = len(custs) * avg_orders
        segment_order_share[seg] = weight
        total_weight += weight

    # Normalize to target
    segment_order_counts: dict[str, int] = {}
    for seg, weight in segment_order_share.items():
        segment_order_counts[seg] = int(target_orders * weight / total_weight)

    all_orders: list[Order] = []
    all_items: list[OrderItem] = []
    order_counter = 0
    customer_first_orders: set[str] = set()

    for seg, num_orders in segment_order_counts.items():
        seg_customers = segment_customers[seg]
        if not seg_customers:
            continue

        for _ in range(num_orders):
            # Pick a customer from this segment
            customer = random.choice(seg_customers)

            # Pick order date
            order_dt = _pick_order_date(customer, start_date, end_date)

            # Apply seasonality — skip some orders in low months
            month_mult = MONTHLY_SEASONALITY.get(order_dt.month, 1.0)
            if random.random() > month_mult:
                continue

            order_id = str(uuid4())
            order_counter += 1

            # Is this the customer's first order?
            is_first = customer.customer_id not in customer_first_orders
            customer_first_orders.add(customer.customer_id)

            # Generate order items
            items = _generate_order_items(
                order_id=order_id,
                products=products,
                segment=seg,
                order_dt=order_dt,
            )

            # Calculate order totals from items
            subtotal = round(sum(i.unit_price * i.quantity for i in items), 2)
            discount = round(sum(i.discount_amount for i in items), 2)
            tax = round(sum(i.tax_amount for i in items), 2)
            shipping = round(random.uniform(*SHIPPING_COST_RANGE), 2)
            total = round(subtotal - discount + tax + shipping, 2)

            # Order status
            status = random.choices(
                list(STATUS_WEIGHTS.keys()),
                weights=list(STATUS_WEIGHTS.values()),
                k=1,
            )[0]

            # Channel and device
            channel = random.choices(
                list(CHANNEL_WEIGHTS.keys()),
                weights=list(CHANNEL_WEIGHTS.values()),
                k=1,
            )[0]

            device = random.choices(
                list(DEVICE_WEIGHTS.keys()),
                weights=list(DEVICE_WEIGHTS.values()),
                k=1,
            )[0]

            currency = REGION_CURRENCY.get(customer.region, "USD")

            order = Order(
                order_id=order_id,
                order_number=f"ORD-{order_dt.year}-{order_counter:08d}",
                customer_id=customer.customer_id,
                region=customer.region,
                order_status=status,
                order_channel=channel,
                device_type=device,
                order_placed_at=order_dt,
                currency=currency,
                subtotal=subtotal,
                discount_amount=discount,
                tax_amount=tax,
                shipping_cost=shipping,
                total_amount=total,
                item_count=len(items),
                is_first_order=is_first,
                created_at=order_dt,
                updated_at=order_dt,
            )

            all_orders.append(order)
            all_items.extend(items)

    return all_orders, all_items
