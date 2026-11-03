# Salary: Hilanet hours → payroll → salary slip

Collects monthly hours reports from a (mock) **Hilanet** reporting system, calculates salaries,
and generates HTML salary slips. A LangChain + OpenAI agent reviews each payroll run and writes the
employee-facing notes; a custom harness validates everything the agent says before it reaches a slip.

```
 hilanet_mock/  ──HTTP──▶  payroll/client.py ──▶ payroll/calculator.py ──▶ PayrollResult (ground truth)
 (FastAPI + JSON data)                                   ▲                         │
                                                         │ tool                    ▼
                                  payroll/agent.py (LangChain, OpenAI) ──▶ SlipReview ──▶ harness.py validates
                                                                                            │  (retry w/ feedback)
                                                                                            ▼
                                                                   payroll/slip.py ──▶ output/<month>/*.html
```

**Design rule:** the LLM never does money math. `calculate_payroll` (Decimal, deterministic) is the
only source of amounts. The agent calls it as a tool and explains the result. The harness rejects any
review whose gross/net differ from the calculator, that skips a warning or critical anomaly, or that
invents one. When a review is rejected, the harness sends the errors back to the agent and retries once.
If the second review also fails, the slip is still issued, without the AI notes.

## Setup

```bash
uv sync
cp .env.example .env      # then put your OPENAI_API_KEY in .env
```

## Run

```bash
# Everything in one process (starts the mock server on :8085)
uv run python harness.py --embedded-server

# One employee, show the agent's tool calls and validation attempts
uv run python harness.py --embedded-server --employee E1006 -v

# No OpenAI key: deterministic payroll + slips only
uv run python harness.py --embedded-server --no-llm

# Or run the mock server separately (Swagger UI at http://127.0.0.1:8085/docs)
uv run uvicorn hilanet_mock.server:app --port 8085
uv run python harness.py
```

Output goes to `output/2026-09/`: `index.html` (run summary), and for each employee `<id>.html`
(the slip) and `<id>.json` (full payroll result plus the AI review). The harness exits with code 1
if any AI review was rejected, so it can gate CI.

Options: `--month YYYY-MM`, `--employee ID` (repeatable), `--model` (default `gpt-4o-mini` or
`$OPENAI_MODEL`), `--server-url`, `--out`.

## Mock Hilanet API

All `/api` calls need the header `X-API-Key: hilanet-demo-key` (override with `$HILANET_API_KEY`).

| Endpoint | Returns |
|---|---|
| `GET /api/v1/employees` | employee master data |
| `GET /api/v1/employees/{id}` | one employee |
| `GET /api/v1/attendance/{id}?month=YYYY-MM` | daily `work`/`sick`/`vacation`/`holiday` entries with clock-in/out |
| `GET /api/v1/holidays?month=YYYY-MM` | public holidays in that month |

## Sample data

`uv run python -m hilanet_mock.generate_data [--month YYYY-MM]` regenerates `hilanet_mock/data/`
(seeded, so the output is reproducible). It holds 8 employees: 5 on monthly salary and 3 hourly,
one of them a 60% part-time student. September 2026 includes holidays on real dates and these
planted cases:

| Employee | Case |
|---|---|
| E1001 Noa Levi | workday with no report |
| E1002 Yossi Cohen | 3-day sick episode (day 1 unpaid, days 2–3 at 50%) |
| E1004 Avi Mizrahi | Saturday deployment shift; 13.75 h incident day |
| E1005 Dana Shapiro | 3 vacation days |
| E1006 Omer Biton | missing clock-out; Friday on-call shifts |
| E1007 Lior Katz | 13.3 h inventory day; Friday shift |
| E1008 Rana Haddad | clock-out before clock-in; not yet eligible for holiday pay |

## Payroll rules (simplified, illustrative)

These follow Israeli payroll conventions, simplified. The parameters are approximate 2025 values
and live at the top of `payroll/calculator.py`. **Do not use this for real payroll.**

- Sun–Thu work week. Daily overtime starts after 8.6 h: the next 2 h are paid at 125%, anything beyond at 150%. Hours on Fri/Sat or a holiday are paid at 150%.
- Monthly employees get their base salary, plus overtime at an hourly rate of salary ÷ 182. Hourly employees are paid for hours worked, plus vacation and holiday days (holiday pay needs 3 months' seniority).
- Sick pay works per episode: day 1 is unpaid, days 2–3 are paid at 50%, and day 4 onward at 100%.
- A punch that can't produce hours (missing clock-out, or clock-out before clock-in) is paid as 0 h and flagged as critical.
- Deductions: employee pension of 6% (overtime excluded), national insurance + health on two tiers, and income tax by bracket minus credit points. Not modelled: break deductions, employer costs, travel, or year-to-date tax.

## Tests

```bash
uv run pytest
```

The tests cover the calculator rules, the mock API, harness validation and retry (using a stub
agent), and slip rendering. They need no OpenAI key.
