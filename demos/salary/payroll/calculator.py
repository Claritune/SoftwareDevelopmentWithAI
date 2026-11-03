"""
Deterministic payroll calculation.

All money math lives here, in Decimal — the LLM agent calls this as a tool and
never computes pay itself. The rules are a simplified model of Israeli payroll;
the statutory parameters below are illustrative (based on 2025 published
values) and are NOT a substitute for a certified payroll engine.

Rules applied:
  * Work week Sun–Thu. Fri/Sat and public holidays are rest days.
  * Weekday overtime: first 8.6 h regular, next 2 h at 125%, the rest at 150%.
  * Any hours on a rest day are paid at 150%.
  * Monthly employees: fixed base salary; hourly rate = salary / 182 for overtime.
  * Hourly employees: paid for hours worked plus paid vacation/holiday days.
  * Sick leave per episode: day 1 unpaid, days 2–3 at 50%, day 4+ at 100%.
  * Holiday pay for hourly employees requires 3 months' seniority.
  * Punches that can't be turned into hours (missing clock-out, clock-out before
    clock-in) are paid as 0 h and raised as critical anomalies for HR to fix.
"""

import calendar
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from payroll.models import (
    Anomaly, AttendanceReport, DayBreakdown, Employee, PayLine, PayrollResult,
)

# --- Statutory / company parameters (illustrative) ---
MONTHLY_HOURS_DIVISOR = Decimal("182")
DAILY_REGULAR_HOURS = Decimal("8.6")
OVERTIME_125_BAND = Decimal("2")
LONG_SHIFT_HOURS = Decimal("12")
REST_DAYS = {4, 5}  # Python weekday(): Fri=4, Sat=5
HOLIDAY_PAY_MIN_SENIORITY_MONTHS = 3

PENSION_EMPLOYEE_RATE = Decimal("0.06")
NI_REDUCED_RATE = Decimal("0.0427")  # national insurance + health, up to threshold
NI_FULL_RATE = Decimal("0.1217")
NI_THRESHOLD = Decimal("7522")
NI_CEILING = Decimal("50695")
TAX_CREDIT_POINT_VALUE = Decimal("242")
TAX_BRACKETS = [  # (monthly upper bound, rate)
    (Decimal("7010"), Decimal("0.10")),
    (Decimal("10060"), Decimal("0.14")),
    (Decimal("16150"), Decimal("0.20")),
    (Decimal("22440"), Decimal("0.31")),
    (Decimal("46690"), Decimal("0.35")),
    (Decimal("60130"), Decimal("0.47")),
    (None, Decimal("0.50")),
]

CENT = Decimal("0.01")
ZERO = Decimal("0")


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def sick_pay_fraction(day_in_episode: int) -> Decimal:
    if day_in_episode == 1:
        return ZERO
    if day_in_episode <= 3:
        return Decimal("0.5")
    return Decimal("1")


def income_tax(taxable: Decimal, credit_points: Decimal) -> Decimal:
    tax, lower = ZERO, ZERO
    for upper, rate in TAX_BRACKETS:
        if upper is None or taxable <= upper:
            tax += (taxable - lower) * rate
            break
        tax += (upper - lower) * rate
        lower = upper
    return money(max(ZERO, tax - credit_points * TAX_CREDIT_POINT_VALUE))


def national_insurance(gross: Decimal) -> Decimal:
    capped = min(gross, NI_CEILING)
    reduced = min(capped, NI_THRESHOLD) * NI_REDUCED_RATE
    full = max(ZERO, capped - NI_THRESHOLD) * NI_FULL_RATE
    return money(reduced + full)


