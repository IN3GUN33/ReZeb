"""Telegram alerting for critical events."""
from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def send_alert(message: str) -> None:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_alert_chat_id:
        return

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={
                "chat_id": settings.telegram_alert_chat_id,
                "text": message,
                "parse_mode": "HTML",
            })
    except Exception as exc:
        logger.warning("telegram_alert_failed", error=str(exc))


async def alert_critical_defect(session_id: str, defect_type: str, construction_type: str) -> None:
    msg = (
        f"🚨 <b>КРИТИЧЕСКИЙ ДЕФЕКТ</b>\n"
        f"Сессия: <code>{session_id[:8]}</code>\n"
        f"Конструкция: {construction_type}\n"
        f"Дефект: {defect_type}\n"
        f"Требуется немедленное устранение!"
    )
    await send_alert(msg)


async def alert_budget(total_rub: float, budget_rub: float) -> None:
    pct = round(total_rub / budget_rub * 100)
    msg = (
        f"⚠️ <b>БЮДЖЕТ LLM: {pct}%</b>\n"
        f"Использовано: {total_rub:.0f} ₽ из {budget_rub:.0f} ₽\n"
        f"Текущий месяц"
    )
    await send_alert(msg)


async def alert_service_down(service: str, error: str) -> None:
    msg = f"🔴 <b>Сервис недоступен: {service}</b>\n{error}"
    await send_alert(msg)
