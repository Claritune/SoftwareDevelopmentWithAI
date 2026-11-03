"""
Generate sample data for the mock Hilanet server.

Writes:
  data/employees.json             — employee master data (names, roles, salaries)
  data/attendance/<YYYY-MM>.json  — daily clock-in/clock-out reports per employee
  data/holidays.json              — public holidays the payroll calculator honours

Output is deterministic (seeded), so regenerating produces the same files.

Usage:
  uv run python -m hilanet_mock.generate_data                 # default month 2026-09
  uv run python -m hilanet_mock.generate_data --month 2026-10
"""

import argparse
import calendar
import json
import random
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_MONTH = "2026-09"
SEED = 2026

# Israeli work week: Sunday–Thursday. Python weekday(): Mon=0 … Sun=6.
WORKDAYS = {6, 0, 1, 2, 3}

HOLIDAYS = {
    "2026-09-12": "Rosh Hashanah",
    "2026-09-13": "Rosh Hashanah (day 2)",
    "2026-09-21": "Yom Kippur",
    "2026-09-26": "Sukkot",
    "2026-10-03": "Shemini Atzeret",
}

EMPLOYEES = [
    {
        "employee_id": "E1001", "first_name": "Noa", "last_name": "Levi",
        "role": "Senior Backend Engineer", "department": "R&D",
        "employment_type": "monthly", "monthly_salary": 32000, "hourly_rate": None,
        "scope_percent": 100, "tax_credit_points": 2.75, "pension_enrolled": True,
        "start_date": "2021-03-01",
    },
    {
        "employee_id": "E1002", "first_name": "Yossi", "last_name": "Cohen",
        "role": "QA Engineer", "department": "R&D",
        "employment_type": "monthly", "monthly_salary": 21000, "hourly_rate": None,
        "scope_percent": 100, "tax_credit_points": 2.25, "pension_enrolled": True,
        "start_date": "2022-08-15",
    },
    {
        "employee_id": "E1003", "first_name": "Maya", "last_name": "Friedman",
        "role": "Product Manager", "department": "Product",
        "employment_type": "monthly", "monthly_salary": 34500, "hourly_rate": None,
        "scope_percent": 100, "tax_credit_points": 2.75, "pension_enrolled": True,
        "start_date": "2020-01-05",
    },
    {
        "employee_id": "E1004", "first_name": "Avi", "last_name": "Mizrahi",
        "role": "DevOps Engineer", "department": "R&D",
        "employment_type": "monthly", "monthly_salary": 29000, "hourly_rate": None,
        "scope_percent": 100, "tax_credit_points": 2.25, "pension_enrolled": True,
        "start_date": "2023-02-01",
    },
    {
        "employee_id": "E1005", "first_name": "Dana", "last_name": "Shapiro",
        "role": "Office Manager", "department": "Operations",
        "employment_type": "monthly", "monthly_salary": 14500, "hourly_rate": None,
        "scope_percent": 100, "tax_credit_points": 4.75, "pension_enrolled": True,
        "start_date": "2019-06-10",
    },
    {
        "employee_id": "E1006", "first_name": "Omer", "last_name": "Biton",
        "role": "Support Technician", "department": "Customer Success",
        "employment_type": "hourly", "monthly_salary": None, "hourly_rate": 58,
        "scope_percent": 100, "tax_credit_points": 2.25, "pension_enrolled": True,
        "start_date": "2024-04-01",
    },
    {
        "employee_id": "E1007", "first_name": "Lior", "last_name": "Katz",
        "role": "Warehouse Associate", "department": "Logistics",
        "employment_type": "hourly", "monthly_salary": None, "hourly_rate": 42,
        "scope_percent": 100, "tax_credit_points": 2.25, "pension_enrolled": True,
        "start_date": "2025-01-12",
    },
    {
        "employee_id": "E1008", "first_name": "Rana", "last_name": "Haddad",
        "role": "Junior Data Analyst (student)", "department": "Data",
        "employment_type": "hourly", "monthly_salary": None, "hourly_rate": 55,
        "scope_percent": 60, "tax_credit_points": 2.75, "pension_enrolled": False,
        "start_date": "2026-07-01",
    },
]

# Per-employee working pattern: (typical start hour, min shift hours, max shift hours, weekdays worked)
PROFILES = {
    "E1001": (9.0, 8.6, 10.5, WORKDAYS),
    "E1002": (8.5, 8.5, 9.5, WORKDAYS),
    "E1003": (8.75, 9.0, 11.0, WORKDAYS),
    "E1004": (9.5, 8.6, 11.5, WORKDAYS),
    "E1005": (8.0, 8.3, 9.0, WORKDAYS),
    "E1006": (7.5, 8.0, 10.0, WORKDAYS),
    "E1007": (7.0, 8.0, 10.5, WORKDAYS),
    "E1008": (12.0, 4.5, 6.0, {6, 1, 3}),  # Sun, Tue, Thu afternoons
}

