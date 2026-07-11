-- Silver layer: returns (clean — no chaos applied)
SELECT * FROM {{ ref('bronze__returns') }}