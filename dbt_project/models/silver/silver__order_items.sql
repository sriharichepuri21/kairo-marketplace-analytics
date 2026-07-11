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

        CASE WHEN quantity < 0 THEN NULL ELSE quantity END AS quantity,
        CASE WHEN quantity < 0 THEN TRUE ELSE FALSE END AS _had_negative_quantity,

        {{ clean_numeric('unit_price') }} AS unit_price,
        {{ clean_numeric('unit_cost') }} AS unit_cost,
        discount_amount,
        tax_amount,
        {{ clean_numeric('line_total') }} AS line_total

    FROM orphans_removed
)

SELECT * FROM type_fixed