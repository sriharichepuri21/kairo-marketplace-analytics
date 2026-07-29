with parameters as (

    select cast(
        '{{ var(
            "operational_analysis_as_of_date",
            "2026-07-29"
        ) }}'
        as date
    ) as analysis_as_of_date

),

actor_steps as (

    select
        actor_id,
        actor_type,

        case
            when sum(product_views) > 0
            then 1
            else 0
        end as viewed_product,

        case
            when sum(add_to_cart_events) > 0
            then 1
            else 0
        end as added_to_cart,

        case
            when sum(checkout_starts) > 0
            then 1
            else 0
        end as started_checkout,

        case
            when sum(orders_placed) > 0
            then 1
            else 0
        end as placed_order

    from {{ ref('int_customer_daily_activity') }}

    group by
        actor_id,
        actor_type

),

funnel as (

    select
        actor_type,

        count(*) as actor_count,

        sum(viewed_product)
            as actors_with_product_view,

        sum(added_to_cart)
            as actors_with_cart_addition,

        sum(started_checkout)
            as actors_with_checkout,

        sum(placed_order)
            as actors_with_order,

        sum(
            case
                when added_to_cart = 1
                 and placed_order = 0
                then 1
                else 0
            end
        ) as actors_with_cart_abandonment

    from actor_steps

    group by actor_type

)

select
    p.analysis_as_of_date,
    f.actor_type,
    f.actor_count,
    f.actors_with_product_view,
    f.actors_with_cart_addition,
    f.actors_with_checkout,
    f.actors_with_order,
    f.actors_with_cart_abandonment,

    round(
        cast(
            f.actors_with_cart_addition
            as double
        )
        / nullif(
            f.actors_with_product_view,
            0
        ),
        4
    ) as view_to_cart_conversion_rate,

    round(
        cast(
            f.actors_with_checkout
            as double
        )
        / nullif(
            f.actors_with_cart_addition,
            0
        ),
        4
    ) as cart_to_checkout_conversion_rate,

    round(
        cast(
            f.actors_with_order
            as double
        )
        / nullif(
            f.actors_with_checkout,
            0
        ),
        4
    ) as checkout_to_order_conversion_rate,

    round(
        cast(
            f.actors_with_cart_abandonment
            as double
        )
        / nullif(
            f.actors_with_cart_addition,
            0
        ),
        4
    ) as cart_abandonment_rate

from funnel f

cross join parameters p
