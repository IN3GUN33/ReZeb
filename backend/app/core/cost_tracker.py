"""LLM cost tracking: aggregate from DB, alert when approaching budget."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_monthly_cost(db: AsyncSession) -> float:
    """Sum total LLM cost in RUB for current calendar month."""
    control_sql = text("""
        SELECT COALESCE(SUM(cost_rub), 0) FROM control.sessions
        WHERE date_trunc('month', created_at) = date_trunc('month', now())
    """)
    pto_sql = text("""
        SELECT COALESCE(SUM(cost_rub), 0) FROM pto.queries
        WHERE date_trunc('month', created_at) = date_trunc('month', now())
    """)
    control_total = (await db.execute(control_sql)).scalar() or 0.0
    pto_total = (await db.execute(pto_sql)).scalar() or 0.0
    return float(control_total) + float(pto_total)


async def check_budget_alert(db: AsyncSession) -> dict:
    settings = get_settings()
    total = await get_monthly_cost(db)
    budget = settings.monthly_llm_budget_rub
    ratio = total / budget if budget > 0 else 0.0

    if ratio >= 1.0:
        logger.warning("budget_exceeded", total_rub=total, budget_rub=budget)
    elif ratio >= settings.budget_alert_threshold:
        logger.warning("budget_alert", total_rub=total, budget_rub=budget, ratio=round(ratio, 2))

    return {
        "total_rub": round(total, 2),
        "budget_rub": budget,
        "ratio": round(ratio, 3),
        "alert": ratio >= settings.budget_alert_threshold,
    }
