"""NTD RAG: fetch relevant clauses for a construction type + defect context."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ntd.service import NTDService


async def fetch_ntd_context(
    db: AsyncSession,
    construction_type: str | None,
    defect_types: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Return formatted NTD context string for use in LLM prompts."""
    if not construction_type and not defect_types:
        return "База НТД пуста или запрос не задан."

    parts = [construction_type or ""]
    if defect_types:
        parts.extend(defect_types[:3])
    query_text = " ".join(parts)

    service = NTDService(db)
    try:
        results = await service.search_clauses(query_text, top_k=top_k)
    except Exception:
        return "Нормативные требования временно недоступны."

    if not results:
        return "Релевантные нормативные требования не найдены."

    lines = []
    for r in results:
        lines.append(f"[{r['doc_code']} п.{r['clause_number']}] {r['text'][:300]}")
    return "\n\n".join(lines)
