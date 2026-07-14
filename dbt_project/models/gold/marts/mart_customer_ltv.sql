-- Gold Mart: Customer Lifetime Spend and Retention
-- Grain: one row per customer
--
-- lifetime_customer_spend is the valid total amount charged to customers.
-- This is not marketplace commission revenue.
-- Activity uses the centralized project analysis date.

WITH parameters AS (

    SELECT CAST(
        '{{ var("analysis_as_of_date", "2025-12-31") }}'
        AS DATE
    ) AS analysis_as_of_date

),

eligible_orders AS (

    SELECT *
    FROM {{ ref('fact_orders') }}
    WHERE order_status NOT IN ('cancelled', 'refunded')

)

SELECT
    c.customer_id,
    c.customer_external_id,
    c.region,
    c.segment,
    c.signup_cohort,
    c.signup_channel,
    c.is_unknown_customer,

    -- Order metrics
    COUNT(DISTINCT o.order_id) AS total_orders,

    COUNT(
        DISTINCT CASE
            WHEN o.total_amount IS NOT NULL THEN o.order_id
        END
    ) AS financially_valid_orders,

    COUNT(
        DISTINCT CASE
            WHEN o.order_id IS NOT NULL
             AND o.total_amount IS NULL
            THEN o.order_id
        END
    ) AS invalid_financial_orders,

    MIN(o.order_date) AS first_order_date,
    MAX(o.order_date) AS last_order_date,

    -- Customer charged amount
    COALESCE(
        ROUND(
            SUM(
                CASE
                    WHEN o.total_amount IS NOT NULL
                    THEN o.total_amount
                    ELSE 0
                END
            ),
            2
        ),
        0
    ) AS lifetime_customer_spend,

    -- Backward-compatible alias
    COALESCE(
        ROUND(
            SUM(
                CASE
                    WHEN o.total_amount IS NOT NULL
                    THEN o.total_amount
                    ELSE 0
                END
            ),
            2
        ),
        0
    ) AS lifetime_revenue,

    ROUND(
        AVG(
            CASE
                WHEN o.total_amount IS NOT NULL
                THEN o.total_amount
            END
        ),
        2
    ) AS avg_order_value,

    -- Retention signals
    CASE
        WHEN COUNT(DISTINCT o.order_id) > 1 THEN TRUE
        ELSE FALSE
    END AS is_repeat_customer,

    CASE
        WHEN COUNT(DISTINCT o.order_id) = 0 THEN NULL
        ELSE DATEDIFF(
            'day',
            MIN(o.order_date),
            MAX(o.order_date)
        )
    END AS customer_lifespan_days,

    -- Activity
    CASE
        WHEN MAX(o.order_date) IS NULL THEN NULL
        ELSE DATEDIFF(
            'day',
            MAX(o.order_date),
            p.analysis_as_of_date
        )
    END AS days_since_last_order,

    CASE
        WHEN MAX(o.order_date) IS NULL THEN 'never_ordered'

        WHEN DATEDIFF(
            'day',
            MAX(o.order_date),
            p.analysis_as_of_date
        ) <= 30
        THEN 'active'

        WHEN DATEDIFF(
            'day',
            MAX(o.order_date),
            p.analysis_as_of_date
        ) <= 90
        THEN 'at_risk'

        WHEN DATEDIFF(
            'day',
            MAX(o.order_date),
            p.analysis_as_of_date
        ) <= 180
        THEN 'dormant'

        ELSE 'churned'
    END AS activity_status

FROM {{ ref('dim_customers') }} c

CROSS JOIN parameters p

LEFT JOIN eligible_orders o
    ON c.customer_id = o.customer_id

GROUP BY
    c.customer_id,
    c.customer_external_id,
    c.region,
    c.segment,
    c.signup_cohort,
    c.signup_channel,
    c.is_unknown_customer,
    p.analysis_as_of_date
