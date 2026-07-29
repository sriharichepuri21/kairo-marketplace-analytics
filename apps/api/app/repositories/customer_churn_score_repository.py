from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import (
    case,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Session

from app.models import (
    CustomerChurnScore,
    User,
)

BatchKey = tuple[date, str]


class CustomerChurnScoreRepository:
    @staticmethod
    def get_latest_batch(
        database: Session,
    ) -> BatchKey | None:
        row = database.execute(
            select(
                CustomerChurnScore.feature_snapshot_date,
                CustomerChurnScore.model_version,
            )
            .order_by(
                CustomerChurnScore.scored_at_utc.desc(),
                CustomerChurnScore
                .feature_snapshot_date
                .desc(),
            )
            .limit(1)
        ).first()

        if row is None:
            return None

        return (
            row.feature_snapshot_date,
            row.model_version,
        )

    @staticmethod
    def list_latest(
        database: Session,
        batch: BatchKey,
        *,
        page: int,
        page_size: int,
        risk_segment: str | None,
        predicted_churn: bool | None,
        search: str | None,
    ) -> tuple[
        list[
            tuple[
                CustomerChurnScore,
                User,
            ]
        ],
        int,
    ]:
        snapshot_date, model_version = batch

        filters = [
            CustomerChurnScore.feature_snapshot_date
            == snapshot_date,

            CustomerChurnScore.model_version
            == model_version,
        ]

        if risk_segment is not None:
            filters.append(
                CustomerChurnScore.risk_segment
                == risk_segment
            )

        if predicted_churn is not None:
            filters.append(
                CustomerChurnScore
                .predicted_churn_flag
                .is_(predicted_churn)
            )

        if search:
            pattern = f"%{search.strip()}%"

            filters.append(
                or_(
                    User.email.ilike(pattern),
                    User.full_name.ilike(pattern),
                )
            )

        total = database.scalar(
            select(
                func.count(
                    CustomerChurnScore.id
                )
            )
            .join(
                User,
                User.id
                == CustomerChurnScore.user_id,
            )
            .where(*filters)
        )

        statement = (
            select(
                CustomerChurnScore,
                User,
            )
            .join(
                User,
                User.id
                == CustomerChurnScore.user_id,
            )
            .where(*filters)
            .order_by(
                CustomerChurnScore
                .churn_probability
                .desc(),
                User.email.asc(),
            )
            .offset(
                (page - 1) * page_size
            )
            .limit(page_size)
        )

        rows = database.execute(
            statement
        ).all()

        results = [
            (
                score,
                user,
            )
            for score, user in rows
        ]

        return results, int(total or 0)

    @staticmethod
    def get_latest_for_user(
        database: Session,
        batch: BatchKey,
        user_id: UUID,
    ) -> tuple[
        CustomerChurnScore,
        User,
    ] | None:
        snapshot_date, model_version = batch

        row = database.execute(
            select(
                CustomerChurnScore,
                User,
            )
            .join(
                User,
                User.id
                == CustomerChurnScore.user_id,
            )
            .where(
                CustomerChurnScore.user_id
                == user_id,

                CustomerChurnScore
                .feature_snapshot_date
                == snapshot_date,

                CustomerChurnScore.model_version
                == model_version,
            )
        ).first()

        if row is None:
            return None

        return (
            row[0],
            row[1],
        )

    @staticmethod
    def summarize_latest(
        database: Session,
        batch: BatchKey,
    ) -> dict[str, Any]:
        snapshot_date, model_version = batch

        row = database.execute(
            select(
                func.count(
                    CustomerChurnScore.id
                ).label(
                    "eligible_customers"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                CustomerChurnScore
                                .predicted_churn_flag
                                .is_(True),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "predicted_churners"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                CustomerChurnScore
                                .risk_segment
                                == "high_risk",
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "high_risk_customers"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                CustomerChurnScore
                                .risk_segment
                                == "medium_risk",
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "medium_risk_customers"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                CustomerChurnScore
                                .risk_segment
                                == "low_risk",
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "low_risk_customers"
                ),

                func.avg(
                    CustomerChurnScore
                    .churn_probability
                ).label(
                    "average_churn_probability"
                ),

                func.max(
                    CustomerChurnScore
                    .churn_probability
                ).label(
                    "maximum_churn_probability"
                ),

                func.max(
                    CustomerChurnScore
                    .probability_threshold
                ).label(
                    "probability_threshold"
                ),

                func.max(
                    CustomerChurnScore
                    .model_name
                ).label(
                    "model_name"
                ),

                func.max(
                    CustomerChurnScore
                    .scored_at_utc
                ).label(
                    "scored_at_utc"
                ),
            )
            .where(
                CustomerChurnScore
                .feature_snapshot_date
                == snapshot_date,

                CustomerChurnScore.model_version
                == model_version,
            )
        ).one()

        return {
            "feature_snapshot_date": (
                snapshot_date
            ),
            "model_version": model_version,
            "model_name": row.model_name,
            "scored_at_utc": row.scored_at_utc,
            "eligible_customers": int(
                row.eligible_customers or 0
            ),
            "predicted_churners": int(
                row.predicted_churners or 0
            ),
            "high_risk_customers": int(
                row.high_risk_customers or 0
            ),
            "medium_risk_customers": int(
                row.medium_risk_customers or 0
            ),
            "low_risk_customers": int(
                row.low_risk_customers or 0
            ),
            "average_churn_probability": float(
                row.average_churn_probability
                or 0
            ),
            "maximum_churn_probability": float(
                row.maximum_churn_probability
                or 0
            ),
            "probability_threshold": float(
                row.probability_threshold
                or 0
            ),
        }
