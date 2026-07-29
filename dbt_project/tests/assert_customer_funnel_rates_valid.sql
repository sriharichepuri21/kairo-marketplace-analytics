select *

from {{ ref('mart_customer_funnel') }}

where view_to_cart_conversion_rate
          not between 0 and 1

   or cart_to_checkout_conversion_rate
          not between 0 and 1

   or checkout_to_order_conversion_rate
          not between 0 and 1

   or cart_abandonment_rate
          not between 0 and 1
