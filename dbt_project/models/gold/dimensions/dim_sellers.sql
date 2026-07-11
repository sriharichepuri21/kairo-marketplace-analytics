-- Gold: Seller dimension
-- Seller attributes enriched with derived fields

SELECT
    seller_id,
    seller_external_id,
    business_name,
    seller_type,
    tier,
    onboarding_date,
    region,
    country_code,
    primary_category,
    avg_rating,
    total_reviews,
    is_verified,
    is_suspended,
    commission_rate,

    -- Derived
    EXTRACT(YEAR FROM onboarding_date) AS onboarding_year,
    STRFTIME(onboarding_date, '%Y-%m') AS onboarding_cohort,

    created_at,
    updated_at
FROM {{ ref('silver__sellers') }}