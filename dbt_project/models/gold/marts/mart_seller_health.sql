-- Gold Mart: Seller Health
-- Metrics M-050, M-052 from the charter
-- Grain: one row per seller

SELECT
    s.seller_id,
    s.seller_external_id,
    s.business_name,
    s.tier,
    s.seller_type,
    s.region,
    s.primary_category,
    s.commission_rate,
    s.avg_rating,
    s.onboarding_cohort,

    -- Order metrics
    COUNT(DISTINCT oi.order_id) AS total_orders,
    SUM(oi.quantity) AS total_items_sold,
    ROUND(SUM(oi.line_total), 2) AS total_gmv,

    -- Revenue to platform
    ROUND(SUM(oi.line_total) * s.commission_rate, 2) AS commission_revenue,

    -- Product metrics
    COUNT(DISTINCT oi.product_id) AS active_products_sold,

    -- Average order metrics
    ROUND(AVG(oi.line_total), 2) AS avg_item_value,

    -- Activity
    MIN(o.order_date) AS first_sale_date,
    MAX(o.order_date) AS last_sale_date,
    DATEDIFF('day', MAX(o.order_date), CURRENT_DATE) AS days_since_last_sale,
    CASE
        WHEN DATEDIFF('day', MAX(o.order_date), CURRENT_DATE) <= 30 THEN 'active'
        WHEN DATEDIFF('day', MAX(o.order_date), CURRENT_DATE) <= 90 THEN 'at_risk'
        ELSE 'churned'
    END AS health_status

FROM {{ ref('dim_sellers') }} s
LEFT JOIN {{ ref('fact_order_items') }} oi ON s.seller_id = oi.seller_id
LEFT JOIN {{ ref('fact_orders') }} o ON oi.order_id = o.order_id
WHERE o.order_status NOT IN ('cancelled', 'refunded')
GROUP BY
    s.seller_id,
    s.seller_external_id,
    s.business_name,
    s.tier,
    s.seller_type,
    s.region,
    s.primary_category,
    s.commission_rate,
    s.avg_rating,
    s.onboarding_cohort