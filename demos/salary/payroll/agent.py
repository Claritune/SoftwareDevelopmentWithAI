"""
LangChain + OpenAI payroll review agent.

The agent pulls data from Hilanet through tools, runs the deterministic payroll
calculator (also a tool), and returns a structured SlipReview: a plain-language
summary for the employee plus an explanation and recommended action for every
anomaly. It never computes money itself — the harness verifies that.
"""

import os

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from payroll.calculator import calculate_payroll
from payroll.client import HilanetClient

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are a payroll review assistant for an HR team.
For the requested employee and month:
1. Call get_employee and get_attendance to see the source data from Hilanet.
2. Call calculate_payroll. It is the single source of truth for every amount.
3. Return a SlipReview.

Rules:
- Never calculate or adjust money yourself. Copy gross_pay and net_pay exactly from calculate_payroll.
- Write one anomaly_note for every anomaly with severity "warning" or "critical", using its exact date and code.
  You may also note "info" anomalies if they help the employee understand their pay. Do not invent anomalies.
- hr_attention_required is true if and only if there is at least one warning or critical anomaly.
- The summary is addressed to the employee: 2-4 short sentences, plain language, mention what drove pay up or down
  (overtime, rest-day work, sick days, unpaid zero-hour punches) without restating every line.
"""


class AnomalyNote(BaseModel):
    date: str = Field(description="YYYY-MM-DD, exactly as reported by calculate_payroll")
    code: str = Field(description="Anomaly code exactly as reported by calculate_payroll")
    explanation: str = Field(description="What happened, in one sentence")
    recommended_action: str = Field(description="Who should do what to resolve it")


class SlipReview(BaseModel):
    employee_id: str
    month: str
    gross_pay: float
    net_pay: float
    summary: str
    anomaly_notes: list[AnomalyNote]
    hr_attention_required: bool


def build_tools(client: HilanetClient):
    @tool
    def get_employee(employee_id: str) -> str:
        """Fetch an employee's master record (role, salary or hourly rate, scope, tax credit points) from Hilanet."""
        return client.get_employee(employee_id).model_dump_json()

    @tool
    def get_attendance(employee_id: str, month: str) -> str:
        """Fetch the employee's daily hours report (clock-in/out, sick, vacation, holiday) for month YYYY-MM."""
        return client.get_attendance(employee_id, month).model_dump_json()

    @tool("calculate_payroll")
    def run_payroll(employee_id: str, month: str) -> str:
        """Run the official payroll calculation for an employee and month YYYY-MM.
        Returns earnings, deductions, gross_pay, net_pay, hour totals and detected anomalies."""
        result = calculate_payroll(client.get_employee(employee_id),
                                   client.get_attendance(employee_id, month),
                                   client.get_holidays(month))
        return result.model_dump_json(exclude={"days", "employee"})

    return [get_employee, get_attendance, run_payroll]


class PayrollReviewAgent:
    def __init__(self, client: HilanetClient, model: str = DEFAULT_MODEL):
        llm = ChatOpenAI(model=model, temperature=0)
        self._agent = create_agent(llm, build_tools(client), system_prompt=SYSTEM_PROMPT,
                                   response_format=SlipReview)

    def review(self, employee_id: str, month: str, history: list | None = None,
               feedback: list[str] | None = None) -> tuple[SlipReview, list]:
        """Run the agent. Pass the previous `history` plus `feedback` to ask it to fix a rejected review."""
        if history and feedback:
            messages = history + [HumanMessage(
                "The harness rejected your SlipReview:\n- " + "\n- ".join(feedback)
                + "\nRe-check calculate_payroll and return a corrected SlipReview.")]
        else:
            messages = [HumanMessage(f"Review payroll for employee {employee_id}, month {month}.")]
        state = self._agent.invoke({"messages": messages})
        return state["structured_response"], state["messages"]

