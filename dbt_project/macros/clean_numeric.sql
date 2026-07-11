{% macro clean_numeric(column_name) %}
    TRY_CAST(
        CASE
            -- Value contains both comma and period: comma is thousands separator
            WHEN POSITION(',' IN TRIM({{ column_name }})) > 0
             AND POSITION('.' IN TRIM({{ column_name }})) > 0
            THEN REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    TRIM({{ column_name }}),
                    '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '')

            -- Value contains comma but no period: comma is decimal separator
            WHEN POSITION(',' IN TRIM({{ column_name }})) > 0
            THEN REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
                    TRIM({{ column_name }}),
                    '$', ''), '€', ''), 'R$', ''), 'USD ', ''), ',', '.')

            -- No comma: just strip currency symbols
            ELSE REPLACE(REPLACE(REPLACE(REPLACE(
                    TRIM({{ column_name }}),
                    '$', ''), '€', ''), 'R$', ''), 'USD ', '')
        END
        AS DOUBLE
    )
{% endmacro %}