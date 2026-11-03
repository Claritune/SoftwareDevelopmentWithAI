"""HTTP client for the (mock) Hilanet reporting API."""

import os

import httpx

from payroll.models import AttendanceReport, Employee

DEFAULT_URL = os.environ.get("HILANET_URL", "http://127.0.0.1:8085")
DEFAULT_API_KEY = os.environ.get("HILANET_API_KEY", "hilanet-demo-key")


class HilanetClient:
    def __init__(self, base_url: str = DEFAULT_URL, api_key: str = DEFAULT_API_KEY,
                 http: httpx.Client | None = None):
        # `http` lets tests pass a client bound to the FastAPI app (no network).
        self._http = http or httpx.Client(base_url=base_url.rstrip("/"), timeout=10.0)
        self._http.headers["X-API-Key"] = api_key

    def _get(self, path: str, **params):
        r = self._http.get(path, params=params or None)
        r.raise_for_status()
        return r.json()

    def health(self) -> bool:
        try:
            return self._http.get("/health").status_code == 200
        except httpx.HTTPError:
            return False

    def list_employees(self) -> list[Employee]:
        return [Employee(**e) for e in self._get("/api/v1/employees")]

    def get_employee(self, employee_id: str) -> Employee:
        return Employee(**self._get(f"/api/v1/employees/{employee_id}"))

    def get_attendance(self, employee_id: str, month: str) -> AttendanceReport:
        return AttendanceReport(**self._get(f"/api/v1/attendance/{employee_id}", month=month))

    def get_holidays(self, month: str) -> dict[str, str]:
        return self._get("/api/v1/holidays", month=month)
