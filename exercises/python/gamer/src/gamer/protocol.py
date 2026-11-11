from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

PROTOCOL_VERSION = 1


def envelope(type_: str, payload: Any) -> dict:
    return {"v": PROTOCOL_VERSION, "type": type_, "payload": payload}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def to_envelope(self) -> dict:
        return envelope("error", {"code": self.code, "message": self.message})


class GameNotFound(ApiError):
    def __init__(self, game_id: str) -> None:
        super().__init__(404, "game_not_found", f"Unknown game: {game_id}")


class BadRequest(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(400, "bad_request", message)


class NamePayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=32)


class NameRequest(BaseModel):
    v: Literal[1]
    type: str
    payload: NamePayload
