select
    actor_id,
    event_date,
    count(*) as row_count

from {{ ref('int_customer_daily_activity') }}

group by
    actor_id,
    event_date

having count(*) > 1
