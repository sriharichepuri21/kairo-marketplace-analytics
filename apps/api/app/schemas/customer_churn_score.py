from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class CustomerChurnScoreResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    user_id: UUID
    email: EmailStr
    full_name: str

    feature_snapshot_date: date

    days_since_last_order: int
    total_orders: int
    orders_last_30d: int
    orders_last_90d: int

    lifetime_spend: Decimal
    average_order_value: Decimal
    spend_last_90d: Decimal
    account_age_days: int
    is_single_order_customer: bool

    churn_probability: float
    predicted_churn_flag: bool

    risk_rank: int
    risk_percentile: float
    risk_decile: int
    risk_segment: str
    recommended_action: str

    scoring_population_size: int
    probability_threshold: float

    model_name: str
    model_version: str
    scored_at_utc: datetime


class CustomerChurnScorePage(BaseModel):
    items: list[CustomerChurnScoreResponse]

    page: int = Field(
        ge=1,
    )

    page_size: int = Field(
        ge=1,
        le=100,
    )

    total_items: int = Field(
        ge=0,
    )

    total_pages: int = Field(
        ge=0,
    )


class CustomerChurnSummaryResponse(BaseModel):
    feature_snapshot_date: date
    model_name: str
    model_version: str
    scored_at_utc: datetime

    eligible_customers: int
    predicted_churners: int

    high_risk_customers: int
    medium_risk_customers: int
    low_risk_customers: int

    average_churn_probability: float
    maximum_churn_probability: float
    probability_threshold: float
