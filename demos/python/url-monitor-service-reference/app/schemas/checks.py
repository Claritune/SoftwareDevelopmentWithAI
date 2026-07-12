from pydantic import BaseModel

from app.schemas.monitors import MonitorStatus


class CheckResult(BaseModel):
    success: bool
    http_status: int | None
    response_time_ms: int
    error_message: str | None


class CheckResponse(BaseModel):
    id: int
    monitor_id: int
    checked_at: str
    http_status: int | None
    response_time_ms: int
    success: bool
    error_message: str | None


class TransitionResponse(BaseModel):
    id: int
    monitor_id: int
    transitioned_at: str
    from_status: MonitorStatus
    to_status: MonitorStatus
    check_id: int


class PaginatedChecks(BaseModel):
    items: list[CheckResponse]
    total: int
    limit: int
    offset: int


class PaginatedTransitions(BaseModel):
    items: list[TransitionResponse]
    total: int
    limit: int
    offset: int


class MonitorSummary(BaseModel):
    id: int
    url: str
    status: MonitorStatus
    consecutive_failures: int


class StatusSummary(BaseModel):
    total: int
    up: int
    down: int
    unknown: int
    monitors: list[MonitorSummary]
