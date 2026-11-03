"""
Salary slip harness.

Pipeline per employee:
  1. Fetch employee + hours report + holidays from Hilanet (mock server).
  2. Compute payroll deterministically (payroll/calculator.py) — the ground truth.
  3. Ask the LangChain/OpenAI agent for a SlipReview (summary + anomaly notes).
  4. Validate the review against the ground truth; on failure, feed the errors back
     to the agent and retry. A review that still fails is dropped from the slip.
  5. Render output/<month>/<employee_id>.html (+ .json) and an index page.

Usage:
  uv run python harness.py --embedded-server                   # all employees, 2026-09
  uv run python harness.py --embedded-server --employee E1006  # one employee
  uv run python harness.py --embedded-server --no-llm          # no OpenAI key needed
"""

import argparse
import json
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

from payroll.agent import DEFAULT_MODEL, PayrollReviewAgent, SlipReview  # noqa: E402
from payroll.calculator import calculate_payroll  # noqa: E402
from payroll.client import DEFAULT_API_KEY, DEFAULT_URL, HilanetClient  # noqa: E402
from payroll.models import PayrollResult  # noqa: E402
from payroll.slip import ils, render_slip  # noqa: E402

DEFAULT_MONTH = "2026-09"
MAX_REVIEW_ATTEMPTS = 2


@dataclass
class SlipOutcome:
    result: PayrollResult
    review: SlipReview | None = None
    attempts: int = 0
    errors: list[str] = field(default_factory=list)
    path: Path | None = None


def validate_review(review: SlipReview, truth: PayrollResult) -> list[str]:
    """Return a list of problems; empty means the review is consistent with the calculator."""
    errors = []
    if review.employee_id != truth.employee.employee_id:
        errors.append(f"employee_id is {review.employee_id!r}, expected {truth.employee.employee_id!r}")
    if review.month != truth.month:
        errors.append(f"month is {review.month!r}, expected {truth.month!r}")
    for name, got, want in [("gross_pay", review.gross_pay, truth.gross_pay),
                            ("net_pay", review.net_pay, truth.net_pay)]:
        if abs(float(want) - got) > 0.005:
            errors.append(f"{name} is {got}, calculate_payroll says {want}")

    known = {(a.date.isoformat(), a.code) for a in truth.anomalies}
    noted = {(n.date, n.code) for n in review.anomaly_notes}
    for a in truth.anomalies:
        if a.severity != "info" and (a.date.isoformat(), a.code) not in noted:
            errors.append(f"missing note for {a.severity} anomaly {a.code} on {a.date}")
    for key in sorted(noted - known):
        errors.append(f"note for {key[1]} on {key[0]} does not match any calculated anomaly")

    needs_hr = any(a.severity != "info" for a in truth.anomalies)
    if review.hr_attention_required != needs_hr:
        errors.append(f"hr_attention_required should be {needs_hr}")
    return errors


def run_review(agent: PayrollReviewAgent, truth: PayrollResult, verbose: bool) -> tuple[SlipReview | None, int, list[str]]:
    emp_id, month = truth.employee.employee_id, truth.month
    history, errors = None, []
    for attempt in range(1, MAX_REVIEW_ATTEMPTS + 1):
        try:
            review, history = agent.review(emp_id, month, history=history, feedback=errors or None)
        except Exception as exc:  # network/model/parse failure — don't lose the slip over it
            return None, attempt, [f"agent error: {exc}"]
        errors = validate_review(review, truth)
        if verbose:
            tools = [m.name for m in history if getattr(m, "type", "") == "tool"]
            print(f"    attempt {attempt}: tools={tools} errors={errors or 'none'}")
        if not errors:
            return review, attempt, []
    return None, MAX_REVIEW_ATTEMPTS, errors


