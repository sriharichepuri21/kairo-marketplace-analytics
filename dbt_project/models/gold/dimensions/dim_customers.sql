-- Gold: Customer dimension
-- Business-ready customer attributes for joining to facts

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

    -- Derived attributes
    EXTRACT(YEAR FROM signup_date) AS signup_year,
    STRFTIME(signup_date, '%Y-%m') AS signup_cohort,

    created_at,
    updated_at
FROM {{ ref('silver__customers') }}
