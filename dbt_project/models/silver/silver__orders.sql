-- Silver layer: cleaned orders
--
-- Issues fixed (from profiling):
--   1. Null representations standardized in order_number, currency
--   2. Type drift fixed: subtotal, discount_amount, shipping_cost, total_amount cast to DOUBLE
--   3. Business logic violations flagged (negative shipping, impossible discounts)
--   4. Late arrivals preserved with delay flag
--   5. Deduplicated by order_number (business key), keeping latest

{% set null_values = ["'N/A'", "''", "'NULL'", "'null'", "'None'", "'-'", "'n/a'", "'NA'", "' '", "'  '"] %}

WITH nulls_fixed AS (
    SELECT
        order_id,

        CASE WHEN order_number IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE order_number
        END AS order_number,

        customer_id,
        region,
        order_status,
        order_channel,
        device_type,
        order_placed_at,

        CASE WHEN currency IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE currency
        END AS currency,

        -- Type drift fix: strip currency symbols, fix comma decimals, cast to numeric
        TRY_CAST(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                TRIM(subtotal),
                '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '.')
            AS DOUBLE
        ) AS subtotal,

        TRY_CAST(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                TRIM(discount_amount),
                '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '.')
            AS DOUBLE
        ) AS discount_amount,

        tax_amount,

        TRY_CAST(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                TRIM(shipping_cost),
                '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '.')
            AS DOUBLE
        ) AS shipping_cost,

        TRY_CAST(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                TRIM(total_amount),
                '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '.')
            AS DOUBLE
        ) AS total_amount,

        item_count,
        is_first_order,
        created_at,
        updated_at,

        -- Preserve late arrival info
        COALESCE(_ingestion_delay_days, 0) AS ingestion_delay_days,
        CASE WHEN _ingestion_delay_days > 0 THEN TRUE ELSE FALSE END AS is_late_arrival

    FROM {{ ref('bronze__orders') }}
),

business_logic_flagged AS (
    SELECT *,
        -- Flag business logic violations (don't delete — flag for investigation)
        CASE WHEN shipping_cost < 0 THEN TRUE ELSE FALSE END AS _has_negative_shipping,
        CASE WHEN discount_amount > subtotal THEN TRUE ELSE FALSE END AS _has_impossible_discount
    FROM nulls_fixed
),

deduplicated AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY order_number
            ORDER BY updated_at DESC
        ) AS _row_num
    FROM business_logic_flagged
    WHERE order_number IS NOT NULL
)

SELECT
    order_id,
    order_number,
    customer_id,
    region,
    order_status,
    order_channel,
    device_type,
    order_placed_at,
    currency,
    subtotal,
    discount_amount,
    tax_amount,
    shipping_cost,
    total_amount,
    item_count,
    is_first_order,
    created_at,
    updated_at,
    ingestion_delay_days,
    is_late_arrival,
    _has_negative_shipping,
    _has_impossible_discount
FROM deduplicated
WHERE _row_num = 1