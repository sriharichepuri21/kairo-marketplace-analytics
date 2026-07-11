-- Silver layer: cleaned shipments
--
-- Issues fixed (from profiling):
--   1. Null representations standardized in tracking_number and carrier
--   2. Deduplicated by shipment_id, keeping latest

{% set null_values = ["'N/A'", "''", "'NULL'", "'null'", "'None'", "'-'", "'n/a'", "'NA'", "' '", "'  '"] %}

WITH nulls_fixed AS (
    SELECT
        shipment_id,
        order_id,

        CASE WHEN carrier IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE carrier
        END AS carrier,

        CASE WHEN tracking_number IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE tracking_number
        END AS tracking_number,

        shipping_method,
        status,
        shipped_at,
        estimated_delivery_at,
        delivered_at,
        weight_kg,
        shipping_cost,
        is_international,
        delay_days,
        delivery_attempts,
        created_at,
        updated_at
    FROM {{ ref('bronze__shipments') }}
),

deduplicated AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY shipment_id
            ORDER BY updated_at DESC
        ) AS _row_num
    FROM nulls_fixed
)

SELECT
    shipment_id,
    order_id,
    carrier,
    tracking_number,
    shipping_method,
    status,
    shipped_at,
    estimated_delivery_at,
    delivered_at,
    weight_kg,
    shipping_cost,
    is_international,
    delay_days,
    delivery_attempts,
    created_at,
    updated_at
FROM deduplicated
WHERE _row_num = 1