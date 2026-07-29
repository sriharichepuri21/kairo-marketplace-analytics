{{ config(
    materialized='table'
) }}

select
    cast(
        feature_snapshot_date
        as date
    ) as feature_snapshot_date,

    cast(
        user_id
        as varchar
    ) as user_id,

    cast(
        days_since_last_order
        as integer
    ) as days_since_last_order,

    cast(
        total_orders
        as integer
    ) as total_orders,

    cast(
        orders_last_30d
        as integer
    ) as orders_last_30d,

    cast(
        orders_last_90d
        as integer
    ) as orders_last_90d,

    cast(
        lifetime_spend
        as double
    ) as lifetime_spend,

    cast(
        average_order_value
        as double
    ) as average_order_value,

    cast(
        spend_last_90d
        as double
    ) as spend_last_90d,

    cast(
        account_age_days
        as integer
    ) as account_age_days,

    cast(
        is_single_order_customer
        as integer
    ) as is_single_order_customer,

    cast(
        churn_probability
        as double
    ) as churn_probability,

    cast(
        predicted_churn_flag
        as integer
    ) as predicted_churn_flag,

    cast(
        risk_rank
        as integer
    ) as risk_rank,

    cast(
        risk_percentile
        as double
    ) as risk_percentile,

    cast(
        risk_decile
        as integer
    ) as risk_decile,

    cast(
        risk_segment
        as varchar
    ) as risk_segment,

    cast(
        recommended_action
        as varchar
    ) as recommended_action,

    cast(
        scoring_population_size
        as integer
    ) as scoring_population_size,

    cast(
        probability_threshold
        as double
    ) as probability_threshold,

    cast(
        model_name
        as varchar
    ) as model_name,

    cast(
        model_version
        as varchar
    ) as model_version,

    cast(
        scored_at_utc
        as timestamptz
    ) as scored_at_utc

from {{ ref(
    'bronze__live_customer_churn_scores'
) }}
