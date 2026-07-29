"""
Score eligible live marketplace customers for churn risk.

Source:
    DuckDB main.mart_customer_features

Eligibility:
    Customers with at least one historical order.

Output:
    analytics/churn_model/data/live_customer_churn_scores.parquet

Usage:
    python analytics/churn_model/06_score_live_customers.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import joblib
import numpy as np
import pandas as pd


CHURN_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CHURN_DIR.parents[1]

DB_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "kairo.duckdb"
)

ARTIFACTS_DIR = (
    CHURN_DIR
    / "model_artifacts"
)

DATA_DIR = (
    CHURN_DIR
    / "data"
)

MODEL_PATH = (
    ARTIFACTS_DIR
    / "live_compatible_model.pkl"
)

CONTRACT_PATH = (
    ARTIFACTS_DIR
    / "live_compatible_feature_contract.json"
)

OUTPUT_PATH = (
    DATA_DIR
    / "live_customer_churn_scores.parquet"
)


def load_json(
    path: Path,
) -> dict[str, Any]:
    """Load and validate a JSON object."""

    if not path.exists():
        raise FileNotFoundError(
            f"Required artifact was not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise TypeError(
            f"Expected a JSON object in {path}"
        )

    return value


def load_model() -> Any:
    """Load and validate the sklearn model pipeline."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model artifact was not found: {MODEL_PATH}"
        )

    model = joblib.load(MODEL_PATH)

    if not hasattr(model, "predict_proba"):
        raise TypeError(
            "Loaded model does not expose predict_proba."
        )

    return model


