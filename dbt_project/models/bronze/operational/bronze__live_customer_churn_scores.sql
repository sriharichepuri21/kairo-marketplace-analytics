{{ config(
    materialized='view'
) }}

select *

from read_parquet(
    '{{ var(
        "live_churn_scores_path",
        "analytics/churn_model/data/live_customer_churn_scores.parquet"
    ) }}'
)
