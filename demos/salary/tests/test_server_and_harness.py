import pytest
from fastapi.testclient import TestClient

import harness
from hilanet_mock.server import app
from payroll.agent import AnomalyNote, SlipReview
from payroll.calculator import calculate_payroll
from payroll.client import HilanetClient
from payroll.slip import render_slip

MONTH = "2026-09"


@pytest.fixture
def client() -> HilanetClient:
    return HilanetClient(http=TestClient(app))


def payroll_for(client, emp_id):
    return calculate_payroll(client.get_employee(emp_id), client.get_attendance(emp_id, MONTH),
                             client.get_holidays(MONTH))


def good_review(truth) -> SlipReview:
    return SlipReview(
        employee_id=truth.employee.employee_id, month=truth.month,
        gross_pay=float(truth.gross_pay), net_pay=float(truth.net_pay), summary="ok",
        anomaly_notes=[AnomalyNote(date=a.date.isoformat(), code=a.code, explanation="x", recommended_action="y")
                       for a in truth.anomalies if a.severity != "info"],
        hr_attention_required=any(a.severity != "info" for a in truth.anomalies))


# --- mock server ---

def test_api_key_required():
    assert TestClient(app).get("/api/v1/employees").status_code == 401


def test_employees_and_attendance(client):
    employees = client.list_employees()
    assert len(employees) == 8
    assert {e.employment_type for e in employees} == {"monthly", "hourly"}
    report = client.get_attendance("E1006", MONTH)
    assert any(d.clock_out is None for d in report.days if d.type == "work")


@pytest.mark.parametrize("path", ["/api/v1/employees/NOPE", "/api/v1/attendance/E1001?month=1999-01"])
def test_not_found(path):
    assert TestClient(app).get(path, headers={"X-API-Key": "hilanet-demo-key"}).status_code == 404


def test_sample_data_contains_planted_anomalies(client):
    expected = {"E1001": "unreported_workday", "E1004": "long_shift", "E1006": "missing_clock_out",
                "E1007": "long_shift", "E1008": "invalid_punch"}
    for emp_id, code in expected.items():
        assert code in {a.code for a in payroll_for(client, emp_id).anomalies}, emp_id


# --- harness validation ---

def test_validate_accepts_consistent_review(client):
    truth = payroll_for(client, "E1006")
    assert harness.validate_review(good_review(truth), truth) == []


def test_validate_rejects_wrong_money_missing_and_invented_notes(client):
    truth = payroll_for(client, "E1006")
    review = good_review(truth)
    review.net_pay += 100
    review.anomaly_notes = [AnomalyNote(date="2026-09-02", code="long_shift", explanation="", recommended_action="")]
    errors = harness.validate_review(review, truth)
    assert any("net_pay" in e for e in errors)
    assert any("missing note" in e and "missing_clock_out" in e for e in errors)
    assert any("does not match" in e for e in errors)


class StubAgent:
    """Returns a bad review first, then a good one — exercises the harness retry path."""

    def __init__(self, reviews):
        self.reviews, self.calls = list(reviews), []

    def review(self, employee_id, month, history=None, feedback=None):
        self.calls.append(feedback)
        return self.reviews.pop(0), ["msg"]


def test_run_review_retries_with_feedback(client):
    truth = payroll_for(client, "E1006")
    bad = good_review(truth).model_copy(update={"gross_pay": 1.0})
    agent = StubAgent([bad, good_review(truth)])
    review, attempts, errors = harness.run_review(agent, truth, verbose=False)
    assert review is not None and attempts == 2 and errors == []
    assert agent.calls[0] is None and "gross_pay" in agent.calls[1][0]


def test_run_review_gives_up_after_max_attempts(client):
    truth = payroll_for(client, "E1006")
    bad = good_review(truth).model_copy(update={"gross_pay": 1.0})
    review, attempts, errors = harness.run_review(StubAgent([bad, bad]), truth, verbose=False)
    assert review is None and attempts == harness.MAX_REVIEW_ATTEMPTS and errors


def test_slip_renders_review_notes(client):
    truth = payroll_for(client, "E1006")
    review = good_review(truth)
    review.anomaly_notes[0].recommended_action = "Ask Omer to submit a punch correction"
    html = render_slip(truth, review, attempts=1, model="test-model")
    assert "Omer Biton" in html and "₪9,404.25" in html
    assert "Ask Omer to submit a punch correction" in html and "validated by harness" in html
