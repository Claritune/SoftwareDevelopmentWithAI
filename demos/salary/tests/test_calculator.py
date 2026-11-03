from datetime import date
from decimal import Decimal

import pytest

from payroll.calculator import calculate_payroll, income_tax, national_insurance, sick_pay_fraction
from payroll.models import AttendanceDay, AttendanceReport, Employee


def employee(**overrides) -> Employee:
    base = dict(employee_id="T1", first_name="Test", last_name="Person", role="Tester", department="QA",
                employment_type="hourly", hourly_rate=Decimal("50"), scope_percent=100,
                tax_credit_points=Decimal("2.25"), pension_enrolled=True, start_date=date(2020, 1, 1))
    base.update(overrides)
    return Employee(**base)


def report(*days: AttendanceDay, month="2026-09") -> AttendanceReport:
    return AttendanceReport(employee_id="T1", month=month, exported_at="", days=list(days))


def work(d: int, clock_in: str | None, clock_out: str | None) -> AttendanceDay:
    return AttendanceDay(date=date(2026, 9, d), type="work", clock_in=clock_in, clock_out=clock_out)


def codes(result) -> set[tuple[int, str]]:
    return {(a.date.day, a.code) for a in result.anomalies if a.code != "unreported_workday"}


def test_weekday_overtime_bands():
    # Tue 1 Sep: 08:00-21:00 = 13 h -> 8.6 regular, 2 at 125%, 2.4 at 150%
    r = calculate_payroll(employee(), report(work(1, "08:00", "21:00")), {})
    day = r.days[0]
    assert (day.regular_hours, day.overtime_125_hours, day.overtime_150_hours) == (
        Decimal("8.6"), Decimal("2"), Decimal("2.4"))
    earnings = {line.label: line.amount for line in r.earnings}
    assert earnings["Regular hours"] == Decimal("430.00")
    assert earnings["Overtime 125%"] == Decimal("125.00")
    assert earnings["Overtime 150%"] == Decimal("180.00")
    assert (1, "long_shift") in codes(r)


def test_rest_day_and_holiday_hours_paid_at_150():
    # Fri 4 Sep and a weekday holiday on Mon 21 Sep
    r = calculate_payroll(employee(), report(work(4, "08:00", "12:00"), work(21, "08:00", "10:00")),
                          {"2026-09-21": "Yom Kippur"})
    assert r.totals["rest_day_hours"] == Decimal("6")
    assert r.totals["regular_hours"] == 0
    assert {line.label: line.amount for line in r.earnings}["Rest day / holiday work 150%"] == Decimal("450.00")


@pytest.mark.parametrize("day,expected", [(1, "0"), (2, "0.5"), (3, "0.5"), (4, "1"), (9, "1")])
def test_sick_ladder(day, expected):
    assert sick_pay_fraction(day) == Decimal(expected)


def test_monthly_sick_episode_deducts_unpaid_portion():
    emp = employee(employment_type="monthly", monthly_salary=Decimal("18200"), hourly_rate=None)
    sick = [AttendanceDay(date=date(2026, 9, d), type="sick") for d in (1, 2, 3)]
    r = calculate_payroll(emp, report(*sick), {})
    # rate 100/h, day = 860; unpaid = 1 + 0.5 + 0.5 = 2 days
    adj = next(line for line in r.earnings if line.label == "Sick leave adjustment")
    assert adj.amount == Decimal("-1720.00")
    assert r.gross_pay == Decimal("16480.00")


def test_broken_punches_pay_zero_and_are_critical():
    r = calculate_payroll(employee(), report(work(1, "08:00", None), work(2, "12:00", "11:00")), {})
    assert r.totals["hours_worked"] == 0
    assert {(1, "missing_clock_out"), (2, "invalid_punch")} <= codes(r)
    assert all(a.severity == "critical" for a in r.anomalies if a.code in {"missing_clock_out", "invalid_punch"})


def test_unreported_workday_flagged_for_full_time_only():
    full = calculate_payroll(employee(), report(), {})
    part = calculate_payroll(employee(scope_percent=60), report(), {})
    assert any(a.code == "unreported_workday" for a in full.anomalies)
    assert not any(a.code == "unreported_workday" for a in part.anomalies)


def test_holiday_pay_requires_three_months_seniority():
    holiday = AttendanceDay(date=date(2026, 9, 13), type="holiday")
    senior = calculate_payroll(employee(), report(holiday), {})
    junior = calculate_payroll(employee(start_date=date(2026, 7, 1)), report(holiday), {})
    assert senior.gross_pay == Decimal("430.00")
    assert junior.gross_pay == 0


def test_tax_and_national_insurance():
    assert income_tax(Decimal("5000"), Decimal("2.25")) == 0  # 500 tax < 544.50 credit
    # 701 + 427 + 1218 + 0.31*2850=883.50 -> 3229.50 - 544.50
    assert income_tax(Decimal("19000"), Decimal("2.25")) == Decimal("2685.00")
    assert national_insurance(Decimal("7522")) == Decimal("321.19")
    assert national_insurance(Decimal("100000")) == national_insurance(Decimal("50695"))


def test_net_is_gross_minus_deductions():
    r = calculate_payroll(employee(), report(work(1, "08:00", "17:00"), work(2, "08:00", "17:00")), {})
    assert r.net_pay == r.gross_pay - sum(line.amount for line in r.deductions)
