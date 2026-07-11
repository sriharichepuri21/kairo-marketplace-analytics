-- Test: No zombie/test records should survive into Silver
-- Expected: 0 rows returned (test passes when query returns nothing)

SELECT customer_id
FROM {{ ref('silver__customers') }}
WHERE customer_id LIKE 'TEST-%'
   OR email LIKE '%test@test%'
   OR email LIKE '%@localhost%'
LIMIT 1