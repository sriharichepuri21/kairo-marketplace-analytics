{{ config(
    materialized='table'
) }}

with scores as (

    select *
    from {{ ref(
        'silver__live_customer_churn_scores'
    ) }}

),

customers as (

    select
        user_id,
        email,
        full_name,
        role,
        is_active,
        activity_status

    from {{ ref(
        'mart_customer_features'
    ) }}

)

select
    s.feature_snapshot_date,
    s.user_id,

    c.email,
    c.full_name,
    c.role,
    c.is_active,
    c.activity_status,

    s.days_since_last_order,
    s.total_orders,
    s.orders_last_30d,
    s.orders_last_90d,
    s.lifetime_spend,
    s.average_order_value,
    s.spend_last_90d,
    s.account_age_days,
    s.is_single_order_customer,

    s.churn_probability,
    s.predicted_churn_flag,

    s.risk_rank,
    s.risk_percentile,
    s.risk_decile,
    s.risk_segment,
    s.recommended_action,
    s.scoring_population_size,

    s.probability_threshold,
    s.model_name,
    s.model_version,
    s.scored_at_utc,

    case
        when c.user_id is not null
        then true
        else false
    end as has_customer_match

from scores s

left join customers c
    on s.user_id = c.user_id
