-- Gold Mart: Customer Lifetime Value
-- Metric M-030 and M-040 from the charter
-- Grain: one row per customer

SELECT
    c.customer_id,
    c.customer_external_id,
    c.region,
    c.segment,
    c.signup_cohort,
    c.signup_channel,

    -- Order metrics
    COUNT(DISTINCT o.order_id) AS total_orders,
    MIN(o.order_date) AS first_order_date,
    MAX(o.order_date) AS last_order_date,

    -- Revenue
    ROUND(SUM(o.total_amount), 2) AS lifetime_revenue,
    ROUND(AVG(o.total_amount), 2) AS avg_order_value,

    -- Retention signals
    CASE WHEN COUNT(DISTINCT o.order_id) > 1 THEN TRUE ELSE FALSE END AS is_repeat_customer,
    DATEDIFF('day', MIN(o.order_date), MAX(o.order_date)) AS customer_lifespan_days,

    -- Activity
    DATEDIFF('day', MAX(o.order_date), CURRENT_DATE) AS days_since_last_order,
    CASE
        WHEN DATEDIFF('day', MAX(o.order_date), CURRENT_DATE) <= 30 THEN 'active'
        WHEN DATEDIFF('day', MAX(o.order_date), CURRENT_DATE) <= 90 THEN 'at_risk'
        WHEN DATEDIFF('day', MAX(o.order_date), CURRENT_DATE) <= 180 THEN 'dormant'
        ELSE 'churned'
    END AS activity_status

FROM {{ ref('dim_customers') }} c
LEFT JOIN {{ ref('fact_orders') }} o ON c.customer_id = o.customer_id
WHERE o.order_status NOT IN ('cancelled', 'refunded')
GROUP BY
    c.customer_id,
    c.customer_external_id,
    c.region,
    c.segment,
    c.signup_cohort,
    c.signup_channel