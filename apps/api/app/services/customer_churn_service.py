from __future__ import annotations

from math import ceil
from uuid import UUID

from fastapi import (
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.models import (
    CustomerChurnScore,
    User,
)
from app.repositories import (
    CustomerChurnScoreRepository,
)
from app.schemas import (
    CustomerChurnScorePage,
    CustomerChurnScoreResponse,
    CustomerChurnSummaryResponse,
)


class CustomerChurnService:
    @staticmethod
    def _latest_batch(
        database: Session,
    ) -> tuple:
        batch = (
            CustomerChurnScoreRepository
            .get_latest_batch(database)
        )

        if batch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "No customer churn scores "
                    "are available."
                ),
            )

        return batch

    @staticmethod
    def _to_response(
        score: CustomerChurnScore,
        user: User,
    ) -> CustomerChurnScoreResponse:
        return CustomerChurnScoreResponse(
            id=score.id,
            user_id=score.user_id,
            email=user.email,
            full_name=user.full_name,
            feature_snapshot_date=(
                score.feature_snapshot_date
            ),
            days_since_last_order=(
                score.days_since_last_order
            ),
            total_orders=score.total_orders,
            orders_last_30d=(
                score.orders_last_30d
            ),
            orders_last_90d=(
                score.orders_last_90d
            ),
            lifetime_spend=(
                score.lifetime_spend
            ),
            average_order_value=(
                score.average_order_value
            ),
            spend_last_90d=(
                score.spend_last_90d
            ),
            account_age_days=(
                score.account_age_days
            ),
            is_single_order_customer=(
                score.is_single_order_customer
            ),
            churn_probability=float(
                score.churn_probability
            ),
            predicted_churn_flag=(
                score.predicted_churn_flag
            ),
            risk_rank=score.risk_rank,
            risk_percentile=float(
                score.risk_percentile
            ),
            risk_decile=score.risk_decile,
            risk_segment=score.risk_segment,
            recommended_action=(
                score.recommended_action
            ),
            scoring_population_size=(
                score.scoring_population_size
            ),
            probability_threshold=float(
                score.probability_threshold
            ),
            model_name=score.model_name,
            model_version=score.model_version,
            scored_at_utc=score.scored_at_utc,
        )

    @classmethod
    def list_customers(
        cls,
        database: Session,
        *,
        page: int,
        page_size: int,
        risk_segment: str | None,
        predicted_churn: bool | None,
        search: str | None,
    ) -> CustomerChurnScorePage:
        batch = cls._latest_batch(database)

        rows, total = (
            CustomerChurnScoreRepository
            .list_latest(
                database,
                batch,
                page=page,
                page_size=page_size,
                risk_segment=risk_segment,
                predicted_churn=(
                    predicted_churn
                ),
                search=search,
            )
        )

        return CustomerChurnScorePage(
            items=[
                cls._to_response(
                    score,
                    user,
                )
                for score, user in rows
            ],
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=(
                ceil(total / page_size)
                if total
                else 0
            ),
        )

    @classmethod
    def get_customer(
        cls,
        database: Session,
        user_id: UUID,
    ) -> CustomerChurnScoreResponse:
        batch = cls._latest_batch(database)

        row = (
            CustomerChurnScoreRepository
            .get_latest_for_user(
                database,
                batch,
                user_id,
            )
        )

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Customer churn score "
                    "not found."
                ),
            )

        score, user = row

        return cls._to_response(
            score,
            user,
        )

    @classmethod
    def get_summary(
        cls,
        database: Session,
    ) -> CustomerChurnSummaryResponse:
        batch = cls._latest_batch(database)

        values = (
            CustomerChurnScoreRepository
            .summarize_latest(
                database,
                batch,
            )
        )

        return CustomerChurnSummaryResponse(
            **values
        )
