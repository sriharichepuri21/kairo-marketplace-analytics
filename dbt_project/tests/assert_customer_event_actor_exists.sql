select
    event_id,
    user_id,
    session_id

from {{ ref('silver__customer_events') }}

where user_id is null
  and session_id is null
