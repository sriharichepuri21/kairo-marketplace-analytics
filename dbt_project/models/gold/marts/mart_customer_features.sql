with parameters as (

    select cast(
        '{{ var(
            "operational_analysis_as_of_date",
            "2026-07-29"
        ) }}'
        as date
    ) as analysis_as_of_date

),

event_features as (

    select
        e.user_id,

        count(*) as lifetime_event_count,

        min(e.occurred_at)
            as first_activity_at,

        max(e.occurred_at)
            as last_activity_at,

        sum(
            case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.event_type
                    = 'product_view'
                then 1
                else 0
            end
        ) as product_views_30d,

        sum(
            case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.event_type
                    = 'product_search'
                then 1
                else 0
            end
        ) as product_searches_30d,

        sum(
            case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.event_type
                    = 'add_to_cart'
                then 1
                else 0
            end
        ) as add_to_cart_events_30d,

        sum(
            case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.event_type
                    = 'remove_from_cart'
                then 1
                else 0
            end
        ) as remove_from_cart_events_30d,

        sum(
            case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.event_type
                    = 'checkout_started'
                then 1
                else 0
            end
        ) as checkout_starts_30d,

        sum(
            case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.event_type
                    = 'order_placed'
                then 1
                else 0
            end
        ) as tracked_orders_30d,

        sum(
            case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.event_type
                    = 'add_to_cart'
                then e.event_quantity
                else 0
            end
        ) as cart_units_added_30d,

        sum(
            case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.event_type
                    = 'remove_from_cart'
                then e.event_quantity
                else 0
            end
        ) as cart_units_removed_30d,

        count(
            distinct case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.product_id is not null
                then e.product_id
            end
        ) as distinct_products_30d,

        count(
            distinct case
                when e.event_date
                    >= p.analysis_as_of_date
                       - interval '30 days'
                 and e.product_category
                    is not null
                then e.product_category
            end
        ) as category_diversity_30d

    from {{ ref('fact_customer_events') }} e

    cross join parameters p

    where e.user_id is not null
      and e.event_date
          <= p.analysis_as_of_date

    group by e.user_id

),

order_features as (

    select
        o.user_id,

        count(*) as total_orders,

        sum(
            case
                when cast(o.created_at as date)
                    >= p.analysis_as_of_date
                       - interval '30 days'
                then 1
                else 0
            end
        ) as orders_last_30d,

        sum(
            case
                when cast(o.created_at as date)
                    >= p.analysis_as_of_date
                       - interval '90 days'
                then 1
                else 0
            end
        ) as orders_last_90d,

        sum(
            case
                when cast(o.created_at as date)
                    >= p.analysis_as_of_date
                       - interval '60 days'

                 and cast(o.created_at as date)
                    < p.analysis_as_of_date
                      - interval '30 days'

                then 1
                else 0
            end
        ) as orders_previous_30d,

        round(
            sum(o.total_amount),
            2
        ) as lifetime_spend,

        round(
            sum(
                case
                    when cast(o.created_at as date)
                        >= p.analysis_as_of_date
                           - interval '90 days'
                    then o.total_amount
                    else 0
                end
            ),
            2
        ) as spend_last_90d,

        round(
            avg(o.total_amount),
            2
        ) as average_order_value,

        min(o.created_at)
            as first_order_at,

        max(o.created_at)
            as last_order_at

    from {{ ref('silver__operational_orders') }} o

    cross join parameters p

    where cast(o.created_at as date)
          <= p.analysis_as_of_date

      and o.order_status != 'cancelled'

    group by o.user_id

)

select
    p.analysis_as_of_date
        as feature_snapshot_date,

    u.user_id,
    u.email,
    u.full_name,
    u.role,
    u.is_active,

    u.created_at
        as account_created_at,

    greatest(
        0,
        datediff(
            'day',
            cast(u.created_at as date),
            p.analysis_as_of_date
        )
    ) as account_age_days,

    coalesce(
        e.lifetime_event_count,
        0
    ) as lifetime_event_count,

    e.first_activity_at,
    e.last_activity_at,

    case
        when e.last_activity_at is null
        then null

        else datediff(
            'day',
            cast(e.last_activity_at as date),
            p.analysis_as_of_date
        )
    end as days_since_last_activity,

    coalesce(
        e.product_views_30d,
        0
    ) as product_views_30d,

    coalesce(
        e.product_searches_30d,
        0
    ) as product_searches_30d,

    coalesce(
        e.add_to_cart_events_30d,
        0
    ) as add_to_cart_events_30d,

    coalesce(
        e.remove_from_cart_events_30d,
        0
    ) as remove_from_cart_events_30d,

    coalesce(
        e.checkout_starts_30d,
        0
    ) as checkout_starts_30d,

    coalesce(
        e.tracked_orders_30d,
        0
    ) as tracked_orders_30d,

    coalesce(
        e.cart_units_added_30d,
        0
    ) as cart_units_added_30d,

    coalesce(
        e.cart_units_removed_30d,
        0
    ) as cart_units_removed_30d,

    coalesce(
        e.distinct_products_30d,
        0
    ) as distinct_products_30d,

    coalesce(
        e.category_diversity_30d,
        0
    ) as category_diversity_30d,

    coalesce(
        o.total_orders,
        0
    ) as total_orders,

    coalesce(
        o.orders_last_30d,
        0
    ) as orders_last_30d,

    coalesce(
        o.orders_last_90d,
        0
    ) as orders_last_90d,

    coalesce(
        o.orders_previous_30d,
        0
    ) as orders_previous_30d,

    coalesce(
        o.orders_last_30d,
        0
    )
    -
    coalesce(
        o.orders_previous_30d,
        0
    ) as purchase_frequency_change_30d,

    coalesce(
        o.lifetime_spend,
        0
    ) as lifetime_spend,

    coalesce(
        o.spend_last_90d,
        0
    ) as spend_last_90d,

    coalesce(
        o.average_order_value,
        0
    ) as average_order_value,

    o.first_order_at,
    o.last_order_at,

    case
        when o.last_order_at is null
        then null

        else datediff(
            'day',
            cast(o.last_order_at as date),
            p.analysis_as_of_date
        )
    end as days_since_last_order,

    case
        when coalesce(
            e.add_to_cart_events_30d,
            0
        ) > 0

         and coalesce(
            o.orders_last_30d,
            0
        ) = 0

        then true
        else false
    end as has_recent_cart_abandonment,

    case
        when e.last_activity_at is null
        then 'no_activity'

        when datediff(
            'day',
            cast(e.last_activity_at as date),
            p.analysis_as_of_date
        ) <= 7
        then 'active'

        when datediff(
            'day',
            cast(e.last_activity_at as date),
            p.analysis_as_of_date
        ) <= 30
        then 'warm'

        else 'dormant'
    end as activity_status

from {{ ref('silver__operational_users') }} u

cross join parameters p

left join event_features e
    on u.user_id = e.user_id

left join order_features o
    on u.user_id = o.user_id
