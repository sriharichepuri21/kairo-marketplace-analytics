"""
Customer entity model and generator.

This module defines the shape of a Kairo customer and produces
synthetic customer records for the data platform.

Key design decision: signup_channel CORRELATES with segment.
Different acquisition channels attract different customer types.
Referral brings the best customers. Paid search brings deal-seekers.
"""

import random
from datetime import date, datetime
from enum import Enum
from uuid import uuid4

from faker import Faker
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────
# Enums — controlled vocabularies for categorical fields
# ─────────────────────────────────────────────────────────


class Region(str, Enum):
    """Geographic regions Kairo operates in."""

    US = "US"
    EU = "EU"
    LATAM = "LATAM"


class CustomerSegment(str, Enum):
    """
    Behavioral segmentation used across the marketplace.

    - whale:          top-tier buyers, high frequency, high AOV
    - regular:        the reliable middle of the distribution
    - bargain_hunter: price-sensitive, promo-driven
    - one_time:       single-purchase customers who never returned
    """

    WHALE = "whale"
    REGULAR = "regular"
    BARGAIN_HUNTER = "bargain_hunter"
    ONE_TIME = "one_time"


class AccountStatus(str, Enum):
    """Account lifecycle status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


# ─────────────────────────────────────────────────────────
# Customer model
# ─────────────────────────────────────────────────────────


class Customer(BaseModel):
    """
    A Kairo marketplace customer.

    Every field has a purpose downstream:
    - customer_id / external_id: internal + business-facing keys
    - email / first_name / last_name: PII we'll later chaos-inject
    - region / country_code: geographic dimensions
    - segment: behavioral dimension (drives generator behavior later)
    - signup_date / signup_channel: cohort analysis inputs
    - account_status: for filtering active customers in metrics
    - created_at / updated_at: audit fields, always present
    """

    customer_id: str = Field(..., description="Internal surrogate key (UUID)")
    customer_external_id: str = Field(..., description="Business-facing key")
    email: str
    first_name: str
    last_name: str
    region: Region
    country_code: str = Field(..., min_length=2, max_length=2)
    segment: CustomerSegment
    signup_date: date
    signup_channel: str
    account_status: AccountStatus
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────
# Configuration — business rules for distributions
# ─────────────────────────────────────────────────────────


# Region distribution — how customers spread across geographies
REGION_WEIGHTS: dict[Region, float] = {
    Region.US: 0.40,
    Region.EU: 0.35,
    Region.LATAM: 0.25,
}

# Region -> list of (country_code, weight) — weights are relative within region
REGION_COUNTRIES: dict[Region, list[tuple[str, float]]] = {
    Region.US: [("US", 1.0)],
    Region.EU: [("GB", 0.30), ("DE", 0.30), ("FR", 0.20), ("ES", 0.10), ("IT", 0.10)],
    Region.LATAM: [("BR", 0.50), ("MX", 0.30), ("AR", 0.10), ("CL", 0.05), ("CO", 0.05)],
}

# Overall segment distribution — reflects a realistic marketplace
# NOTE: This is the GLOBAL average. Actual per-customer segment is
# determined by signup_channel via CHANNEL_SEGMENT_WEIGHTS below.
SEGMENT_WEIGHTS: dict[CustomerSegment, float] = {
    CustomerSegment.WHALE: 0.05,
    CustomerSegment.REGULAR: 0.45,
    CustomerSegment.BARGAIN_HUNTER: 0.25,
    CustomerSegment.ONE_TIME: 0.25,
}

# Signup channels — where the customer came from
SIGNUP_CHANNELS = ["organic", "paid_search", "social", "referral", "email"]

# Channel → segment weights — each channel attracts different customer types
#
# Business rationale:
#   Referral:     Best customers. A friend recommended Kairo — they arrive
#                 with trust and intent. Highest whale rate (10%).
#   Organic:      Strong customers. They actively searched for Kairo —
#                 high intent, good retention. Second-highest whale rate (8%).
#   Email:        Good customers. They opted into marketing — already
#                 engaged with the brand. Moderate whale rate (6%).
#   Social:       Mixed quality. Impulse clicks from Instagram/TikTok.
#                 Some become engaged, many don't return. Low whale rate (4%).
#   Paid search:  Weakest customers. They clicked a Google ad while
#                 price-comparing. Deal-seekers who buy once and leave.
#                 Lowest whale rate (3%), highest one-time rate (32%).
#
CHANNEL_SEGMENT_WEIGHTS: dict[str, dict[CustomerSegment, float]] = {
    "organic": {
        CustomerSegment.WHALE: 0.08,
        CustomerSegment.REGULAR: 0.50,
        CustomerSegment.BARGAIN_HUNTER: 0.25,
        CustomerSegment.ONE_TIME: 0.17,
    },
    "referral": {
        CustomerSegment.WHALE: 0.10,
        CustomerSegment.REGULAR: 0.55,
        CustomerSegment.BARGAIN_HUNTER: 0.20,
        CustomerSegment.ONE_TIME: 0.15,
    },
    "paid_search": {
        CustomerSegment.WHALE: 0.03,
        CustomerSegment.REGULAR: 0.35,
        CustomerSegment.BARGAIN_HUNTER: 0.30,
        CustomerSegment.ONE_TIME: 0.32,
    },
    "social": {
        CustomerSegment.WHALE: 0.04,
        CustomerSegment.REGULAR: 0.40,
        CustomerSegment.BARGAIN_HUNTER: 0.28,
        CustomerSegment.ONE_TIME: 0.28,
    },
    "email": {
        CustomerSegment.WHALE: 0.06,
        CustomerSegment.REGULAR: 0.45,
        CustomerSegment.BARGAIN_HUNTER: 0.30,
        CustomerSegment.ONE_TIME: 0.19,
    },
}


# ─────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────


def generate_customer(fake: Faker) -> Customer:
    """
    Generate a single synthetic customer.

    Parameters
    ----------
    fake : Faker
        A Faker instance used for names, emails, dates.

    Returns
    -------
    Customer
        A fully-populated Customer record.
    """
    # Pick region using weighted distribution
    region = random.choices(
        list(REGION_WEIGHTS.keys()),
        weights=list(REGION_WEIGHTS.values()),
        k=1,
    )[0]

    # Pick country within the chosen region, using country weights
    country_pool = REGION_COUNTRIES[region]
    countries, country_weights = zip(*country_pool)
    country_code = random.choices(countries, weights=country_weights, k=1)[0]

    # Pick channel first — this determines segment distribution
    signup_channel = random.choices(SIGNUP_CHANNELS, k=1)[0]

    # Pick segment using channel-specific weights
    # Different channels attract different customer types
    channel_weights = CHANNEL_SEGMENT_WEIGHTS[signup_channel]
    segment = random.choices(
        list(channel_weights.keys()),
        weights=list(channel_weights.values()),
        k=1,
    )[0]

    # Names + email
    first_name = fake.first_name()
    last_name = fake.last_name()
    email = f"{first_name.lower()}.{last_name.lower()}{fake.random_int(1, 9999)}@example.com"

    # Dates
    signup_date = fake.date_between(start_date="-3y", end_date="today")
    signup_dt = datetime.combine(signup_date, datetime.min.time())

    return Customer(
        customer_id=str(uuid4()),
        customer_external_id=f"CUS-{fake.random_int(10_000_000, 99_999_999)}",
        email=email,
        first_name=first_name,
        last_name=last_name,
        region=region,
        country_code=country_code,
        segment=segment,
        signup_date=signup_date,
        signup_channel=signup_channel,
        account_status=AccountStatus.ACTIVE,
        created_at=signup_dt,
        updated_at=signup_dt,
    )


def generate_customers(n: int, seed: int | None = None) -> list[Customer]:
    """
    Generate a batch of synthetic customers.

    Parameters
    ----------
    n : int
        Number of customers to generate.
    seed : int, optional
        Random seed for reproducibility. Same seed = same output.

    Returns
    -------
    list[Customer]
        List of Customer records.
    """
    fake = Faker()
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)

    return [generate_customer(fake) for _ in range(n)]