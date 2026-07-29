import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CustomerChurnScore(Base):
    __tablename__ = "customer_churn_scores"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "feature_snapshot_date",
            "model_version",
            name="one_score_per_user_snapshot_model",
        ),
        CheckConstraint(
            "total_orders >= 1",
            name="eligible_customer_has_order",
        ),
        CheckConstraint(
            "days_since_last_order >= 0",
            name="days_since_last_order_nonnegative",
        ),
        CheckConstraint(
            "lifetime_spend >= 0",
            name="lifetime_spend_nonnegative",
        ),
        CheckConstraint(
            (
                "churn_probability >= 0 "
                "AND churn_probability <= 1"
            ),
            name="churn_probability_valid",
        ),
        CheckConstraint(
            (
                "probability_threshold >= 0 "
                "AND probability_threshold <= 1"
            ),
            name="probability_threshold_valid",
        ),
        CheckConstraint(
            "risk_decile BETWEEN 1 AND 10",
            name="risk_decile_valid",
        ),
        CheckConstraint(
            (
                "risk_segment IN ("
                "'high_risk', "
                "'medium_risk', "
                "'low_risk'"
                ")"
            ),
            name="risk_segment_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    feature_snapshot_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    days_since_last_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    total_orders: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    orders_last_30d: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    orders_last_90d: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    lifetime_spend: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    average_order_value: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    spend_last_90d: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )

    account_age_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_single_order_customer: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    churn_probability: Mapped[Decimal] = mapped_column(
        Numeric(12, 10),
        nullable=False,
    )

    predicted_churn_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    risk_rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    risk_percentile: Mapped[Decimal] = mapped_column(
        Numeric(12, 10),
        nullable=False,
    )

    risk_decile: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    risk_segment: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    recommended_action: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    scoring_population_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    probability_threshold: Mapped[Decimal] = mapped_column(
        Numeric(12, 10),
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    model_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    scored_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
