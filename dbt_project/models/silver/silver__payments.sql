-- Silver layer: cleaned payments
--
-- Issues fixed (from profiling):
--   1. Orphan order references filtered (order_id starts with 'ORPHAN-')
--   2. Null representations standardized in card_brand and failure_reason
--   3. Deduplicated by order_id + attempted_at (keeping latest per payment attempt)

{% set null_values = ["'N/A'", "''", "'NULL'", "'null'", "'None'", "'-'", "'n/a'", "'NA'", "' '", "'  '"] %}

WITH orphans_removed AS (
    SELECT *
    FROM {{ ref('bronze__payments') }}
    WHERE order_id NOT LIKE 'ORPHAN-%'
),

nulls_fixed AS (
    SELECT
        payment_id,
        order_id,
        payment_method,

        CASE WHEN card_brand IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE card_brand
        END AS card_brand,

        payment_status,
        amount,
        currency,
        processor,
        processor_transaction_id,
        attempted_at,
        completed_at,

        CASE WHEN failure_reason IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE failure_reason
        END AS failure_reason,

        is_retry,
        retry_of_payment_id,
        created_at,
        updated_at
    FROM orphans_removed
),

deduplicated AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY payment_id
            ORDER BY updated_at DESC
        ) AS _row_num
    FROM nulls_fixed
)

SELECT
    payment_id,
    order_id,
    payment_method,
    card_brand,
    payment_status,
    amount,
    currency,
    processor,
    processor_transaction_id,
    attempted_at,
    completed_at,
    failure_reason,
    is_retry,
    retry_of_payment_id,
    created_at,
    updated_at
FROM deduplicated
WHERE _row_num = 1