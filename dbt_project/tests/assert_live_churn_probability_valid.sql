select
    user_id,
    churn_probability,
    probability_threshold

from {{ ref(
    'mart_live_customer_churn_scores'
) }}

where churn_probability is null
   or churn_probability < 0
   or churn_probability > 1
   or probability_threshold is null
   or probability_threshold < 0
   or probability_threshold > 1
