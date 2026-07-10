"""
Seller entity model and generator.

Sellers are the supply side of the Kairo marketplace.
Their tier, category, and region drive downstream metrics
like GMV contribution, commission revenue, and retention.
"""

import random
from datetime import date, datetime
from enum import Enum
from uuid import uuid4

from faker import Faker
from pydantic import BaseModel, Field

from generator.entities.customer import Region, REGION_WEIGHTS, REGION_COUNTRIES


# ─────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────


class SellerType(str, Enum):
    """Business structure of the seller."""

    INDIVIDUAL = "individual"
    SMALL_BUSINESS = "small_business"
    BRAND = "brand"
    ENTERPRISE = "enterprise"


class SellerTier(str, Enum):
    """
    Performance tier — determines commission rate and visibility.

    Tiers are earned over time based on GMV, ratings, and reliability.
    New sellers start at 'new' and graduate upward.
    """

    NEW = "new"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class ProductCategory(str, Enum):
    """Top-level product categories on the Kairo marketplace."""

    ELECTRONICS = "electronics"
    FASHION = "fashion"
    HOME_GARDEN = "home_garden"
    BEAUTY = "beauty"
    SPORTS_OUTDOORS = "sports_outdoors"
    BOOKS_MEDIA = "books_media"
    TOYS_GAMES = "toys_games"


# ─────────────────────────────────────────────────────────
# Seller model
# ─────────────────────────────────────────────────────────


class Seller(BaseModel):
    """
    A Kairo marketplace seller.

    Fields map to downstream analytics:
    - seller_id / external_id: join keys
    - seller_type: filters for seller ecosystem analysis
    - tier: drives commission rate and seller health metrics
    - primary_category: links sellers to category performance
    - avg_rating / total_reviews: seller quality signals
    - commission_rate: revenue calculation input
    - is_verified / is_suspended: trust & safety dimensions
    """

    seller_id: str = Field(..., description="Internal surrogate key (UUID)")
    seller_external_id: str = Field(..., description="Business-facing key")
    business_name: str
    seller_type: SellerType
    tier: SellerTier
    onboarding_date: date
    region: Region
    country_code: str = Field(..., min_length=2, max_length=2)
    primary_category: ProductCategory
    avg_rating: float = Field(..., ge=1.0, le=5.0)
    total_reviews: int = Field(..., ge=0)
    is_verified: bool
    is_suspended: bool
    commission_rate: float = Field(..., ge=0.0, le=1.0)
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────
# Configuration — business rules
# ─────────────────────────────────────────────────────────


# Seller type distribution
SELLER_TYPE_WEIGHTS: dict[SellerType, float] = {
    SellerType.INDIVIDUAL: 0.40,
    SellerType.SMALL_BUSINESS: 0.35,
    SellerType.BRAND: 0.20,
    SellerType.ENTERPRISE: 0.05,
}

# Tier distribution — most sellers are new or bronze
TIER_WEIGHTS: dict[SellerTier, float] = {
    SellerTier.NEW: 0.25,
    SellerTier.BRONZE: 0.30,
    SellerTier.SILVER: 0.25,
    SellerTier.GOLD: 0.15,
    SellerTier.PLATINUM: 0.05,
}

# Commission rate ranges by tier — higher tier = lower commission (reward)
TIER_COMMISSION_RANGE: dict[SellerTier, tuple[float, float]] = {
    SellerTier.NEW: (0.15, 0.18),
    SellerTier.BRONZE: (0.13, 0.15),
    SellerTier.SILVER: (0.11, 0.13),
    SellerTier.GOLD: (0.09, 0.11),
    SellerTier.PLATINUM: (0.07, 0.09),
}

# Category distribution — what sellers primarily sell
CATEGORY_WEIGHTS: dict[ProductCategory, float] = {
    ProductCategory.ELECTRONICS: 0.15,
    ProductCategory.FASHION: 0.22,
    ProductCategory.HOME_GARDEN: 0.18,
    ProductCategory.BEAUTY: 0.14,
    ProductCategory.SPORTS_OUTDOORS: 0.12,
    ProductCategory.BOOKS_MEDIA: 0.10,
    ProductCategory.TOYS_GAMES: 0.09,
}

