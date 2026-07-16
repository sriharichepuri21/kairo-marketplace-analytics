"""
Step 3: Score the Latest Customer Population

Builds a point-in-time customer feature snapshot as of 2025-12-31,
loads the approved behavioral-only churn model, generates customer
churn probabilities, assigns risk bands, and writes the results to
Parquet for downstream dbt publication.

Production model decision
-------------------------
The behavioral-only model is used because signup_channel produced only
negligible out-of-time improvement:

    ROC-AUC improvement:       +0.0008
    PR-AUC improvement:        +0.0013
    Top-10% lift improvement:  +0.01x
    Test F1 change:            -0.0013

The channel model remains an experiment but is not used for production
scoring.

Usage
-----
python analytics/churn_model/03_write_scores.py
"""

import importlib.util
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from config import (
    ARTIFACTS_DIR,
    BEHAVIORAL_BINARY_FEATURES,
    BEHAVIORAL_NUMERIC_FEATURES,
    DATA_DIR,
    MODEL_VERSION,
)


CHURN_MODEL_DIR = Path(__file__).resolve().parent

FEATURE_ENGINEERING_PATH = (
    CHURN_MODEL_DIR
    / "01_feature_engineering.py"
)

MODEL_PATH = (
    ARTIFACTS_DIR
    / "behavioral_model.pkl"
)

OUTPUT_PATH = (
    DATA_DIR
    / "customer_churn_scores.parquet"
)

DECISION_PATH = (
    ARTIFACTS_DIR
    / "production_model_decision.json"
)

SCORE_DATE = date(2025, 12, 31)

PROBABILITY_THRESHOLD = 0.30

PRODUCTION_MODEL_NAME = "behavioral_only"


