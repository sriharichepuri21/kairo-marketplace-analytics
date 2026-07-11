-- Silver layer: products (clean — no chaos applied)
SELECT * FROM {{ ref('bronze__products') }}