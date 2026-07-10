"""
Product entity model and generator.

Products belong to sellers and fall into categories.
Price, weight, and return rates vary by category — these
drive realistic order values and fulfillment metrics downstream.
"""

import random
from datetime import date, datetime
from enum import Enum
from uuid import uuid4

from faker import Faker
from pydantic import BaseModel, Field

from generator.entities.customer import Region
from generator.entities.seller import ProductCategory


# ─────────────────────────────────────────────────────────
# Product model
# ─────────────────────────────────────────────────────────


class Product(BaseModel):
    """
    A product listed on the Kairo marketplace.

    Fields drive downstream analytics:
    - product_id / sku: join keys for orders and inventory
    - seller_id: links product to its seller
    - category / subcategory: dimension for GMV, returns, reviews
    - price / cost: margin analysis
    - weight_kg: fulfillment cost driver
    - return_rate: category-level return expectations
    - avg_rating / review_count: quality signals
    - is_active: filters for current catalog analysis
    """

    product_id: str = Field(..., description="Internal surrogate key (UUID)")
    product_sku: str = Field(..., description="Stock Keeping Unit")
    seller_id: str = Field(..., description="FK to dim_sellers")
    product_name: str
    category: ProductCategory
    subcategory: str
    brand: str
    price: float = Field(..., gt=0)
    cost: float = Field(..., gt=0)
    weight_kg: float = Field(..., ge=0.01)
    avg_rating: float = Field(..., ge=1.0, le=5.0)
    review_count: int = Field(..., ge=0)
    return_rate: float = Field(..., ge=0.0, le=1.0)
    is_active: bool
    launch_date: date
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────
# Configuration — category-specific business rules
# ─────────────────────────────────────────────────────────


# How many products per category (as fraction of total catalog)
CATEGORY_PRODUCT_WEIGHTS: dict[ProductCategory, float] = {
    ProductCategory.ELECTRONICS: 0.15,
    ProductCategory.FASHION: 0.25,
    ProductCategory.HOME_GARDEN: 0.18,
    ProductCategory.BEAUTY: 0.14,
    ProductCategory.SPORTS_OUTDOORS: 0.10,
    ProductCategory.BOOKS_MEDIA: 0.10,
    ProductCategory.TOYS_GAMES: 0.08,
}

# Subcategories per category
SUBCATEGORIES: dict[ProductCategory, list[str]] = {
    ProductCategory.ELECTRONICS: [
        "smartphones", "laptops", "tablets", "headphones",
        "cameras", "smart_home", "accessories", "monitors",
    ],
    ProductCategory.FASHION: [
        "mens_clothing", "womens_clothing", "shoes", "bags",
        "jewelry", "watches", "activewear", "outerwear",
    ],
    ProductCategory.HOME_GARDEN: [
        "furniture", "kitchen", "bedding", "lighting",
        "garden_tools", "storage", "decor", "cleaning",
    ],
    ProductCategory.BEAUTY: [
        "skincare", "makeup", "haircare", "fragrances",
        "supplements", "bath_body", "tools", "mens_grooming",
    ],
    ProductCategory.SPORTS_OUTDOORS: [
        "fitness", "camping", "cycling", "running",
        "team_sports", "water_sports", "yoga", "hiking",
    ],
    ProductCategory.BOOKS_MEDIA: [
        "fiction", "non_fiction", "textbooks", "ebooks",
        "audiobooks", "magazines", "music", "movies",
    ],
    ProductCategory.TOYS_GAMES: [
        "board_games", "puzzles", "action_figures", "dolls",
        "outdoor_toys", "educational", "video_games", "building",
    ],
}

# Price ranges by category (min, max in USD)
CATEGORY_PRICE_RANGE: dict[ProductCategory, tuple[float, float]] = {
    ProductCategory.ELECTRONICS: (15.00, 1200.00),
    ProductCategory.FASHION: (8.00, 350.00),
    ProductCategory.HOME_GARDEN: (10.00, 800.00),
    ProductCategory.BEAUTY: (5.00, 150.00),
    ProductCategory.SPORTS_OUTDOORS: (10.00, 500.00),
    ProductCategory.BOOKS_MEDIA: (3.00, 60.00),
    ProductCategory.TOYS_GAMES: (5.00, 120.00),
}

# Median price by category (log-normal distribution centers here)
CATEGORY_MEDIAN_PRICE: dict[ProductCategory, float] = {
    ProductCategory.ELECTRONICS: 89.00,
    ProductCategory.FASHION: 45.00,
    ProductCategory.HOME_GARDEN: 55.00,
    ProductCategory.BEAUTY: 28.00,
    ProductCategory.SPORTS_OUTDOORS: 42.00,
    ProductCategory.BOOKS_MEDIA: 16.00,
    ProductCategory.TOYS_GAMES: 25.00,
}

