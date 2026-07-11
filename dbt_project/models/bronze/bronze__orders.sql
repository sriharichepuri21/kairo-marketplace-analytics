SELECT
    *,
    current_timestamp AS _loaded_at,
    'raw_orders' AS _source
FROM read_parquet('/Users/sriharichepuri/dev/kairo-marketplace-analytics/raw_data/orders/orders.parquet')