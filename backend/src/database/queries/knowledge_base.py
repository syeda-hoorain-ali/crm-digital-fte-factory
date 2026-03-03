"""KnowledgeBase CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from sqlmodel import col
from sqlalchemy import select, delete, cast as sa_cast
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector
from typing import cast

from ..models import (
    KnowledgeBase,
)

logger = logging.getLogger(__name__)


# ============================================================================
# KnowledgeBase CRUD Operations (T025)
# ============================================================================

async def create_knowledge_base_entry(
    session: AsyncSession,
    title: str,
    content: str,
    embedding: list[float],
    category: str | None = None,
    metadata: dict = {},
) -> KnowledgeBase:
    """
    Create a new knowledge base entry with vector embedding.

    Args:
        session: Database session
        title: Entry title
        content: Entry content
        embedding: Vector embedding for semantic search
        category: Entry category for classification
        metadata: Entry category for classification

    Returns:
        KnowledgeBase: Created knowledge base entry
    """
    entry = KnowledgeBase(
        title=title,
        content=content,
        embedding=embedding,
        category=category,
        meta_data=metadata,
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return entry


async def search_knowledge_base(
    session: AsyncSession,
    query_embedding: list[float],
    limit: int = 5,
    min_similarity: float = 0.7,
) -> List[tuple[KnowledgeBase, float]]:
    """
    Semantic search in knowledge base using vector similarity (T025).

    Args:
        session: Database session
        query_embedding: Query vector embedding
        limit: Maximum number of results
        min_similarity: Minimum cosine similarity threshold

    Returns:
        List[tuple[KnowledgeBase, float]]: List of (entry, similarity_score) tuples
    """
    import time
    start_time = time.time()

    try:
        # Calculate cosine similarity using pgvector
        similarity = sa_cast(KnowledgeBase.embedding, Vector).cosine_distance(query_embedding)

        stmt = (
            select(KnowledgeBase, (1 - similarity).label("similarity"))
            .where((1 - similarity) >= min_similarity)
            .order_by(similarity)
            .limit(limit)
        )

        result = await session.execute(stmt)
        results = [(row[0], row[1]) for row in result.all()]

        execution_time = (time.time() - start_time) * 1000
        logger.info(
            f"Searched knowledge base",
            extra={
                "operation": "search",
                "entity": "knowledge_base",
                "results_count": len(results),
                "limit": limit,
                "min_similarity": min_similarity,
                "execution_time_ms": round(execution_time, 2),
                "success": True,
            }
        )
        return results
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        logger.error(
            f"Failed to search knowledge base: {e}",
            extra={
                "operation": "search",
                "entity": "knowledge_base",
                "execution_time_ms": round(execution_time, 2),
                "success": False,
                "error": str(e),
            }
        )
        raise


async def get_knowledge_base_entry(
    session: AsyncSession,
    entry_id: UUID,
) -> KnowledgeBase | None:
    """
    Get knowledge base entry by ID.

    Args:
        session: Database session
        entry_id: Entry UUID

    Returns:
        KnowledgeBase | None: Entry instance or None if not found
    """
    stmt = select(KnowledgeBase).where(col(KnowledgeBase.id) == entry_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_knowledge_base_entry(
    session: AsyncSession,
    entry_id: UUID,
    title: str | None = None,
    content: str | None = None,
    embedding: list[float] | None = None,
    metadata: dict | None = None,
) -> KnowledgeBase | None:
    """
    Update knowledge base entry.

    Args:
        session: Database session
        entry_id: Entry UUID
        title: New title (optional)
        content: New content (optional)
        embedding: New embedding (optional)
        metadata: New metadata (optional)

    Returns:
        KnowledgeBase | None: Updated entry or None if not found
    """
    entry = await get_knowledge_base_entry(session, entry_id)

    if not entry:
        return None

    if title is not None:
        entry.title = title
    if content is not None:
        entry.content = content
    if embedding is not None:
        entry.embedding = embedding
    if metadata is not None:
        entry.meta_data = metadata

    entry.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(entry)
    return entry


async def delete_knowledge_base_entry(
    session: AsyncSession,
    entry_id: UUID,
) -> bool:
    """
    Delete knowledge base entry by ID.

    Args:
        session: Database session
        entry_id: Entry UUID

    Returns:
        bool: True if deleted, False if not found
    """
    stmt = delete(KnowledgeBase).where(col(KnowledgeBase.id) == entry_id)
    result = cast(CursorResult, await session.execute(stmt))
    return result.rowcount > 0
