select
    user_id,
    churn_probability,
    probability_threshold,
    predicted_churn_flag

from {{ ref(
    'mart_live_customer_churn_scores'
) }}

where predicted_churn_flag
      != case
          when churn_probability
               >= probability_threshold
          then 1
          else 0
      end