def start_embedded_server(url: str) -> None:
    import uvicorn

    from hilanet_mock.server import app

    parsed = urlparse(url)
    server = uvicorn.Server(uvicorn.Config(app, host=parsed.hostname, port=parsed.port or 80, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(50):
        if server.started:
            return
        time.sleep(0.1)
    raise RuntimeError(f"Embedded Hilanet server did not start on {url}")


def write_index(out_dir: Path, month: str, outcomes: list[SlipOutcome]) -> Path:
    rows = "".join(
        f"<tr><td><a href='{o.path.name}'>{o.result.employee.full_name}</a></td>"
        f"<td>{o.result.employee.role}</td><td class='num'>{ils(o.result.gross_pay)}</td>"
        f"<td class='num'>{ils(o.result.net_pay)}</td>"
        f"<td class='num'>{sum(a.severity != 'info' for a in o.result.anomalies)}</td>"
        f"<td>{'validated' if o.review else ('rejected' if o.errors else 'not run')}</td></tr>"
        for o in outcomes)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Payroll {month}</title>
<style>body{{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:900px;margin:24px auto;padding:0 16px}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:6px 8px;border-bottom:1px solid #ddd;text-align:left}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}</style></head><body>
<h1>Payroll run — {month}</h1>
<table><tr><th>Employee</th><th>Role</th><th class="num">Gross</th><th class="num">Net</th>
<th class="num">Issues</th><th>AI review</th></tr>{rows}</table></body></html>"""
    path = out_dir / "index.html"
    path.write_text(html)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--month", default=DEFAULT_MONTH, help="YYYY-MM (default: %(default)s)")
    parser.add_argument("--employee", action="append", help="Employee id; repeatable (default: all)")
    parser.add_argument("--server-url", default=DEFAULT_URL, help="Hilanet base URL (default: %(default)s)")
    parser.add_argument("--embedded-server", action="store_true", help="Start the mock Hilanet server in-process")
    parser.add_argument("--no-llm", action="store_true", help="Skip the OpenAI review agent")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI model (default: %(default)s)")
    parser.add_argument("--out", default="output", type=Path, help="Output directory (default: %(default)s)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show agent attempts and tool calls")
    args = parser.parse_args()

    if args.embedded_server:
        start_embedded_server(args.server_url)
    client = HilanetClient(args.server_url, DEFAULT_API_KEY)
    if not client.health():
        print(f"Hilanet not reachable at {args.server_url}. Start it with\n"
              f"  uv run uvicorn hilanet_mock.server:app --port 8085\nor pass --embedded-server.", file=sys.stderr)
        return 2

    agent = None
    if not args.no_llm:
        if not os.environ.get("OPENAI_API_KEY"):
            print("OPENAI_API_KEY is not set (add it to .env), or run with --no-llm.", file=sys.stderr)
            return 2
        agent = PayrollReviewAgent(client, model=args.model)

    employees = client.list_employees()
    if args.employee:
        wanted = set(args.employee)
        employees = [e for e in employees if e.employee_id in wanted]
        missing = wanted - {e.employee_id for e in employees}
        if missing:
            print(f"Unknown employee id(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    out_dir = args.out / args.month
    out_dir.mkdir(parents=True, exist_ok=True)
    holidays = client.get_holidays(args.month)
    outcomes: list[SlipOutcome] = []

    print(f"Payroll run {args.month} — {len(employees)} employee(s), AI review: {'off' if not agent else args.model}")
    for emp in employees:
        result = calculate_payroll(emp, client.get_attendance(emp.employee_id, args.month), holidays)
        outcome = SlipOutcome(result)
        if agent:
            outcome.review, outcome.attempts, outcome.errors = run_review(agent, result, args.verbose)

        outcome.path = out_dir / f"{emp.employee_id}.html"
        outcome.path.write_text(render_slip(result, outcome.review, attempts=outcome.attempts,
                                            review_errors=outcome.errors, model=args.model))
        (out_dir / f"{emp.employee_id}.json").write_text(json.dumps({
            "payroll": result.model_dump(mode="json"),
            "review": outcome.review.model_dump() if outcome.review else None,
            "review_errors": outcome.errors,
        }, indent=2, ensure_ascii=False))
        outcomes.append(outcome)

        issues = sum(a.severity != "info" for a in result.anomalies)
        status = "" if not agent else ("  AI ✓" if outcome.review else "  AI ✗ " + "; ".join(outcome.errors))
        print(f"  {emp.employee_id} {emp.full_name:<16} gross {ils(result.gross_pay):>12}  "
              f"net {ils(result.net_pay):>12}  issues {issues}{status}")

    index = write_index(out_dir, args.month, outcomes)
    print(f"Slips written to {out_dir}/ — open {index}")
    return 1 if any(o.errors for o in outcomes) else 0


if __name__ == "__main__":
    sys.exit(main())
