# Kairo Marketplace Analytics — Project Charter

**Status:** Active — Phase 1 (Local Development)
**Owner:** Srihari Chepuri
**Repository:** https://github.com/sriharichepuri21/kairo-marketplace-analytics

---

## 1. What This Project Is

An end-to-end Business Intelligence Engineering project that simulates a fictional
e-commerce marketplace called **Kairo**. It covers the full BIE workflow: generating
realistic messy data, ingesting it through a medallion architecture, modeling it
with dbt, testing it with data quality controls, and serving it through stakeholder
dashboards.

## 2. Why It Exists

To prove operational Business Intelligence Engineering capability — the ability to
take a business from ambiguous objectives to trusted, self-serve analytics — with
a portfolio artifact that mirrors the day-to-day work of a BIE at a company like
Amazon.

## 3. Guiding Principles

1. **Business First, Technology Second** — no table or dashboard exists without a business question behind it.
2. **Metrics Are Products** — every metric has a precise definition, grain, and owner.
3. **Trust Is Non-Negotiable** — data quality is tested at every layer.
4. **Ship Small, Ship Often** — end-to-end slices ship early; complexity grows incrementally.
5. **Own It Fully** — from raw event to executive dashboard, every layer is understood.

## 4. The Fictional Company: Kairo

- **Industry:** Global e-commerce marketplace (three-sided: buyers, sellers, platform)
- **Founded:** 2020 (5 years old)
- **Scale:** 2M customers, 50K sellers, 500K products, ~$500M annual GMV
- **Regions:** US, EU, LATAM
- **Business Model:** 12% commission on GMV + seller subscriptions + advertising
- **Strategic Tension:** growth decelerating from 45% to 30% YoY; investors want margin

## 5. Strategic Business Objectives

| # | Objective | Target |
|---|-----------|--------|
| O1 | Grow GMV with improving unit economics | 30%+ YoY, margin ≥ 12% |
| O2 | Improve customer retention | Repeat rate +5 pts, 12mo retention ≥ 42% |
| O3 | Retain top sellers | Reduce top-20% seller churn by 25% |
| O4 | Hit fulfillment SLA | 95% on-time delivery across regions |
| O5 | Improve marketing efficiency | CAC payback 14mo → 9mo |
| O6 | Reduce fraud losses | Cut losses 30%, false-positive rate ≤ 0.5% |

## 6. Stakeholder Personas

Every dashboard we build serves at least one of these people:

- **Executive Leadership** — GMV, margin, cohort health (weekly WBR)
- **VP of Category** — category performance, mix, returns (weekly)
- **Head of Seller Success** — retention, churn risk (weekly)
- **Head of Fulfillment** — SLA, cost per shipment (daily)
- **Marketing Director** — LTV:CAC, cohort retention (weekly)
- **Head of Trust & Safety** — fraud rate, rule performance (daily)
- **Finance & FP&A** — recognized revenue, refunds (monthly)

## 7. Deliverables

- **7 dashboards** — one per persona
- **7 data marts** — GMV, LTV, seller health, fulfillment SLA, marketing attribution, fraud, finance
- **1 WBR narrative** — Amazon-style weekly business review doc
- **1 ad-hoc analysis** — deep-dive investigation (e.g., "why did LATAM GMV drop?")
- **1 metric catalog** — 40+ metrics with precise definitions

## 8. Architecture

**Medallion pattern** on a local-first lakehouse:

**Tech stack (local phase):**
Python, Polars, DuckDB, dbt Core, Streamlit

**Tech stack (cloud phase):**
S3, Athena, Redshift Serverless, Glue, Step Functions, QuickSight

## 9. Project Phases

| Phase | Focus | Duration |
|-------|-------|----------|
| 0 | Foundation (env, repo, docs) | Week 1 |
| 1 | Local generator + DuckDB warehouse | Weeks 2–4 |
| 2 | Full generator + chaos engine | Weeks 5–7 |
| 3 | dbt models + data quality | Weeks 8–9 |
| 4 | Streamlit dashboards + WBR docs | Weeks 10–11 |
| 5 | AWS migration | Weeks 12–13 |
| 6 | QuickSight + public launch | Weeks 14–16 |

## 10. Success Criteria

- End-to-end pipeline runs locally, unattended, without errors
- 40+ metrics defined with precise definitions
- 4+ persona dashboards operational
- Data quality tests pass at 95%+ rate
- Project publicly launched with README, blog posts, and video walkthrough
- Every architectural decision defensible in a 30-minute interview

## 11. Change Log

| Version | Date | Change |
|---------|------|--------|
| 0.1 | 2026-07-09 | Initial charter drafted |