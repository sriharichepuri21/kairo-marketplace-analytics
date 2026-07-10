"""
Review entity model and generator.

~15% of delivered orders leave a review.
Rating follows a J-curve: 62% five-star, 10% one-star.
Review text length correlates with extreme ratings.
"""

import random
from datetime import datetime, timedelta
from uuid import uuid4

from faker import Faker
from pydantic import BaseModel, Field


class Review(BaseModel):
    review_id: str = Field(..., description="Surrogate key (UUID)")
    order_id: str
    order_item_id: str
    product_id: str
    customer_id: str
    seller_id: str
    rating: int = Field(..., ge=1, le=5)
    title: str
    review_text: str
    is_verified_purchase: bool = True
    helpful_votes: int = Field(default=0, ge=0)
    total_votes: int = Field(default=0, ge=0)
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime


# J-curve rating distribution
RATING_WEIGHTS: dict[int, float] = {
    5: 0.62,
    4: 0.15,
    3: 0.08,
    2: 0.05,
    1: 0.10,
}

# Review probability — 15% of delivered items get reviewed
REVIEW_RATE = 0.15

# Positive review title templates
POSITIVE_TITLES = [
    "Love it!", "Great product", "Exactly what I needed",
    "Highly recommend", "Amazing quality", "Best purchase ever",
    "Worth every penny", "Five stars", "Perfect", "Exceeded expectations",
    "Very happy", "Will buy again", "Fantastic", "Great value",
]

# Negative review title templates
NEGATIVE_TITLES = [
    "Disappointed", "Not as described", "Poor quality",
    "Would not recommend", "Waste of money", "Terrible",
    "Broke after a week", "Very unhappy", "Do not buy",
    "Expected better", "Cheap materials", "Returned immediately",
]

# Neutral review title templates
NEUTRAL_TITLES = [
    "It's okay", "Decent product", "Average",
    "Does the job", "Nothing special", "Fair enough",
    "Mixed feelings", "Could be better", "Acceptable",
]


class DeliveredItemReviewInfo:
    def __init__(
        self,
        order_id: str,
        order_item_id: str,
        product_id: str,
        customer_id: str,
        seller_id: str,
        delivered_at: datetime,
    ):
        self.order_id = order_id
        self.order_item_id = order_item_id
        self.product_id = product_id
        self.customer_id = customer_id
        self.seller_id = seller_id
        self.delivered_at = delivered_at


def _generate_review_text(fake: Faker, rating: int) -> str:
    """Generate review text. Extreme ratings get longer reviews."""
    if rating >= 4:
        sentences = random.randint(2, 5)
    elif rating <= 2:
        sentences = random.randint(3, 6)
    else:
        sentences = random.randint(1, 3)

    return " ".join(fake.sentence() for _ in range(sentences))


def generate_reviews(
    delivered_items: list[DeliveredItemReviewInfo],
    seed: int | None = None,
) -> list[Review]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    fake = Faker()
    reviews: list[Review] = []

    for item in delivered_items:
        if random.random() > REVIEW_RATE:
            continue

        rating = random.choices(
            list(RATING_WEIGHTS.keys()),
            weights=list(RATING_WEIGHTS.values()),
            k=1,
        )[0]

        # Title based on rating
        if rating >= 4:
            title = random.choice(POSITIVE_TITLES)
        elif rating <= 2:
            title = random.choice(NEGATIVE_TITLES)
        else:
            title = random.choice(NEUTRAL_TITLES)

        review_text = _generate_review_text(fake, rating)

        # Submitted 1-60 days after delivery
        days_after = random.randint(1, 60)
        submitted_at = item.delivered_at + timedelta(days=days_after)

        # Helpful votes — older reviews and extreme ratings get more
        max_votes = random.randint(0, 30)
        helpful_votes = random.randint(0, max_votes)
        total_votes = helpful_votes + random.randint(0, max(1, max_votes - helpful_votes))

        reviews.append(Review(
            review_id=str(uuid4()),
            order_id=item.order_id,
            order_item_id=item.order_item_id,
            product_id=item.product_id,
            customer_id=item.customer_id,
            seller_id=item.seller_id,
            rating=rating,
            title=title,
            review_text=review_text,
            is_verified_purchase=True,
            helpful_votes=helpful_votes,
            total_votes=total_votes,
            submitted_at=submitted_at,
            created_at=submitted_at,
            updated_at=submitted_at,
        ))

    return reviews