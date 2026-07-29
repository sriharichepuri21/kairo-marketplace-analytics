#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.."
  pwd
)"

LOCK_DIRECTORY="/tmp/kairo_customer_intelligence_pipeline.lock"

SNAPSHOT_DATE="$(
  date -u +%F
)"

cleanup() {
  rm -rf "$LOCK_DIRECTORY"
}

if ! mkdir "$LOCK_DIRECTORY" 2>/dev/null; then
  echo "Customer intelligence pipeline is already running."
  exit 1
fi

trap cleanup EXIT

cd "$PROJECT_ROOT"

echo "============================================================"
echo "KAIRO CUSTOMER INTELLIGENCE PIPELINE"
echo "============================================================"
echo "Snapshot date: $SNAPSHOT_DATE"
echo

echo "[1/6] Checking application services..."

docker compose ps \
  --status running \
  --services \
  | grep -q '^api$' || {
    echo "The API container is not running."
    echo "Run: docker compose up -d"
    exit 1
  }

docker compose ps \
  --status running \
  --services \
  | grep -q '^postgres$' || {
    echo "The PostgreSQL container is not running."
    echo "Run: docker compose up -d"
    exit 1
  }

echo "Application services are running."
echo

echo "[2/6] Exporting operational snapshots..."

bash scripts/export_operational_snapshot.sh

echo
echo "[3/6] Building operational customer features..."

dbt build \
  --project-dir dbt_project \
  --indirect-selection cautious \
  --vars \
  "{\"operational_analysis_as_of_date\": \"$SNAPSHOT_DATE\"}" \
  --select \
  silver__operational_users \
  silver__operational_orders \
  fact_customer_events \
  int_customer_daily_activity \
  mart_customer_funnel \
  mart_customer_features

echo
echo "[4/6] Scoring eligible live customers..."

python \
  analytics/churn_model/06_score_live_customers.py

echo
echo "[5/6] Publishing governed churn marts..."

dbt build \
  --project-dir dbt_project \
  --vars \
  "{\"operational_analysis_as_of_date\": \"$SNAPSHOT_DATE\"}" \
  --select \
  +mart_live_customer_churn_scores

echo
echo "[6/6] Synchronizing scores to PostgreSQL..."

bash \
  scripts/sync_live_churn_scores_to_postgres.sh

echo
echo "============================================================"
echo "PIPELINE COMPLETED SUCCESSFULLY"
echo "============================================================"

docker compose exec -T api python - <<'PY'
from sqlalchemy import (
    func,
    select,
)

from app.core.database import SessionLocal
from app.models import CustomerChurnScore


database = SessionLocal()

try:
    latest_batch = database.execute(
        select(
            CustomerChurnScore.feature_snapshot_date,
            CustomerChurnScore.model_version,
        )
        .order_by(
            CustomerChurnScore.scored_at_utc.desc(),
        )
        .limit(1)
    ).first()

    if latest_batch is None:
        raise SystemExit(
            "No churn scores were found after synchronization."
        )

    snapshot_date = latest_batch.feature_snapshot_date
    model_version = latest_batch.model_version

    summary = database.execute(
        select(
            func.count(
                CustomerChurnScore.id
            ),
            func.sum(
                CustomerChurnScore
                .predicted_churn_flag
                .cast(int)
            ),
            func.avg(
                CustomerChurnScore
                .churn_probability
            ),
            func.max(
                CustomerChurnScore
                .churn_probability
            ),
        ).where(
            CustomerChurnScore
            .feature_snapshot_date
            == snapshot_date,
            CustomerChurnScore
            .model_version
            == model_version,
        )
    ).one()

    print(
        f"Snapshot:             {snapshot_date}"
    )
    print(
        f"Model:                {model_version}"
    )
    print(
        f"Eligible customers:   {summary[0] or 0}"
    )
    print(
        f"Predicted churners:   {summary[1] or 0}"
    )
    print(
        "Average probability: "
        f"{float(summary[2] or 0):.4f}"
    )
    print(
        "Maximum probability: "
        f"{float(summary[3] or 0):.4f}"
    )

finally:
    database.close()
PY

echo
echo "Dashboard:"
echo "http://localhost:3001/admin/churn"
