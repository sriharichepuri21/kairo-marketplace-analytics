-- Gold Mart: Daily Marketplace Economics
-- Grain: day × region × category × customer segment
-- Excludes cancelled and refunded orders
--
-- IMPORTANT:
-- order_count is correct at this exact grain but is not additive across
-- categories or customer segments. Use fact_orders for company-wide
-- distinct order totals.

SELECT
    o.order_date,
    o.region,
    oi.category,
    o.customer_segment,

    -- Volume metrics
    COUNT(DISTINCT o.order_id) AS order_count,

    COUNT(
        DISTINCT CASE
            WHEN oi.is_gmv_valid THEN o.order_id
        END
    ) AS financially_valid_order_count,

    COUNT(DISTINCT o.customer_id) AS customer_count,

    SUM(
        CASE
            WHEN oi.is_gmv_valid THEN oi.quantity
            ELSE 0
        END
    ) AS items_sold,

    -- Data-quality metrics
    SUM(
        CASE
            WHEN NOT oi.is_gmv_valid THEN 1
            ELSE 0
        END
    ) AS invalid_gmv_item_count,

    SUM(
        CASE
            WHEN NOT oi.is_margin_valid THEN 1
            ELSE 0
        END
    ) AS invalid_margin_item_count,

    -- Merchandise metrics
    ROUND(
        SUM(
            CASE
                WHEN oi.is_gmv_valid THEN oi.gross_gmv
                ELSE 0
            END
        ),
        2
    ) AS gross_gmv,

    ROUND(
        SUM(
            CASE
                WHEN oi.is_gmv_valid THEN oi.net_gmv
                ELSE 0
            END
        ),
        2
    ) AS net_gmv,

    -- Backward-compatible alias:
    -- from this point forward, gmv means Net GMV.
    ROUND(
        SUM(
            CASE
                WHEN oi.is_gmv_valid THEN oi.net_gmv
                ELSE 0
            END
        ),
        2
    ) AS gmv,

    ROUND(
        SUM(
            CASE
                WHEN oi.is_gmv_valid THEN oi.discount_amount
                ELSE 0
            END
        ),
        2
    ) AS total_discounts,

    ROUND(
        SUM(
            CASE
                WHEN oi.is_gmv_valid
                THEN COALESCE(oi.tax_amount, 0)
                ELSE 0
            END
        ),
        2
    ) AS total_item_tax,

    -- Margin metrics use only rows with valid cost information
    ROUND(
        SUM(
            CASE
                WHEN oi.is_margin_valid THEN oi.merchandise_cost
                ELSE 0
            END
        ),
        2
    ) AS total_cost,

    ROUND(
        SUM(
            CASE
                WHEN oi.is_margin_valid
                THEN oi.net_gmv - oi.merchandise_cost
                ELSE 0
            END
        ),
        2
    ) AS gross_profit,

    ROUND(
        AVG(
            CASE
                WHEN oi.is_gmv_valid THEN oi.net_gmv
            END
        ),
        2
    ) AS avg_item_value,

    CASE
        WHEN SUM(
            CASE
                WHEN oi.is_margin_valid THEN oi.net_gmv
                ELSE 0
            END
        ) > 0
        THEN ROUND(
            100.0
            * SUM(
                CASE
                    WHEN oi.is_margin_valid
                    THEN oi.net_gmv - oi.merchandise_cost
                    ELSE 0
                END
            )
            / SUM(
                CASE
                    WHEN oi.is_margin_valid THEN oi.net_gmv
                    ELSE 0
                END
            ),
            2
        )
        ELSE 0
    END AS gross_margin_pct

FROM {{ ref('fact_orders') }} o

JOIN {{ ref('fact_order_items') }} oi
    ON o.order_id = oi.order_id

WHERE o.order_status NOT IN ('cancelled', 'refunded')

GROUP BY
    o.order_date,
    o.region,
    oi.category,
    o.customer_segment
