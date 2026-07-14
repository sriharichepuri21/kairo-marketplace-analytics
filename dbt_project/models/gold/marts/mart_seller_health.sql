-- Gold Mart: Seller Health
-- Grain: one row per seller
--
-- Commission revenue is calculated from Net GMV, excluding tax.
-- Seller activity uses the centralized project analysis date.

WITH parameters AS (

    SELECT CAST(
        '{{ var("analysis_as_of_date", "2025-12-31") }}'
        AS DATE
    ) AS analysis_as_of_date

),

eligible_sales AS (

    SELECT
        oi.*,
        o.order_date

    FROM {{ ref('fact_order_items') }} oi

    JOIN {{ ref('fact_orders') }} o
        ON oi.order_id = o.order_id

    WHERE o.order_status NOT IN ('cancelled', 'refunded')

)

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
    COUNT(DISTINCT es.order_id) AS total_orders,

    SUM(
        CASE
            WHEN es.is_gmv_valid THEN es.quantity
            ELSE 0
        END
    ) AS total_items_sold,

    -- Net GMV is the primary seller GMV metric
    COALESCE(
        ROUND(
            SUM(
                CASE
                    WHEN es.is_gmv_valid THEN es.net_gmv
                    ELSE 0
                END
            ),
            2
        ),
        0
    ) AS total_gmv,

    COALESCE(
        ROUND(
            SUM(
                CASE
                    WHEN es.is_gmv_valid THEN es.gross_gmv
                    ELSE 0
                END
            ),
            2
        ),
        0
    ) AS gross_gmv,

    COALESCE(
        ROUND(
            SUM(
                CASE
                    WHEN es.is_gmv_valid THEN es.net_gmv
                    ELSE 0
                END
            ),
            2
        ),
        0
    ) AS net_gmv,

    -- Platform revenue: Net GMV × seller commission rate
    COALESCE(
        ROUND(
            SUM(
                CASE
                    WHEN es.is_gmv_valid
                    THEN es.net_gmv * COALESCE(s.commission_rate, 0)
                    ELSE 0
                END
            ),
            2
        ),
        0
    ) AS commission_revenue,

    -- Data quality
    SUM(
        CASE
            WHEN es.order_item_id IS NOT NULL
             AND NOT es.is_gmv_valid
            THEN 1
            ELSE 0
        END
    ) AS invalid_financial_item_count,

    -- Product metrics
    COUNT(
        DISTINCT CASE
            WHEN es.is_gmv_valid THEN es.product_id
        END
    ) AS active_products_sold,

    -- Average item-level Net GMV
    ROUND(
        AVG(
            CASE
                WHEN es.is_gmv_valid THEN es.net_gmv
            END
        ),
        2
    ) AS avg_item_value,

    -- Activity
    MIN(es.order_date) AS first_sale_date,
    MAX(es.order_date) AS last_sale_date,

    CASE
        WHEN MAX(es.order_date) IS NULL THEN NULL
        ELSE DATEDIFF(
            'day',
            MAX(es.order_date),
            p.analysis_as_of_date
        )
    END AS days_since_last_sale,

    CASE
        WHEN MAX(es.order_date) IS NULL THEN 'no_sales'

        WHEN DATEDIFF(
            'day',
            MAX(es.order_date),
            p.analysis_as_of_date
        ) <= 30
        THEN 'active'

        WHEN DATEDIFF(
            'day',
            MAX(es.order_date),
            p.analysis_as_of_date
        ) <= 90
        THEN 'at_risk'

        ELSE 'churned'
    END AS health_status

FROM {{ ref('dim_sellers') }} s

CROSS JOIN parameters p

LEFT JOIN eligible_sales es
    ON s.seller_id = es.seller_id

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
    s.onboarding_cohort,
    p.analysis_as_of_date
