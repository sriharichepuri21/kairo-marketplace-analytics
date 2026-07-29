select
    event_id,

    user_id,
    session_id,

    case
        when user_id is not null
            then user_id

        else concat(
            'anonymous:',
            session_id
        )
    end as actor_id,

    case
        when user_id is not null
            then 'authenticated'

        else 'anonymous'
    end as actor_type,

    event_type,
    product_id,
    order_id,

    event_source,
    search_query,
    product_category,
    product_brand,

    coalesce(event_quantity, 1)
        as event_quantity,

    final_cart_quantity,
    search_result_count,
    order_item_count,
    tracked_order_amount,
    tracked_currency_code,

    event_date,
    occurred_at,

    event_properties

from {{ ref('silver__customer_events') }}