# Weight ranges by category (kg)
CATEGORY_WEIGHT_RANGE: dict[ProductCategory, tuple[float, float]] = {
    ProductCategory.ELECTRONICS: (0.1, 8.0),
    ProductCategory.FASHION: (0.1, 2.5),
    ProductCategory.HOME_GARDEN: (0.3, 25.0),
    ProductCategory.BEAUTY: (0.05, 1.5),
    ProductCategory.SPORTS_OUTDOORS: (0.2, 15.0),
    ProductCategory.BOOKS_MEDIA: (0.1, 1.5),
    ProductCategory.TOYS_GAMES: (0.1, 5.0),
}

# Return rate by category — this drives realistic return metrics
CATEGORY_RETURN_RATE: dict[ProductCategory, tuple[float, float]] = {
    ProductCategory.ELECTRONICS: (0.03, 0.08),
    ProductCategory.FASHION: (0.20, 0.35),
    ProductCategory.HOME_GARDEN: (0.05, 0.12),
    ProductCategory.BEAUTY: (0.08, 0.15),
    ProductCategory.SPORTS_OUTDOORS: (0.05, 0.10),
    ProductCategory.BOOKS_MEDIA: (0.01, 0.04),
    ProductCategory.TOYS_GAMES: (0.06, 0.12),
}

# Cost as fraction of price (margin profile)
CATEGORY_COST_FRACTION: dict[ProductCategory, tuple[float, float]] = {
    ProductCategory.ELECTRONICS: (0.55, 0.75),
    ProductCategory.FASHION: (0.25, 0.50),
    ProductCategory.HOME_GARDEN: (0.40, 0.60),
    ProductCategory.BEAUTY: (0.15, 0.40),
    ProductCategory.SPORTS_OUTDOORS: (0.35, 0.55),
    ProductCategory.BOOKS_MEDIA: (0.30, 0.50),
    ProductCategory.TOYS_GAMES: (0.30, 0.55),
}

# Brand name generators per category
BRAND_PREFIXES: dict[ProductCategory, list[str]] = {
    ProductCategory.ELECTRONICS: [
        "TechVolt", "NovaByte", "PixelPro", "ZenithWave", "CoreSync",
        "VoltEdge", "DataPulse", "QuantumLink", "ByteForce", "NeonCircuit",
    ],
    ProductCategory.FASHION: [
        "UrbanThread", "Velvetine", "NordStitch", "PrimeLine", "LuxWeave",
        "SilkRoute", "ArcticWear", "BloomStyle", "EdgeCraft", "TrueForm",
    ],
    ProductCategory.HOME_GARDEN: [
        "NestCraft", "GreenHaven", "HomeSphere", "TerraBuild", "PureNest",
        "OakLine", "BrightSpace", "CozyCore", "BloomField", "RootWorks",
    ],
    ProductCategory.BEAUTY: [
        "GlowLab", "PureSkin", "LuminaBeauty", "VelvetGlow", "ZenGlow",
        "FreshAura", "BloomGlow", "NaturEdge", "ClearSkin", "SilkPetal",
    ],
    ProductCategory.SPORTS_OUTDOORS: [
        "PeakForce", "TrailBlaze", "IronGrip", "VelocityX", "SummitGear",
        "FlexPower", "RapidStride", "TitanFit", "WildEdge", "CoreMotion",
    ],
    ProductCategory.BOOKS_MEDIA: [
        "PageTurn", "InkWell", "StoryVault", "MindPress", "ClearType",
        "BrightPage", "DeepRead", "NovelNest", "WordCraft", "OpenMind",
    ],
    ProductCategory.TOYS_GAMES: [
        "FunSpark", "PlayCraft", "JoyBox", "BrightPlay", "TinyWorld",
        "GameNest", "StarToy", "WonderKit", "PixelPlay", "BuildJoy",
    ],
}

