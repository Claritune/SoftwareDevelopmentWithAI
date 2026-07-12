from typing import Annotated

import aiosqlite
from fastapi import Depends, Request

from app.schemas.common import PaginationParams
from app.settings import Settings, get_settings


async def get_db(request: Request) -> aiosqlite.Connection:
    return request.app.state.db


def get_settings_dep() -> Settings:
    return get_settings()


DbConn = Annotated[aiosqlite.Connection, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
PaginationDep = Annotated[PaginationParams, Depends()]