def load_live_features() -> pd.DataFrame:
    """Read eligible customer features from the DuckDB mart."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB warehouse was not found: {DB_PATH}"
        )

    connection = duckdb.connect(
        str(DB_PATH),
        read_only=True,
    )

    try:
        frame = connection.execute(
            """
            select
                cast(
                    feature_snapshot_date
                    as date
                ) as feature_snapshot_date,

                cast(
                    user_id
                    as varchar
                ) as user_id,

                cast(
                    days_since_last_order
                    as double
                ) as days_since_last_order,

                cast(
                    total_orders
                    as double
                ) as total_orders,

                cast(
                    orders_last_30d
                    as double
                ) as orders_last_30d,

                cast(
                    orders_last_90d
                    as double
                ) as orders_last_90d,

                cast(
                    lifetime_spend
                    as double
                ) as lifetime_spend,

                cast(
                    average_order_value
                    as double
                ) as average_order_value,

                cast(
                    spend_last_90d
                    as double
                ) as spend_last_90d,

                cast(
                    account_age_days
                    as double
                ) as account_age_days

            from main.mart_customer_features

            where total_orders >= 1

            order by user_id
            """
        ).df()

    finally:
        connection.close()

    if frame.empty:
        raise ValueError(
            "No live customers are currently eligible "
            "for churn scoring."
        )

    duplicate_users = (
        frame["user_id"]
        .duplicated()
        .sum()
    )

    if duplicate_users:
        raise ValueError(
            "Live feature mart contains "
            f"{duplicate_users:,} duplicate users."
        )

    if frame["user_id"].isna().any():
        raise ValueError(
            "Live feature mart contains null user IDs."
        )

    frame[
        "is_single_order_customer"
    ] = (
        frame["total_orders"] == 1
    ).astype(int)

    return frame


def validate_feature_contract(
    frame: pd.DataFrame,
    contract: dict[str, Any],
) -> list[str]:
    """Confirm that scoring data matches the saved contract."""

    features = contract.get(
        "feature_columns"
    )

    if not isinstance(features, list):
        raise ValueError(
            "Feature contract does not contain "
            "a valid feature_columns list."
        )

    if not all(
        isinstance(feature, str)
        for feature in features
    ):
        raise ValueError(
            "Feature contract contains invalid feature names."
        )

    missing = sorted(
        set(features)
        - set(frame.columns)
    )

    if missing:
        raise ValueError(
            "Live scoring data is missing features: "
            f"{missing}"
        )

    return features


def assign_risk_segments(
    scores: pd.DataFrame,
    threshold: float,
) -> pd.DataFrame:
    """
    Add relative ranks and absolute risk segments.

    Risk decile is population-relative:
        1 represents the highest relative risk.

    Risk segment is probability-based:
        high:   probability >= threshold
        medium: probability >= half threshold
        low:    probability < half threshold
    """

    output = scores.copy()

    population_size = len(output)

    descending_rank = (
        output["churn_probability"]
        .rank(
            method="first",
            ascending=False,
        )
        .astype(int)
    )

    output["risk_rank"] = descending_rank

    output["risk_percentile"] = (
        1.0
        - (
            descending_rank - 1
        )
        / population_size
    )

    output["risk_decile"] = (
        np.floor(
            (
                descending_rank - 1
            )
            * 10
            / population_size
        )
        + 1
    ).clip(
        1,
        10,
    ).astype(int)

    medium_threshold = (
        threshold / 2.0
    )

    output["risk_segment"] = np.select(
        [
            output["churn_probability"]
            >= threshold,

            output["churn_probability"]
            >= medium_threshold,
        ],
        [
            "high_risk",
            "medium_risk",
        ],
        default="low_risk",
    )

    output["recommended_action"] = np.select(
        [
            output["risk_segment"]
            == "high_risk",

            output["risk_segment"]
            == "medium_risk",
        ],
        [
            "priority_retention_outreach",
            "targeted_reengagement",
        ],
        default="standard_monitoring",
    )

    output[
        "scoring_population_size"
    ] = population_size

    return output


def main() -> None:
    """Generate live customer churn scores."""

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    contract = load_json(
        CONTRACT_PATH
    )

    model = load_model()

    customers = load_live_features()

    feature_columns = (
        validate_feature_contract(
            customers,
            contract,
        )
    )

    probabilities = model.predict_proba(
        customers[feature_columns]
    )[:, 1]

    if len(probabilities) != len(customers):
        raise ValueError(
            "Prediction count does not match "
            "the scoring population."
        )

    if np.isnan(probabilities).any():
        raise ValueError(
            "Model generated null probabilities."
        )

    if (
        (probabilities < 0).any()
        or (probabilities > 1).any()
    ):
        raise ValueError(
            "Model generated probabilities "
            "outside the range [0, 1]."
        )

    threshold = float(
        contract[
            "probability_threshold"
        ]
    )

    output = customers.copy()

    output[
        "churn_probability"
    ] = probabilities

    output[
        "predicted_churn_flag"
    ] = (
        probabilities >= threshold
    ).astype(int)

    output = assign_risk_segments(
        output,
        threshold,
    )

    output[
        "probability_threshold"
    ] = threshold

    output[
        "model_name"
    ] = contract["model_name"]

    output[
        "model_version"
    ] = contract["model_version"]

    output[
        "scored_at_utc"
    ] = datetime.now(
        timezone.utc
    )

    output = output.sort_values(
        by=[
            "churn_probability",
            "user_id",
        ],
        ascending=[
            False,
            True,
        ],
    ).reset_index(
        drop=True
    )

    output.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print("=" * 68)
    print("KAIRO LIVE CUSTOMER CHURN SCORING")
    print("=" * 68)

    print(
        f"Eligible customers:  "
        f"{len(output):,}"
    )

    print(
        f"Predicted churners:  "
        f"{output['predicted_churn_flag'].sum():,}"
    )

    print(
        f"Average probability: "
        f"{output['churn_probability'].mean():.4f}"
    )

    print(
        f"Maximum probability: "
        f"{output['churn_probability'].max():.4f}"
    )

    print(
        f"Threshold:           "
        f"{threshold:.2f}"
    )

    print(
        f"Output:              "
        f"{OUTPUT_PATH}"
    )

    print()
    print(
        output[
            [
                "user_id",
                "feature_snapshot_date",
                "total_orders",
                "days_since_last_order",
                "lifetime_spend",
                "churn_probability",
                "predicted_churn_flag",
                "risk_decile",
                "risk_segment",
            ]
        ].to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
