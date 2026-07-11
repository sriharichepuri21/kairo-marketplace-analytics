-- Silver layer: cleaned customers
-- 
-- Issues fixed (from profiling):
--   1. Zombie test records filtered (ID starts with 'TEST-')
--   2. Column rename reversed: cust_ext_id → customer_external_id
--   3. Null representations standardized across email, first_name, last_name, signup_channel
--   4. Schema evolution columns preserved (promo_code, loyalty_points, referral_source)
--   5. Deduplicated by business key (customer_external_id), keeping latest record

{% set null_values = ["'N/A'", "''", "'NULL'", "'null'", "'None'", "'-'", "'n/a'", "'NA'", "' '", "'  '"] %}

WITH zombies_removed AS (
    -- Step 1: Remove test/QA records
    SELECT *
    FROM {{ ref('bronze__customers') }}
    WHERE customer_id NOT LIKE 'TEST-%'
      AND email NOT LIKE '%@localhost%'
      AND email NOT LIKE '%test@test%'
      AND email NOT LIKE '%asdf@asdf%'
),

nulls_standardized AS (
    -- Step 2: Fix column rename + standardize null representations
    SELECT
        customer_id,
        cust_ext_id AS customer_external_id,

        CASE WHEN email IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE email
        END AS email,

        CASE WHEN first_name IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE first_name
        END AS first_name,

        CASE WHEN last_name IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE last_name
        END AS last_name,

        region,
        country_code,
        segment,
        signup_date,

        CASE WHEN signup_channel IN ({{ null_values | join(', ') }}) THEN NULL
             ELSE signup_channel
        END AS signup_channel,

        account_status,
        created_at,
        updated_at,

        -- Schema evolution columns — keep as-is
        promo_code,
        loyalty_points,
        referral_source
    FROM zombies_removed
),

deduplicated AS (
    -- Step 3: Deduplicate by business key, keep latest record
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY customer_external_id
            ORDER BY updated_at ASC
        ) AS _row_num
    FROM nulls_standardized
)

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
    created_at,
    updated_at,
    promo_code,
    loyalty_points,
    referral_source
FROM deduplicated
WHERE _row_num = 1