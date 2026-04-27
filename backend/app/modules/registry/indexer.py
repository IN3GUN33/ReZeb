"""
Registry embedding indexer.
Run once after importing registry to build pgvector embeddings via AITUNNEL Batch API.
Usage: python -m app.modules.registry.indexer [--batch-size 100]
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


async def index_registry(batch_size: int = 50) -> None:
    from sqlalchemy import select, update
    from app.core.aitunnel import get_embeddings_batch
    from app.db.session import AsyncSessionFactory
    from app.modules.pto.models import RegistryItem

    total = 0
    async with AsyncSessionFactory() as db:
        # Get items without embeddings
        stmt = (
            select(RegistryItem)
            .where(RegistryItem.embedding.is_(None), RegistryItem.deleted_at.is_(None))
            .limit(10_000)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())
        print(f"Found {len(items)} items without embeddings")

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            texts = [item.name + (" " + item.name_normalized if item.name_normalized else "") for item in batch]
            try:
                embeddings = await get_embeddings_batch(texts)
                for item, emb in zip(batch, embeddings):
                    item.embedding = emb
                    total += 1
                await db.flush()
                print(f"Indexed {total}/{len(items)} items...")
            except Exception as exc:
                print(f"Batch {i} failed: {exc}", file=sys.stderr)

        await db.commit()
        print(f"Done. Total indexed: {total}")


if __name__ == "__main__":
    batch_size = 50
    if "--batch-size" in sys.argv:
        idx = sys.argv.index("--batch-size")
        batch_size = int(sys.argv[idx + 1])
    asyncio.run(index_registry(batch_size))
