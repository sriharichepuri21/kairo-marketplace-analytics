# Kairo Churn Production Model

## Production decision

- Production model: `behavioral_only`
- Validation winner: `behavioral_plus_channel`
- Probability threshold: `0.30`
- Model version: `kairo_churn_v1`

## Governance rule

Select the signup-channel model only when its validation PR-AUC improves by at least 0.005; otherwise select behavioral-only. The out-of-time test set is used only for final reporting.

## Validation comparison

| Model | Validation PR-AUC |
|---|---:|
| Behavioral only | 0.500365 |
| Behavioral plus channel | 0.501659 |
| Channel uplift | 0.001294 |
| Required uplift | 0.005000 |

## Production rationale

The signup-channel model's validation PR-AUC improvement was below the 0.005 materiality threshold, so the simpler and more portable behavioral-only model was selected.

The out-of-time test results are retained for final reporting and were
not used to select the production model.
