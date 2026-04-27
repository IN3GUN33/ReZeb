from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler, http_exception_handler
from app.core.logging import configure_logging, get_logger

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
        import sentry_sdk
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

    yield

    # Close arq pool on shutdown
    try:
        from app.core.queue import _pool
        if _pool:
            await _pool.close()
    except Exception:
        pass

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

from app.core.audit_middleware import AuditMiddleware
app.add_middleware(AuditMiddleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    import uuid
    import structlog
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

from app.modules.audit.router import router as audit_router
from app.modules.auth.admin_router import router as admin_router
from app.modules.auth.apikey_router import router as apikey_router
from app.modules.auth.profile_router import router as profile_router
from app.modules.auth.router import router as auth_router
from app.modules.control.router import router as control_router
from app.modules.ntd.router import router as ntd_router
from app.modules.projects.router import router as projects_router
from app.modules.pto.registry_router import router as pto_registry_router
from app.modules.pto.router import router as pto_router

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(apikey_router, prefix=API_PREFIX)
app.include_router(profile_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(projects_router, prefix=API_PREFIX)
app.include_router(control_router, prefix=API_PREFIX)
app.include_router(pto_router, prefix=API_PREFIX)
app.include_router(pto_registry_router, prefix=API_PREFIX)
app.include_router(ntd_router, prefix=API_PREFIX)
app.include_router(audit_router, prefix=API_PREFIX)


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Deep health check: DB + Redis connectivity."""
    checks: dict = {"status": "ok", "version": "0.1.0"}
    from app.db.session import engine
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc}"
        checks["status"] = "degraded"

    try:
        from app.core.ratelimit import get_redis
        r = get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc}"
        checks["status"] = "degraded"

    return checks


@app.get("/", tags=["system"])
async def root() -> dict:
    return {"name": "ReZeb API", "docs": "/docs"}
