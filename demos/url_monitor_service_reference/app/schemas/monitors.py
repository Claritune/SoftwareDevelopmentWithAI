from enum import Enum
from typing import TypedDict

from pydantic import BaseModel, HttpUrl


class MonitorStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    UP = "UP"
    DOWN = "DOWN"


class MonitorRow(TypedDict):
    id: int
    url: str
    display_name: str | None
    enabled: int
    check_interval_seconds: int
    timeout_seconds: int
    failure_threshold: int
    status: str
    consecutive_failures: int
    last_checked_at: str | None
    created_at: str
    updated_at: str


class MonitorCreate(BaseModel):
    url: HttpUrl
    display_name: str | None = None
    check_interval_seconds: int | None = None
    timeout_seconds: int | None = None
    failure_threshold: int | None = None
    enabled: bool = True


class MonitorUpdate(BaseModel):
    url: HttpUrl | None = None
    display_name: str | None = None
    check_interval_seconds: int | None = None
    timeout_seconds: int | None = None
    failure_threshold: int | None = None
    enabled: bool | None = None


class MonitorResponse(BaseModel):
    id: int
    url: str
    display_name: str | None
    enabled: bool
    check_interval_seconds: int
    timeout_seconds: int
    failure_threshold: int
    status: MonitorStatus
    consecutive_failures: int
    last_checked_at: str | None
    created_at: str
    updated_at: str


class PaginatedMonitors(BaseModel):
    items: list[MonitorResponse]
    total: int
    limit: int
    offset: int


def row_to_monitor_row(row) -> MonitorRow:
    return MonitorRow(
        id=row["id"],
        url=row["url"],
        display_name=row["display_name"],
        enabled=row["enabled"],
        check_interval_seconds=row["check_interval_seconds"],
        timeout_seconds=row["timeout_seconds"],
        failure_threshold=row["failure_threshold"],
        status=row["status"],
        consecutive_failures=row["consecutive_failures"],
        last_checked_at=row["last_checked_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_response(row: MonitorRow) -> MonitorResponse:
    return MonitorResponse(
        id=row["id"],
        url=row["url"],
        display_name=row["display_name"],
        enabled=bool(row["enabled"]),
        check_interval_seconds=row["check_interval_seconds"],
        timeout_seconds=row["timeout_seconds"],
        failure_threshold=row["failure_threshold"],
        status=MonitorStatus(row["status"]),
        consecutive_failures=row["consecutive_failures"],
        last_checked_at=row["last_checked_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
