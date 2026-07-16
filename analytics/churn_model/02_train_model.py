"""
Step 2: Train and evaluate point-in-time churn models.

Model A: behavioral features only
Model B: behavioral features plus signup_channel

The script:
- trains only on train_dataset.parquet
- chooses class weighting and thresholds on validation_dataset.parquet
- evaluates once on test_dataset.parquet
- excludes customer_id, snapshot_date, segment, and future-label columns
- saves both models, the selected model, metrics, coefficients,
  threshold analysis, predictions, and a Markdown report

Usage:
    python analytics/churn_model/02_train_model.py
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
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import (
    ARTIFACTS_DIR,
    BEHAVIORAL_BINARY_FEATURES,
    BEHAVIORAL_NUMERIC_FEATURES,
    CHANNEL_FEATURES,
    DATA_DIR,
    LABEL_COLUMN,
    MODEL_VERSION,
    REPORT_PATH,
    SNAPSHOT_COLUMN,
)


TRAIN_PATH = DATA_DIR / "train_dataset.parquet"
VALIDATION_PATH = DATA_DIR / "validation_dataset.parquet"
TEST_PATH = DATA_DIR / "test_dataset.parquet"

BEHAVIORAL_MODEL_PATH = ARTIFACTS_DIR / "behavioral_model.pkl"
CHANNEL_MODEL_PATH = ARTIFACTS_DIR / "channel_model.pkl"
SELECTED_MODEL_PATH = ARTIFACTS_DIR / "model.pkl"

METRICS_PATH = ARTIFACTS_DIR / "evaluation_metrics.json"
IMPORTANCE_PATH = ARTIFACTS_DIR / "feature_importance.csv"
THRESHOLD_PATH = ARTIFACTS_DIR / "threshold_analysis.csv"
PREDICTIONS_PATH = ARTIFACTS_DIR / "test_predictions.parquet"


def make_one_hot_encoder() -> OneHotEncoder:
    """Create a OneHotEncoder compatible with old and new sklearn."""

    try:
        return OneHotEncoder(
            handle_unknown="ignore",
            sparse_output=True,
        )
    except TypeError:
        return OneHotEncoder(
            handle_unknown="ignore",
            sparse=True,
        )


def load_split(path: Path, split_name: str) -> pd.DataFrame:
    """Load and validate one point-in-time split."""

    if not path.exists():
        raise FileNotFoundError(
            f"{split_name} dataset not found: {path}. "
            "Run 01_feature_engineering.py first."
        )

    df = pd.read_parquet(path)

    required = {
        "customer_id",
        SNAPSHOT_COLUMN,
        LABEL_COLUMN,
        *BEHAVIORAL_NUMERIC_FEATURES,
        *BEHAVIORAL_BINARY_FEATURES,
        *CHANNEL_FEATURES,
    }

    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(
            f"{split_name} is missing required columns: {missing}"
        )

    if df.empty:
        raise ValueError(f"{split_name} is empty.")

    if not df[LABEL_COLUMN].isin([0, 1]).all():
        raise ValueError(
            f"{split_name} contains labels outside 0 and 1."
        )

    duplicates = df.duplicated(
        ["customer_id", SNAPSHOT_COLUMN]
    ).sum()

    if duplicates:
        raise ValueError(
            f"{split_name} contains {duplicates:,} duplicate "
            "customer-snapshot rows."
        )

    return df


def validate_feature_configuration(df: pd.DataFrame) -> None:
    """Ensure future or synthetic-shortcut columns are not features."""

    configured = set(
        BEHAVIORAL_NUMERIC_FEATURES
        + BEHAVIORAL_BINARY_FEATURES
        + CHANNEL_FEATURES
    )

    forbidden = {
        "customer_id",
        SNAPSHOT_COLUMN,
        LABEL_COLUMN,
        "segment",
        "signup_date",
        "orders_in_prediction_window",
    }

    leakage = sorted(configured & forbidden)
    if leakage:
        raise ValueError(
            f"Forbidden columns configured as features: {leakage}"
        )

    missing = sorted(configured - set(df.columns))
    if missing:
        raise ValueError(
            f"Configured features missing from dataset: {missing}"
        )


def build_pipeline(
    include_channel: bool,
    class_weight: str | None,
) -> tuple[Pipeline, list[str]]:
    """Build the preprocessing and logistic-regression pipeline."""

    numeric = list(BEHAVIORAL_NUMERIC_FEATURES)
    binary = list(BEHAVIORAL_BINARY_FEATURES)
    channel = list(CHANNEL_FEATURES) if include_channel else []

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median",
                    add_indicator=True,
                ),
            ),
            ("scaler", StandardScaler()),
        ]
    )

    binary_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
            )
        ]
    )

    transformers: list[tuple[str, Any, list[str]]] = [
        ("numeric", numeric_pipeline, numeric),
        ("binary", binary_pipeline, binary),
    ]

    if channel:
        channel_pipeline = Pipeline(
            steps=[
                (
                    "imputer",
                    SimpleImputer(strategy="most_frequent"),
                ),
                ("onehot", make_one_hot_encoder()),
            ]
        )
        transformers.append(
            ("channel", channel_pipeline, channel)
        )

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        verbose_feature_names_out=True,
    )

    classifier = LogisticRegression(
        solver="lbfgs",
        max_iter=1500,
        class_weight=class_weight,
        random_state=42,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    return pipeline, numeric + binary + channel


def top_fraction_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    fraction: float,
) -> dict[str, float | int]:
    """Evaluate the highest-risk fraction of customers."""

    top_n = max(
        1,
        int(np.ceil(len(y_true) * fraction)),
    )

    order = np.argsort(-probabilities)
    selected = order[:top_n]

    selected_churners = int(y_true[selected].sum())
    total_churners = int(y_true.sum())

    selected_rate = float(y_true[selected].mean())
    overall_rate = float(y_true.mean())

    return {
        "fraction": float(fraction),
        "customers": int(top_n),
        "captured_churners": selected_churners,
        "precision": selected_rate,
        "recall": (
            float(selected_churners / total_churners)
            if total_churners
            else 0.0
        ),
        "lift": (
            float(selected_rate / overall_rate)
            if overall_rate
            else 0.0
        ),
    }


def make_threshold_table(
    model_name: str,
    y_true: np.ndarray,
    probabilities: np.ndarray,
) -> pd.DataFrame:
    """Evaluate validation performance across thresholds."""

    rows = []

    for threshold in np.arange(0.05, 0.951, 0.01):
        predictions = (
            probabilities >= threshold
        ).astype(int)

        rows.append(
            {
                "model_name": model_name,
                "threshold": round(float(threshold), 2),
                "precision": precision_score(
                    y_true,
                    predictions,
                    zero_division=0,
                ),
                "recall": recall_score(
                    y_true,
                    predictions,
                    zero_division=0,
                ),
                "f1": f1_score(
                    y_true,
                    predictions,
                    zero_division=0,
                ),
                "predicted_positive_rate": float(
                    predictions.mean()
                ),
                "predicted_positive_customers": int(
                    predictions.sum()
                ),
            }
        )

    return pd.DataFrame(rows)


def choose_threshold(table: pd.DataFrame) -> float:
    """Choose the validation threshold with the highest F1."""

    best = table.sort_values(
        by=["f1", "recall", "precision", "threshold"],
        ascending=[False, False, False, True],
    ).iloc[0]

    return float(best["threshold"])


def evaluate(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    """Calculate model metrics at the selected threshold."""

    predictions = (
        probabilities >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1],
    ).ravel()

    return {
        "rows": int(len(y_true)),
        "churners": int(y_true.sum()),
        "churn_rate": float(y_true.mean()),
        "roc_auc": float(
            roc_auc_score(y_true, probabilities)
        ),
        "pr_auc": float(
            average_precision_score(
                y_true,
                probabilities,
            )
        ),
        "brier_score": float(
            brier_score_loss(
                y_true,
                probabilities,
            )
        ),
        "threshold": float(threshold),
        "precision": float(
            precision_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "recall": float(
            recall_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "f1": float(
            f1_score(
                y_true,
                predictions,
                zero_division=0,
            )
        ),
        "predicted_positive_rate": float(
            predictions.mean()
        ),
        "predicted_positive_customers": int(
            predictions.sum()
        ),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "top_10_percent": top_fraction_metrics(
            y_true,
            probabilities,
            0.10,
        ),
        "top_20_percent": top_fraction_metrics(
            y_true,
            probabilities,
            0.20,
        ),
    }


def train_model_family(
    model_name: str,
    include_channel: bool,
    train_df: pd.DataFrame,
    validation_df: pd.DataFrame,
) -> dict[str, Any]:
    """Choose class weighting using validation PR-AUC."""

    candidates = []
    best_result = None

    for class_weight in [None, "balanced"]:
        pipeline, features = build_pipeline(
            include_channel=include_channel,
            class_weight=class_weight,
        )

        pipeline.fit(
            train_df[features],
            train_df[LABEL_COLUMN],
        )

        val_probabilities = pipeline.predict_proba(
            validation_df[features]
        )[:, 1]

        pr_auc = average_precision_score(
            validation_df[LABEL_COLUMN],
            val_probabilities,
        )

        roc_auc = roc_auc_score(
            validation_df[LABEL_COLUMN],
            val_probabilities,
        )

        top_20 = top_fraction_metrics(
            validation_df[LABEL_COLUMN].to_numpy(),
            val_probabilities,
            0.20,
        )

        candidate = {
            "model_name": model_name,
            "include_channel": include_channel,
            "class_weight": (
                "none"
                if class_weight is None
                else "balanced"
            ),
            "pipeline": pipeline,
            "features": features,
            "validation_probabilities": val_probabilities,
            "validation_pr_auc": float(pr_auc),
            "validation_roc_auc": float(roc_auc),
            "validation_top_20_recall": float(
                top_20["recall"]
            ),
        }

        candidates.append(
            {
                "class_weight": candidate["class_weight"],
                "validation_pr_auc": candidate[
                    "validation_pr_auc"
                ],
                "validation_roc_auc": candidate[
                    "validation_roc_auc"
                ],
                "validation_top_20_recall": candidate[
                    "validation_top_20_recall"
                ],
            }
        )

        if best_result is None:
            best_result = candidate
        else:
            current_key = (
                candidate["validation_pr_auc"],
                candidate["validation_top_20_recall"],
                candidate["validation_roc_auc"],
            )
            best_key = (
                best_result["validation_pr_auc"],
                best_result["validation_top_20_recall"],
                best_result["validation_roc_auc"],
            )

            if current_key > best_key:
                best_result = candidate

    if best_result is None:
        raise RuntimeError(
            f"No candidates trained for {model_name}."
        )

    threshold_table = make_threshold_table(
        model_name,
        validation_df[LABEL_COLUMN].to_numpy(),
        best_result["validation_probabilities"],
    )

    threshold = choose_threshold(threshold_table)

    best_result["candidate_results"] = candidates
    best_result["threshold_table"] = threshold_table
    best_result["selected_threshold"] = threshold
    best_result["validation_metrics"] = evaluate(
        validation_df[LABEL_COLUMN].to_numpy(),
        best_result["validation_probabilities"],
        threshold,
    )

    return best_result


def evaluate_test(
    result: dict[str, Any],
    test_df: pd.DataFrame,
) -> None:
    """Evaluate the chosen validation candidate on test data."""

    probabilities = result["pipeline"].predict_proba(
        test_df[result["features"]]
    )[:, 1]

    result["test_probabilities"] = probabilities
    result["test_metrics"] = evaluate(
        test_df[LABEL_COLUMN].to_numpy(),
        probabilities,
        result["selected_threshold"],
    )


def extract_coefficients(
    result: dict[str, Any],
) -> pd.DataFrame:
    """Extract standardized logistic-regression coefficients."""

    preprocessor = result["pipeline"].named_steps[
        "preprocessor"
    ]
    classifier = result["pipeline"].named_steps[
        "classifier"
    ]

    names = preprocessor.get_feature_names_out()
    coefficients = classifier.coef_.ravel()

    if len(names) != len(coefficients):
        raise ValueError(
            "Feature names and coefficients do not align."
        )

    output = pd.DataFrame(
        {
            "model_name": result["model_name"],
            "feature": names,
            "coefficient": coefficients,
            "absolute_coefficient": np.abs(coefficients),
            "direction": np.where(
                coefficients >= 0,
                "increases_churn_risk",
                "decreases_churn_risk",
            ),
        }
    )

    return output.sort_values(
        "absolute_coefficient",
        ascending=False,
    )


def prediction_frame(
    test_df: pd.DataFrame,
    result: dict[str, Any],
) -> pd.DataFrame:
    """Create auditable test predictions."""

    probabilities = result["test_probabilities"]

    output = test_df[
        [
            "customer_id",
            SNAPSHOT_COLUMN,
            LABEL_COLUMN,
        ]
    ].copy()

    output["model_name"] = result["model_name"]
    output["churn_probability"] = probabilities
    output["selected_threshold"] = result[
        "selected_threshold"
    ]
    output["predicted_churn"] = (
        probabilities
        >= result["selected_threshold"]
    ).astype(int)

    percentile = pd.Series(
        probabilities
    ).rank(
        method="first",
        pct=True,
    )

    output["risk_decile"] = np.ceil(
        percentile.to_numpy() * 10
    ).clip(1, 10).astype(int)

    return output


def serializable_result(
    result: dict[str, Any],
) -> dict[str, Any]:
    """Return only JSON-safe model information."""

    return {
        "model_name": result["model_name"],
        "include_channel": result["include_channel"],
        "selected_class_weight": result["class_weight"],
        "feature_columns": result["features"],
        "selected_threshold": result[
            "selected_threshold"
        ],
        "candidate_results": result[
            "candidate_results"
        ],
        "validation": result[
            "validation_metrics"
        ],
        "test": result["test_metrics"],
    }


def write_report(
    behavioral: dict[str, Any],
    channel: dict[str, Any],
    selected_name: str,
) -> None:
    """Write the main findings to Markdown."""

    b_val = behavioral["validation_metrics"]
    c_val = channel["validation_metrics"]
    b_test = behavioral["test_metrics"]
    c_test = channel["test_metrics"]

    test_pr_delta = (
        c_test["pr_auc"] - b_test["pr_auc"]
    )

    conclusion = (
        "Signup channel improved test PR-AUC."
        if test_pr_delta > 0
        else "Signup channel did not improve test PR-AUC."
    )

    report = f"""# Kairo Customer Churn Model Report

