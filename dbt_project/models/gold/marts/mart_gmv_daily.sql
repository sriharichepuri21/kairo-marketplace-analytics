-- Gold Mart: Daily GMV
-- Metric M-001 from the charter
-- Grain: day × region × category
-- Excludes cancelled and refunded orders

SELECT
    o.order_date,
    o.region,
    oi.category,
    o.customer_segment,

    -- Volume metrics
    COUNT(DISTINCT o.order_id) AS order_count,
    COUNT(DISTINCT o.customer_id) AS customer_count,
    SUM(oi.quantity) AS items_sold,

    -- Revenue metrics
    ROUND(SUM(oi.line_total), 2) AS gmv,
    ROUND(SUM(oi.unit_cost * oi.quantity), 2) AS total_cost,
    ROUND(SUM(oi.line_total) - SUM(oi.unit_cost * oi.quantity), 2) AS gross_profit,
    ROUND(SUM(oi.discount_amount), 2) AS total_discounts,

    -- Averages
    ROUND(AVG(oi.line_total), 2) AS avg_item_value,

    -- Margin
    CASE WHEN SUM(oi.line_total) > 0
         THEN ROUND((SUM(oi.line_total) - SUM(oi.unit_cost * oi.quantity)) / SUM(oi.line_total) * 100, 2)
         ELSE 0
    END AS gross_margin_pct

FROM {{ ref('fact_orders') }} o
JOIN {{ ref('fact_order_items') }} oi ON o.order_id = oi.order_id
WHERE o.order_status NOT IN ('cancelled', 'refunded')
  AND oi.quantity > 0
  AND oi.line_total > 0
GROUP BY
    o.order_date,
    o.region,
    oi.category,
    o.customer_segment