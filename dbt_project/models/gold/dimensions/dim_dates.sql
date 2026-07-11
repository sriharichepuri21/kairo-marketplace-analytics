-- Gold: Date dimension
-- Every fact table joins here for time-based analysis
-- Covers our full data window: 2022-01-01 to 2026-12-31

WITH date_spine AS (
    SELECT
        CAST(UNNEST(generate_series(
            DATE '2022-01-01',
            DATE '2026-12-31',
            INTERVAL '1 day'
        )) AS DATE) AS date_day
),

enriched AS (
    SELECT
        date_day,
        EXTRACT(YEAR FROM date_day) AS year,
        EXTRACT(QUARTER FROM date_day) AS quarter,
        EXTRACT(MONTH FROM date_day) AS month,
        EXTRACT(WEEK FROM date_day) AS week_of_year,
        EXTRACT(DOW FROM date_day) AS day_of_week,
        EXTRACT(DOY FROM date_day) AS day_of_year,

        -- Human-readable
        STRFTIME(date_day, '%B') AS month_name,
        STRFTIME(date_day, '%A') AS day_name,
        STRFTIME(date_day, '%Y-%m') AS year_month,
        STRFTIME(date_day, '%Y-Q') || EXTRACT(QUARTER FROM date_day) AS year_quarter,

        -- Flags
        CASE WHEN EXTRACT(DOW FROM date_day) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,

        -- Fiscal year (assuming Feb 1 start like Amazon)
        CASE
            WHEN EXTRACT(MONTH FROM date_day) >= 2
            THEN EXTRACT(YEAR FROM date_day)
            ELSE EXTRACT(YEAR FROM date_day) - 1
        END AS fiscal_year,

        -- Seasonality flags
        CASE
            WHEN EXTRACT(MONTH FROM date_day) IN (10, 11, 12) THEN 'Q4_peak'
            WHEN EXTRACT(MONTH FROM date_day) = 1 THEN 'post_holiday'
            WHEN EXTRACT(MONTH FROM date_day) IN (7, 8) THEN 'summer_dip'
            ELSE 'normal'
        END AS season_label

    FROM date_spine
)

SELECT * FROM enriched