## Objective

Predict whether an existing customer places no eligible order during
the 90 days after a point-in-time snapshot.

## Experimental Design

- Training snapshots: 2024-12-31 and 2025-03-31
- Validation snapshot: 2025-06-30
- Test snapshot: 2025-09-30
- Model A: behavioral features only
- Model B: behavioral features plus signup channel
- Synthetic segment was excluded from both primary models
- Class weighting and thresholds were selected on validation data

## Validation Results

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 | Top-10% Lift |
|---|---:|---:|---:|---:|---:|---:|
| Behavioral only | {b_val['roc_auc']:.4f} | {b_val['pr_auc']:.4f} | {b_val['precision']:.4f} | {b_val['recall']:.4f} | {b_val['f1']:.4f} | {b_val['top_10_percent']['lift']:.2f}x |
| Behavioral + channel | {c_val['roc_auc']:.4f} | {c_val['pr_auc']:.4f} | {c_val['precision']:.4f} | {c_val['recall']:.4f} | {c_val['f1']:.4f} | {c_val['top_10_percent']['lift']:.2f}x |

## Final Out-of-Time Test Results

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 | Top-10% Lift | Top-20% Recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Behavioral only | {b_test['roc_auc']:.4f} | {b_test['pr_auc']:.4f} | {b_test['precision']:.4f} | {b_test['recall']:.4f} | {b_test['f1']:.4f} | {b_test['top_10_percent']['lift']:.2f}x | {b_test['top_20_percent']['recall']:.4f} |
| Behavioral + channel | {c_test['roc_auc']:.4f} | {c_test['pr_auc']:.4f} | {c_test['precision']:.4f} | {c_test['recall']:.4f} | {c_test['f1']:.4f} | {c_test['top_10_percent']['lift']:.2f}x | {c_test['top_20_percent']['recall']:.4f} |

