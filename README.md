# 📊 Kairo Marketplace Business Intelligence Platform

An end-to-end Business Intelligence Engineering project simulating a global e-commerce marketplace—from synthetic operational data generation and production-style data-quality failures to governed dimensional models, financial reconciliation, and interactive executive dashboards.

## 🎯 What This Project Demonstrates

- **Large-scale synthetic data generation** — 16M+ records across nine interconnected marketplace entities
- **Production data-quality simulation** — duplicates, null variants, schema drift, orphan keys, late-arriving records, and business-rule violations
- **Medallion architecture** — Bronze, Silver, and Gold transformation layers built with dbt
- **Dimensional modeling** — four dimensions, two facts, and three analytical marts
- **Metric governance** — explicit Gross GMV, Net GMV, customer charged amount, and commission definitions
- **Automated reconciliation** — $0 cross-model variance across governed financial measures
- **107 dbt tests** — 102 passing tests, five documented data-quality warnings, and zero errors
- **Interactive BI dashboards** — executive, category, regional, customer, and seller reporting in Streamlit

---

## 📸 Dashboard Screenshots

### Home — Executive KPIs
![Home Dashboard](docs/screenshots/home_dashboard.png)

### Executive Weekly Business Review
![Executive WBR](docs/screenshots/executive_wbr.png)

### Category Performance
![Category Performance](docs/screenshots/category_performance.png)

### Seller Health
![Seller Health](docs/screenshots/seller_health.png)

---

## 🏗️ Architecture

```text
Python Generators — Faker, Pydantic, Polars
├── 200,000 customers
├── 5,000 sellers
├── 50,000 products
├── 2,872,706 orders
├── 6,838,891 order items
├── 2,991,801 payments
├── 2,499,789 shipments
├── 595,152 returns
└── 738,108 reviews
              │
              ▼
Chaos Engine — 9 production-style failure injectors
├── Duplicate and replayed records
├── Null representation variants
├── Type and schema drift
├── Late-arriving records
├── Orphan foreign keys
└── Business-logic violations
              │
              ▼
Bronze Layer — 9 dbt views
└── Raw Parquet ingestion
              │
              ▼
Silver Layer — 9 dbt tables
├── Deduplication and null standardization
├── Type casting and schema alignment
├── Zombie-record filtering
└── Data-quality flags and orphan-item controls
              │
              ▼
Gold Layer — 9 dbt tables
├── dim_customers, dim_sellers, dim_products, dim_dates
├── fact_orders, fact_order_items
├── mart_gmv_daily
├── mart_customer_ltv
└── mart_seller_health
              │
              ▼
Metric Governance and Testing
├── Unknown-customer dimension-member handling
├── Gross and Net GMV validation
├── Customer-spend reconciliation
├── Seller-commission reconciliation
└── 107 automated dbt tests
              │
              ▼
Streamlit Business Intelligence Dashboards
├── Executive overview
├── Weekly Business Review
├── Category performance
└── Seller health
```

---

## 🛠️ Tech Stack

| Layer | Tools |
|---|---|
| Language | Python 3.11 |
| Data generation | Faker, Pydantic, Polars, NumPy |
| Storage | Parquet with Zstandard compression |
| Warehouse | DuckDB |
| Transformation | dbt Core and dbt-duckdb |
| Modeling | Star schema, fact tables, dimensions, analytical marts |
| Testing | dbt generic tests and custom SQL tests |
| Dashboards | Streamlit and Plotly |
| Version control | Git and GitHub |

---

## 📁 Project Structure

```text
kairo-marketplace-analytics/
├── generator/
│   ├── entities/
│   ├── chaos/
│   └── writers/
├── dbt_project/
│   ├── models/
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   ├── macros/
│   └── tests/
├── analytics/
│   └── streamlit_app/
├── scripts/
├── raw_data/
├── raw_data_clean/
├── chaos_manifest/
├── warehouse/
└── docs/
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- macOS or Linux

### Setup

```bash
git clone https://github.com/sriharichepuri21/kairo-marketplace-analytics.git
cd kairo-marketplace-analytics
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Generate Data

```bash
python scripts/generate_customers.py
python scripts/generate_sellers.py
python scripts/generate_products.py
python scripts/generate_orders.py
python scripts/generate_payments.py
python scripts/generate_fulfillment.py
python scripts/apply_chaos.py
```

### Build and Test the Warehouse

```bash
cd dbt_project
dbt build
cd ..
```

Expected dbt result:

```text
PASS=129 WARN=5 ERROR=0 SKIP=0 TOTAL=134
```

