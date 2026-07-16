select
    customer_id,
    churn_probability

from {{ ref('mart_customer_churn_scores') }}

where churn_probability < 0
   or churn_probability > 1
   or churn_probability is null
