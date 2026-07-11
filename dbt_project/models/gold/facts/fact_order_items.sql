-- Gold: Fact order items
-- One row per product line within an order
-- Grain: order × product

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

FROM {{ ref('silver__order_items') }} oi
LEFT JOIN {{ ref('dim_products') }} p ON oi.product_id = p.product_id
LEFT JOIN {{ ref('dim_sellers') }} s ON oi.seller_id = s.seller_id
LEFT JOIN {{ ref('fact_orders') }} o ON oi.order_id = o.order_id