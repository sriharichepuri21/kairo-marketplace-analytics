SELECT
    *,
    current_timestamp AS _loaded_at,
    'raw_shipments' AS _source
FROM read_parquet('/Users/sriharichepuri/dev/kairo-marketplace-analytics/raw_data/shipments/shipments.parquet')