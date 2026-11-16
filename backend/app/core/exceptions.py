from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Exceção base de domínio da aplicação."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(self, detail: str, status_code: int | None = None, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class ConfigurationError(AppError):
    status_code = 500
    code = "configuration_error"


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"


def register_exception_handlers(app: FastAPI) -> None:
    """Registra manipuladores globais de exceções de domínio no FastAPI."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

