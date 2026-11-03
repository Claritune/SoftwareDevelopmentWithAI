"""Render a PayrollResult (plus the optional validated AI review) into an HTML salary slip."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from payroll.agent import SlipReview
from payroll.models import PayrollResult

COMPANY = "Acme Demo Ltd."
_env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"),
                   autoescape=select_autoescape(["html"]))


def ils(x: Decimal | None) -> str:
    return "" if x is None else f"₪{x:,.2f}"


def qty(x: Decimal | None) -> str:
    if x is None:
        return ""
    if x == 0:
        return "–"
    return f"{x.normalize():f}"


def render_slip(result: PayrollResult, review: SlipReview | None = None, *,
                attempts: int = 0, review_errors: list[str] | None = None, model: str = "") -> str:
    year, mon = map(int, result.month.split("-"))
    notes = {(n.date, n.code): n for n in review.anomaly_notes} if review else {}
    return _env.get_template("slip.html").render(
        r=result, review=review, notes=notes, attempts=attempts, review_errors=review_errors or [],
        model=model, company=COMPANY, ils=ils, qty=qty,
        month_label=date(year, mon, 1).strftime("%B %Y"),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
