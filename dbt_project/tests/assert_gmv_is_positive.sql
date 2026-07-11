-- Test: All GMV values in the daily mart should be positive

SELECT order_date, region, category, gmv
FROM {{ ref('mart_gmv_daily') }}
WHERE gmv <= 0
LIMIT 1