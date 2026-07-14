-- Gold: Fact orders
-- Grain: one row per order
--
-- Unmatched source customer IDs are mapped to the unknown-customer
-- dimension member while the original source ID is preserved.

WITH customer_lookup AS (

    SELECT
        customer_id,
        segment,
        signup_cohort,
        country_code

    FROM {{ ref('dim_customers') }}

    WHERE is_unknown_customer = FALSE

)

SELECT
    o.order_id,
    o.order_number,

    -- Conformed customer key
    COALESCE(
        c.customer_id,
        '00000000-0000-0000-0000-000000000000'
    ) AS customer_id,

    -- Original customer ID retained for investigation
    o.customer_id AS source_customer_id,

    CASE
        WHEN c.customer_id IS NULL THEN TRUE
        ELSE FALSE
    END AS is_unknown_customer,

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
    COALESCE(c.segment, 'unknown') AS customer_segment,
    COALESCE(c.signup_cohort, 'unknown') AS customer_signup_cohort,
    COALESCE(c.country_code, 'UNK') AS customer_country,

    o.created_at,
    o.updated_at

FROM {{ ref('silver__orders') }} o

LEFT JOIN customer_lookup c
    ON o.customer_id = c.customer_id
