select
    order_id,
    subtotal,
    shipping_amount,
    tax_amount,
    total_amount

from {{ ref('silver__operational_orders') }}

where subtotal < 0
   or shipping_amount < 0
   or tax_amount < 0
   or total_amount < 0
