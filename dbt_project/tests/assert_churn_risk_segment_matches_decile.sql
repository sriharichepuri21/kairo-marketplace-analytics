select
    customer_id,
    risk_decile,
    risk_segment

from {{ ref('mart_customer_churn_scores') }}

where
    (
        risk_decile between 1 and 2
        and risk_segment != 'high_risk'
    )

    or (
        risk_decile between 3 and 5
        and risk_segment != 'medium_risk'
    )

    or (
        risk_decile between 6 and 10
        and risk_segment != 'low_risk'
    )