# Product name templates per category
PRODUCT_NAME_TEMPLATES: dict[ProductCategory, list[str]] = {
    ProductCategory.ELECTRONICS: [
        "{brand} Wireless {sub}", "{brand} Pro {sub}", "{brand} Smart {sub}",
        "{brand} Ultra {sub}", "{brand} {sub} Series X",
    ],
    ProductCategory.FASHION: [
        "{brand} Classic {sub}", "{brand} Slim Fit {sub}", "{brand} Premium {sub}",
        "{brand} Essential {sub}", "{brand} {sub} Collection",
    ],
    ProductCategory.HOME_GARDEN: [
        "{brand} Deluxe {sub}", "{brand} Essential {sub}", "{brand} Pro {sub}",
        "{brand} Compact {sub}", "{brand} {sub} Set",
    ],
    ProductCategory.BEAUTY: [
        "{brand} Daily {sub}", "{brand} Hydrating {sub}", "{brand} Glow {sub}",
        "{brand} Natural {sub}", "{brand} {sub} Serum",
    ],
    ProductCategory.SPORTS_OUTDOORS: [
        "{brand} Elite {sub}", "{brand} Pro {sub}", "{brand} Endurance {sub}",
        "{brand} {sub} Gear", "{brand} Max {sub}",
    ],
    ProductCategory.BOOKS_MEDIA: [
        "{brand} Bestseller {sub}", "{brand} {sub} Guide", "{brand} Essential {sub}",
        "{brand} {sub} Edition", "{brand} Complete {sub}",
    ],
    ProductCategory.TOYS_GAMES: [
        "{brand} Super {sub}", "{brand} {sub} Adventure", "{brand} Magic {sub}",
        "{brand} {sub} Deluxe", "{brand} Ultimate {sub}",
    ],
}


# ─────────────────────────────────────────────────────────
# Generator
# ─────────────────────────────────────────────────────────

import math


def _log_normal_price(median: float, low: float, high: float) -> float:
    """
    Generate a price from a log-normal distribution, clamped to a range.

    Log-normal produces the realistic long-tail price distribution
    seen in real e-commerce: many cheap items, few expensive ones.
    """
    mu = math.log(median)
    sigma = 0.5
    price = random.lognormvariate(mu, sigma)
    return round(max(low, min(high, price)), 2)


def generate_product(fake: Faker, seller_ids: list[str]) -> Product:
    """Generate a single synthetic product linked to a random seller."""

    # Pick category
    category = random.choices(
        list(CATEGORY_PRODUCT_WEIGHTS.keys()),
        weights=list(CATEGORY_PRODUCT_WEIGHTS.values()),
        k=1,
    )[0]

    # Pick subcategory
    subcategory = random.choice(SUBCATEGORIES[category])

    # Pick brand
    brand = random.choice(BRAND_PREFIXES[category])

    # Generate product name
    template = random.choice(PRODUCT_NAME_TEMPLATES[category])
    sub_display = subcategory.replace("_", " ").title()
    product_name = template.format(brand=brand, sub=sub_display)

    # Price — log-normal distribution within category range
    price_low, price_high = CATEGORY_PRICE_RANGE[category]
    median_price = CATEGORY_MEDIAN_PRICE[category]
    price = _log_normal_price(median_price, price_low, price_high)

    # Cost — fraction of price (margin varies by category)
    cost_low, cost_high = CATEGORY_COST_FRACTION[category]
    cost = round(price * random.uniform(cost_low, cost_high), 2)

    # Weight
    weight_low, weight_high = CATEGORY_WEIGHT_RANGE[category]
    weight_kg = round(random.uniform(weight_low, weight_high), 2)

    # Return rate
    return_low, return_high = CATEGORY_RETURN_RATE[category]
    return_rate = round(random.uniform(return_low, return_high), 4)

    # Rating — most products cluster 3.5–4.5
    avg_rating = round(random.gauss(4.0, 0.6), 2)
    avg_rating = max(1.0, min(5.0, avg_rating))

    # Review count — log-normal (few products have many reviews)
    review_count = int(random.lognormvariate(3.5, 1.5))
    review_count = max(0, min(50000, review_count))

    # Active status — 90% of products are active
    is_active = random.random() < 0.90

    # Dates
    launch_date = fake.date_between(start_date="-3y", end_date="today")
    launch_dt = datetime.combine(launch_date, datetime.min.time())

    # Assign to a random seller
    seller_id = random.choice(seller_ids)

    return Product(
        product_id=str(uuid4()),
        product_sku=f"SKU-{category.value[:3].upper()}-{fake.random_int(100000, 999999)}",
        seller_id=seller_id,
        product_name=product_name,
        category=category,
        subcategory=subcategory,
        brand=brand,
        price=price,
        cost=cost,
        weight_kg=weight_kg,
        avg_rating=avg_rating,
        review_count=review_count,
        return_rate=return_rate,
        is_active=is_active,
        launch_date=launch_date,
        created_at=launch_dt,
        updated_at=launch_dt,
    )


def generate_products(
    n: int,
    seller_ids: list[str],
    seed: int | None = None,
) -> list[Product]:
    """
    Generate a batch of synthetic products.

    Parameters
    ----------
    n : int
        Number of products to generate.
    seller_ids : list[str]
        Valid seller IDs to assign products to.
    seed : int, optional
        Random seed for reproducibility.
    """
    if not seller_ids:
        raise ValueError("seller_ids cannot be empty — generate sellers first.")

    fake = Faker()
    if seed is not None:
        Faker.seed(seed)
        random.seed(seed)

    return [generate_product(fake, seller_ids) for _ in range(n)]