The 129 successful nodes include 27 models and 102 passing tests. Five warnings represent intentionally injected null conditions.

### Run Governed Metric Reconciliation

```bash
python scripts/verify_metrics.py
python scripts/reconcile_metrics.py
python scripts/final_reconciliation.py
python scripts/marketing_channel_analysis.py
```

### Launch the Dashboards

```bash
streamlit run analytics/streamlit_app/app.py
```

---

## 📊 Governed Business Metrics

| Metric | Governed Value |
|---|---:|
| Gross GMV | $383,987,652.90 |
| Net GMV — primary GMV metric | $372,465,446.03 |
| Customer charged amount | $457,134,465.37 |
| Real-customer lifetime spend | $456,728,338.76 |
| Orphan-order reconciliation spend | $406,126.61 |
| Commission revenue | $49,127,906.69 |
| Effective commission take rate | 13.19% |
| Eligible orders | 2,198,838 |
| Net GMV per eligible order | $169.39 |
| Real registered customers | 199,797 |
| Repeat-buyer rate among buyers | 96.5% |
| On-time delivery rate | 92.1% |
| Return incidence | 12.1% |
| Active sellers | 3,504 |
| At-risk sellers | 756 |
| Churned sellers | 489 |
| Sellers with no sales | 251 |

### Metric Definitions

**Gross GMV**
Merchandise value before item discounts and before tax.

**Net GMV**
Gross GMV minus valid item discounts. Net GMV excludes tax and is the primary marketplace GMV metric.

**Customer charged amount**
Sum of eligible `fact_orders.total_amount` values. It is used for customer-LTV and payment reconciliation.

**Commission revenue**
Marketplace earnings calculated by applying each seller's commission rate to Net GMV.

`fact_order_items.line_total` is not used as GMV because it includes item-level tax.

---

## 📈 Business Intelligence Findings

- Referral customers generated **1.71× the average 90-day spend** of paid-search customers: **$725.54 versus $424.96**.
- Referral customers achieved a **79.0% 90-day repeat rate**, compared with **70.5%** for paid search, an **8.5-percentage-point difference**.
- Whale-persona customers represented **6.1% of real customers** and **40.2% of real-customer spend**.
- Electronics generated the largest category contribution with approximately **$108.7M in Net GMV**.
- The platform maintained a **92.1% on-time delivery rate**.
- Overall return incidence was **12.1%** across eligible sold items.

Channel findings represent associations created partly by intentional synthetic generator assumptions; they are not causal marketing conclusions.

---

## 🔬 Data Quality and Chaos Engineering

The chaos engine injects nine categories of production-style issues:

| Chaos Type | Example |
|---|---|
| Near-duplicate records | Payment retries and CDC replays |
| Null variants | `"N/A"`, `""`, `"NULL"`, `"-"` |
| Type drift | Numeric values represented as strings |
| Encoding corruption | Character-set inconsistencies |
| Late-arriving records | Delayed events and batch outages |
| Orphan foreign keys | Deleted or missing dimension records |
| Business-rule violations | Negative quantities and impossible discounts |
| Zombie test data | QA records left in production |
| Schema evolution | Added or renamed source columns |

Every injected change is recorded in `chaos_manifest/` for audit and comparison.

---

## 🧪 Testing and Reconciliation

Current dbt validation:

```text
Models: 27
Tests: 107
Passing tests: 102
Documented warnings: 5
Errors: 0
```

Validation includes:

- Primary-key uniqueness
- Required-field checks
- Accepted categorical values
- Fact-to-dimension referential integrity
- Unknown-member customer reconciliation
- Orders occurring after customer signup
- Non-negative governed GMV
- Cross-model customer-spend reconciliation
- Cross-model seller and marketplace GMV reconciliation

---

## 📋 Business Context

Kairo is a fictional global marketplace operating across the United States, European Union, and Latin America.

- **Scale:** 200K customers, 5K sellers, and 50K products
- **Revenue model:** Tiered seller commissions applied to Net GMV
- **Effective take rate:** 13.19%
- **Primary stakeholders:** Executives, category managers, seller-success teams, and analytics engineers

See [PROJECT_CHARTER.md](./PROJECT_CHARTER.md) for the full business context and stakeholder definitions.

---

## 👤 About

Built by **Srihari Chepuri** as a portfolio project demonstrating end-to-end Business Intelligence Engineering, analytics engineering, data modeling, metric governance, and executive reporting.

- GitHub: [@sriharichepuri21](https://github.com/sriharichepuri21)

---

## 📄 License

This project is available under the [MIT License](LICENSE).
