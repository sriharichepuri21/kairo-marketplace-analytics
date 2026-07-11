-- Gold: Product dimension
-- Product catalog with derived margin fields

SELECT
    product_id,
    product_sku,
    seller_id,
    product_name,
    category,
    subcategory,
    brand,
    price,
    cost,
    weight_kg,
    avg_rating,
    review_count,
    return_rate,
    is_active,
    launch_date,

    -- Derived: margin analysis
    ROUND(price - cost, 2) AS gross_margin,
    CASE WHEN price > 0
         THEN ROUND((price - cost) / price * 100, 2)
         ELSE 0
    END AS gross_margin_pct,

    -- Price tier
    CASE
        WHEN price < 20 THEN 'budget'
        WHEN price < 50 THEN 'mid_range'
        WHEN price < 150 THEN 'premium'
        ELSE 'luxury'
    END AS price_tier,

    created_at,
    updated_at
FROM {{ ref('silver__products') }}