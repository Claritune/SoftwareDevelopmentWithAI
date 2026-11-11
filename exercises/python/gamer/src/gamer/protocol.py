from typing import Any

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
