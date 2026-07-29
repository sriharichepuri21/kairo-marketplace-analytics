with typed as (

    select
        nullif(trim(id), '')
            as event_id,

        nullif(trim(user_id), '')
            as user_id,

        nullif(trim(session_id), '')
            as session_id,

        lower(
            nullif(trim(event_type), '')
        ) as event_type,

        nullif(trim(product_id), '')
            as product_id,

        nullif(trim(order_id), '')
            as order_id,

        try_cast(properties as json)
            as event_properties,

        try_cast(occurred_at as timestamptz)
            as occurred_at,

        _loaded_at,
        _source

    from {{ ref('bronze__customer_events') }}

),

validated as (

    select *
    from typed

    where event_id is not null

      and occurred_at is not null

      and (
          user_id is not null
          or session_id is not null
      )

      and event_type in (
          'product_view',
          'product_search',
          'add_to_cart',
          'remove_from_cart',
          'checkout_started',
          'order_placed'
      )

)

select
    event_id,
    user_id,
    session_id,
    event_type,
    product_id,
    order_id,
    event_properties,

    json_extract_string(
        event_properties,
        '$.source'
    ) as event_source,

    json_extract_string(
        event_properties,
        '$.query'
    ) as search_query,

    json_extract_string(
        event_properties,
        '$.category'
    ) as product_category,

    json_extract_string(
        event_properties,
        '$.brand'
    ) as product_brand,

    try_cast(
        json_extract_string(
            event_properties,
            '$.quantity'
        )
        as integer
    ) as event_quantity,

    try_cast(
        json_extract_string(
            event_properties,
            '$.final_quantity'
        )
        as integer
    ) as final_cart_quantity,

    try_cast(
        json_extract_string(
            event_properties,
            '$.result_count'
        )
        as integer
    ) as search_result_count,

    try_cast(
        json_extract_string(
            event_properties,
            '$.item_count'
        )
        as integer
    ) as order_item_count,

    try_cast(
        json_extract_string(
            event_properties,
            '$.total_amount'
        )
        as decimal(18, 2)
    ) as tracked_order_amount,

    upper(
        json_extract_string(
            event_properties,
            '$.currency_code'
        )
    ) as tracked_currency_code,

    cast(occurred_at as date)
        as event_date,

    occurred_at,
    _loaded_at,
    _source

from validated
