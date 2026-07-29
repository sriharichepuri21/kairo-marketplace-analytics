{% set export_dir = var(
    'operational_export_dir',
    '../warehouse/operational'
) %}

select
    *,
    current_timestamp as _loaded_at,
    'postgres_orders' as _source

from read_csv_auto(
    '{{ export_dir }}/operational_orders.csv',
    header = true,
    all_varchar = true
)
