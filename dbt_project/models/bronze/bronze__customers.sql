SELECT
    *,
    current_timestamp AS _loaded_at,
    'raw_customers' AS _source
FROM read_parquet('/Users/sriharichepuri/dev/kairo-marketplace-analytics/raw_data/customers/customers.parquet')