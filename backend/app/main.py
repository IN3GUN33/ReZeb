from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import sentry_sdk
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler, http_exception_handler
from app.core.logging import configure_logging, get_logger
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.control.router import router as control_router
from app.modules.ntd.router import router as ntd_router
from app.modules.pto.router import router as pto_router
from app.modules.test.router import router as test_router

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.auth.models import User

settings = get_settings()
configure_logging(settings.app_debug)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("startup", env=settings.app_env)
    # Ensure S3 buckets exist
    try:
        from app.modules.media.service import MediaService

        await MediaService().ensure_buckets()
    except Exception as exc:
        logger.warning("s3_init_failed", error=str(exc))

    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

    yield
    logger.info("shutdown")


app = FastAPI(
    title="ReZeb API",
    description="AI-powered SaaS platform for construction industry",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware ──────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.app_allowed_hosts)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next: Any) -> Any:  # noqa: ANN401

    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Exception handlers ──────────────────────────────────────────────────────

app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]

# ── Routers ─────────────────────────────────────────────────────────────────

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(control_router, prefix=API_PREFIX)
app.include_router(pto_router, prefix=API_PREFIX)
app.include_router(ntd_router, prefix=API_PREFIX)
app.include_router(audit_router, prefix=API_PREFIX)
app.include_router(test_router, prefix=API_PREFIX)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/admin/costs", tags=["admin"])
async def get_costs(
    current_user: User,
    db: AsyncSession,
) -> dict:
    from app.core.cost_tracker import check_budget_alert
    from app.modules.auth.models import UserRole

    if current_user.role not in (UserRole.superadmin, UserRole.org_admin):
        from app.core.exceptions import ForbiddenError

        raise ForbiddenError("Admin only")
    return await check_budget_alert(db)


@app.get("/", tags=["system"])
async def root() -> dict:
    return {"name": "ReZeb API", "docs": "/docs"}
