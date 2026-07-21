---
name: implement-section
description: Implements one HTML report section at a time with its SQL query and acceptance criteria from the report spec. Use when building report_generator.py incrementally or when the user asks to add a specific report section like KPI cards or MRR trend.
disable-model-invocation: true
paths: "report_generator.py, **/*.html, **/*.{py,sql}"
---

# Implement Section

Build one report section at a time inside `report_generator.py`.

## Before starting

1. Read `README.md` section **Report Structure**
2. Read `.cursor/rules/html-report-layout.mdc`
3. Confirm which section the user wants (or pick the next missing one)

## Section catalog

| Section ID | SQL/data needed | Visual |
|------------|-----------------|--------|
| `report-header` | MIN/MAX dates from subscriptions or events | Title block + metadata |
| `kpi-cards` | Total MRR, customer count, churn rate, ARPC | Large number cards |
| `mrr-trend` | MRR grouped by month | Line chart |
| `revenue-by-plan` | MRR by plan tier from active subscriptions | Bar or donut chart |
| `churn-analysis` | Monthly churned customers / total | Line chart or table |
| `top-customers` | Top 10 by MRR with activity level | HTML table |
| `engagement-summary` | Event counts grouped by event_type | Bar chart or table |

## Workflow

```
- [ ] Step 1: Write the SQL query and test it against database.db
- [ ] Step 2: Add a Python function that runs the query
- [ ] Step 3: Add an HTML renderer for this section only
- [ ] Step 4: Wire into report_generator.py output in correct order
- [ ] Step 5: Run /verify-report or bash .cursor/hooks/verify-report.sh --manual
```

### Step 1: SQL first

Write and test the query via MCP or `sqlite3 database.db`. Do not hardcode values that should come from the database.

**KPI examples (adapt to your schema):**

```sql
-- Total MRR from active subscriptions
SELECT COALESCE(SUM(mrr), 0) FROM subscriptions WHERE status = 'active';

-- Churn rate: churned customers / total customers
SELECT
  ROUND(100.0 * SUM(CASE WHEN status = 'churned' THEN 1 ELSE 0 END) / COUNT(*), 1)
FROM customers;
```

### Step 2: Python function

Add a focused function in `report_generator.py`:

```python
def render_kpi_cards(conn) -> str:
    ...
    return '<section id="kpi-cards">...</section>'
```

### Step 3: HTML fragment

- Use the exact section ID from the layout rule
- Embed CSS inline or in a `<style>` block (self-contained HTML)
- For charts, prefer inline SVG or a small embedded JS library (Chart.js CDN is acceptable for POC)

### Step 4: Wire up

Append the section in spec order. Do not reorder existing sections.

### Step 5: Verify

Run verification for the implemented section at minimum; full `/verify-report` when all sections exist.

## One section per invocation

Do not implement all seven sections in one pass unless the user explicitly asks. Default to **one section** to keep diffs reviewable.

## Activity level (top customers)

Derive activity level from event counts in the data period:

- High: ≥ 30 events/month average
- Medium: 10–29 events/month
- Low: < 10 events/month

Do not hardcode activity labels.
