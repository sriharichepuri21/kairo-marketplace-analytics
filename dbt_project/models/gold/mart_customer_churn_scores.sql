{{ config(
    materialized='table'
) }}

with churn_scores as (

    select
        cast(customer_id as varchar)
            as customer_id,

        cast(score_date as date)
            as score_date,

        cast(signup_channel as varchar)
            as signup_channel,

        cast(region as varchar)
            as region,

        cast(segment as varchar)
            as segment,

        cast(days_since_last_order as integer)
            as days_since_last_order,

        cast(total_orders as integer)
            as total_orders,

        cast(orders_last_90d as integer)
            as orders_last_90d,

        cast(lifetime_spend as double)
            as lifetime_spend,

        cast(return_order_rate as double)
            as return_order_rate,

        cast(discount_order_rate as double)
            as discount_order_rate,

        cast(is_single_order_customer as integer)
            as is_single_order_customer,

        cast(churn_probability as double)
            as churn_probability,

        cast(predicted_churn_flag as integer)
            as predicted_churn_flag,

        cast(risk_decile as integer)
            as risk_decile,

        cast(risk_segment as varchar)
            as risk_segment,

        cast(recommended_action as varchar)
            as recommended_action,

        cast(lifetime_spend_missing_flag as integer)
            as lifetime_spend_missing_flag,

        cast(probability_threshold as double)
            as probability_threshold,

        cast(model_name as varchar)
            as model_name,

        cast(model_version as varchar)
            as model_version,

        cast(scored_at_utc as timestamp)
            as scored_at_utc

    from read_parquet(
        '{{ var(
            "churn_scores_path",
            "../analytics/churn_model/data/customer_churn_scores.parquet"
        ) }}'
    )

)

select *
from churn_scores
