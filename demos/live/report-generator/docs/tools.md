# Cursor Tools for Report Generator POC

This document lists the skills, rules, and hooks configured for this project, and when to use each one.

## Skills

Skills are reusable workflows the agent can invoke with `/skill-name`. They encode *how* to work in this repo, not just what the README says.

### `/seed-database` — Initialize schema + realistic sample data

**When useful:** Starting the project, resetting data, or when the agent keeps inventing inconsistent enums/MRR values.

**What it does:**
- Reads `schema.md` and `README.md`
- Creates tables with explicit columns and CHECK constraints
- Inserts ~10 rows per entity with realistic values (company names, plan tiers, MRR by tier, engagement patterns)
- Verifies: one active subscription per customer, valid enum values, date ranges that make churn/MRR charts meaningful

**Location:** `.cursor/skills/seed-database/SKILL.md`

### `/verify-report` — End-to-end report check without LLM

**When useful:** After editing `report_generator.py` or SQL queries — confirms the deliverable actually works.

**What it does:**
- Runs `python report_generator.py --output report.html`
- Asserts output file exists and is non-empty
- Checks all 7 sections are present (header, KPIs, MRR trend, plan tier, churn, top 10, engagement)
- Fails with a clear checklist if anything is missing

This reinforces the key constraint: **report generation must not depend on the agent/LLM at runtime**.

**Location:** `.cursor/skills/verify-report/SKILL.md`

### `/implement-section` — Build one report section at a time

**When useful:** Incremental development of the HTML report, one section per iteration.

**What it does:**
- Implements a single report section (e.g. KPI cards only)
- Adds the SQL query + HTML fragment + acceptance criteria from `task.md` / `README.md`
- Validates the section against `html-report-layout` rule requirements

**Location:** `.cursor/skills/implement-section/SKILL.md`

---

## Rules

Rules are always-on or file-scoped guardrails in `.cursor/rules/*.mdc`.

### `report-generator-scope.mdc` (always apply)

Keeps the agent from overbuilding the POC or breaking the architecture.

**In scope:**
- SQLite at `database.db` (via MCP during development)
- Seed script/data (~10 records per entity, realistic values)
- `report_generator.py` — standalone Python, reads DB, writes HTML
- Self-contained HTML report with embedded CSS/charts (no external API calls at render time)

**Out of scope (confirm with user first):**
- Connecting to a real production database
- Flask/FastAPI web server or dashboard
- LLM calls inside `report_generator.py`
- Heavy frameworks unless user asks (React, separate frontend build)

**Architecture rule:** MCP is for development/seeding only. Production report path is: `database.db` → `report_generator.py` → `report.html`

**Location:** `.cursor/rules/report-generator-scope.mdc`

### `schema-constraints.mdc` (globs: `**/*.{py,sql}`)

Prevents subtle data bugs that break KPI/churn calculations.

**Enforces:**
- Valid enum values for customers, subscriptions, invoices, and activity events
- At most one active subscription per customer
- MRR from active subscriptions, not invoices
- Churn rate computed from history, not hardcoded
- Sample data spanning multiple months for trend charts

**Location:** `.cursor/rules/schema-constraints.mdc`

### `html-report-layout.mdc` (globs: `**/*.{py,html}`)

Enforces report section order and semantic HTML structure from the spec.

**Requires section IDs:**
- `#report-header`
- `#kpi-cards`
- `#mrr-trend`
- `#revenue-by-plan`
- `#churn-analysis`
- `#top-customers`
- `#engagement-summary`

**Location:** `.cursor/rules/html-report-layout.mdc`

---

## Hooks

Hooks automate safety checks and feedback loops around agent actions.

### `beforeMCPExecution` — Gate destructive SQLite writes

**When useful:** During development, the MCP SQLite server can run arbitrary SQL. This hook blocks `DROP`, `DELETE`, or `UPDATE` unless the user explicitly mentions reset/reseed.

**Behavior:** Allow `SELECT`, `PRAGMA`, `CREATE TABLE`, `INSERT`. Deny `DROP TABLE`, `DELETE FROM`, `UPDATE`, and `ALTER` by default.

**Location:** `.cursor/hooks/guard-sqlite-writes.sh`

### `stop` — Auto-verify report after agent completes

**When useful:** Tight feedback loop — agent finishes editing, you immediately know if the report still generates.

**Behavior:**
- If `report_generator.py` exists, run it
- Check `report.html` was created
- Return a follow-up message listing missing sections if validation fails
- Log output to `.cursor/hooks/logs/report-verify.log`

**Location:** `.cursor/hooks/verify-report.sh`

### `beforeShellExecution` — Protect `database.db` from deletion

**When useful:** Prevents accidental loss of seeded sample data.

**Behavior:** Blocks shell commands that delete `database.db` (e.g. `rm database.db`).

**Location:** `.cursor/hooks/block-rm-database.sh`

---

## Quick pairing guide

| Pain point | Best tool |
|------------|-----------|
| Agent drifts from POC scope | **Rule:** `report-generator-scope.mdc` |
| Wrong enum values / bad seed data | **Skill:** `/seed-database` + **Rule:** `schema-constraints.mdc` |
| Report breaks silently after edits | **Hook:** `stop` → verify report |
| Accidental DB wipe via MCP | **Hook:** `beforeMCPExecution` guard |
| "Does the deliverable actually work?" | **Skill:** `/verify-report` |
| Building report incrementally | **Skill:** `/implement-section` |
| Accidental `rm database.db` | **Hook:** `beforeShellExecution` guard |

---

## Configuration files

| File | Purpose |
|------|---------|
| `.cursor/hooks.json` | Registers all project hooks |
| `.cursor/mcp.json` | SQLite MCP server connection |
| `.cursor/rules/*.mdc` | Persistent agent guardrails |
| `.cursor/skills/*/SKILL.md` | Invokable workflows |

## Cursor docs compliance (verified)

Checked against [Cursor Rules](https://cursor.com/docs/rules), [Hooks](https://cursor.com/docs/hooks), and [Skills](https://cursor.com/docs/skills) docs.

| Area | Status | Notes |
|------|--------|-------|
| Rules (`.mdc`) | OK | Valid frontmatter; `alwaysApply` + `globs` patterns match docs |
| Skills | OK | `name` matches folder; `disable-model-invocation: true` for slash-command use; `paths` on file-scoped skills |
| Hooks schema | OK | `version: 1`, valid events, supported output fields |
| MCP guard hook | Fixed | Parses official `tool_input` JSON string; no unsupported matcher on `beforeMCPExecution`; `failClosed: true` |
| Shell guard hook | OK | JS regex matcher on command string; script-side filtering |
| Stop hook | OK | Returns `followup_message` only when `status` is `completed`; respects `loop_limit` |
