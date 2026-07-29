"""
Reconcile Kairo churn-model research and production artifacts.

The statistically strongest validation candidate is preserved as the
validation winner. A simpler model is promoted to production unless
the more complex candidate provides a material validation improvement.

The out-of-time test set is reported but is never used for production
model selection.

Usage:
    python analytics/churn_model/04_reconcile_production_artifacts.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


CHURN_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CHURN_DIR / "model_artifacts"

METRICS_PATH = (
    ARTIFACTS_DIR
    / "evaluation_metrics.json"
)

DECISION_PATH = (
    ARTIFACTS_DIR
    / "production_model_decision.json"
)

PRODUCTION_FEATURES_PATH = (
    ARTIFACTS_DIR
    / "production_feature_columns.json"
)

PRODUCTION_MODEL_CARD_PATH = (
    ARTIFACTS_DIR
    / "production_model_card.md"
)

BEHAVIORAL_MODEL_PATH = (
    ARTIFACTS_DIR
    / "behavioral_model.pkl"
)

CHANNEL_MODEL_PATH = (
    ARTIFACTS_DIR
    / "channel_model.pkl"
)

PRODUCTION_MODEL_PATH = (
    ARTIFACTS_DIR
    / "model.pkl"
)

MODEL_FILES = {
    "behavioral_only": BEHAVIORAL_MODEL_PATH,
    "behavioral_plus_channel": CHANNEL_MODEL_PATH,
}

# The channel model must improve validation PR-AUC by at least
# 0.005 absolute before accepting its extra dependency.
MINIMUM_VALIDATION_PR_AUC_UPLIFT = 0.005


def load_json(
    path: Path,
) -> dict[str, Any]:
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


def write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            value,
            file,
            indent=2,
        )

        file.write("\n")


def required_model_result(
    metrics: dict[str, Any],
    model_name: str,
) -> dict[str, Any]:
    value = metrics.get(model_name)

    if not isinstance(value, dict):
        raise ValueError(
            f"Metrics are missing model result: {model_name}"
        )

    for section in [
        "validation",
        "test",
        "feature_columns",
        "selected_threshold",
    ]:
        if section not in value:
            raise ValueError(
                f"{model_name} is missing {section}"
            )

    return value


def main() -> None:
    metrics = load_json(METRICS_PATH)

    behavioral = required_model_result(
        metrics,
        "behavioral_only",
    )

    channel = required_model_result(
        metrics,
        "behavioral_plus_channel",
    )

    behavioral_validation = behavioral[
        "validation"
    ]

    channel_validation = channel[
        "validation"
    ]

    behavioral_pr_auc = float(
        behavioral_validation["pr_auc"]
    )

    channel_pr_auc = float(
        channel_validation["pr_auc"]
    )

    validation_pr_auc_delta = (
        channel_pr_auc
        - behavioral_pr_auc
    )

    validation_winner = (
        "behavioral_plus_channel"
        if channel_pr_auc > behavioral_pr_auc
        else "behavioral_only"
    )

    if (
        validation_pr_auc_delta
        >= MINIMUM_VALIDATION_PR_AUC_UPLIFT
    ):
        production_model = (
            "behavioral_plus_channel"
        )

        production_reason = (
            "The signup-channel model exceeded the "
            "minimum material validation PR-AUC uplift."
        )
    else:
        production_model = "behavioral_only"

        production_reason = (
            "The signup-channel model's validation "
            "PR-AUC improvement was below the "
            "0.005 materiality threshold, so the "
            "simpler and more portable behavioral-only "
            "model was selected."
        )

    production_result = required_model_result(
        metrics,
        production_model,
    )

    production_threshold = float(
        production_result[
            "selected_threshold"
        ]
    )

    source_model_path = MODEL_FILES[
        production_model
    ]

    if not source_model_path.exists():
        raise FileNotFoundError(
            "Selected production model artifact "
            f"does not exist: {source_model_path}"
        )

    shutil.copy2(
        source_model_path,
        PRODUCTION_MODEL_PATH,
    )

    selection_rule = (
        "Select the signup-channel model only when "
        "its validation PR-AUC improves by at least "
        f"{MINIMUM_VALIDATION_PR_AUC_UPLIFT:.3f}; "
        "otherwise select behavioral-only. "
        "The out-of-time test set is used only for "
        "final reporting."
    )

    metrics["validation_winner"] = (
        validation_winner
    )

    # Keep selected_model as the deployable model for
    # compatibility with downstream consumers.
    metrics["selected_model"] = (
        production_model
    )

    metrics["production_model"] = (
        production_model
    )

    metrics["production_threshold"] = (
        production_threshold
    )

    metrics["production_selection_rule"] = (
        selection_rule
    )

    metrics[
        "production_validation_pr_auc_delta"
    ] = validation_pr_auc_delta

    write_json(
        METRICS_PATH,
        metrics,
    )

    behavioral_test = behavioral["test"]
    channel_test = channel["test"]

    decision = {
        "production_model": production_model,
        "validation_winner": validation_winner,
        "model_version": metrics.get(
            "model_version",
        ),
        "probability_threshold": (
            production_threshold
        ),
        "selection_rule": selection_rule,
        "decision": (
            f"Use {production_model} for "
            "production scoring."
        ),
        "reason": production_reason,
        "validation_comparison": {
            "behavioral_pr_auc": (
                behavioral_pr_auc
            ),
            "channel_pr_auc": (
                channel_pr_auc
            ),
            "channel_pr_auc_delta": (
                validation_pr_auc_delta
            ),
            "minimum_required_uplift": (
                MINIMUM_VALIDATION_PR_AUC_UPLIFT
            ),
        },
        "production_validation_metrics": (
            production_result["validation"]
        ),
        "production_test_metrics": (
            production_result["test"]
        ),
        "test_metrics_for_reporting_only": {
            "behavioral_only": (
                behavioral_test
            ),
            "behavioral_plus_channel": (
                channel_test
            ),
        },
    }

    write_json(
        DECISION_PATH,
        decision,
    )

    feature_contract = {
        "model_name": production_model,
        "model_version": metrics.get(
            "model_version",
        ),
        "probability_threshold": (
            production_threshold
        ),
        "feature_columns": (
            production_result[
                "feature_columns"
            ]
        ),
    }

    write_json(
        PRODUCTION_FEATURES_PATH,
        feature_contract,
    )

    model_card = f"""# Kairo Churn Production Model

