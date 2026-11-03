"""
Mock Hilanet reporting server.

Serves the sample data in ./data over a small REST API that mimics an
attendance/HR export: employee master data, monthly hours reports, and holidays.
Every /api request needs the header  X-API-Key: <HILANET_API_KEY>.

Run:
  uv run uvicorn hilanet_mock.server:app --port 8085
  open http://127.0.0.1:8085/docs
"""

import json
import os
import re
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query

DATA_DIR = Path(__file__).parent / "data"
API_KEY = os.environ.get("HILANET_API_KEY", "hilanet-demo-key")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

app = FastAPI(title="Hilanet (mock)", version="1.0")


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


def _load_employees() -> list[dict]:
    return json.loads((DATA_DIR / "employees.json").read_text())


def _load_month(month: str) -> dict:
    if not MONTH_RE.match(month):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")
    path = DATA_DIR / "attendance" / f"{month}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No hours report exported for {month}")
    return json.loads(path.read_text())


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/employees", dependencies=[Depends(require_api_key)])
def list_employees() -> list[dict]:
    return _load_employees()


@app.get("/api/v1/employees/{employee_id}", dependencies=[Depends(require_api_key)])
def get_employee(employee_id: str) -> dict:
    for emp in _load_employees():
        if emp["employee_id"] == employee_id:
            return emp
    raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")


@app.get("/api/v1/attendance/{employee_id}", dependencies=[Depends(require_api_key)])
def get_attendance(employee_id: str, month: str = Query(..., description="YYYY-MM")) -> dict:
    get_employee(employee_id)  # 404 for unknown employees
    data = _load_month(month)
    return {
        "employee_id": employee_id,
        "month": month,
        "exported_at": data["exported_at"],
        "days": data["records"].get(employee_id, []),
    }


@app.get("/api/v1/holidays", dependencies=[Depends(require_api_key)])
def get_holidays(month: str = Query(..., description="YYYY-MM")) -> dict[str, str]:
    if not MONTH_RE.match(month):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")
    holidays = json.loads((DATA_DIR / "holidays.json").read_text())
    return {d: name for d, name in holidays.items() if d.startswith(month)}
