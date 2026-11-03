"""Data models shared by the Hilanet client, the payroll calculator, the agent and the slip renderer."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class Employee(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    role: str
    department: str
    employment_type: Literal["monthly", "hourly"]
    monthly_salary: Decimal | None = None
    hourly_rate: Decimal | None = None
    scope_percent: int = 100
    tax_credit_points: Decimal = Decimal("2.25")
    pension_enrolled: bool = True
    start_date: date

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class AttendanceDay(BaseModel):
    date: date
    type: Literal["work", "sick", "vacation", "holiday"]
    clock_in: str | None = None
    clock_out: str | None = None
    note: str | None = None


class AttendanceReport(BaseModel):
    employee_id: str
    month: str
    exported_at: str
    days: list[AttendanceDay]


class DayBreakdown(BaseModel):
    date: date
    type: str
    hours_worked: Decimal = Decimal("0")
    regular_hours: Decimal = Decimal("0")
    overtime_125_hours: Decimal = Decimal("0")
    overtime_150_hours: Decimal = Decimal("0")
    rest_day_hours: Decimal = Decimal("0")
    note: str | None = None


class Anomaly(BaseModel):
    date: date
    code: Literal[
        "missing_clock_out", "invalid_punch", "long_shift",
        "unreported_workday", "rest_day_work", "sick_leave",
    ]
    detail: str
    severity: Literal["info", "warning", "critical"]


class PayLine(BaseModel):
    label: str
    quantity: Decimal | None = None  # hours or days, when meaningful
    rate: Decimal | None = None
    amount: Decimal


class PayrollResult(BaseModel):
    employee: Employee
    month: str
    hourly_rate: Decimal
    days: list[DayBreakdown]
    earnings: list[PayLine]
    deductions: list[PayLine]
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    totals: dict[str, Decimal] = Field(default_factory=dict)
    anomalies: list[Anomaly] = Field(default_factory=list)
