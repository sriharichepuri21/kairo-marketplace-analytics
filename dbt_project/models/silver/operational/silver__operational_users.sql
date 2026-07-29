with typed as (

    select
        nullif(trim(id), '') as user_id,

        lower(
            nullif(trim(email), '')
        ) as email,

        nullif(trim(full_name), '')
            as full_name,

        lower(
            nullif(trim(role), '')
        ) as role,

        try_cast(is_active as boolean)
            as is_active,

        try_cast(created_at as timestamptz)
            as created_at,

        try_cast(updated_at as timestamptz)
            as updated_at,

        _loaded_at,
        _source

    from {{ ref('bronze__operational_users') }}

)

select *
from typed

where user_id is not null
  and email is not null
  and created_at is not null
