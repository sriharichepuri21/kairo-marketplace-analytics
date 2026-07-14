-- Gold: Fact order items
-- Grain: one row per order item
--
-- Financial definitions:
-- gross_gmv = unit_price × quantity
-- net_gmv   = gross_gmv - item discount
--
-- line_total is retained for reconciliation only because it includes item tax.

WITH item_base AS (

    SELECT
        oi.*,

        CASE
            WHEN oi.quantity > 0
             AND oi.unit_price IS NOT NULL
             AND oi.unit_price >= 0
             AND oi.discount_amount IS NOT NULL
             AND oi.discount_amount >= 0
             AND oi.discount_amount <= (oi.unit_price * oi.quantity)
            THEN TRUE
            ELSE FALSE
        END AS is_gmv_valid

    FROM {{ ref('silver__order_items') }} oi

)

SELECT
    oi.order_item_id,
    oi.order_id,
    oi.product_id,
    oi.seller_id,
    oi.category,
    oi.quantity,
    oi.unit_price,
    oi.unit_cost,
    oi.discount_amount,
    oi.tax_amount,
    oi.line_total,
    oi._had_negative_quantity,

    -- Financial quality flags
    oi.is_gmv_valid,

    CASE
        WHEN oi.is_gmv_valid
         AND oi.unit_cost IS NOT NULL
         AND oi.unit_cost >= 0
        THEN TRUE
        ELSE FALSE
    END AS is_margin_valid,

    -- Correct merchandise metrics
    CASE
        WHEN oi.is_gmv_valid
        THEN ROUND(oi.unit_price * oi.quantity, 2)
        ELSE NULL
    END AS gross_gmv,

    CASE
        WHEN oi.is_gmv_valid
        THEN ROUND(
            (oi.unit_price * oi.quantity) - oi.discount_amount,
            2
        )
        ELSE NULL
    END AS net_gmv,

    CASE
        WHEN oi.is_gmv_valid
         AND oi.unit_cost IS NOT NULL
         AND oi.unit_cost >= 0
        THEN ROUND(oi.unit_cost * oi.quantity, 2)
        ELSE NULL
    END AS merchandise_cost,

    -- Diagnostic reconstruction of source line_total
    CASE
        WHEN oi.is_gmv_valid
         AND oi.tax_amount IS NOT NULL
        THEN ROUND(
            (oi.unit_price * oi.quantity)
            - oi.discount_amount
            + oi.tax_amount,
            2
        )
        ELSE NULL
    END AS expected_line_total,

    -- Product enrichment
    p.product_name,
    p.subcategory,
    p.brand,
    p.price_tier,
    p.gross_margin_pct AS product_margin_pct,

    -- Seller enrichment
    s.business_name AS seller_name,
    s.tier AS seller_tier,
    s.commission_rate AS seller_commission_rate,

    -- Order context
    o.order_date,
    o.region,
    o.customer_segment,
    o.order_status

FROM item_base oi

LEFT JOIN {{ ref('dim_products') }} p
    ON oi.product_id = p.product_id

LEFT JOIN {{ ref('dim_sellers') }} s
    ON oi.seller_id = s.seller_id

LEFT JOIN {{ ref('fact_orders') }} o
    ON oi.order_id = o.order_id
