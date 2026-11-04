# Task: SaaS Metrics Report

Build a tool that turns a subscription business's data into a single, self-contained HTML analytics report.

## Data

A subscription analytics platform with four entities. Seed it with realistic sample data: about **10 records per entity**, spanning **several months** so trends are visible.

### Customers

| Field | Values |
|-------|--------|
| Company name | |
| Primary contact | Name and email |
| Plan tier | `free`, `starter`, `professional`, `enterprise` |
| Signup date | |
| Country | |
| Status | `active`, `churned` |

### Subscriptions

| Field | Values |
|-------|--------|
| Customer | |
| MRR | Monthly recurring revenue, USD |
| Status | `active`, `cancelled`, `past_due` |
| Start date | |
| Cancel date | Optional |

A customer can have several subscriptions over time, but only **one active** at a time.

### Invoices

| Field | Values |
|-------|--------|
| Customer | |
| Amount | |
| Currency | Always `USD` |
| Issued date | |
| Paid date | Optional |
| Status | `paid`, `pending`, `overdue`, `void` |

### Activity Events

| Field | Values |
|-------|--------|
| Customer | |
| Event type | `login`, `feature_use`, `support_ticket`, `api_call`, `export` |
| Timestamp | |

High-engagement customers generate **30–50 events per month**; low-engagement ones **5–10**.

## Rules

- MRR comes from active subscriptions, not invoices.
- Churn is calculated from customer and subscription history, never hard-coded.

## Report

Sections, in this order:

1. **Header**: title, generation time, date range covered
2. **KPIs**: Total MRR, Total Customers, Churn Rate (%), Average Revenue Per Customer
3. **MRR Trend**: MRR by month
4. **Revenue by Plan Tier**: MRR split by tier
5. **Churn Analysis**: monthly churn trend
6. **Top 10 Customers**: by MRR, with company, plan, MRR, signup date, activity level
7. **Engagement Summary**: event counts by type
