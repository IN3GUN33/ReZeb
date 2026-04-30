"""arq background worker for heavy tasks (CV inference, LLM processing)."""

from uuid import UUID

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)
settings = get_settings()


async def startup(ctx: dict) -> None:
    configure_logging(settings.app_debug)
    from app.db.session import AsyncSessionFactory

    ctx["db_factory"] = AsyncSessionFactory
    logger.info("worker_started")


async def shutdown(ctx: dict) -> None:
    logger.info("worker_stopped")


async def process_control_session(ctx: dict, session_id: str) -> None:
    """Process a control inspection session (CV → LLM)."""
    from app.modules.control.service import ControlService

    async with ctx["db_factory"]() as db:
        service = ControlService(db)
        await service.process_session(UUID(session_id))
        logger.info("worker_control_done", session_id=session_id)


async def process_pto_query(ctx: dict, query_id: str) -> None:
    """Process a PTO matching query (normalize → search → LLM)."""
    from app.modules.pto.service import PTOService

    async with ctx["db_factory"]() as db:
        service = PTOService(db)
        await service.process_query(UUID(query_id))
        logger.info("worker_pto_done", query_id=query_id)


async def send_email_task(
    ctx: dict, subject: str, recipient: str, template_name: str, context: dict
) -> None:
    from app.core.email import send_email

    await send_email(subject, recipient, template_name, context)


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_queue_url)
    functions = [process_control_session, process_pto_query, send_email_task]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 300  # 5 min per job