# Deliberate events so the payroll and the review agent have something to find.
# Keyed by (employee_id, day-of-month). Applied only to DEFAULT_MONTH.
EVENTS = {
    ("E1001", 16): {"kind": "unreported"},                      # no report, no reason
    ("E1002", 7): {"kind": "sick"},
    ("E1002", 8): {"kind": "sick"},
    ("E1002", 9): {"kind": "sick"},
    ("E1004", 19): {"kind": "work", "clock_in": "10:00", "clock_out": "16:30",
                    "note": "Weekend production deployment"},  # Saturday
    ("E1004", 24): {"kind": "work", "clock_in": "08:30", "clock_out": "22:15",
                    "note": "Incident response"},
    ("E1005", 28): {"kind": "vacation"},
    ("E1005", 29): {"kind": "vacation"},
    ("E1005", 30): {"kind": "vacation"},
    ("E1006", 10): {"kind": "work", "clock_in": "07:42", "clock_out": None},  # forgot to clock out
    ("E1006", 4): {"kind": "work", "clock_in": "08:00", "clock_out": "13:00",
                   "note": "Friday on-call shift"},
    ("E1006", 18): {"kind": "work", "clock_in": "08:00", "clock_out": "13:00",
                    "note": "Friday on-call shift"},
    ("E1007", 15): {"kind": "work", "clock_in": "06:00", "clock_out": "19:20",
                    "note": "Inventory count"},
    ("E1007", 25): {"kind": "work", "clock_in": "07:00", "clock_out": "12:00"},  # Friday
    ("E1008", 22): {"kind": "work", "clock_in": "12:10", "clock_out": "11:50"},  # clock-out before clock-in
}


def _fmt(hours_from_midnight: float) -> str:
    minutes = int(round(hours_from_midnight * 60))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _random_shift(rng: random.Random, profile) -> tuple[str, str]:
    start_hour, min_len, max_len, _ = profile
    start = start_hour + rng.uniform(-0.4, 0.4)
    length = rng.uniform(min_len, max_len)
    # Round to the nearest 5 minutes, like a real time clock export would look.
    start = round(start * 12) / 12
    end = round((start + length) * 12) / 12
    return _fmt(start), _fmt(end)


def generate_attendance(month: str) -> dict:
    year, mon = map(int, month.split("-"))
    rng = random.Random(f"{SEED}-{month}")
    days_in_month = calendar.monthrange(year, mon)[1]
    apply_events = month == DEFAULT_MONTH

    records = {}
    for emp in EMPLOYEES:
        emp_id = emp["employee_id"]
        profile = PROFILES[emp_id]
        days = []
        for dom in range(1, days_in_month + 1):
            d = date(year, mon, dom)
            iso = d.isoformat()
            event = EVENTS.get((emp_id, dom)) if apply_events else None

            if event:
                if event["kind"] == "unreported":
                    continue
                entry = {"date": iso, "type": event["kind"], "clock_in": None,
                         "clock_out": None, "note": event.get("note")}
                if event["kind"] == "work":
                    entry["clock_in"] = event["clock_in"]
                    entry["clock_out"] = event["clock_out"]
                days.append(entry)
                continue

            if iso in HOLIDAYS:
                if d.weekday() in profile[3]:
                    days.append({"date": iso, "type": "holiday", "clock_in": None,
                                 "clock_out": None, "note": HOLIDAYS[iso]})
                continue
            if d.weekday() not in profile[3]:
                continue
            clock_in, clock_out = _random_shift(rng, profile)
            days.append({"date": iso, "type": "work", "clock_in": clock_in,
                         "clock_out": clock_out, "note": None})
        records[emp_id] = days

    return {
        "month": month,
        "exported_at": datetime(year, mon, days_in_month, 23, 0).isoformat(),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--month", default=DEFAULT_MONTH, help="YYYY-MM (default: %(default)s)")
    args = parser.parse_args()

    (DATA_DIR / "attendance").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "employees.json").write_text(json.dumps(EMPLOYEES, indent=2) + "\n")
    (DATA_DIR / "holidays.json").write_text(json.dumps(HOLIDAYS, indent=2) + "\n")
    out = DATA_DIR / "attendance" / f"{args.month}.json"
    out.write_text(json.dumps(generate_attendance(args.month), indent=2) + "\n")
    print(f"Wrote {len(EMPLOYEES)} employees, holidays, and attendance -> {out.relative_to(DATA_DIR.parent)}")


if __name__ == "__main__":
    main()
