"""
Import live customer churn scores from CSV into PostgreSQL.

The import is idempotent. Existing rows at the same user, snapshot,
and model-version grain are updated rather than duplicated.

Usage:
    python -m app.scripts.import_customer_churn_scores /tmp/scores.csv
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.database import SessionLocal
from app.models import (
    CustomerChurnScore,
    User,
)

REQUIRED_COLUMNS = {
    "user_id",
    "feature_snapshot_date",
    "days_since_last_order",
    "total_orders",
    "orders_last_30d",
    "orders_last_90d",
    "lifetime_spend",
    "average_order_value",
    "spend_last_90d",
    "account_age_days",
    "is_single_order_customer",
    "churn_probability",
    "predicted_churn_flag",
    "risk_rank",
    "risk_percentile",
    "risk_decile",
    "risk_segment",
    "recommended_action",
    "scoring_population_size",
    "probability_threshold",
    "model_name",
    "model_version",
    "scored_at_utc",
}


def parse_bool(
    value: str,
) -> bool:
    normalized = value.strip().lower()

    if normalized in {
        "1",
        "true",
        "t",
        "yes",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "f",
        "no",
    }:
        return False

    raise ValueError(
        f"Invalid Boolean value: {value!r}"
    )


def parse_datetime(
    value: str,
) -> datetime:
    normalized = value.strip().replace(
        "Z",
        "+00:00",
    )

    return datetime.fromisoformat(
        normalized
    )


def load_rows(
    path: Path,
) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Score CSV was not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        columns = set(
            reader.fieldnames or []
        )

        missing = sorted(
            REQUIRED_COLUMNS - columns
        )

        if missing:
            raise ValueError(
                "Score CSV is missing columns: "
                f"{missing}"
            )

        rows: list[
            dict[str, object]
        ] = []

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            try:
                values = {
                    "user_id": UUID(
                        row["user_id"]
                    ),
                    "feature_snapshot_date": (
                        date.fromisoformat(
                            row[
                                "feature_snapshot_date"
                            ]
                        )
                    ),
                    "days_since_last_order": int(
                        float(
                            row[
                                "days_since_last_order"
                            ]
                        )
                    ),
                    "total_orders": int(
                        float(
                            row["total_orders"]
                        )
                    ),
                    "orders_last_30d": int(
                        float(
                            row["orders_last_30d"]
                        )
                    ),
                    "orders_last_90d": int(
                        float(
                            row["orders_last_90d"]
                        )
                    ),
                    "lifetime_spend": Decimal(
                        row["lifetime_spend"]
                    ),
                    "average_order_value": Decimal(
                        row[
                            "average_order_value"
                        ]
                    ),
                    "spend_last_90d": Decimal(
                        row["spend_last_90d"]
                    ),
                    "account_age_days": int(
                        float(
                            row["account_age_days"]
                        )
                    ),
                    "is_single_order_customer": (
                        parse_bool(
                            row[
                                "is_single_order_customer"
                            ]
                        )
                    ),
                    "churn_probability": Decimal(
                        row["churn_probability"]
                    ),
                    "predicted_churn_flag": (
                        parse_bool(
                            row[
                                "predicted_churn_flag"
                            ]
                        )
                    ),
                    "risk_rank": int(
                        float(
                            row["risk_rank"]
                        )
                    ),
                    "risk_percentile": Decimal(
                        row["risk_percentile"]
                    ),
                    "risk_decile": int(
                        float(
                            row["risk_decile"]
                        )
                    ),
                    "risk_segment": row[
                        "risk_segment"
                    ].strip(),
                    "recommended_action": row[
                        "recommended_action"
                    ].strip(),
                    "scoring_population_size": int(
                        float(
                            row[
                                "scoring_population_size"
                            ]
                        )
                    ),
                    "probability_threshold": Decimal(
                        row[
                            "probability_threshold"
                        ]
                    ),
                    "model_name": row[
                        "model_name"
                    ].strip(),
                    "model_version": row[
                        "model_version"
                    ].strip(),
                    "scored_at_utc": parse_datetime(
                        row["scored_at_utc"]
                    ),
                }

            except (
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                raise ValueError(
                    "Invalid churn-score row "
                    f"{row_number}: {error}"
                ) from error

            rows.append(values)

    if not rows:
        raise ValueError(
            "Score CSV contains no records."
        )

    return rows


def import_scores(
    path: Path,
) -> None:
    rows = load_rows(path)

    user_ids = {
        row["user_id"]
        for row in rows
    }

    database = SessionLocal()

    try:
        existing_user_ids = set(
            database.scalars(
                select(User.id).where(
                    User.id.in_(user_ids)
                )
            ).all()
        )

        missing_users = sorted(
            str(user_id)
            for user_id in (
                user_ids
                - existing_user_ids
            )
        )

        if missing_users:
            raise ValueError(
                "Scores reference users that do "
                "not exist in PostgreSQL: "
                f"{missing_users}"
            )

        snapshot_groups: dict[
            tuple[date, str],
            set[UUID],
        ] = defaultdict(set)

        for values in rows:
            snapshot_groups[
                (
                    values[
                        "feature_snapshot_date"
                    ],
                    values["model_version"],
                )
            ].add(
                values["user_id"]
            )

            statement = insert(
                CustomerChurnScore
            ).values(
                **values
            )

            statement = (
                statement.on_conflict_do_update(
                    index_elements=[
                        CustomerChurnScore.user_id,
                        CustomerChurnScore.feature_snapshot_date,
                        CustomerChurnScore.model_version,
                    ],
                    set_={
                        "days_since_last_order": (
                            statement.excluded
                            .days_since_last_order
                        ),
                        "total_orders": (
                            statement.excluded
                            .total_orders
                        ),
                        "orders_last_30d": (
                            statement.excluded
                            .orders_last_30d
                        ),
                        "orders_last_90d": (
                            statement.excluded
                            .orders_last_90d
                        ),
                        "lifetime_spend": (
                            statement.excluded
                            .lifetime_spend
                        ),
                        "average_order_value": (
                            statement.excluded
                            .average_order_value
                        ),
                        "spend_last_90d": (
                            statement.excluded
                            .spend_last_90d
                        ),
                        "account_age_days": (
                            statement.excluded
                            .account_age_days
                        ),
                        "is_single_order_customer": (
                            statement.excluded
                            .is_single_order_customer
                        ),
                        "churn_probability": (
                            statement.excluded
                            .churn_probability
                        ),
                        "predicted_churn_flag": (
                            statement.excluded
                            .predicted_churn_flag
                        ),
                        "risk_rank": (
                            statement.excluded
                            .risk_rank
                        ),
                        "risk_percentile": (
                            statement.excluded
                            .risk_percentile
                        ),
                        "risk_decile": (
                            statement.excluded
                            .risk_decile
                        ),
                        "risk_segment": (
                            statement.excluded
                            .risk_segment
                        ),
                        "recommended_action": (
                            statement.excluded
                            .recommended_action
                        ),
                        "scoring_population_size": (
                            statement.excluded
                            .scoring_population_size
                        ),
                        "probability_threshold": (
                            statement.excluded
                            .probability_threshold
                        ),
                        "model_name": (
                            statement.excluded
                            .model_name
                        ),
                        "scored_at_utc": (
                            statement.excluded
                            .scored_at_utc
                        ),
                        "updated_at": func.now(),
                    },
                )
            )

            database.execute(statement)

        stale_deleted = 0

        for (
            snapshot_date,
            model_version,
        ), imported_user_ids in (
            snapshot_groups.items()
        ):
            result = database.execute(
                delete(
                    CustomerChurnScore
                ).where(
                    CustomerChurnScore
                    .feature_snapshot_date
                    == snapshot_date,

                    CustomerChurnScore
                    .model_version
                    == model_version,

                    CustomerChurnScore
                    .user_id
                    .notin_(
                        imported_user_ids
                    ),
                )
            )

            stale_deleted += (
                result.rowcount or 0
            )

        database.commit()

    except Exception:
        database.rollback()
        raise

    finally:
        database.close()

    print(
        f"Imported or updated "
        f"{len(rows):,} churn scores."
    )

    print(
        f"Deleted {stale_deleted:,} "
        "stale scores."
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "csv_path",
        type=Path,
    )

    arguments = parser.parse_args()

    import_scores(
        arguments.csv_path
    )


if __name__ == "__main__":
    main()
