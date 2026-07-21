---
name: verify-report
description: Runs end-to-end validation that report_generator.py produces a complete HTML report with all required sections, without LLM involvement. Use after editing report_generator.py, SQL queries, or HTML templates, or when the user asks to verify the report deliverable.
disable-model-invocation: true
paths: "report_generator.py, **/*.html"
---

# Verify Report

Confirm the standalone report generator works end-to-end.

## Quick start

```bash
bash .cursor/hooks/verify-report.sh --manual
```

Or run the generator directly:

```bash
python report_generator.py --output report.html
```

Then validate output (the hook script does this automatically on agent stop).

## Validation checklist

```
- [ ] report_generator.py exists
- [ ] Script runs without errors
- [ ] report.html is created and non-empty
- [ ] All 7 sections present with correct IDs
- [ ] No LLM/API calls inside report_generator.py
```

## Required HTML sections

The output must contain these section IDs in order:

| Order | Section ID | Content |
|-------|------------|---------|
| 1 | `report-header` | Title, generation timestamp, date range |
| 2 | `kpi-cards` | Total MRR, customers, churn rate, ARPC |
| 3 | `mrr-trend` | Line chart — MRR by month |
| 4 | `revenue-by-plan` | Bar or donut — MRR by plan tier |
| 5 | `churn-analysis` | Monthly churn trend |
| 6 | `top-customers` | Top 10 table by MRR |
| 7 | `engagement-summary` | Event counts by type |

## Manual verification commands

```bash
# Check section IDs exist in output
for id in report-header kpi-cards mrr-trend revenue-by-plan churn-analysis top-customers engagement-summary; do
  grep -q "id=\"${id}\"" report.html && echo "OK: ${id}" || echo "MISSING: ${id}"
done
```

## On failure

1. Read the error from the script or hook log at `.cursor/hooks/logs/report-verify.log`
2. Fix the missing section or broken query
3. Re-run verification until all checks pass

## Architecture check

Scan `report_generator.py` for forbidden runtime dependencies:

- No `openai`, `anthropic`, or other LLM client imports
- No HTTP calls to AI APIs
- Data source is SQLite only (`database.db`)
