# Kairo Customer Churn Model Report

## Objective

Predict whether an existing customer places no eligible order during
the 90 days after a point-in-time snapshot.

## Experimental Design

- Training snapshots: 2024-12-31 and 2025-03-31
- Validation snapshot: 2025-06-30
- Test snapshot: 2025-09-30
- Model A: behavioral features only
- Model B: behavioral features plus signup channel
- Synthetic segment was excluded from both primary models
- Class weighting and thresholds were selected on validation data

## Validation Results

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 | Top-10% Lift |
|---|---:|---:|---:|---:|---:|---:|
| Behavioral only | 0.7394 | 0.5004 | 0.4156 | 0.7409 | 0.5325 | 2.20x |
| Behavioral + channel | 0.7401 | 0.5017 | 0.4086 | 0.7639 | 0.5324 | 2.21x |

## Final Out-of-Time Test Results

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 | Top-10% Lift | Top-20% Recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Behavioral only | 0.7757 | 0.4865 | 0.3831 | 0.7873 | 0.5154 | 2.51x | 0.4323 |
| Behavioral + channel | 0.7765 | 0.4878 | 0.3768 | 0.8089 | 0.5141 | 2.52x | 0.4333 |

## Selected Production Model

**behavioral_plus_channel**

Signup channel improved test PR-AUC.

The production model was selected using validation PR-AUC. Test data
was used only for final out-of-time reporting.

## Interpretation

This dataset is synthetic. Signup-channel differences partly reflect
intentional generator assumptions and are predictive associations,
not causal marketing effects.
