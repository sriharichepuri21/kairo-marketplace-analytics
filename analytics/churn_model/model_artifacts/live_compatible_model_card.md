# Kairo Live-Compatible Churn Model

## Purpose

Score registered marketplace customers using features available in the
live `mart_customer_features` model.

## Eligibility

Only customers with at least one order are churn-score eligible.
Customers with zero orders are classified as prospects.

## Feature contract

- `days_since_last_order`
- `total_orders`
- `orders_last_30d`
- `orders_last_90d`
- `account_age_days`
- `is_single_order_customer`

## Validation

- PR-AUC: 0.4968
- ROC-AUC: 0.7377
- F1: 0.5336
- Threshold: 0.30

## Out-of-time test

- PR-AUC: 0.4811
- ROC-AUC: 0.7732
- F1: 0.5159
- Top-10% lift: 2.46x
