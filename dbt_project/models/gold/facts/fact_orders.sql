-- Gold: Fact orders
-- One row per order — the core business event table
-- Joins to dim_customers, dim_dates for analysis

SELECT
    o.order_id,
    o.order_number,
    o.customer_id,
    o.region,
    o.order_status,
    o.order_channel,
    o.device_type,
    o.order_placed_at,
    CAST(o.order_placed_at AS DATE) AS order_date,
    o.currency,
    o.subtotal,
    o.discount_amount,
    o.tax_amount,
    o.shipping_cost,
    o.total_amount,
    o.item_count,
    o.is_first_order,
    o.ingestion_delay_days,
    o.is_late_arrival,
    o._has_negative_shipping,
    o._has_impossible_discount,

    -- Customer enrichment
    c.segment AS customer_segment,
    c.signup_cohort AS customer_signup_cohort,
    c.country_code AS customer_country,

    o.created_at,
    o.updated_at
FROM {{ ref('silver__orders') }} o
LEFT JOIN {{ ref('dim_customers') }} c
    ON o.customer_id = c.customer_id