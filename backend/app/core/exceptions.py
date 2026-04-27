from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    status_code: int = 500
    error_type: str = "internal_error"
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    error_type = "not_found"
    detail = "Resource not found"


class ForbiddenError(AppError):
    status_code = 403
    error_type = "forbidden"
    detail = "Access denied"


class ValidationError(AppError):
    status_code = 422
    error_type = "validation_error"
    detail = "Validation failed"


class LimitExceededError(AppError):
    status_code = 429
    error_type = "limit_exceeded"
    detail = "Daily limit exceeded"


class MLServiceError(AppError):
    status_code = 502
    error_type = "ml_service_error"
    detail = "ML service unavailable"


class LLMError(AppError):
    status_code = 502
    error_type = "llm_error"
    detail = "LLM API error"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://rezeb.ru/errors/{exc.error_type}",
            "title": exc.error_type.replace("_", " ").title(),
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url),
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"https://rezeb.ru/errors/http_{exc.status_code}",
            "title": "HTTP Error",
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url),
        },
    )
