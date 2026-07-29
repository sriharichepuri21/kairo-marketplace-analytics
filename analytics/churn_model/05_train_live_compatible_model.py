"""
Train a churn model whose feature schema matches the live marketplace.

The historical training data uses:
    avg_order_value
    customer_tenure_days

The live customer mart uses:
    average_order_value
    account_age_days

Historical columns are renamed to the live production contract before
training. Customers must have at least one historical order to qualify.

Usage:
    python analytics/churn_model/05_train_live_compatible_model.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


CHURN_DIR = Path(__file__).resolve().parent
DATA_DIR = CHURN_DIR / "data"
ARTIFACTS_DIR = CHURN_DIR / "model_artifacts"

TRAIN_PATH = DATA_DIR / "train_dataset.parquet"
VALIDATION_PATH = DATA_DIR / "validation_dataset.parquet"
TEST_PATH = DATA_DIR / "test_dataset.parquet"

MODEL_PATH = (
    ARTIFACTS_DIR
    / "live_compatible_model.pkl"
)

METRICS_PATH = (
    ARTIFACTS_DIR
    / "live_compatible_metrics.json"
)

CONTRACT_PATH = (
    ARTIFACTS_DIR
    / "live_compatible_feature_contract.json"
)

IMPORTANCE_PATH = (
    ARTIFACTS_DIR
    / "live_compatible_feature_importance.csv"
)

PREDICTIONS_PATH = (
    DATA_DIR
    / "live_compatible_test_predictions.parquet"
)

MODEL_CARD_PATH = (
    ARTIFACTS_DIR
    / "live_compatible_model_card.md"
)

MODEL_VERSION = "kairo_churn_live_v2"

LABEL_COLUMN = "churned"
ID_COLUMN = "customer_id"
SNAPSHOT_COLUMN = "snapshot_date"

NUMERIC_FEATURES = [
    "days_since_last_order",
    "total_orders",
    "orders_last_30d",
    "orders_last_90d",
    "account_age_days",
]

BINARY_FEATURES = [
    "is_single_order_customer",
]

FEATURE_COLUMNS = [
    *NUMERIC_FEATURES,
    *BINARY_FEATURES,
]

HISTORICAL_COLUMN_MAPPING = {
    "avg_order_value": "average_order_value",
    "customer_tenure_days": "account_age_days",
}


def normalize_historical_columns(
    frame: pd.DataFrame,
) -> pd.DataFrame:
    """Rename historical columns to the live feature contract."""

    output = frame.copy()

    for source, target in HISTORICAL_COLUMN_MAPPING.items():
        if target not in output.columns:
            if source not in output.columns:
                raise ValueError(
                    f"Missing historical source column: {source}"
                )

            output[target] = output[source]

    return output


def load_split(
    path: Path,
    split_name: str,
) -> pd.DataFrame:
    """Load and validate a historical point-in-time dataset."""

    if not path.exists():
        raise FileNotFoundError(
            f"{split_name} dataset was not found: {path}"
        )

    frame = pd.read_parquet(path)
    frame = normalize_historical_columns(frame)

    required = {
        ID_COLUMN,
        SNAPSHOT_COLUMN,
        LABEL_COLUMN,
        *FEATURE_COLUMNS,
    }

    missing = sorted(required - set(frame.columns))

    if missing:
        raise ValueError(
            f"{split_name} is missing columns: {missing}"
        )

    frame = frame.loc[
        frame["total_orders"] >= 1
    ].copy()

    if frame.empty:
        raise ValueError(
            f"{split_name} contains no eligible customers."
        )

    if not frame[LABEL_COLUMN].isin([0, 1]).all():
        raise ValueError(
            f"{split_name} contains invalid churn labels."
        )

    duplicate_rows = frame.duplicated(
        [ID_COLUMN, SNAPSHOT_COLUMN]
    ).sum()

    if duplicate_rows:
        raise ValueError(
            f"{split_name} contains {duplicate_rows:,} "
            "duplicate customer-snapshot rows."
        )

    return frame


def build_pipeline(
    class_weight: str | None,
) -> Pipeline:
    """Build the production-compatible preprocessing pipeline."""

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    binary_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent",
                ),
            ),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_FEATURES,
            ),
            (
                "binary",
                binary_pipeline,
                BINARY_FEATURES,
            ),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )

    classifier = LogisticRegression(
        solver="lbfgs",
        max_iter=1500,
        class_weight=class_weight,
        random_state=42,
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def top_fraction_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    fraction: float,
) -> dict[str, float | int]:
    """Measure performance among the highest-risk customers."""

    top_n = max(
        1,
        int(np.ceil(len(labels) * fraction)),
    )

    ranked_indices = np.argsort(
        -probabilities
    )[:top_n]

    selected_labels = labels[
        ranked_indices
    ]

    total_churners = int(labels.sum())
    captured_churners = int(
        selected_labels.sum()
    )

    selected_rate = float(
        selected_labels.mean()
    )

    overall_rate = float(
        labels.mean()
    )

    return {
        "fraction": float(fraction),
        "customers": int(top_n),
        "captured_churners": captured_churners,
        "precision": selected_rate,
        "recall": (
            float(
                captured_churners
                / total_churners
            )
            if total_churners
            else 0.0
        ),
        "lift": (
            float(
                selected_rate
                / overall_rate
            )
            if overall_rate
            else 0.0
        ),
    }


def choose_threshold(
    labels: np.ndarray,
    probabilities: np.ndarray,
) -> tuple[float, pd.DataFrame]:
    """Choose the validation threshold with the highest F1."""

    rows: list[dict[str, float | int]] = []

    for threshold in np.arange(
        0.05,
        0.951,
        0.01,
    ):
        predictions = (
            probabilities >= threshold
        ).astype(int)

        rows.append(
            {
                "threshold": round(
                    float(threshold),
                    2,
                ),
                "precision": precision_score(
                    labels,
                    predictions,
                    zero_division=0,
                ),
                "recall": recall_score(
                    labels,
                    predictions,
                    zero_division=0,
                ),
                "f1": f1_score(
                    labels,
                    predictions,
                    zero_division=0,
                ),
                "predicted_positive_rate": float(
                    predictions.mean()
                ),
            }
        )

    table = pd.DataFrame(rows)

    best = table.sort_values(
        by=[
            "f1",
            "recall",
            "precision",
            "threshold",
        ],
        ascending=[
            False,
            False,
            False,
            True,
        ],
    ).iloc[0]

    return float(best["threshold"]), table


def evaluate(
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    """Calculate model quality and operating metrics."""

    predictions = (
        probabilities >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        labels,
        predictions,
        labels=[0, 1],
    ).ravel()

    return {
        "rows": int(len(labels)),
        "churners": int(labels.sum()),
        "churn_rate": float(labels.mean()),
        "roc_auc": float(
            roc_auc_score(
                labels,
                probabilities,
            )
        ),
        "pr_auc": float(
            average_precision_score(
                labels,
                probabilities,
            )
        ),
        "brier_score": float(
            brier_score_loss(
                labels,
                probabilities,
            )
        ),
        "threshold": float(threshold),
        "precision": float(
            precision_score(
                labels,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                labels,
                predictions,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                labels,
                predictions,
                zero_division=0,
            )
        ),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "top_10_percent": top_fraction_metrics(
            labels,
            probabilities,
            0.10,
        ),
        "top_20_percent": top_fraction_metrics(
            labels,
            probabilities,
            0.20,
        ),
    }


def extract_importance(
    pipeline: Pipeline,
) -> pd.DataFrame:
    """Extract standardized logistic-regression coefficients."""

    preprocessor = pipeline.named_steps[
        "preprocessor"
    ]

    classifier = pipeline.named_steps[
        "classifier"
    ]

    feature_names = (
        preprocessor.get_feature_names_out()
    )

    coefficients = (
        classifier.coef_.ravel()
    )

    return pd.DataFrame(
        {
            "feature": feature_names,
            "coefficient": coefficients,
            "absolute_coefficient": np.abs(
                coefficients
            ),
            "direction": np.where(
                coefficients >= 0,
                "increases_churn_risk",
                "decreases_churn_risk",
            ),
        }
    ).sort_values(
        "absolute_coefficient",
        ascending=False,
    )


def main() -> None:
    """Train, evaluate, and save the live-compatible model."""

    ARTIFACTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    train = load_split(
        TRAIN_PATH,
        "TRAIN",
    )

    validation = load_split(
        VALIDATION_PATH,
        "VALIDATION",
    )

    test = load_split(
        TEST_PATH,
        "TEST",
    )

    print("=" * 68)
    print("KAIRO LIVE-COMPATIBLE CHURN MODEL")
    print("=" * 68)

    print(
        f"Train:      {len(train):,} rows"
    )

    print(
        f"Validation: {len(validation):,} rows"
    )

    print(
        f"Test:       {len(test):,} rows"
    )

    candidates: list[dict[str, Any]] = []

    for class_weight in [
        None,
        "balanced",
    ]:
        pipeline = build_pipeline(
            class_weight
        )

        pipeline.fit(
            train[FEATURE_COLUMNS],
            train[LABEL_COLUMN],
        )

        validation_probabilities = (
            pipeline.predict_proba(
                validation[FEATURE_COLUMNS]
            )[:, 1]
        )

        candidates.append(
            {
                "class_weight": class_weight,
                "pipeline": pipeline,
                "validation_probabilities": (
                    validation_probabilities
                ),
                "validation_pr_auc": float(
                    average_precision_score(
                        validation[
                            LABEL_COLUMN
                        ],
                        validation_probabilities,
                    )
                ),
                "validation_roc_auc": float(
                    roc_auc_score(
                        validation[
                            LABEL_COLUMN
                        ],
                        validation_probabilities,
                    )
                ),
                "validation_top_20_recall": (
                    top_fraction_metrics(
                        validation[
                            LABEL_COLUMN
                        ].to_numpy(),
                        validation_probabilities,
                        0.20,
                    )["recall"]
                ),
            }
        )

    selected = max(
        candidates,
        key=lambda candidate: (
            candidate[
                "validation_pr_auc"
            ],
            candidate[
                "validation_top_20_recall"
            ],
            candidate[
                "validation_roc_auc"
            ],
        ),
    )

    threshold, threshold_table = (
        choose_threshold(
            validation[
                LABEL_COLUMN
            ].to_numpy(),
            selected[
                "validation_probabilities"
            ],
        )
    )

    validation_metrics = evaluate(
        validation[
            LABEL_COLUMN
        ].to_numpy(),
        selected[
            "validation_probabilities"
        ],
        threshold,
    )

    test_probabilities = (
        selected["pipeline"].predict_proba(
            test[FEATURE_COLUMNS]
        )[:, 1]
    )

    test_metrics = evaluate(
        test[
            LABEL_COLUMN
        ].to_numpy(),
        test_probabilities,
        threshold,
    )

    joblib.dump(
        selected["pipeline"],
        MODEL_PATH,
    )

    importance = extract_importance(
        selected["pipeline"]
    )

    importance.to_csv(
        IMPORTANCE_PATH,
        index=False,
    )

    predictions = test[
        [
            ID_COLUMN,
            SNAPSHOT_COLUMN,
            LABEL_COLUMN,
        ]
    ].copy()

    predictions[
        "churn_probability"
    ] = test_probabilities

    predictions[
        "predicted_churn"
    ] = (
        test_probabilities >= threshold
    ).astype(int)

    predictions.to_parquet(
        PREDICTIONS_PATH,
        index=False,
    )

    metrics = {
        "model_name": (
            "live_compatible_behavioral"
        ),
        "model_version": MODEL_VERSION,
        "selected_class_weight": (
            "none"
            if selected[
                "class_weight"
            ] is None
            else "balanced"
        ),
        "selection_rule": (
            "Highest validation PR-AUC, "
            "then validation top-20% recall, "
            "then validation ROC-AUC."
        ),
        "feature_columns": (
            FEATURE_COLUMNS
        ),
        "validation": (
            validation_metrics
        ),
        "test": test_metrics,
        "candidate_results": [
            {
                "class_weight": (
                    "none"
                    if candidate[
                        "class_weight"
                    ] is None
                    else "balanced"
                ),
                "validation_pr_auc": (
                    candidate[
                        "validation_pr_auc"
                    ]
                ),
                "validation_roc_auc": (
                    candidate[
                        "validation_roc_auc"
                    ]
                ),
                "validation_top_20_recall": (
                    candidate[
                        "validation_top_20_recall"
                    ]
                ),
            }
            for candidate in candidates
        ],
    }

    with METRICS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics,
            file,
            indent=2,
        )
        file.write("\n")

    contract = {
        "model_name": (
            "live_compatible_behavioral"
        ),
        "model_version": MODEL_VERSION,
        "probability_threshold": (
            threshold
        ),
        "scoring_eligibility": (
            "total_orders >= 1"
        ),
        "live_source_model": (
            "mart_customer_features"
        ),
        "feature_columns": (
            FEATURE_COLUMNS
        ),
        "historical_column_mapping": (
            HISTORICAL_COLUMN_MAPPING
        ),
        "excluded_live_customers": (
            "Customers with zero orders are "
            "prospects, not churn candidates."
        ),
    }

    with CONTRACT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            contract,
            file,
            indent=2,
        )
        file.write("\n")

    model_card = f"""# Kairo Live-Compatible Churn Model

