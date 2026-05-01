"""PTO module: normalization → hybrid retrieval → reranking → LLM matching."""

from __future__ import annotations

import contextlib
import json
from typing import Any
from uuid import UUID

from rapidfuzz import fuzz
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.aitunnel import TokenUsage, chat_completion, get_embedding
from app.core.config import get_settings
from app.core.exceptions import LimitExceededError, NotFoundError
from app.core.logging import get_logger
from app.modules.auth.models import User
from app.modules.pto.models import MatchStatus, PTOQuery, RegistryItem
from app.modules.pto.prompts import (
    MATCHING_PROMPT,
    MATCHING_SYSTEM,
    NORMALIZATION_SYSTEM,
)

logger = get_logger(__name__)
settings = get_settings()

RRF_K = 60  # Reciprocal Rank Fusion constant


class PTOService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_query(
        self, user: User, raw_text: str, project_id: UUID | None = None
    ) -> PTOQuery:
        await self._check_daily_limit(user)
        query = PTOQuery(
            user_id=user.id, raw_text=raw_text, project_id=project_id, status="pending"
        )
        self.db.add(query)
        await self.db.flush()
        return query

    async def process_query(self, query_id: UUID) -> PTOQuery:
        """Full pipeline: normalize → retrieve → LLM match."""
        query = await self.db.get(PTOQuery, query_id)
        if not query:
            raise NotFoundError("Query not found")

        query.status = "processing"
        await self.db.commit()

        try:
            # Step 1: Haiku normalization
            normalized, norm_usage = await chat_completion(
                model=settings.model_fast,
                messages=[{"role": "user", "content": query.raw_text}],
                system=NORMALIZATION_SYSTEM,
                max_tokens=300,
                temperature=0.0,
            )
            query.normalized_text = normalized.strip()
            query.input_tokens += norm_usage.input_tokens
            query.output_tokens += norm_usage.output_tokens
            query.cached_tokens += norm_usage.cached_tokens
            query.cost_rub += norm_usage.cost_rub

            # Step 2: Hybrid retrieval (pgvector + FTS + RRF)
            candidates = await self._hybrid_search(query.normalized_text, top_k=10)

            # Step 3: LLM matching (Sonnet)
            match_result, match_usage = await self._llm_match(
                query.raw_text, query.normalized_text, candidates
            )

            query.input_tokens += match_usage.input_tokens
            query.output_tokens += match_usage.output_tokens
            query.cached_tokens += match_usage.cached_tokens
            query.cost_rub += match_usage.cost_rub

            query.match_status = MatchStatus(match_result.get("match_status", "not_found"))
            query.confidence = match_result.get("confidence", 0.0)
            query.results = [
                {
                    "registry_id": str(c.id),
                    "name": c.name,
                    "code": c.code,
                    "unit": c.unit,
                }
                for c in candidates[:5]
            ]

            best_id_str = match_result.get("best_match_id")
            if best_id_str:
                with contextlib.suppress(ValueError):
                    query.best_match_id = UUID(best_id_str)

            query.status = "completed"
            await self.db.commit()
            logger.info("pto_query_completed", query_id=str(query_id), status=query.match_status)
            return query

        except Exception as exc:
            query.status = "failed"
            await self.db.commit()
            logger.error("pto_query_failed", query_id=str(query_id), error=str(exc))
            raise

    async def get_query(self, query_id: UUID, user: User) -> PTOQuery:
        query = await self.db.get(PTOQuery, query_id)
        if not query or query.user_id != user.id:
            raise NotFoundError("Query not found")
        return query

    async def search_registry(self, q: str, limit: int = 20) -> list[RegistryItem]:
        items = await self._hybrid_search(q, top_k=limit)
        return items

    async def import_registry_from_excel(self, data: bytes, filename: str) -> dict[str, int]:
        """Import registry items from Excel. Deduplicates via RapidFuzz (threshold 0.92)."""
        import openpyxl

        wb = openpyxl.load_workbook(filename=__import__("io").BytesIO(data))
        ws = wb.active

        imported = skipped = errors = 0
        existing_names: list[str] = []

        # Load existing names for dedup
        stmt = select(RegistryItem.name_normalized).where(RegistryItem.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        existing_names = [r[0] or "" for r in result.fetchall()]

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            try:
                name = str(row[0]).strip()
                code = str(row[1]).strip() if len(row) > 1 and row[1] else None
                unit = str(row[2]).strip() if len(row) > 2 and row[2] else None
                category = str(row[3]).strip() if len(row) > 3 and row[3] else None

                # Fuzzy dedup
                if existing_names:
                    best_score = max(
                        fuzz.token_sort_ratio(name.lower(), e.lower()) for e in existing_names
                    )
                    if best_score >= 92:
                        skipped += 1
                        continue

                item = RegistryItem(
                    name=name, name_normalized=name.lower(), code=code, unit=unit, category=category
                )
                self.db.add(item)
                existing_names.append(name.lower())
                imported += 1

                if imported % 100 == 0:
                    await self.db.flush()

            except Exception:
                errors += 1

        await self.db.flush()
        logger.info("registry_import", imported=imported, skipped=skipped, errors=errors)
        return {"imported": imported, "skipped": skipped, "errors": errors}

    # ── Private ──────────────────────────────────────────────────────────────

    async def _hybrid_search(self, query_text: str, top_k: int = 10) -> list[RegistryItem]:
        """RRF fusion of pgvector cosine similarity + Postgres FTS."""
        # Vector search
        embedding = await get_embedding(query_text)
        vector_sql = text("""
            SELECT id, ROW_NUMBER() OVER (ORDER BY embedding <=> :emb) AS rn
            FROM pto.registry
            WHERE deleted_at IS NULL AND embedding IS NOT NULL
            ORDER BY embedding <=> :emb
            LIMIT :k
        """)
        vec_result = await self.db.execute(vector_sql, {"emb": str(embedding), "k": top_k * 2})
        vec_ranks: dict[str, int] = {str(r.id): r.rn for r in vec_result}

        # FTS search
        fts_sql = text("""
            SELECT id, ROW_NUMBER() OVER (ORDER BY ts_rank(fts_vector, query) DESC) AS rn
            FROM pto.registry, plainto_tsquery('russian', :q) AS query
            WHERE deleted_at IS NULL
              AND fts_vector IS NOT NULL
              AND fts_vector @@ query
            ORDER BY ts_rank(fts_vector, query) DESC
            LIMIT :k
        """)
        fts_result = await self.db.execute(fts_sql, {"q": query_text, "k": top_k * 2})
        fts_ranks: dict[str, int] = {str(r.id): r.rn for r in fts_result}

        # RRF fusion
        all_ids = set(vec_ranks) | set(fts_ranks)
        rrf_scores: dict[str, float] = {}
        for item_id in all_ids:
            score = 0.0
            if item_id in vec_ranks:
                score += 1.0 / (RRF_K + vec_ranks[item_id])
            if item_id in fts_ranks:
                score += 1.0 / (RRF_K + fts_ranks[item_id])
            rrf_scores[item_id] = score

        top_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:top_k]
        if not top_ids:
            return []

        stmt = select(RegistryItem).where(
            RegistryItem.id.in_([UUID(i) for i in top_ids]),
            RegistryItem.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        items = {str(item.id): item for item in result.scalars().all()}
        return [items[i] for i in top_ids if i in items]

    async def _llm_match(
        self,
        raw: str,
        normalized: str,
        candidates: list[RegistryItem],
    ) -> tuple[dict[str, Any], TokenUsage]:
        candidates_text = "\n".join(
            f"{i + 1}. [{item.id}] {item.name} (код: {item.code or '-'}, ед: {item.unit or '-'})"
            for i, item in enumerate(candidates[:5])
        )
        prompt = MATCHING_PROMPT.format(
            query=raw,
            normalized=normalized,
            candidates=candidates_text or "Кандидаты не найдены.",
        )
        raw_response, usage = await chat_completion(
            model=settings.model_vision,
            messages=[{"role": "user", "content": prompt}],
            system=MATCHING_SYSTEM,
            temperature=0.0,
            max_tokens=512,
        )
        # Parse JSON
        text = raw_response.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:-1])
        try:
            return json.loads(text), usage
        except json.JSONDecodeError:
            return {"match_status": "not_found", "confidence": 0.0}, usage

    async def _check_daily_limit(self, user: User) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        if user.daily_reset_at is None or user.daily_reset_at.date() < now.date():
            user.daily_pto_used = 0
            user.daily_reset_at = now

        if user.daily_pto_used >= settings.daily_pto_limit_per_user:
            raise LimitExceededError(
                f"Daily PTO limit ({settings.daily_pto_limit_per_user}) reached"
            )
        user.daily_pto_used += 1
