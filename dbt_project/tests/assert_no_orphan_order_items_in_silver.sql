-- Test: No orphan order_ids should exist in Silver order items

SELECT order_item_id
FROM {{ ref('silver__order_items') }}
WHERE order_id LIKE 'ORPHAN-%'
LIMIT 1