def _hours_between(clock_in: str, clock_out: str) -> Decimal:
    t_in = datetime.strptime(clock_in, "%H:%M")
    t_out = datetime.strptime(clock_out, "%H:%M")
    minutes = int((t_out - t_in).total_seconds() // 60)
    return (Decimal(minutes) / Decimal(60)).quantize(CENT, rounding=ROUND_HALF_UP)


def _months_between(start: date, on: date) -> int:
    months = (on.year - start.year) * 12 + (on.month - start.month)
    return months - (1 if on.day < start.day else 0)


def calculate_payroll(employee: Employee, report: AttendanceReport,
                      holidays: dict[str, str]) -> PayrollResult:
    year, mon = map(int, report.month.split("-"))
    first_day = date(year, mon, 1)
    monthly = employee.employment_type == "monthly"
    rate = (employee.monthly_salary / MONTHLY_HOURS_DIVISOR) if monthly else employee.hourly_rate
    paid_day_hours = DAILY_REGULAR_HOURS * Decimal(employee.scope_percent) / Decimal(100)

    days: list[DayBreakdown] = []
    anomalies: list[Anomaly] = []
    sick_fractions: list[Decimal] = []
    sick_streak = 0
    counts = {"work": 0, "sick": 0, "vacation": 0, "holiday": 0}

    for day in sorted(report.days, key=lambda d: d.date):
        counts[day.type] += 1
        sick_streak = sick_streak + 1 if day.type == "sick" else 0
        row = DayBreakdown(date=day.date, type=day.type, note=day.note)

        if day.type == "sick":
            fraction = sick_pay_fraction(sick_streak)
            sick_fractions.append(fraction)
            anomalies.append(Anomaly(
                date=day.date, code="sick_leave", severity="info",
                detail=f"Sick day {sick_streak} of episode, paid at {fraction:.0%}"))

        if day.type == "work":
            if not day.clock_in or not day.clock_out:
                anomalies.append(Anomaly(
                    date=day.date, code="missing_clock_out", severity="critical",
                    detail=f"Clocked in at {day.clock_in} with no clock-out; paid as 0 h until corrected"))
            else:
                hours = _hours_between(day.clock_in, day.clock_out)
                if hours <= 0:
                    anomalies.append(Anomaly(
                        date=day.date, code="invalid_punch", severity="critical",
                        detail=f"Clock-out {day.clock_out} is not after clock-in {day.clock_in}; paid as 0 h"))
                    hours = ZERO
                row.hours_worked = hours
                if day.date.weekday() in REST_DAYS or day.date.isoformat() in holidays:
                    row.rest_day_hours = hours
                    if hours > 0:
                        anomalies.append(Anomaly(
                            date=day.date, code="rest_day_work", severity="info",
                            detail=f"{hours} h worked on a rest day/holiday, paid at 150%"))
                else:
                    row.regular_hours = min(hours, DAILY_REGULAR_HOURS)
                    row.overtime_125_hours = min(max(ZERO, hours - DAILY_REGULAR_HOURS), OVERTIME_125_BAND)
                    row.overtime_150_hours = max(ZERO, hours - DAILY_REGULAR_HOURS - OVERTIME_125_BAND)
                if hours > LONG_SHIFT_HOURS:
                    anomalies.append(Anomaly(
                        date=day.date, code="long_shift", severity="warning",
                        detail=f"{hours} h shift exceeds {LONG_SHIFT_HOURS} h; check rest-time compliance"))
        days.append(row)

    # Workdays with no report at all (only meaningful for full-time staff).
    if employee.scope_percent == 100:
        reported = {d.date for d in report.days}
        for dom in range(1, calendar.monthrange(year, mon)[1] + 1):
            d = date(year, mon, dom)
            if (d.weekday() not in REST_DAYS and d.isoformat() not in holidays
                    and d not in reported and d >= employee.start_date):
                anomalies.append(Anomaly(
                    date=d, code="unreported_workday", severity="warning",
                    detail="Workday with no attendance report and no absence reason"))

    totals = {
        "hours_worked": sum((d.hours_worked for d in days), ZERO),
        "regular_hours": sum((d.regular_hours for d in days), ZERO),
        "overtime_125_hours": sum((d.overtime_125_hours for d in days), ZERO),
        "overtime_150_hours": sum((d.overtime_150_hours for d in days), ZERO),
        "rest_day_hours": sum((d.rest_day_hours for d in days), ZERO),
        **{f"{k}_days": Decimal(v) for k, v in counts.items()},
    }

    earnings: list[PayLine] = []
    non_pensionable = ZERO
    if monthly:
        earnings.append(PayLine(label="Base salary", amount=money(employee.monthly_salary)))
        unpaid_sick = sum((Decimal(1) - f for f in sick_fractions), ZERO)
        if unpaid_sick:
            daily = rate * DAILY_REGULAR_HOURS
            earnings.append(PayLine(label="Sick leave adjustment", quantity=unpaid_sick,
                                    rate=money(daily), amount=money(-unpaid_sick * daily)))
    else:
        earnings.append(PayLine(label="Regular hours", quantity=totals["regular_hours"],
                                rate=rate, amount=money(totals["regular_hours"] * rate)))
        if counts["vacation"]:
            earnings.append(PayLine(label="Vacation pay", quantity=Decimal(counts["vacation"]),
                                    rate=money(paid_day_hours * rate),
                                    amount=money(counts["vacation"] * paid_day_hours * rate)))
        if counts["holiday"]:
            eligible = _months_between(employee.start_date, first_day) >= HOLIDAY_PAY_MIN_SENIORITY_MONTHS
            label = "Holiday pay" if eligible else "Holiday pay (not eligible: < 3 months seniority)"
            amount = money(counts["holiday"] * paid_day_hours * rate) if eligible else ZERO
            earnings.append(PayLine(label=label, quantity=Decimal(counts["holiday"]),
                                    rate=money(paid_day_hours * rate), amount=amount))
        if sick_fractions:
            paid_sick_days = sum(sick_fractions, ZERO)
            earnings.append(PayLine(label="Sick pay", quantity=paid_sick_days,
                                    rate=money(paid_day_hours * rate),
                                    amount=money(paid_sick_days * paid_day_hours * rate)))

    for label, hours, multiplier in [
        ("Overtime 125%", totals["overtime_125_hours"], Decimal("1.25")),
        ("Overtime 150%", totals["overtime_150_hours"], Decimal("1.5")),
        ("Rest day / holiday work 150%", totals["rest_day_hours"], Decimal("1.5")),
    ]:
        if hours:
            amount = money(hours * rate * multiplier)
            earnings.append(PayLine(label=label, quantity=hours, rate=money(rate * multiplier), amount=amount))
            non_pensionable += amount

    gross = sum((line.amount for line in earnings), ZERO)

    deductions: list[PayLine] = []
    if employee.pension_enrolled:
        pensionable = gross - non_pensionable
        deductions.append(PayLine(label="Pension (employee 6%)", quantity=None, rate=PENSION_EMPLOYEE_RATE,
                                  amount=money(pensionable * PENSION_EMPLOYEE_RATE)))
    deductions.append(PayLine(label="National insurance + health", amount=national_insurance(gross)))
    deductions.append(PayLine(label=f"Income tax ({employee.tax_credit_points} credit points)",
                              amount=income_tax(gross, employee.tax_credit_points)))
    total_deductions = sum((line.amount for line in deductions), ZERO)

    anomalies.sort(key=lambda a: (a.date, a.code))
    return PayrollResult(
        employee=employee, month=report.month, hourly_rate=money(rate), days=days,
        earnings=earnings, deductions=deductions, gross_pay=gross,
        total_deductions=total_deductions, net_pay=gross - total_deductions,
        totals=totals, anomalies=anomalies,
    )
