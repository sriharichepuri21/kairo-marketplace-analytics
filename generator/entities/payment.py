"""
Payment entity model and generator.

Each order has one or more payment attempts. ~5% of first attempts
fail and get retried, creating realistic multi-row payment data.
"""

import random
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

from faker import Faker
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────


class PaymentMethod(str, Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    BANK_TRANSFER = "bank_transfer"


class CardBrand(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    CHARGEBACK = "chargeback"


class PaymentProcessor(str, Enum):
    STRIPE = "stripe"
    ADYEN = "adyen"
    MERCADOPAGO = "mercadopago"


# ─────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────


class Payment(BaseModel):
    """A single payment attempt for an order."""

    payment_id: str = Field(..., description="Surrogate key (UUID)")
    order_id: str = Field(..., description="FK to fact_orders")
    payment_method: PaymentMethod
    card_brand: str | None = None
    payment_status: PaymentStatus
    amount: float = Field(..., gt=0)
    currency: str
    processor: PaymentProcessor
    processor_transaction_id: str
    attempted_at: datetime
    completed_at: datetime | None = None
    failure_reason: str | None = None
    is_retry: bool = False
    retry_of_payment_id: str | None = None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────


PAYMENT_METHOD_WEIGHTS: dict[PaymentMethod, float] = {
    PaymentMethod.CREDIT_CARD: 0.40,
    PaymentMethod.DEBIT_CARD: 0.20,
    PaymentMethod.PAYPAL: 0.15,
    PaymentMethod.APPLE_PAY: 0.12,
    PaymentMethod.GOOGLE_PAY: 0.08,
    PaymentMethod.BANK_TRANSFER: 0.05,
}

CARD_BRAND_WEIGHTS: dict[CardBrand, float] = {
    CardBrand.VISA: 0.45,
    CardBrand.MASTERCARD: 0.35,
    CardBrand.AMEX: 0.12,
    CardBrand.DISCOVER: 0.08,
}

# Processor by region
REGION_PROCESSOR: dict[str, PaymentProcessor] = {
    "US": PaymentProcessor.STRIPE,
    "EU": PaymentProcessor.ADYEN,
    "LATAM": PaymentProcessor.MERCADOPAGO,
}

FAILURE_REASONS = [
    "insufficient_funds",
    "card_declined",
    "expired_card",
    "invalid_cvv",
    "processor_timeout",
    "fraud_suspected",
    "bank_rejected",
]

# Probability of first payment attempt failing
FAILURE_RATE = 0.05

# Probability of retry succeeding after failure
RETRY_SUCCESS_RATE = 0.80


# ─────────────────────────────────────────────────────────
# Order info holder
# ─────────────────────────────────────────────────────────


class OrderPaymentInfo:
    """Lightweight holder for order data needed during payment generation."""

    def __init__(
        self,
        order_id: str,
        total_amount: float,
        currency: str,
        region: str,
        order_status: str,
        order_placed_at: datetime,
    ):
        self.order_id = order_id
        self.total_amount = total_amount
        self.currency = currency
        self.region = region
        self.order_status = order_status
        self.order_placed_at = order_placed_at


# ─────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────


def _generate_payment(
    order: OrderPaymentInfo,
    fake: Faker,
    is_retry: bool = False,
    retry_of_id: str | None = None,
    attempted_at: datetime | None = None,
) -> Payment:
    """Generate a single payment attempt."""

    payment_id = str(uuid4())

    # Payment method
    method = random.choices(
        list(PAYMENT_METHOD_WEIGHTS.keys()),
        weights=list(PAYMENT_METHOD_WEIGHTS.values()),
        k=1,
    )[0]

    # Card brand (only for card payments)
    card_brand = None
    if method in (PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD):
        card_brand = random.choices(
            list(CARD_BRAND_WEIGHTS.keys()),
            weights=list(CARD_BRAND_WEIGHTS.values()),
            k=1,
        )[0].value

    # Processor based on region
    processor = REGION_PROCESSOR.get(order.region, PaymentProcessor.STRIPE)

    # Timing
    if attempted_at is None:
        attempted_at = order.order_placed_at + timedelta(seconds=random.randint(1, 30))

    # Determine status
    if order.order_status == "cancelled":
        status = PaymentStatus.FAILED
        failure_reason = random.choice(FAILURE_REASONS)
        completed_at = None
    elif is_retry:
        if random.random() < RETRY_SUCCESS_RATE:
            status = PaymentStatus.CAPTURED
            failure_reason = None
            completed_at = attempted_at + timedelta(seconds=random.randint(2, 15))
        else:
            status = PaymentStatus.FAILED
            failure_reason = random.choice(FAILURE_REASONS)
            completed_at = None
    elif order.order_status == "refunded":
        status = PaymentStatus.REFUNDED
        failure_reason = None
        completed_at = attempted_at + timedelta(seconds=random.randint(2, 15))
    elif random.random() < FAILURE_RATE:
        status = PaymentStatus.FAILED
        failure_reason = random.choice(FAILURE_REASONS)
        completed_at = None
    else:
        status = PaymentStatus.CAPTURED
        failure_reason = None
        completed_at = attempted_at + timedelta(seconds=random.randint(2, 15))

    return Payment(
        payment_id=payment_id,
        order_id=order.order_id,
        payment_method=method,
        card_brand=card_brand,
        payment_status=status,
        amount=order.total_amount,
        currency=order.currency,
        processor=processor,
        processor_transaction_id=f"txn_{uuid4().hex[:16]}",
        attempted_at=attempted_at,
        completed_at=completed_at,
        failure_reason=failure_reason,
        is_retry=is_retry,
        retry_of_payment_id=retry_of_id,
        created_at=attempted_at,
        updated_at=completed_at or attempted_at,
    )


def generate_payments(
    orders: list[OrderPaymentInfo],
    seed: int | None = None,
) -> list[Payment]:
    """
    Generate payment attempts for a list of orders.

    Most orders get one payment. ~5% get a failed first attempt
    followed by a retry, creating realistic multi-row payment data.
    """
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    fake = Faker()
    all_payments: list[Payment] = []

    for order in orders:
        # Generate first payment attempt
        payment = _generate_payment(order, fake)
        all_payments.append(payment)

        # If first attempt failed and order wasn't cancelled, generate retry
        if (
            payment.payment_status == PaymentStatus.FAILED
            and order.order_status != "cancelled"
        ):
            retry_at = payment.attempted_at + timedelta(
                seconds=random.randint(30, 300)
            )
            retry = _generate_payment(
                order, fake,
                is_retry=True,
                retry_of_id=payment.payment_id,
                attempted_at=retry_at,
            )
            all_payments.append(retry)

    return all_payments