## Purpose

Score registered marketplace customers using features available in the
live `mart_customer_features` model.

## Eligibility

Only customers with at least one order are churn-score eligible.
Customers with zero orders are classified as prospects.

## Feature contract

{chr(10).join(f"- `{feature}`" for feature in FEATURE_COLUMNS)}

## Validation

- PR-AUC: {validation_metrics["pr_auc"]:.4f}
- ROC-AUC: {validation_metrics["roc_auc"]:.4f}
- F1: {validation_metrics["f1"]:.4f}
- Threshold: {threshold:.2f}

## Out-of-time test

- PR-AUC: {test_metrics["pr_auc"]:.4f}
- ROC-AUC: {test_metrics["roc_auc"]:.4f}
- F1: {test_metrics["f1"]:.4f}
- Top-10% lift: {test_metrics["top_10_percent"]["lift"]:.2f}x
"""

    MODEL_CARD_PATH.write_text(
        model_card,
        encoding="utf-8",
    )

    threshold_table.to_csv(
        ARTIFACTS_DIR
        / "live_compatible_threshold_analysis.csv",
        index=False,
    )

    print()
    print(
        "Selected class weight: "
        f"{metrics['selected_class_weight']}"
    )

    print(
        "Validation PR-AUC:      "
        f"{validation_metrics['pr_auc']:.4f}"
    )

    print(
        "Validation ROC-AUC:     "
        f"{validation_metrics['roc_auc']:.4f}"
    )

    print(
        "Selected threshold:     "
        f"{threshold:.2f}"
    )

    print(
        "Test PR-AUC:            "
        f"{test_metrics['pr_auc']:.4f}"
    )

    print(
        "Test ROC-AUC:           "
        f"{test_metrics['roc_auc']:.4f}"
    )

    print(
        "Test F1:                "
        f"{test_metrics['f1']:.4f}"
    )

    print(
        "Test top-10% lift:      "
        f"{test_metrics['top_10_percent']['lift']:.2f}x"
    )

    print()
    print(
        f"Model saved: {MODEL_PATH}"
    )

    print(
        f"Contract:    {CONTRACT_PATH}"
    )


if __name__ == "__main__":
    main()
