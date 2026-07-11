SELECT
    *,
    current_timestamp AS _loaded_at,
    'raw_reviews' AS _source
FROM read_parquet('/Users/sriharichepuri/dev/kairo-marketplace-analytics/raw_data/reviews/reviews.parquet')