select
    s.user_id,
    s.feature_snapshot_date,
    f.feature_snapshot_date
        as current_feature_snapshot_date,

    s.total_orders
        as scored_total_orders,

    f.total_orders
        as current_total_orders,

    s.lifetime_spend
        as scored_lifetime_spend,

    f.lifetime_spend
        as current_lifetime_spend

from {{ ref(
    'mart_live_customer_churn_scores'
) }} s

left join {{ ref(
    'mart_customer_features'
) }} f
    on s.user_id = f.user_id

where f.user_id is null

   or s.feature_snapshot_date
      != f.feature_snapshot_date

   or s.total_orders
      != f.total_orders

   or abs(
       s.lifetime_spend
       - f.lifetime_spend
   ) > 0.01
