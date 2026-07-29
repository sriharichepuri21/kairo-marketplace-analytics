with parameters as (

    select cast(
        '{{ var(
            "operational_analysis_as_of_date",
            "2026-07-29"
        ) }}'
        as date
    ) as analysis_as_of_date

),

events as (

    select *
    from {{ ref('fact_customer_events') }}
    where event_date <= (
        select analysis_as_of_date
        from parameters
    )

)

select
    actor_id,
    actor_type,
    user_id,
    session_id,
    event_date,

    count(*) as total_events,

    sum(
        case
            when event_type = 'product_view'
            then 1
            else 0
        end
    ) as product_views,

    sum(
        case
            when event_type = 'product_search'
            then 1
            else 0
        end
    ) as product_searches,

    sum(
        case
            when event_type = 'add_to_cart'
            then 1
            else 0
        end
    ) as add_to_cart_events,

    sum(
        case
            when event_type = 'remove_from_cart'
            then 1
            else 0
        end
    ) as remove_from_cart_events,

    sum(
        case
            when event_type = 'checkout_started'
            then 1
            else 0
        end
    ) as checkout_starts,

    sum(
        case
            when event_type = 'order_placed'
            then 1
            else 0
        end
    ) as orders_placed,

    sum(
        case
            when event_type = 'add_to_cart'
            then event_quantity
            else 0
        end
    ) as cart_units_added,

    sum(
        case
            when event_type = 'remove_from_cart'
            then event_quantity
            else 0
        end
    ) as cart_units_removed,

    count(
        distinct case
            when product_id is not null
            then product_id
        end
    ) as distinct_products_interacted,

    count(
        distinct case
            when product_category is not null
            then product_category
        end
    ) as distinct_categories_interacted,

    sum(
        case
            when event_type = 'order_placed'
            then coalesce(
                tracked_order_amount,
                0
            )
            else 0
        end
    ) as tracked_order_value,

    min(occurred_at) as first_event_at,
    max(occurred_at) as last_event_at

from events

group by
    actor_id,
    actor_type,
    user_id,
    session_id,
    event_date
