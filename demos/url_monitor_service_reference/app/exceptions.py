class AppError(Exception):
    def __init__(self, message: str, code: str, status: int):
        self.message = message
        self.code = code
        self.status = status


class NotFoundError(AppError):
    def __init__(self, resource: str, id: int | str):
        super().__init__(f"{resource} {id} not found", "NOT_FOUND", 404)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "CONFLICT", 409)
