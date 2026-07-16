# Kairo dbt Analytics Warehouse

This dbt project transforms production-style marketplace data through governed Bronze, Silver, and Gold layers.

## Model Layers

### Bronze

Nine views load raw Parquet data without changing source semantics.

### Silver

Nine tables perform:

- Deduplication
- Null standardization
- Type casting
- Schema normalization
- Zombie-record filtering
- Referential-integrity controls
- Business-rule flagging

### Gold

The governed BI layer contains:

- `dim_customers`
- `dim_sellers`
- `dim_products`
- `dim_dates`
- `fact_orders`
- `fact_order_items`
- `mart_gmv_daily`
- `mart_customer_ltv`
- `mart_seller_health`

## Analysis Reference Date

Customer and seller activity models use the centralized variable:

```yaml
vars:
  analysis_as_of_date: '2025-12-31'
```

This prevents activity classifications from changing based on the current system date.

## Governed Financial Definitions

- **Gross GMV:** merchandise value before discounts and tax
- **Net GMV:** Gross GMV minus item discounts; primary GMV measure
- **Customer charged amount:** eligible `fact_orders.total_amount`
- **Commission revenue:** seller commission applied to Net GMV

`line_total` is tax-inclusive and must not be used as the primary GMV metric.

## Commands

From the `dbt_project` directory:

```bash
dbt parse --no-partial-parse --show-all-deprecations
dbt build
```

Expected build result:

```text
PASS=129 WARN=5 ERROR=0 SKIP=0 TOTAL=134
```

The warnings are documented null conditions introduced intentionally by the chaos engine.

## Test Coverage

The project includes 107 data tests covering:

- Primary-key uniqueness
- Required fields
- Accepted values
- Fact-to-dimension relationships
- Orders after signup dates
- No zombie customers in Silver
- No orphan order items in Silver
- Non-negative GMV
- Governed customer and seller marts
