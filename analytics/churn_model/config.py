"""
Central configuration for the Kairo customer churn system.

This file defines:
- Project and artifact paths
- Point-in-time snapshot dates
- Churn-label rules
- Model feature groups
- Reproducibility settings
"""

from datetime import date
from pathlib import Path


CHURN_MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CHURN_MODEL_DIR.parents[1]

DB_PATH = PROJECT_ROOT / "warehouse" / "kairo.duckdb"

DATA_DIR = CHURN_MODEL_DIR / "data"
ARTIFACTS_DIR = CHURN_MODEL_DIR / "model_artifacts"

REPORT_PATH = CHURN_MODEL_DIR / "churn_analysis_report.md"


TRAIN_SNAPSHOTS = [
    date(2024, 12, 31),
    date(2025, 3, 31),
]

VALIDATION_SNAPSHOT = date(2025, 6, 30)

TEST_SNAPSHOT = date(2025, 9, 30)

ALL_SNAPSHOTS = [
    *TRAIN_SNAPSHOTS,
    VALIDATION_SNAPSHOT,
    TEST_SNAPSHOT,
]


CHURN_WINDOW_DAYS = 90

MIN_ORDERS_FOR_ELIGIBILITY = 1

RANDOM_SEED = 42


ID_COLUMN = "customer_id"
SNAPSHOT_COLUMN = "snapshot_date"
LABEL_COLUMN = "churned"

PREDICTION_COUNT_COLUMN = "orders_in_prediction_window"


BEHAVIORAL_NUMERIC_FEATURES = [
    "days_since_last_order",
    "days_since_first_order",
    "total_orders",
    "orders_last_30d",
    "orders_last_90d",
    "avg_days_between_orders",
    "lifetime_spend",
    "avg_order_value",
    "spend_last_90d",
    "spend_trend",
    "category_count",
    "historical_item_count",
    "discount_order_rate",
    "return_count",
    "return_order_rate",
    "return_item_rate",
    "review_count",
    "avg_rating_given",
    "late_delivery_count",
    "avg_delivery_delay",
    "customer_tenure_days",
]


BEHAVIORAL_BINARY_FEATURES = [
    "is_single_order_customer",
    "has_return",
    "has_review",
    "has_completed_delivery",
]


CHANNEL_FEATURES = [
    "signup_channel",
]


SEGMENT_FEATURES = [
    "segment",
]


REGION_FEATURES = [
    "region",
]


BEHAVIORAL_FEATURES = [
    *BEHAVIORAL_NUMERIC_FEATURES,
    *BEHAVIORAL_BINARY_FEATURES,
]


BEHAVIORAL_PLUS_CHANNEL_FEATURES = [
    *BEHAVIORAL_FEATURES,
    *CHANNEL_FEATURES,
]


BEHAVIORAL_PLUS_CHANNEL_AND_REGION_FEATURES = [
    *BEHAVIORAL_FEATURES,
    *CHANNEL_FEATURES,
    *REGION_FEATURES,
]


SYNTHETIC_SEGMENT_EXPERIMENT_FEATURES = [
    *BEHAVIORAL_FEATURES,
    *CHANNEL_FEATURES,
    *REGION_FEATURES,
    *SEGMENT_FEATURES,
]


LOG_TRANSFORM_FEATURES = [
    "total_orders",
    "orders_last_30d",
    "orders_last_90d",
    "lifetime_spend",
    "avg_order_value",
    "spend_last_90d",
    "category_count",
    "historical_item_count",
    "return_count",
    "review_count",
    "late_delivery_count",
    "customer_tenure_days",
]


MODEL_NAMES = {
    "behavioral": "behavioral_only",
    "behavioral_plus_channel": "behavioral_plus_channel",
    "synthetic_segment_experiment": "behavioral_channel_segment",
}


MODEL_VERSION = "kairo_churn_v1"

DEFAULT_PROBABILITY_THRESHOLD = 0.50

HIGH_RISK_PERCENTILE = 0.20
MEDIUM_RISK_PERCENTILE = 0.50


DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

ARTIFACTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)
