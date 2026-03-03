"""AgentMetric CRUD operations."""

import logging
from datetime import datetime
from typing import List
from uuid import UUID

from sqlmodel import col
from sqlalchemy import select, func, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    AgentMetric,
)

logger = logging.getLogger(__name__)


# ============================================================================
# AgentMetric CRUD Operations (T027)
# ============================================================================

async def create_agent_metric(
    session: AsyncSession,
    conversation_id: UUID,
    tokens_used: int,
    latency_ms: int,
    tool_call_count: int,
    estimated_cost: float,
    success: bool = True,
    error_message: str | None = None,
) -> AgentMetric:
    """
    Create a new agent performance metric.

    Args:
        session: Database session
        conversation_id: Conversation UUID
        tokens_used: Total tokens used
        latency_ms: Response latency in milliseconds
        tool_call_count: Number of tool calls made
        estimated_cost: Estimated cost in USD
        success: Whether the agent run was successful
        error_message: Error message if failed

    Returns:
        AgentMetric: Created metric instance
    """
    
    metric = AgentMetric(
        conversation_id=conversation_id,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        tool_call_count=tool_call_count,
        estimated_cost=estimated_cost,
        success=success,
        error_message=error_message,
    )
    session.add(metric)
    await session.flush()
    await session.refresh(metric)
    return metric


async def get_conversation_metrics(
    session: AsyncSession,
    conversation_id: UUID,
) -> List[AgentMetric]:
    """
    Get all metrics for a conversation.

    Args:
        session: Database session
        conversation_id: Conversation UUID

    Returns:
        List[AgentMetric]: List of metrics
    """
    stmt = (
        select(AgentMetric)
        .where(col(AgentMetric.conversation_id) == conversation_id)
        .order_by(col(AgentMetric.created_at).asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_aggregate_metrics(
    session: AsyncSession,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> dict:
    """
    Get aggregated performance metrics for a time period.

    Args:
        session: Database session
        start_date: Start of time period (optional)
        end_date: End of time period (optional)

    Returns:
        dict: Aggregated metrics (total_tokens, avg_latency, total_cost, etc.)
    """
    stmt = select(
        func.count(col(AgentMetric.id)).label("total_runs"),
        func.sum(col(AgentMetric.tokens_used)).label("total_tokens"),
        func.avg(col(AgentMetric.latency_ms)).label("avg_latency_ms"),
        func.sum(col(AgentMetric.estimated_cost)).label("total_cost"),
        func.sum(col(AgentMetric.tool_call_count)).label("total_tool_calls"),
        func.sum(func.cast(col(AgentMetric.success), Integer)).label("successful_runs"),
    )

    if start_date:
        stmt = stmt.where(col(AgentMetric.created_at) >= start_date)
    if end_date:
        stmt = stmt.where(col(AgentMetric.created_at) <= end_date)

    result = await session.execute(stmt)
    row = result.one()

    return {
        "total_runs": row.total_runs or 0,
        "total_tokens": row.total_tokens or 0,
        "avg_latency_ms": float(row.avg_latency_ms) if row.avg_latency_ms else 0.0,
        "total_cost": float(row.total_cost) if row.total_cost else 0.0,
        "total_tool_calls": row.total_tool_calls or 0,
        "successful_runs": row.successful_runs or 0,
        "success_rate": (
            float(row.successful_runs) / float(row.total_runs)
            if row.total_runs and row.successful_runs
            else 0.0
        ),
    }
