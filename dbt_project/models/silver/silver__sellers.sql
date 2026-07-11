-- Silver layer: sellers (clean — no chaos applied)
SELECT * FROM {{ ref('bronze__sellers') }}