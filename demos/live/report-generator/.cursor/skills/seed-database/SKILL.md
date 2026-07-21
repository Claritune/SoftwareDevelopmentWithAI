---
name: seed-database
description: Initializes the SQLite schema and seeds realistic sample data (~10 records per entity) for the SaaS metrics report generator POC. Use when creating database.db, resetting sample data, reseeding, or when the user asks to populate the database.
disable-model-invocation: true
---

# Seed Database

Initialize `database.db` with schema and realistic sample data for the report generator POC.

## Prerequisites

- Read `schema.md`, `README.md`, and `.cursor/rules/schema-constraints.mdc`
- Target database: `database.db` in the project root
- Use MCP SQLite tools or a `seed.py` / `schema.sql` script

## Workflow

Copy this checklist and track progress:

```
- [ ] Step 1: Create tables with CHECK constraints
- [ ] Step 2: Seed ~10 customers
- [ ] Step 3: Seed subscriptions (6–12 month span)
- [ ] Step 4: Seed invoices
- [ ] Step 5: Seed activity events
- [ ] Step 6: Run validation queries
```

### Step 1: Create tables

Create four tables matching the schema spec:

- `customers` — company_name, contact_name, contact_email, plan_tier, signup_date, country, status
- `subscriptions` — customer_id, mrr, status, start_date, cancel_date
- `invoices` — customer_id, amount, currency, issued_date, paid_date, status
- `activity_events` — customer_id, event_type, timestamp

Add CHECK constraints for all enum fields (see `schema-constraints` rule).

### Step 2: Seed ~10 customers

Use realistic B2B company names, contact details, and countries. Mix:

- Plan tiers: `free`, `starter`, `professional`, `enterprise`
- Status: mostly `active`, 2–3 `churned`
- Signup dates spread across the last 12 months

### Step 3: Seed subscriptions

- ~10–15 subscription rows total (some customers have history)
- MRR by tier (realistic ranges):
  - free: $0
  - starter: $29–$99
  - professional: $199–$499
  - enterprise: $999–$4999
- Only **one active subscription per customer**
- Cancelled subscriptions need `cancel_date` set
- Date range must cover multiple months for MRR/churn charts

### Step 4: Seed invoices

- ~10 invoices tied to customers
- Status mix: `paid`, `pending`, `overdue`, `void`
- Some with null `paid_date`
- Currency always `USD`

### Step 5: Seed activity events

- ~10 customers × multiple events each (100+ rows total is fine)
- High-engagement customers: 30–50 events/month
- Low-engagement customers: 5–10 events/month
- Event types: `login`, `feature_use`, `support_ticket`, `api_call`, `export`
- Timestamps within the data period

### Step 6: Validate

Run and report row counts:

```sql
SELECT 'customers' AS t, COUNT(*) FROM customers
UNION ALL SELECT 'subscriptions', COUNT(*) FROM subscriptions
UNION ALL SELECT 'invoices', COUNT(*) FROM invoices
UNION ALL SELECT 'activity_events', COUNT(*) FROM activity_events;
```

Also verify:

```sql
-- At most one active subscription per customer
SELECT customer_id, COUNT(*) AS active_count
FROM subscriptions WHERE status = 'active'
GROUP BY customer_id HAVING COUNT(*) > 1;
-- Must return zero rows
```

## Reset / reseed

When resetting, tell the user you are reseeding so MCP write guards allow destructive SQL if needed. Prefer dropping and recreating tables over partial deletes.

## Do not

- Invent enum values outside the schema spec
- Hardcode KPI values instead of deriving them from data
- Seed so much data that the POC becomes unwieldy (~10 per entity, not 1000)
