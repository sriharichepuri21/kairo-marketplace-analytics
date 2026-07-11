SELECT
    *,
    current_timestamp AS _loaded_at,
    'raw_products' AS _source
FROM read_parquet('/Users/sriharichepuri/dev/kairo-marketplace-analytics/raw_data/products/products.parquet')