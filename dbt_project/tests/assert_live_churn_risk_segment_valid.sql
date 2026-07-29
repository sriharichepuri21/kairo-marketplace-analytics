select
    user_id,
    churn_probability,
    probability_threshold,
    risk_decile,
    risk_segment

from {{ ref(
    'mart_live_customer_churn_scores'
) }}

where risk_segment
      != case
          when churn_probability
               >= probability_threshold
          then 'high_risk'

          when churn_probability
               >= probability_threshold / 2.0
          then 'medium_risk'

          else 'low_risk'
      end
