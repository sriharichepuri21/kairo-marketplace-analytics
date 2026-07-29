#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.."
  pwd
)"

OUTPUT_DIR="${REPO_ROOT}/warehouse/operational"

mkdir -p "${OUTPUT_DIR}"
cd "${REPO_ROOT}"


export_query() {
  local output_file="$1"
  local query="$2"
  local final_path="${OUTPUT_DIR}/${output_file}"
  local temporary_path="${final_path}.tmp"

  echo "Exporting ${output_file}..."

  rm -f "${temporary_path}"

  {
    printf "COPY (\n%s\n) TO STDOUT WITH (FORMAT CSV, HEADER TRUE);\n" \
      "${query}"
  } |
    docker compose exec -T postgres sh -lc '
      DB_USER="${POSTGRES_USER:-postgres}"
      DB_NAME="${POSTGRES_DB:-${POSTGRES_USER:-postgres}}"

      exec psql \
        --no-psqlrc \
        --quiet \
        -v ON_ERROR_STOP=1 \
        -U "$DB_USER" \
        -d "$DB_NAME"
    ' > "${temporary_path}"

  if [[ ! -s "${temporary_path}" ]]; then
    echo "Export failed: ${output_file} is empty." >&2
    rm -f "${temporary_path}"
    exit 1
  fi

  mv "${temporary_path}" "${final_path}"
}


export_query \
  "operational_users.csv" \
  "
    SELECT
      id,
      email,
      full_name,
      role,
      is_active,
      created_at,
      updated_at
    FROM users
    ORDER BY created_at, id
  "


export_query \
  "operational_orders.csv" \
  "
    SELECT
      id,
      order_number,
      user_id,
      status,
      payment_status,
      currency_code,
      subtotal,
      shipping_amount,
      tax_amount,
      total_amount,
      created_at,
      updated_at
    FROM orders
    ORDER BY created_at, id
  "


export_query \
  "customer_events.csv" \
  "
    SELECT
      id,
      user_id,
      session_id,
      event_type,
      product_id,
      order_id,
      properties,
      occurred_at
    FROM customer_events
    ORDER BY occurred_at, id
  "


echo
echo "Operational snapshot completed:"

for file in \
  operational_users.csv \
  operational_orders.csv \
  customer_events.csv
do
  printf "%-32s %s rows including header\n" \
    "${file}" \
    "$(wc -l < "${OUTPUT_DIR}/${file}" | tr -d ' ')"
done