def load_feature_engineering_module():
    """
    Dynamically load 01_feature_engineering.py.

    Python module names cannot normally begin with a number, so
    importlib is used to access the validated feature-building
    functions without duplicating their SQL logic.
    """

    if not FEATURE_ENGINEERING_PATH.exists():
        raise FileNotFoundError(
            "Feature-engineering script not found: "
            f"{FEATURE_ENGINEERING_PATH}"
        )

    sys.path.insert(
        0,
        str(CHURN_MODEL_DIR),
    )

    spec = importlib.util.spec_from_file_location(
        "kairo_feature_engineering",
        FEATURE_ENGINEERING_PATH,
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            "Unable to load the feature-engineering module."
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


def load_model() -> Any:
    """Load the approved behavioral-only sklearn model pipeline."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Behavioral model artifact was not found at: "
            f"{MODEL_PATH}"
        )

    artifact = joblib.load(MODEL_PATH)

    if hasattr(artifact, "predict_proba"):
        return artifact

    if isinstance(artifact, dict):
        for key in [
            "pipeline",
            "model",
            "estimator",
        ]:
            candidate = artifact.get(key)

            if (
                candidate is not None
                and hasattr(
                    candidate,
                    "predict_proba",
                )
            ):
                return candidate

    raise TypeError(
        "The behavioral model artifact does not expose "
        "a predict_proba method."
    )


def build_scoring_snapshot(
    feature_module,
) -> pd.DataFrame:
    """
    Build customer features through SCORE_DATE without creating labels.

    Output grain:
        one row per eligible customer
    """

    conn = feature_module.get_conn()

    try:
        print("  Building order features...")

        order_features = (
            feature_module.build_order_features(
                conn,
                SCORE_DATE,
            )
        )

        print(
            f"    → {len(order_features):,} customers"
        )

        print("  Building item features...")

        item_features = (
            feature_module.build_item_features(
                conn,
                SCORE_DATE,
            )
        )

        print(
            f"    → {len(item_features):,} customers"
        )

        print("  Building return features...")

        return_features = (
            feature_module.build_return_features(
                conn,
                SCORE_DATE,
            )
        )

        print(
            f"    → {len(return_features):,} customers"
        )

        print("  Building review features...")

        review_features = (
            feature_module.build_review_features(
                conn,
                SCORE_DATE,
            )
        )

        print(
            f"    → {len(review_features):,} customers"
        )

        print("  Building delivery features...")

        delivery_features = (
            feature_module.build_delivery_features(
                conn,
                SCORE_DATE,
            )
        )

        print(
            f"    → {len(delivery_features):,} customers"
        )

        print("  Building customer attributes...")

        customer_attributes = (
            feature_module.build_customer_attributes(
                conn,
                SCORE_DATE,
            )
        )

        print(
            f"    → {len(customer_attributes):,} customers"
        )

    finally:
        conn.close()

    print("  Joining feature domains...")

    dataset = order_features.copy()

    dataset = dataset.merge(
        item_features,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        return_features,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        review_features,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        delivery_features,
        on="customer_id",
        how="left",
        validate="one_to_one",
    )

    dataset = dataset.merge(
        customer_attributes,
        on="customer_id",
        how="inner",
        validate="one_to_one",
    )

    count_columns = [
        "category_count",
        "historical_item_count",
        "return_count",
        "review_count",
        "late_delivery_count",
    ]

    for column in count_columns:
        dataset[column] = (
            dataset[column]
            .fillna(0)
            .astype(int)
        )

    rate_columns = [
        "discount_order_rate",
        "return_order_rate",
        "return_item_rate",
    ]

    for column in rate_columns:
        dataset[column] = (
            dataset[column]
            .fillna(0.0)
            .clip(
                lower=0.0,
                upper=1.0,
            )
        )

    binary_columns = [
        "is_single_order_customer",
        "has_return",
        "has_review",
        "has_completed_delivery",
    ]

    for column in binary_columns:
        dataset[column] = (
            dataset[column]
            .fillna(0)
            .astype(int)
        )

    dataset["score_date"] = (
        SCORE_DATE.isoformat()
    )

    duplicate_customers = (
        dataset["customer_id"]
        .duplicated()
        .sum()
    )

    if duplicate_customers:
        raise ValueError(
            "Scoring snapshot contains "
            f"{duplicate_customers:,} duplicate customers."
        )

    if dataset["customer_id"].isna().any():
        raise ValueError(
            "Scoring snapshot contains null customer IDs."
        )

    if dataset.empty:
        raise ValueError(
            "Scoring snapshot is empty."
        )

    print(
        f"  PASS — scoring snapshot contains "
        f"{len(dataset):,} customers"
    )

    return dataset


def get_model_features(
    dataset: pd.DataFrame,
) -> list[str]:
    """Return the behavioral feature list in training order."""

    features = [
        *BEHAVIORAL_NUMERIC_FEATURES,
        *BEHAVIORAL_BINARY_FEATURES,
    ]

    missing_features = [
        feature
        for feature in features
        if feature not in dataset.columns
    ]

    if missing_features:
        raise ValueError(
            "Scoring data is missing model features: "
            f"{missing_features}"
        )

    return features


def predict_probabilities(
    model: Any,
    dataset: pd.DataFrame,
    features: list[str],
) -> np.ndarray:
    """Generate and validate customer churn probabilities."""

    feature_frame = dataset[features].copy()

    probabilities = model.predict_proba(
        feature_frame
    )[:, 1]

    if len(probabilities) != len(dataset):
        raise ValueError(
            "Prediction count does not match the "
            "scoring population."
        )

    if np.isnan(probabilities).any():
        raise ValueError(
            "Model generated null churn probabilities."
        )

    if (
        (probabilities < 0).any()
        or (probabilities > 1).any()
    ):
        raise ValueError(
            "Model generated probabilities outside [0, 1]."
        )

    return probabilities


def assign_risk_deciles(
    probabilities: pd.Series,
) -> pd.Series:
    """
    Assign risk deciles.

    Decile 1:
        Highest predicted churn risk.

    Decile 10:
        Lowest predicted churn risk.
    """

    risk_rank = probabilities.rank(
        method="first",
        ascending=False,
    )

    return pd.qcut(
        risk_rank,
        q=10,
        labels=list(range(1, 11)),
    ).astype(int)


def assign_risk_segment(
    probability: float,
    risk_decile: int,
) -> str:
    """
    Assign capacity-based operational risk segments.

    High Risk:
        Top 20% of predicted churn probabilities.

    Medium Risk:
        Next 30% of predicted churn probabilities.

    Low Risk:
        Remaining 50%.

    The validation-selected probability threshold is stored separately
    as predicted_churn_flag and does not define outreach capacity.
    """

    del probability

    if risk_decile <= 2:
        return "high_risk"

    if risk_decile <= 5:
        return "medium_risk"

    return "low_risk"


def assign_recommended_action(
    row: pd.Series,
    high_value_cutoff: float,
) -> str:
    """Create an explainable rule-based retention action."""

    risk_segment = row["risk_segment"]

    lifetime_spend = row["lifetime_spend_for_action"]

    return_order_rate = row["return_order_rate"]

    discount_order_rate = row[
        "discount_order_rate"
    ]

    if (
        risk_segment == "high_risk"
        and lifetime_spend >= high_value_cutoff
    ):
        return "priority_retention_outreach"

    if (
        risk_segment == "high_risk"
        and return_order_rate >= 0.25
    ):
        return "service_recovery_review"

    if (
        risk_segment == "high_risk"
        and discount_order_rate >= 0.50
    ):
        return "targeted_retention_incentive"

    if risk_segment == "high_risk":
        return "standard_retention_campaign"

    if risk_segment == "medium_risk":
        return "low_cost_reengagement"

    return "no_immediate_action"


def create_score_output(
    dataset: pd.DataFrame,
    probabilities: np.ndarray,
) -> pd.DataFrame:
    """Create the final customer-level scoring output."""

    scored_at = datetime.now(
        timezone.utc
    ).replace(
        tzinfo=None
    )

    output = dataset[
        [
            "customer_id",
            "score_date",
            "signup_channel",
            "region",
            "segment",
            "days_since_last_order",
            "total_orders",
            "orders_last_90d",
            "lifetime_spend",
            "return_order_rate",
            "discount_order_rate",
            "is_single_order_customer",
        ]
    ].copy()

    output["churn_probability"] = (
        probabilities
    )

    output["predicted_churn_flag"] = (
        output["churn_probability"]
        >= PROBABILITY_THRESHOLD
    ).astype(int)

    output["lifetime_spend_missing_flag"] = (
        output["lifetime_spend"]
        .isna()
        .astype(int)
    )

    output["lifetime_spend_for_action"] = (
        output["lifetime_spend"]
        .fillna(0.0)
    )

    output["risk_decile"] = (
        assign_risk_deciles(
            output["churn_probability"]
        )
    )

    output["risk_segment"] = output.apply(
        lambda row: assign_risk_segment(
            probability=row[
                "churn_probability"
            ],
            risk_decile=row[
                "risk_decile"
            ],
        ),
        axis=1,
    )

    high_value_cutoff = (
        output["lifetime_spend"]
        .dropna()
        .quantile(0.80)
    )

    output["recommended_action"] = (
        output.apply(
            lambda row: assign_recommended_action(
                row,
                high_value_cutoff,
            ),
            axis=1,
        )
    )

    output = output.drop(
        columns=["lifetime_spend_for_action"]
    )

    output["probability_threshold"] = (
        PROBABILITY_THRESHOLD
    )

    output["model_name"] = (
        PRODUCTION_MODEL_NAME
    )

    output["model_version"] = (
        MODEL_VERSION
    )

    output["scored_at_utc"] = (
        scored_at
    )

    output = output.sort_values(
        [
            "churn_probability",
            "lifetime_spend",
        ],
        ascending=[
            False,
            False,
        ],
    ).reset_index(
        drop=True
    )

    return output


def validate_scores(
    scores: pd.DataFrame,
) -> None:
    """Validate the final score output."""

    if scores.empty:
        raise ValueError(
            "Final score output is empty."
        )

    if scores["customer_id"].duplicated().any():
        raise ValueError(
            "Final score output contains "
            "duplicate customers."
        )

    if scores["customer_id"].isna().any():
        raise ValueError(
            "Final score output contains "
            "null customer IDs."
        )

    if scores["churn_probability"].isna().any():
        raise ValueError(
            "Final score output contains "
            "null probabilities."
        )

    if not scores["predicted_churn_flag"].isin([0, 1]).all():
        raise ValueError(
            "predicted_churn_flag must contain only 0 or 1."
        )

    if not scores["lifetime_spend_missing_flag"].isin([0, 1]).all():
        raise ValueError(
            "lifetime_spend_missing_flag must contain only 0 or 1."
        )

    invalid_probabilities = ~scores[
        "churn_probability"
    ].between(
        0,
        1,
        inclusive="both",
    )

    if invalid_probabilities.any():
        raise ValueError(
            "Final score output contains "
            f"{invalid_probabilities.sum():,} "
            "invalid probabilities."
        )

    expected_risk_segments = {
        "high_risk",
        "medium_risk",
        "low_risk",
    }

    actual_risk_segments = set(
        scores["risk_segment"].unique()
    )

    unexpected_segments = (
        actual_risk_segments
        - expected_risk_segments
    )

    if unexpected_segments:
        raise ValueError(
            "Unexpected risk segments: "
            f"{unexpected_segments}"
        )

    if not scores["risk_decile"].between(
        1,
        10,
        inclusive="both",
    ).all():
        raise ValueError(
            "Risk decile values must be "
            "between 1 and 10."
        )


def write_production_decision() -> None:
    """Document why the behavioral model was promoted."""

    decision = {
        "production_model": (
            PRODUCTION_MODEL_NAME
        ),
        "model_version": MODEL_VERSION,
        "probability_threshold": (
            PROBABILITY_THRESHOLD
        ),
        "decision": (
            "Use behavioral-only model for "
            "production scoring."
        ),
        "reason": (
            "Adding signup_channel produced "
            "negligible out-of-time improvement "
            "and slightly reduced test F1."
        ),
        "behavioral_test_metrics": {
            "roc_auc": 0.7757,
            "pr_auc": 0.4865,
            "precision": 0.3831,
            "recall": 0.7873,
            "f1": 0.5154,
            "top_10_pct_lift": 2.51,
            "top_20_pct_recall": 0.4323,
        },
        "channel_test_metrics": {
            "roc_auc": 0.7765,
            "pr_auc": 0.4878,
            "precision": 0.3768,
            "recall": 0.8089,
            "f1": 0.5141,
            "top_10_pct_lift": 2.52,
            "top_20_pct_recall": 0.4333,
        },
        "incremental_channel_value": {
            "roc_auc_delta": 0.0008,
            "pr_auc_delta": 0.0013,
            "f1_delta": -0.0013,
            "top_10_pct_lift_delta": 0.01,
            "top_20_pct_recall_delta": 0.0010,
        },
    }

    with DECISION_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            decision,
            file,
            indent=2,
        )


def print_summary(
    scores: pd.DataFrame,
) -> None:
    """Print scoring results and intervention volumes."""

    print("\n" + "=" * 68)
    print("  CUSTOMER CHURN SCORING SUMMARY")
    print("=" * 68)

    print(
        f"\n  Score date:          "
        f"{SCORE_DATE.isoformat()}"
    )

    print(
        f"  Production model:    "
        f"{PRODUCTION_MODEL_NAME}"
    )

    print(
        f"  Customers scored:    "
        f"{len(scores):,}"
    )

    print(
        f"  Average probability: "
        f"{scores['churn_probability'].mean():.3f}"
    )

    print(
        f"  Median probability:  "
        f"{scores['churn_probability'].median():.3f}"
    )

    print(
        f"  Threshold:           "
        f"{PROBABILITY_THRESHOLD:.2f}"
    )

    threshold_positive = int(
        scores["predicted_churn_flag"].sum()
    )

    print(
        f"  Threshold-positive:  "
        f"{threshold_positive:,} "
        f"({100.0 * threshold_positive / len(scores):.1f}%)"
    )

    missing_spend = int(
        scores["lifetime_spend_missing_flag"].sum()
    )

    print(
        f"  Missing spend values:"
        f" {missing_spend:,}"
    )

    print("\n  Risk-segment distribution:")

    risk_summary = (
        scores
        .groupby("risk_segment")
        .agg(
            customers=(
                "customer_id",
                "count",
            ),
            avg_probability=(
                "churn_probability",
                "mean",
            ),
            avg_lifetime_spend=(
                "lifetime_spend",
                "mean",
            ),
        )
        .sort_values(
            "avg_probability",
            ascending=False,
        )
    )

    risk_summary["share_pct"] = (
        100.0
        * risk_summary["customers"]
        / len(scores)
    )

    risk_summary[
        "avg_probability"
    ] = risk_summary[
        "avg_probability"
    ].round(3)

    risk_summary[
        "avg_lifetime_spend"
    ] = risk_summary[
        "avg_lifetime_spend"
    ].round(2)

    risk_summary[
        "share_pct"
    ] = risk_summary[
        "share_pct"
    ].round(1)

    print(
        risk_summary.to_string()
    )

    print("\n  Recommended actions:")

    action_summary = (
        scores[
            "recommended_action"
        ]
        .value_counts()
        .rename_axis(
            "recommended_action"
        )
        .reset_index(
            name="customers"
        )
    )

    action_summary["share_pct"] = (
        100.0
        * action_summary["customers"]
        / len(scores)
    ).round(1)

    print(
        action_summary.to_string(
            index=False
        )
    )

    print("\n  Highest-risk customers:")

    top_customers = scores[
        [
            "customer_id",
            "churn_probability",
            "risk_decile",
            "lifetime_spend",
            "days_since_last_order",
            "recommended_action",
        ]
    ].head(10).copy()

    top_customers[
        "churn_probability"
    ] = top_customers[
        "churn_probability"
    ].round(4)

    top_customers[
        "lifetime_spend"
    ] = top_customers[
        "lifetime_spend"
    ].round(2)

    print(
        top_customers.to_string(
            index=False
        )
    )


def main() -> None:
    """Build the latest snapshot, score it, and save results."""

    print("=" * 68)
    print("  KAIRO CUSTOMER CHURN PRODUCTION SCORING")
    print("=" * 68)

    print(
        f"\n  Score date: "
        f"{SCORE_DATE.isoformat()}"
    )

    print(
        f"  Model:      "
        f"{PRODUCTION_MODEL_NAME}"
    )

    feature_module = (
        load_feature_engineering_module()
    )

    model = load_model()

    scoring_dataset = (
        build_scoring_snapshot(
            feature_module
        )
    )

    model_features = get_model_features(
        scoring_dataset
    )

    print(
        f"\n  Generating probabilities "
        f"with {len(model_features)} features..."
    )

    probabilities = predict_probabilities(
        model=model,
        dataset=scoring_dataset,
        features=model_features,
    )

    scores = create_score_output(
        dataset=scoring_dataset,
        probabilities=probabilities,
    )

    validate_scores(scores)

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARTIFACTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    scores.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    write_production_decision()

    print_summary(scores)

    print("\n" + "=" * 68)
    print("  SCORING COMPLETE")
    print("=" * 68)

    print(
        f"\n  Scores written to:\n"
        f"  {OUTPUT_PATH}"
    )

    print(
        f"\n  Production decision written to:\n"
        f"  {DECISION_PATH}"
    )

    print(
        "\n  Next step:\n"
        "  Publish the scores through "
        "dbt mart_customer_churn_scores."
    )


if __name__ == "__main__":
    main()
