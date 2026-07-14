-- Test: GMV values must never be negative.
-- Zero-GMV rows are allowed when a group contains only financially invalid
-- items or legitimate fully discounted merchandise.

SELECT
    order_date,
    region,
    category,
    customer_segment,
    gmv
FROM {{ ref('mart_gmv_daily') }}
WHERE gmv < 0