# Rating distribution by tier — better sellers have higher ratings
TIER_RATING_RANGE: dict[SellerTier, tuple[float, float]] = {
    SellerTier.NEW: (3.0, 4.5),
    SellerTier.BRONZE: (3.2, 4.6),
    SellerTier.SILVER: (3.5, 4.7),
    SellerTier.GOLD: (4.0, 4.9),
    SellerTier.PLATINUM: (4.5, 5.0),
}

# Review count ranges by tier — established sellers have more reviews
TIER_REVIEW_RANGE: dict[SellerTier, tuple[int, int]] = {
    SellerTier.NEW: (0, 50),
    SellerTier.BRONZE: (20, 200),
    SellerTier.SILVER: (100, 1000),
    SellerTier.GOLD: (500, 5000),
    SellerTier.PLATINUM: (2000, 20000),
}

# Business name suffixes for realism
BUSINESS_SUFFIXES = [
    "Store", "Shop", "Mart", "Direct", "Hub", "Supply",
    "Trading", "Goods", "Market", "Outlet", "Co", "Global",
    "Deals", "Essentials", "Plus", "Express", "Warehouse",
]


# ─────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────


def generate_seller(fake: Faker) -> Seller:
    """Generate a single synthetic seller."""

    # Region and country (reuse customer weights)
    region = random.choices(
        list(REGION_WEIGHTS.keys()),
        weights=list(REGION_WEIGHTS.values()),
        k=1,
    )[0]

    country_pool = REGION_COUNTRIES[region]
    countries, country_weights = zip(*country_pool)
    country_code = random.choices(countries, weights=country_weights, k=1)[0]

    # Seller type
    seller_type = random.choices(
        list(SELLER_TYPE_WEIGHTS.keys()),
        weights=list(SELLER_TYPE_WEIGHTS.values()),
        k=1,
    )[0]

    # Tier
    tier = random.choices(
        list(TIER_WEIGHTS.keys()),
        weights=list(TIER_WEIGHTS.values()),
        k=1,
    )[0]

    # Category
    primary_category = random.choices(
        list(CATEGORY_WEIGHTS.keys()),
        weights=list(CATEGORY_WEIGHTS.values()),
        k=1,
    )[0]

    # Business name — combine a last name with a suffix
    name_base = fake.last_name()
    suffix = random.choice(BUSINESS_SUFFIXES)
    business_name = f"{name_base} {suffix}"

    # Rating and reviews — correlated with tier
    rating_low, rating_high = TIER_RATING_RANGE[tier]
    avg_rating = round(random.uniform(rating_low, rating_high), 2)

    review_low, review_high = TIER_REVIEW_RANGE[tier]
    total_reviews = random.randint(review_low, review_high)

    # Commission rate — correlated with tier (better tier = lower rate)
    comm_low, comm_high = TIER_COMMISSION_RANGE[tier]
    commission_rate = round(random.uniform(comm_low, comm_high), 4)

    # Verification and suspension
    is_verified = tier not in (SellerTier.NEW,) or random.random() < 0.3
    is_suspended = random.random() < 0.02  # 2% suspension rate

    # Dates — sellers onboard over the 3-year window
    onboarding_date = fake.date_between(start_date="-3y", end_date="today")
    onboarding_dt = datetime.combine(onboarding_date, datetime.min.time())

    return Seller(
        seller_id=str(uuid4()),
        seller_external_id=f"SLR-{fake.random_int(10_000_000, 99_999_999)}",
        business_name=business_name,
        seller_type=seller_type,
        tier=tier,
        onboarding_date=onboarding_date,
        region=region,
        country_code=country_code,
        primary_category=primary_category,
        avg_rating=avg_rating,
        total_reviews=total_reviews,
        is_verified=is_verified,
        is_suspended=is_suspended,
        commission_rate=commission_rate,
        created_at=onboarding_dt,
        updated_at=onboarding_dt,
    )


def generate_sellers(n: int, seed: int | None = None) -> list[Seller]:
    """
    Generate a batch of synthetic sellers.

    Parameters
    ----------
    n : int
        Number of sellers to generate.
    seed : int, optional
        Random seed for reproducibility.
    """
    fake = Faker()
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)

    return [generate_seller(fake) for _ in range(n)]