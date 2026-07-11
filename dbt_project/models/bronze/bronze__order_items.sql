SELECT
    *,
    current_timestamp AS _loaded_at,
    'raw_order_items' AS _source
FROM read_parquet('/Users/sriharichepuri/dev/kairo-marketplace-analytics/raw_data/order_items/order_items.parquet')