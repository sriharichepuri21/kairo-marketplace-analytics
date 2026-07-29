with typed as (

    select
        nullif(trim(id), '')
            as order_id,

        nullif(trim(order_number), '')
            as order_number,

        nullif(trim(user_id), '')
            as user_id,

        lower(
            nullif(trim(status), '')
        ) as order_status,

        lower(
            nullif(trim(payment_status), '')
        ) as payment_status,

        upper(
            nullif(trim(currency_code), '')
        ) as currency_code,

        try_cast(subtotal as decimal(18, 2))
            as subtotal,

        try_cast(
            shipping_amount as decimal(18, 2)
        ) as shipping_amount,

        try_cast(
            tax_amount as decimal(18, 2)
        ) as tax_amount,

        try_cast(
            total_amount as decimal(18, 2)
        ) as total_amount,

        try_cast(created_at as timestamptz)
            as created_at,

        try_cast(updated_at as timestamptz)
            as updated_at,

        _loaded_at,
        _source

    from {{ ref('bronze__operational_orders') }}

)

select *
from typed

where order_id is not null
  and user_id is not null
  and created_at is not null
  and order_status in (
      'pending',
      'confirmed',
      'processing',
      'shipped',
      'delivered',
      'cancelled'
  )
