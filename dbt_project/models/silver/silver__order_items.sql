-- Silver layer: cleaned order items
--
-- Issues fixed (from profiling):
--   1. Orphan records filtered (order_id starts with 'ORPHAN-')
--   2. Negative quantities set to NULL and flagged
--   3. Type drift fixed: unit_price, unit_cost, line_total cast to DOUBLE

WITH orphans_removed AS (
    SELECT *
    FROM {{ ref('bronze__order_items') }}
    WHERE order_id NOT LIKE 'ORPHAN-%'
),

type_fixed AS (
    SELECT
        order_item_id,
        order_id,
        product_id,
        seller_id,
        category,

        -- Fix negative quantities
        CASE WHEN quantity < 0 THEN NULL ELSE quantity END AS quantity,
        CASE WHEN quantity < 0 THEN TRUE ELSE FALSE END AS _had_negative_quantity,

        -- Type drift fix: strip symbols, cast to numeric
        TRY_CAST(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                TRIM(unit_price),
                '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '.')
            AS DOUBLE
        ) AS unit_price,

        TRY_CAST(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                TRIM(unit_cost),
                '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '.')
            AS DOUBLE
        ) AS unit_cost,

        discount_amount,
        tax_amount,

        TRY_CAST(
            REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                TRIM(line_total),
                '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '.')
            AS DOUBLE
        ) AS line_total

    FROM orphans_removed
)

SELECT * FROM type_fixed