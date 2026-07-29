#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(
  cd "$(
    dirname "${BASH_SOURCE[0]}"
  )/.."
  pwd
)"

PARQUET_PATH="$PROJECT_ROOT/analytics/churn_model/data/live_customer_churn_scores.parquet"

CSV_PATH="$PROJECT_ROOT/warehouse/operational/live_customer_churn_scores.csv"

CONTAINER_PATH="/tmp/live_customer_churn_scores.csv"

if [[ ! -f "$PARQUET_PATH" ]]; then
  echo "Missing score Parquet: $PARQUET_PATH"
  exit 1
fi

mkdir -p "$(
  dirname "$CSV_PATH"
)"

python - "$PARQUET_PATH" "$CSV_PATH" <<'PY'
from pathlib import Path
import sys

import pandas as pd

source = Path(sys.argv[1])
destination = Path(sys.argv[2])

scores = pd.read_parquet(source)

if scores.empty:
    raise SystemExit(
        "Live score dataset is empty."
    )

scores.to_csv(
    destination,
    index=False,
)

print(
    f"Prepared {len(scores):,} scores "
    f"at {destination}"
)
PY

cd "$PROJECT_ROOT"

docker compose cp \
  "$CSV_PATH" \
  "api:$CONTAINER_PATH"

docker compose exec -T api \
  python -m \
  app.scripts.import_customer_churn_scores \
  "$CONTAINER_PATH"

docker compose exec -T api \
  rm -f "$CONTAINER_PATH"

echo "Live churn score sync completed."
