select
    user_id,
    total_orders,
    days_since_last_order,
    average_order_value

from {{ ref(
    'mart_live_customer_churn_scores'
) }}

where total_orders < 1
   or days_since_last_order is null
   or average_order_value is null
