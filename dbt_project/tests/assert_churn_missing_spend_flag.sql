select
    customer_id,
    lifetime_spend,
    lifetime_spend_missing_flag

from {{ ref('mart_customer_churn_scores') }}

where
    (
        lifetime_spend is null
        and lifetime_spend_missing_flag != 1
    )

    or (
        lifetime_spend is not null
        and lifetime_spend_missing_flag != 0
    )
