# Kairo Marketplace Analytics Platform

**A full-stack marketplace, analytics engineering, machine learning, and data-observability portfolio project.**

Kairo simulates a global e-commerce marketplace from end to end: synthetic operational data generation, production-style data failures, governed dimensional models, financial reconciliation, point-in-time churn prediction, a customer-facing storefront, admin analytics, and persisted data-quality monitoring.

> **Project status:** Core platform complete. The application is designed to run locally with Docker Compose; public cloud deployment is optional.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Platform at a Glance](#platform-at-a-glance)
- [What the Project Demonstrates](#what-the-project-demonstrates)
- [Architecture](#architecture)
- [Application Features](#application-features)
- [Analytics and Machine Learning](#analytics-and-machine-learning)
- [Data Quality and Observability](#data-quality-and-observability)
- [Screenshots](#screenshots)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Local Setup](#local-setup)
- [Analytics Pipeline](#analytics-pipeline)
- [Testing and Validation](#testing-and-validation)
- [Verified Business Metrics](#verified-business-metrics)
- [Point-in-Time Churn System](#point-in-time-churn-system)
- [Limitations](#limitations)
- [License](#license)

---

## Project Overview

Kairo was built to answer a practical engineering and business question:

> How can a marketplace turn fragmented operational activity into a trusted system for commerce, financial reporting, customer intelligence, and data-quality monitoring?

The repository combines two connected platforms:

1. **Operational marketplace application**
   - Next.js storefront
   - FastAPI REST API
   - PostgreSQL transactional database
   - Authentication, catalog, cart, checkout, orders, and event tracking
   - Admin dashboards for operations, churn, and data quality

2. **Analytical and machine-learning platform**
   - Large-scale synthetic data generation
   - Production-style chaos injection
   - Bronze, Silver, and Gold dbt layers
   - Governed marketplace metrics and reconciliation
   - Streamlit stakeholder dashboards
   - Point-in-time customer churn modeling and production scoring

The result is not only a dashboard project. It is a locally reproducible, end-to-end data and software system.

---

## Platform at a Glance

### Analytical Platform

| Area | Verified scale or result |
|---|---:|
| Synthetic marketplace records | 16M+ |
| Customers generated | 200K |
| Sellers generated | 5K |
| Products generated | 50K |
| Orders generated | 2.87M |
| Order items generated | 6.83M |
| Payments generated | 2.99M |
| Shipments generated | 2.50M |
| Returns generated | 595K |
| Reviews generated | 738K |
| dbt build result | 153 pass, 5 warnings, 0 errors |
| Passing dbt data tests | 125 |
| Governed reconciliation variance | $0 across validated measures |

### Operational Application

| Entity or validation | Current local result |
|---|---:|
| Categories | 15 |
| Products | 37,754 |
| Users | 5,002 |
| Orders | 50,003 |
| Order items | 108,935 |
| Customer events | 524,877 |
| Distinct customer sessions | 187,001 |
| Backend tests | 116 passed |
| Operational quality checks | 16 |
| Latest quality result | 15 passed, 1 warning, 0 failed |
| Storefront ESLint | Passed |
| Storefront TypeScript validation | Passed |

Operational counts represent the current local synthetic demonstration database and can change when tests or new user activity create records.

---

## What the Project Demonstrates

### Full-Stack Marketplace Engineering

- Customer registration and JWT-based authentication
- Role-based customer and administrator authorization
- Product browsing, categories, ratings, prices, and inventory availability
- Shopping-cart creation and item management
- Address management and checkout workflows
- Persisted orders, order items, and status history
- Customer event collection for funnel analytics
- Layered API design using routes, schemas, services, repositories, and SQLAlchemy models

### Analytics Engineering

- Large-scale synthetic data generation across nine interconnected entities
- Production-style failure simulation:
  - Duplicates and replayed records
  - Null representation variants
  - Type drift and schema evolution
  - Late-arriving records
  - Orphan foreign keys
  - Invalid business-rule values
  - Zombie test data
- Bronze, Silver, and Gold transformation layers
- Star-schema modeling with dimensions, facts, and analytical marts
- Explicit governance for Gross GMV, Net GMV, customer charged amount, and commission revenue
- Cross-model financial reconciliation
- Operational-to-analytical data export workflows

### Machine Learning

- Historical point-in-time customer snapshots
- Temporal training, validation, and test periods
- Leakage-aware feature engineering
- Out-of-time model evaluation
- Churn probability scoring
- Capacity-based risk deciles and segments
- Retention-action recommendations
- Score publication to both dbt Gold models and PostgreSQL

### Data Quality and Observability

- Persisted data-quality runs and check results
- Availability, freshness, completeness, relationship, uniqueness, and validity checks
- Warning and failure investigation views
- Authenticated admin observability APIs
- Historical run pagination and drill-down
- A server-rendered data-quality dashboard
- Automated API and runner tests

---

## Architecture

Kairo combines synthetic e-commerce data generation, governed analytics, machine learning, operational APIs, and full-stack marketplace experiences.

![Kairo Marketplace Platform Architecture](docs/screenshots/kairo-platform-architecture.png)

> Current local architecture with AWS deployment shown as a future roadmap.


```mermaid
flowchart TD
    subgraph A["Synthetic Analytics Platform"]
        G["Python Data Generators<br/>Faker · Pydantic · Polars"]
        C["Chaos Engine<br/>Duplicates · Nulls · Drift · Orphans"]
        P["Parquet Data Lake<br/>Raw and Cleaned Datasets"]
        D["dbt + DuckDB<br/>Bronze · Silver · Gold"]
        R["Governance and Reconciliation<br/>GMV · Spend · Commission"]
        M["Point-in-Time Churn ML<br/>Temporal Validation · Risk Actions"]
        S["Streamlit BI Dashboards"]
        G --> C --> P --> D
        D --> R
        D --> M
        R --> S
        M --> S
    end

    subgraph B["Operational Marketplace Application"]
        DB["PostgreSQL 16<br/>Transactional and Observability Data"]
        API["FastAPI REST API<br/>Auth · Catalog · Cart · Orders · Admin"]
        WEB["Next.js Storefront<br/>Customer and Admin Experiences"]
        Q["Operational Quality Runner<br/>16 Persisted Checks"]
        DB --> API --> WEB
        DB --> Q
        Q --> API
    end

    D -->|"validated demo import"| DB
    M -->|"live churn score sync"| DB
    DB -->|"operational exports"| D
```

### End-to-End Data Flow

```text
Synthetic generation
        ↓
Chaos injection
        ↓
Parquet raw data
        ↓
dbt Bronze → Silver → Gold
        ↓
Governed metrics and reconciliation
        ↓
Point-in-time churn training and scoring
        ↓
Validated operational import
        ↓
PostgreSQL
        ↓
FastAPI
        ↓
Next.js storefront and admin dashboards
        ↓
Persisted quality monitoring and historical run analysis
```

---

## Application Features

### Customer Experience

| Capability | Description |
|---|---|
| Authentication | Registration, login, JWT sessions, and protected pages |
| Product catalog | Category browsing, pagination, product details, prices, ratings, and availability |
| Cart | Add, update, remove, and clear cart items |
| Addresses | Create, edit, select, and delete delivery addresses |
| Checkout | Convert an authenticated cart into a persisted order |
| Orders | Order history, order detail, totals, and status history |
| Event tracking | Product views, cart activity, checkout starts, and order conversions |

### Admin Operations Dashboard

- Total and eligible order volume
- Delivered and cancelled orders
- Active-customer counts
- Revenue trends by currency
- Average order value
- Order-status distribution
- Category performance
- Inventory alerts
- Product-view-to-order conversion funnel

### Admin Churn Dashboard

- Latest eligible scoring population
- Churn probability and model threshold
- High-, medium-, and low-risk segments
- Predicted churn flags
- Recommended retention actions
- Customer search and filtering
- Individual customer detail views

### Admin Data-Quality Dashboard

- Overall health status
- Passed, warning, and failed totals
- Run timestamp, trigger, and duration
- Observed versus expected values
- Warning and failure investigation cards
- Collapsible passed-check details
- Historical run table and pagination
- Run-level drill-down

---

## Analytics and Machine Learning

### Medallion Modeling

The analytical warehouse follows a governed medallion design:

```text
Bronze
└── Raw Parquet ingestion and source preservation

Silver
├── Deduplication
├── Null normalization
├── Type casting
├── Zombie-record filtering
├── Referential-integrity controls
└── Data-quality flags

Gold
├── dim_customers
├── dim_sellers
├── dim_products
├── dim_dates
├── fact_orders
├── fact_order_items
├── mart_gmv_daily
├── mart_customer_ltv
├── mart_seller_health
└── mart_customer_churn_scores
```

### Governed Metric Definitions

**Gross GMV**  
Merchandise value before item-level discounts and tax.

**Net GMV**  
Gross GMV minus valid item discounts. Net GMV excludes tax and is the primary marketplace-volume measure.

**Customer charged amount**  
The amount charged to customers, including applicable tax and shipping.

**Commission revenue**  
Marketplace transaction revenue calculated by applying each seller's commission rate to Net GMV.

`fact_order_items.line_total` is not used as GMV because it includes item-level tax.

---

## Data Quality and Observability

### Operational Quality Checks

The FastAPI quality runner executes and persists 16 checks.

#### Availability and Freshness

1. Database connectivity
2. Orders freshness
3. Customer-events freshness

#### Relationships and Completeness

4. Order items referencing missing orders
5. Order items referencing missing products
6. Active products without inventory
7. Customer events without a customer or session actor
8. Order events without an order identifier
9. Paid or progressed orders missing an order event
10. Pending unpaid orders missing an order event

#### Uniqueness

11. Duplicate order events
12. Duplicate order numbers
13. Duplicate customer email addresses

#### Business-Rule Validity

14. Invalid order amounts
15. Invalid inventory quantities
16. Invalid order-item line totals

### Latest Verified Run

```text
Status:    warning
Checks:    16
Passed:    15
Warnings:  1
Failed:    0
Duration:  approximately 369 ms
```

The warning represents one pending unpaid order without a corresponding order event. No critical checks failed.

### Observability API

```text
GET /api/v1/admin/data-quality/latest
GET /api/v1/admin/data-quality/runs
GET /api/v1/admin/data-quality/runs/{run_id}
```

All endpoints require an authenticated administrator.

---

## Full-Stack Admin Dashboards

### Operations Overview

The Operations dashboard summarizes order volume, eligible orders, active customers, fulfilment outcomes, and revenue by transaction currency.

![Operations Dashboard](docs/screenshots/app_admin_operations_overview.png)

<details>
<summary><strong>View additional Operations dashboard panels</strong></summary>

### Revenue Trends

![Revenue Trends](docs/screenshots/app_admin_revenue_trend.png)

### Conversion Funnel

![Conversion Funnel](docs/screenshots/app_admin_conversion_funnel.png)

### Category Performance

![Category Performance](docs/screenshots/app_admin_category_performance.png)

### Inventory Health

![Inventory Health](docs/screenshots/app_admin_inventory_health.png)

### Order-Status Distribution

![Order-Status Distribution](docs/screenshots/app_admin_order_status.png)

</details>

### Customer Churn Intelligence

The Churn dashboard prioritizes retention outreach using point-in-time customer behavior, recency, churn probability, risk segmentation, and recommended actions.

![Churn Risk Dashboard](docs/screenshots/app_admin_churn_overview.png)

<details>
<summary><strong>View the customer risk queue</strong></summary>

![Customer Churn Scores](docs/screenshots/app_admin_churn_customers.png)

</details>

### Data-Quality Observability

The Data Quality dashboard exposes persisted operational checks, warning and failure details, observed-versus-expected values, and historical run results.

![Data-Quality Dashboard](docs/screenshots/app_admin_data_quality_overview.png)

<details>
<summary><strong>View warning details and run history</strong></summary>

![Data-Quality Warning and History](docs/screenshots/app_admin_data_quality_details.png)

</details>


---

## Screenshots

### Data-Quality Overview

![Data-Quality Overview](docs/screenshots/admin_data_quality_overview.png)

### Data-Quality Warning Detail

![Data-Quality Warning Detail](docs/screenshots/admin_data_quality_warning.png)

### Data-Quality Run History

![Data-Quality Run History](docs/screenshots/admin_data_quality_history.png)

### Executive Marketplace Overview

![Executive Marketplace Overview](docs/screenshots/home_dashboard.png)

### Marketplace Performance and Customer Activity

![Marketplace Performance](docs/screenshots/home_marketplace_performance.png)

### Executive Weekly Business Review

![Executive Weekly Business Review](docs/screenshots/executive_wbr.png)

### Category Performance

![Category Performance](docs/screenshots/category_performance.png)

### Category Comparison and Customer Segments

![Category Comparison](docs/screenshots/category_comparison.png)

### Seller Health

![Seller Health](docs/screenshots/seller_health.png)

### Seller Performance and At-Risk Intervention

![Seller Intervention](docs/screenshots/seller_intervention.png)

### Customer Churn Risk Overview

![Customer Churn Risk Overview](docs/screenshots/customer_churn_overview.png)

### Churn Risk Deciles and Recommended Actions

![Churn Risk Deciles and Actions](docs/screenshots/customer_churn_deciles_actions.png)

### High-Risk Customer Intervention Queue

![High-Risk Customer Intervention Queue](docs/screenshots/customer_churn_intervention.png)

### Production Churn Model Performance

![Production Churn Model Performance](docs/screenshots/customer_churn_model_performance.png)

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Storefront | Next.js 16, React 19, TypeScript 5, Tailwind CSS 4 |
| API | FastAPI, Python 3.12, Uvicorn, Pydantic |
| API architecture | Routes, schemas, services, repositories, and SQLAlchemy models |
| Authentication | JWT and Argon2 password hashing |
| Operational database | PostgreSQL 16 |
| Migrations | Alembic |
| Containers | Docker and Docker Compose |
| Data generation | Python, Faker, Pydantic, Polars, and NumPy |
| Storage | Parquet with Zstandard compression |
| Analytical warehouse | DuckDB |
| Transformation | dbt Core and dbt-duckdb |
| Modeling | Bronze/Silver/Gold, dimensions, facts, and analytical marts |
| Machine learning | scikit-learn pipelines and temporal validation |
| Dashboards | Next.js, Streamlit, and Plotly |
| Backend testing | Pytest and Ruff |
| Frontend validation | ESLint and TypeScript |
| Data testing | dbt generic tests and custom SQL assertions |
| Version control | Git, GitHub branches, pull requests, releases, and milestone tags |

---

## Repository Structure

```text
kairo-marketplace-analytics/
├── apps/
│   ├── api/
│   │   ├── alembic/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   ├── core/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   ├── schemas/
│   │   │   ├── scripts/
│   │   │   └── services/
│   │   ├── scripts/
│   │   └── tests/
│   └── storefront/
│       ├── public/
│       └── src/
│           ├── app/
│           ├── components/
│           └── lib/
├── analytics/
│   ├── churn_model/
│   ├── demo_ingestion/
│   └── streamlit_app/
├── dbt_project/
│   ├── models/
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   ├── macros/
│   └── tests/
├── generator/
│   ├── entities/
│   ├── chaos/
│   └── writers/
├── scripts/
├── raw_data/
├── raw_data_clean/
├── chaos_manifest/
├── warehouse/
├── docs/
│   └── screenshots/
├── docker-compose.yml
├── PROJECT_CHARTER.md
└── README.md
```

---

## Local Setup

### Prerequisites

- Git
- Docker Desktop
- Node.js and npm
- Python 3.11+
- `uv` for the analytical environment

### 1. Clone the Repository

```bash
git clone https://github.com/sriharichepuri21/kairo-marketplace-analytics.git
cd kairo-marketplace-analytics
```

### 2. Start PostgreSQL and FastAPI

```bash
docker compose up --build -d
```

Apply migrations:

```bash
docker compose exec -T api alembic upgrade head
```

Check service health:

```bash
curl http://localhost:8000/health
```

Local API locations:

```text
API:      http://localhost:8000
API docs: http://localhost:8000/docs
Health:   http://localhost:8000/health
```

### 3. Configure and Start the Storefront

```bash
cp apps/storefront/.env.example apps/storefront/.env.local
npm --prefix apps/storefront ci
npm --prefix apps/storefront run dev
```

Open:

```text
Storefront: http://localhost:3001
```

The environment example uses:

```env
API_URL=http://localhost:8000
```

### 4. Optional Lightweight Catalog Seed

The catalog seed is idempotent and can be run for a lightweight local development environment:

```bash
docker compose exec -T api python scripts/seed_catalog.py
```

The complete analytical and admin demonstration environment uses the larger synthetic generation and demo-ingestion workflows described below.

---

## Analytics Pipeline

### 1. Create the Python Environment

```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 2. Generate Synthetic Marketplace Data

```bash
python scripts/generate_customers.py
python scripts/generate_sellers.py
python scripts/generate_products.py
python scripts/generate_orders.py
python scripts/generate_payments.py
python scripts/generate_fulfillment.py
python scripts/apply_chaos.py
```

### 3. Build and Test the Warehouse

```bash
cd dbt_project
dbt build
cd ..
```

Verified result:

```text
PASS=153 WARN=5 ERROR=0 SKIP=0 TOTAL=158
```

The successful nodes include 28 models and 125 passing tests. The five warnings represent documented, intentionally injected synthetic conditions.

### 4. Verify Governed Metrics

```bash
python scripts/verify_metrics.py
python scripts/reconcile_metrics.py
python scripts/final_reconciliation.py
python scripts/marketing_channel_analysis.py
```

### 5. Run the Customer Intelligence Pipeline

```bash
bash scripts/run_customer_intelligence_pipeline.sh
```

The workflow:

1. Checks application services
2. Exports operational snapshots
3. Builds operational customer features
4. Trains or loads the live-compatible model
5. Scores eligible customers
6. Synchronizes scores to PostgreSQL

### 6. Launch Streamlit BI

```bash
streamlit run analytics/streamlit_app/app.py
```

---

## Testing and Validation

### Backend Integration Tests

```bash
docker compose exec -T api pytest -q
```

Verified result:

```text
116 passed
```

Two non-blocking framework deprecation warnings are currently emitted by FastAPI/Starlette dependencies.

### Backend Linting

```bash
docker compose exec -T api ruff check .
```

### Storefront Linting

```bash
npm --prefix apps/storefront run lint
```

Verified result:

```text
ESLint passed
```

### Storefront Type Checking

```bash
cd apps/storefront
npx tsc --noEmit
```

Verified result:

```text
TypeScript validation passed
```

### Operational Quality Runner

```bash
docker compose exec -T api \
  python -m app.scripts.run_data_quality_checks
```

### dbt Validation

```bash
cd dbt_project
dbt build
```

Verified result:

```text
153 pass
5 documented warnings
0 errors
```

---

## Verified Business Metrics

| Metric | Governed value |
|---|---:|
| Gross GMV | $383,987,652.90 |
| Net GMV — primary marketplace-volume metric | $372,465,446.03 |
| Item discounts | $11,522,206.87 |
| Item tax | $37,247,710.32 |
| Customer charged amount | $457,134,465.37 |
| Real-customer lifetime spend | $456,728,338.76 |
| Orphan-order reconciliation spend | $406,126.61 |
| Commission revenue | $49,127,906.69 |
| Effective commission take rate | 13.19% |
| Eligible orders | 2,198,838 |
| Net GMV per eligible order | $169.39 |
| Real registered customers | 199,797 |
| Repeat-buyer rate among buyers | 96.5% |
| Weighted merchandise margin | 50.2% |
| On-time delivery rate | 92.1% |
| Return incidence | 12.1% |

### Seller Health

| Status | Sellers | Share |
|---|---:|---:|
| Active | 3,504 | 70.1% |
| At risk | 756 | 15.1% |
| Churned | 489 | 9.8% |
| No sales | 251 | 5.0% |
| **Total** | **5,000** | **100.0%** |

### Selected Business Findings

- Referral customers generated **1.71×** the average 90-day spend of paid-search customers: **$725.54 versus $424.96**.
- Referral customers achieved a **79.0%** 90-day repeat rate versus **70.5%** for paid search.
- Whale-persona customers represented **6.1%** of real customers and **40.2%** of real-customer spend.
- Electronics contributed approximately **$108.7M in Net GMV**, the largest category contribution.
- The platform maintained a **92.1% on-time delivery rate**.
- Overall return incidence was **12.1%**.
- Seller lifecycle modeling identified **756 at-risk**, **489 churned**, and **251 no-sales sellers**.

Channel findings are associations partly created by intentional synthetic generator assumptions; they are not causal marketing conclusions.

---

## Point-in-Time Churn System

### Temporal Design

| Dataset | Snapshot dates | Rows | Churn rate |
|---|---|---:|---:|
| Training | 2024-12-31 and 2025-03-31 | 226,740 | 31.4% |
| Validation | 2025-06-30 | 148,272 | 27.4% |
| Test | 2025-09-30 | 172,352 | 23.0% |
| **All snapshots** | Four snapshots | **547,364** | — |

Each record represents `customer_id × snapshot_date`. Features use only information available through the snapshot date. Churn is defined as no eligible order during the following 90 days.

The primary model excludes the synthetic `segment` field because it is intentionally correlated with generated purchasing behavior.

### Model Comparison

| Test metric | Behavioral only | Behavioral + channel | Change |
|---|---:|---:|---:|
| ROC-AUC | 0.7757 | 0.7765 | +0.0008 |
| PR-AUC | 0.4865 | 0.4878 | +0.0013 |
| Precision | 0.3831 | 0.3768 | -0.0063 |
| Recall | 0.7873 | 0.8089 | +0.0216 |
| F1 | 0.5154 | 0.5141 | -0.0013 |
| Top-10% lift | 2.51× | 2.52× | +0.01× |
| Top-20% recall | 43.23% | 43.33% | +0.10 pp |

Signup channel added negligible out-of-time predictive value, so the simpler behavioral-only model was promoted.

### Analytical Production Scoring Output

| Metric | Result |
|---|---:|
| Customers scored | 197,546 |
| Average churn probability | 30.1% |
| Threshold-positive customers | 87,510 |
| Threshold-positive share | 44.3% |
| High-risk customers | 39,510 |
| Medium-risk customers | 59,263 |
| Low-risk customers | 98,773 |
| High-risk lifetime spend | Approximately $32.0M |
| Missing lifetime-spend values tracked | 18 |

### Retention Actions

| Recommended action | Customers |
|---|---:|
| No immediate action | 98,773 |
| Low-cost re-engagement | 59,263 |
| Standard retention campaign | 18,757 |
| Service-recovery review | 12,725 |
| Targeted retention incentive | 7,499 |
| Priority retention outreach | 529 |

### Live-Compatible Operational Scoring

The operational pipeline also trains and publishes a live-compatible model against the PostgreSQL demonstration population. This score set is kept separate from the large historical analytical scoring output because the populations and snapshot dates differ.

---

## Limitations

- All marketplace data is synthetic.
- Business findings demonstrate analytical method, not real-world causal evidence.
- The latest PostgreSQL counts reflect one local demonstration database and can change.
- The lightweight catalog seed does not reproduce the complete dashboard dataset.
- The full analytical pipeline requires more storage and runtime than the operational demo.
- Public cloud deployment is optional and is not required to reproduce the project locally.
- The application should not be described as publicly production-deployed unless a real hosting environment is created.

---

## Project Milestones

- `analytics-v1`
- `analytics-v2`
- `operations-dashboard-v1`
- `observability-v1`

These tags preserve major stages of the platform as reproducible Git milestones.

---

## About

Built by **Srihari Chepuri** as a portfolio project demonstrating:

- Business Intelligence Engineering
- Analytics Engineering
- Data Engineering
- Full-Stack Application Development
- Machine Learning
- Data Quality and Observability

GitHub: [@sriharichepuri21](https://github.com/sriharichepuri21)

---

## License

This project is available under the [MIT License](LICENSE).
