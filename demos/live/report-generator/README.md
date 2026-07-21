# SaaS Metrics Report Generator — POC

You were asked to generate a proof of concept (POC) of a report generator that uses data described by the provided schema. The goal is to produce a self-contained HTML analytics report from a local SQLite database, without requiring an LLM at generation time.

## Objectives

1. **Use SQLite via MCP for now** — The database lives locally at `database.db`. Cursor is configured to access it through the official [`mcp-server-sqlite`](https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite) MCP server (see `.cursor/mcp.json`). A real production database will be connected later; for this POC, SQLite is the data source.

2. **Initialize the database with sample data** — Create the schema and seed it with realistic sample records. Keep the dataset small: about **10 records per entity** (customers, subscriptions, invoices, activity events). Data should look believable — plausible company names, contact details, plan tiers, MRR amounts, invoice statuses, and engagement patterns.

3. **Generate an HTML report from the database** — Build `report_generator.py`, a standalone Python script that reads from the SQLite database and outputs a complete HTML report. The script must work on its own after the database is populated — no LLM calls during report generation.

## Database Schema

The schema models a subscription analytics platform with four core entities.

### Customers

Each customer represents a company using the product.

| Field | Description |
|-------|-------------|
| Company name | Name of the customer organization |
| Primary contact | Contact name and email |
| Plan tier | One of: `free`, `starter`, `professional`, `enterprise` |
| Signup date | When the customer joined |
| Country | Customer location |
| Status | `active` or `churned` |

### Subscriptions

A subscription links a customer to a plan and tracks recurring revenue.

| Field | Description |
|-------|-------------|
| Customer | Reference to the customer |
| MRR | Monthly recurring revenue in USD |
| Status | `active`, `cancelled`, or `past_due` |
| Start date | When the subscription began |
| Cancel date | Optional — set when the subscription was cancelled |

A customer may have multiple subscriptions over time (e.g., cancel and re-subscribe), but only **one active subscription at a time**.

### Invoices

Each invoice is tied to a customer.

| Field | Description |
|-------|-------------|
| Customer | Reference to the customer |
| Amount | Invoice amount |
| Currency | Always USD for now |
| Issued date | When the invoice was created |
| Paid date | Nullable — not all invoices are paid |
| Status | `paid`, `pending`, `overdue`, or `void` |

### Activity Events

User engagement events tracked per customer.

| Field | Description |
|-------|-------------|
| Customer | Reference to the customer |
| Event type | One of: `login`, `feature_use`, `support_ticket`, `api_call`, `export` |
| Timestamp | When the event occurred |

Engagement varies by customer: high-engagement customers typically generate **30–50 events per month**; low-engagement ones generate **5–10**.

## Report Structure

The generated HTML report must include the following sections, in this order:

1. **Header** — Report title, generation timestamp, and date range covered by the data.

2. **KPI Cards Row** — Four to five key metrics displayed as large numbers with labels:
   - Total MRR
   - Total Customers
   - Churn Rate (%)
   - Average Revenue Per Customer

3. **MRR Trend** — Line chart showing MRR by month over the data period.

4. **Revenue by Plan Tier** — Bar or donut chart breaking down MRR by plan tier.

5. **Churn Analysis** — Monthly churn trend (line chart or table).

6. **Top 10 Customers** — Table sorted by MRR, showing company, plan, MRR, signup date, and activity level.

7. **Engagement Summary** — Event counts by type (bar chart or table).

## Expected Deliverables

| Artifact | Purpose |
|----------|---------|
| `database.db` | SQLite database with schema and sample data |
| `report_generator.py` | Standalone script that queries the database and writes an HTML report |
| Generated HTML report | Output file produced by running the script |

## MCP Setup

The project includes a Cursor MCP configuration at `.cursor/mcp.json` that connects to the local SQLite database:

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "/Users/bigromanov/.local/bin/uvx",
      "args": [
        "mcp-server-sqlite",
        "--db-path",
        "database.db"
      ]
    }
  }
}
```

After reloading Cursor, the MCP server can be used to explore the schema, run queries, and seed data during development. Report generation itself should go through `report_generator.py`, not the LLM.

## Related Files

- `schema.md` — Original schema specification
- `task.md` — Original report layout specification