## Production decision

- Production model: `{production_model}`
- Validation winner: `{validation_winner}`
- Probability threshold: `{production_threshold:.2f}`
- Model version: `{metrics.get("model_version")}`

## Governance rule

{selection_rule}

## Validation comparison

| Model | Validation PR-AUC |
|---|---:|
| Behavioral only | {behavioral_pr_auc:.6f} |
| Behavioral plus channel | {channel_pr_auc:.6f} |
| Channel uplift | {validation_pr_auc_delta:.6f} |
| Required uplift | {MINIMUM_VALIDATION_PR_AUC_UPLIFT:.6f} |

## Production rationale

{production_reason}

The out-of-time test results are retained for final reporting and were
not used to select the production model.
"""

    PRODUCTION_MODEL_CARD_PATH.write_text(
        model_card,
        encoding="utf-8",
    )

    print("=" * 68)
    print("KAIRO CHURN PRODUCTION ARTIFACTS RECONCILED")
    print("=" * 68)
    print(
        f"Validation winner:  {validation_winner}"
    )
    print(
        f"Production model:   {production_model}"
    )
    print(
        f"PR-AUC uplift:      "
        f"{validation_pr_auc_delta:.6f}"
    )
    print(
        f"Required uplift:    "
        f"{MINIMUM_VALIDATION_PR_AUC_UPLIFT:.6f}"
    )
    print(
        f"Threshold:          "
        f"{production_threshold:.2f}"
    )
    print(
        f"Deployable model:   "
        f"{PRODUCTION_MODEL_PATH}"
    )


if __name__ == "__main__":
    main()
