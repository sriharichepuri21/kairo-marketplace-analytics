-- Gold: Customer dimension
-- Business-ready customer attributes for joining to facts
--
-- Includes one unknown-customer member so orphan facts remain
-- reconcilable without being treated as real registered customers.

WITH real_customers AS (

    SELECT
        customer_id,
        customer_external_id,
        email,
        first_name,
        last_name,
        region,
        country_code,
        segment,
        signup_date,
        signup_channel,
        account_status,

        EXTRACT(YEAR FROM signup_date) AS signup_year,
        STRFTIME(signup_date, '%Y-%m') AS signup_cohort,

        created_at,
        updated_at,

        FALSE AS is_unknown_customer

    FROM {{ ref('silver__customers') }}

),

unknown_customer AS (

    SELECT
        '00000000-0000-0000-0000-000000000000' AS customer_id,
        'UNKNOWN-CUSTOMER' AS customer_external_id,
        'unknown@kairo.invalid' AS email,
        'Unknown' AS first_name,
        'Customer' AS last_name,
        'UNKNOWN' AS region,
        'UNK' AS country_code,
        'unknown' AS segment,
        DATE '1900-01-01' AS signup_date,
        'unknown' AS signup_channel,
        'closed' AS account_status,

        1900 AS signup_year,
        'unknown' AS signup_cohort,

        TIMESTAMP '1900-01-01 00:00:00' AS created_at,
        TIMESTAMP '1900-01-01 00:00:00' AS updated_at,

        TRUE AS is_unknown_customer

)

SELECT * FROM real_customers

UNION ALL

SELECT * FROM unknown_customer
