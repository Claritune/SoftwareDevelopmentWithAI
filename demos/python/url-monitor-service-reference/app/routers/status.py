from app.dependencies import DbConn

from fastapi import APIRouter

from app.repositories import monitors as monitor_repo
from app.schemas.checks import MonitorSummary, StatusSummary
from app.schemas.monitors import MonitorStatus

router = APIRouter(prefix="/api/v1/status", tags=["status"])


@router.get("/summary", response_model=StatusSummary)
async def status_summary(conn: DbConn) -> StatusSummary:
    data = await monitor_repo.get_status_summary(conn)
    return StatusSummary(
        total=data["total"],
        up=data["up"],
        down=data["down"],
        unknown=data["unknown"],
        monitors=[
            MonitorSummary(
                id=m["id"],
                url=m["url"],
                status=MonitorStatus(m["status"]),
                consecutive_failures=m["consecutive_failures"],
            )
            for m in data["monitors"]
        ],
    )
