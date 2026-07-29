select
    user_id,
    lifetime_event_count,
    product_views_30d,
    add_to_cart_events_30d,
    total_orders,
    lifetime_spend

from {{ ref('mart_customer_features') }}

where lifetime_event_count < 0
   or product_views_30d < 0
   or add_to_cart_events_30d < 0
   or total_orders < 0
   or lifetime_spend < 0