## Selected Production Model

**{selected_name}**

{conclusion}

The production model was selected using validation PR-AUC. Test data
was used only for final out-of-time reporting.

## Interpretation

This dataset is synthetic. Signup-channel differences partly reflect
intentional generator assumptions and are predictive associations,
not causal marketing effects.
"""

    REPORT_PATH.write_text(
        report,
        encoding="utf-8",
    )


def print_summary(result: dict[str, Any]) -> None:
    """Print validation and final test results."""

    validation = result["validation_metrics"]
    test = result["test_metrics"]

    print(f"\n  {result['model_name']}")
    print(
        f"    Class weight:       "
        f"{result['class_weight']}"
    )
    print(
        f"    Threshold:          "
        f"{result['selected_threshold']:.2f}"
    )
    print(
        f"    Validation ROC-AUC: "
        f"{validation['roc_auc']:.4f}"
    )
    print(
        f"    Validation PR-AUC:  "
        f"{validation['pr_auc']:.4f}"
    )
    print(
        f"    Validation F1:      "
        f"{validation['f1']:.4f}"
    )
    print(
        f"    Test ROC-AUC:       "
        f"{test['roc_auc']:.4f}"
    )
    print(
        f"    Test PR-AUC:        "
        f"{test['pr_auc']:.4f}"
    )
    print(
        f"    Test precision:     "
        f"{test['precision']:.4f}"
    )
    print(
        f"    Test recall:        "
        f"{test['recall']:.4f}"
    )
    print(
        f"    Test F1:            "
        f"{test['f1']:.4f}"
    )
    print(
        f"    Test top-10% lift:  "
        f"{test['top_10_percent']['lift']:.2f}x"
    )
    print(
        f"    Test top-20% recall:"
        f" {test['top_20_percent']['recall']:.4f}"
    )


def main() -> None:
    """Train, evaluate, and save both churn models."""

    ARTIFACTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 68)
    print("  KAIRO CUSTOMER CHURN MODEL TRAINING")
    print("=" * 68)

    train_df = load_split(
        TRAIN_PATH,
        "TRAIN",
    )
    validation_df = load_split(
        VALIDATION_PATH,
        "VALIDATION",
    )
    test_df = load_split(
        TEST_PATH,
        "TEST",
    )

    validate_feature_configuration(
        train_df
    )

    print(
        f"\n  Train:      {len(train_df):,} rows, "
        f"{100 * train_df[LABEL_COLUMN].mean():.1f}% churn"
    )
    print(
        f"  Validation: {len(validation_df):,} rows, "
        f"{100 * validation_df[LABEL_COLUMN].mean():.1f}% churn"
    )
    print(
        f"  Test:       {len(test_df):,} rows, "
        f"{100 * test_df[LABEL_COLUMN].mean():.1f}% churn"
    )

    print("\n  Training behavioral-only model...")
    behavioral = train_model_family(
        model_name="behavioral_only",
        include_channel=False,
        train_df=train_df,
        validation_df=validation_df,
    )

    print(
        "  Training behavioral + signup-channel model..."
    )
    channel = train_model_family(
        model_name="behavioral_plus_channel",
        include_channel=True,
        train_df=train_df,
        validation_df=validation_df,
    )

    print("\n  Running final out-of-time test evaluation...")
    evaluate_test(
        behavioral,
        test_df,
    )
    evaluate_test(
        channel,
        test_df,
    )

    print_summary(behavioral)
    print_summary(channel)

    selected = max(
        [behavioral, channel],
        key=lambda result: (
            result["validation_metrics"]["pr_auc"],
            result["validation_metrics"][
                "top_20_percent"
            ]["recall"],
            result["validation_metrics"]["roc_auc"],
        ),
    )

    selected_name = selected["model_name"]

    joblib.dump(
        behavioral["pipeline"],
        BEHAVIORAL_MODEL_PATH,
    )
    joblib.dump(
        channel["pipeline"],
        CHANNEL_MODEL_PATH,
    )
    joblib.dump(
        selected["pipeline"],
        SELECTED_MODEL_PATH,
    )

    coefficients = pd.concat(
        [
            extract_coefficients(behavioral),
            extract_coefficients(channel),
        ],
        ignore_index=True,
    )
    coefficients.to_csv(
        IMPORTANCE_PATH,
        index=False,
    )

    thresholds = pd.concat(
        [
            behavioral["threshold_table"],
            channel["threshold_table"],
        ],
        ignore_index=True,
    )
    thresholds.to_csv(
        THRESHOLD_PATH,
        index=False,
    )

    predictions = pd.concat(
        [
            prediction_frame(
                test_df,
                behavioral,
            ),
            prediction_frame(
                test_df,
                channel,
            ),
        ],
        ignore_index=True,
    )
    predictions.to_parquet(
        PREDICTIONS_PATH,
        index=False,
    )

    metrics = {
        "model_version": MODEL_VERSION,
        "selected_model": selected_name,
        "selection_rule": (
            "Highest validation PR-AUC, then validation "
            "top-20% recall, then validation ROC-AUC."
        ),
        "behavioral_only": serializable_result(
            behavioral
        ),
        "behavioral_plus_channel": serializable_result(
            channel
        ),
        "channel_incremental_value": {
            "validation_pr_auc_delta": float(
                channel["validation_metrics"]["pr_auc"]
                - behavioral["validation_metrics"]["pr_auc"]
            ),
            "test_pr_auc_delta": float(
                channel["test_metrics"]["pr_auc"]
                - behavioral["test_metrics"]["pr_auc"]
            ),
            "test_roc_auc_delta": float(
                channel["test_metrics"]["roc_auc"]
                - behavioral["test_metrics"]["roc_auc"]
            ),
            "test_top_10_lift_delta": float(
                channel["test_metrics"][
                    "top_10_percent"
                ]["lift"]
                - behavioral["test_metrics"][
                    "top_10_percent"
                ]["lift"]
            ),
        },
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

    write_report(
        behavioral,
        channel,
        selected_name,
    )

    print("\n" + "=" * 68)
    print("  MODEL TRAINING COMPLETE")
    print("=" * 68)
    print(
        f"\n  Selected model:       {selected_name}"
    )
    print(
        f"  Selected model file:  {SELECTED_MODEL_PATH}"
    )
    print(
        f"  Metrics:              {METRICS_PATH}"
    )
    print(
        f"  Feature importance:   {IMPORTANCE_PATH}"
    )
    print(
        f"  Threshold analysis:   {THRESHOLD_PATH}"
    )
    print(
        f"  Test predictions:     {PREDICTIONS_PATH}"
    )
    print(
        f"  Markdown report:      {REPORT_PATH}"
    )
    print(
        "\n  Next step:\n"
        "  python analytics/churn_model/03_write_scores.py"
    )


if __name__ == "__main__":
    main()