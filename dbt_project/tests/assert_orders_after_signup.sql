-- Test: Flag customers with orders before signup (known synthetic data edge case)
-- Configured as WARN — not a data quality issue, but a generation quirk

{{ config(severity='warn') }}

SELECT
    o.order_id,
    o.order_date,
    c.signup_date
FROM {{ ref('fact_orders') }} o
JOIN {{ ref('dim_customers') }} c ON o.customer_id = c.customer_id
WHERE o.order_date < c.signup_date
LIMIT 1