{% set export_dir = var(
    'operational_export_dir',
    '../warehouse/operational'
) %}

select
    *,
    current_timestamp as _loaded_at,
    'postgres_customer_events' as _source

from read_csv_auto(
    '{{ export_dir }}/customer_events.csv',
    header = true,
    all_varchar = true
)
