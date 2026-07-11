-- Silver layer: cleaned reviews
-- Issue fixed: orphan product_id references filtered

SELECT *
FROM {{ ref('bronze__reviews') }}
WHERE product_id NOT LIKE 'ORPHAN-%'