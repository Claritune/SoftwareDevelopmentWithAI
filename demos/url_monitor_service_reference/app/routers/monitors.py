import aiosqlite
from fastapi import APIRouter

from app.dependencies import DbConn, PaginationDep, SettingsDep
from app.exceptions import ConflictError, NotFoundError
from app.repositories import checks as check_repo
from app.repositories import monitors as monitor_repo
from app.repositories import transitions as transition_repo
from app.schemas.checks import (
    CheckResponse,
    PaginatedChecks,
    PaginatedTransitions,
    TransitionResponse,
)
from app.schemas.monitors import (
    MonitorCreate,
    MonitorResponse,
    MonitorStatus,
    MonitorUpdate,
    PaginatedMonitors,
    row_to_response,
)

router = APIRouter(prefix="/api/v1/monitors", tags=["monitors"])


@router.post("", response_model=MonitorResponse, status_code=201)
async def create_monitor_endpoint(
    data: MonitorCreate,
    conn: DbConn,
    settings: SettingsDep,
) -> MonitorResponse:
    try:
        row = await monitor_repo.create_monitor(conn, data, settings)
    except aiosqlite.IntegrityError:
        raise ConflictError(f"Monitor with url {data.url} already exists")
    return row_to_response(row)


@router.get("", response_model=PaginatedMonitors)
async def list_monitors_endpoint(
    pagination: PaginationDep,
    conn: DbConn,
) -> PaginatedMonitors:
    items, total = await monitor_repo.list_monitors(conn, pagination.limit, pagination.offset)
    return PaginatedMonitors(
        items=[row_to_response(row) for row in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{monitor_id}", response_model=MonitorResponse)
async def get_monitor_endpoint(
    monitor_id: int,
    conn: DbConn,
) -> MonitorResponse:
    row = await monitor_repo.get_monitor(conn, monitor_id)
    if row is None:
        raise NotFoundError("Monitor", monitor_id)
    return row_to_response(row)


@router.patch("/{monitor_id}", response_model=MonitorResponse)
async def update_monitor_endpoint(
    monitor_id: int,
    data: MonitorUpdate,
    conn: DbConn,
) -> MonitorResponse:
    try:
        row = await monitor_repo.update_monitor(conn, monitor_id, data)
    except aiosqlite.IntegrityError:
        raise ConflictError(f"Monitor with url {data.url} already exists")
    if row is None:
        raise NotFoundError("Monitor", monitor_id)
    return row_to_response(row)


@router.delete("/{monitor_id}", status_code=204)
async def delete_monitor_endpoint(
    monitor_id: int,
    conn: DbConn,
) -> None:
    deleted = await monitor_repo.delete_monitor(conn, monitor_id)
    if not deleted:
        raise NotFoundError("Monitor", monitor_id)


@router.get("/{monitor_id}/checks", response_model=PaginatedChecks)
async def list_checks_endpoint(
    monitor_id: int,
    pagination: PaginationDep,
    conn: DbConn,
) -> PaginatedChecks:
    if await monitor_repo.get_monitor(conn, monitor_id) is None:
        raise NotFoundError("Monitor", monitor_id)
    rows, total = await check_repo.list_checks(
        conn, monitor_id, pagination.limit, pagination.offset
    )
    return PaginatedChecks(
        items=[
            CheckResponse(
                id=row["id"],
                monitor_id=row["monitor_id"],
                checked_at=row["checked_at"],
                http_status=row["http_status"],
                response_time_ms=row["response_time_ms"],
                success=bool(row["success"]),
                error_message=row["error_message"],
            )
            for row in rows
        ],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.get("/{monitor_id}/transitions", response_model=PaginatedTransitions)
async def list_transitions_endpoint(
    monitor_id: int,
    pagination: PaginationDep,
    conn: DbConn,
) -> PaginatedTransitions:
    if await monitor_repo.get_monitor(conn, monitor_id) is None:
        raise NotFoundError("Monitor", monitor_id)
    rows, total = await transition_repo.list_transitions(
        conn, monitor_id, pagination.limit, pagination.offset
    )
    return PaginatedTransitions(
        items=[
            TransitionResponse(
                id=row["id"],
                monitor_id=row["monitor_id"],
                transitioned_at=row["transitioned_at"],
                from_status=MonitorStatus(row["from_status"]),
                to_status=MonitorStatus(row["to_status"]),
                check_id=row["check_id"],
            )
            for row in rows
        ],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )
