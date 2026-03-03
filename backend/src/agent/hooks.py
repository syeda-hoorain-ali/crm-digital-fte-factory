"""RunHooks implementation for agent lifecycle tracking and observability."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from agents import RunHooks as BaseRunHooks, AgentHookContext, RunContextWrapper, Agent, Tool
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database.queries import create_agent_metric
from .context import CustomerSuccessContext

logger = logging.getLogger(__name__)


class RunHooks(BaseRunHooks):
    """
    Custom RunHooks implementation with lifecycle tracking and observability (T033).

    Provides structured logging, token usage tracking, and performance metrics
    for agent runs with database persistence.
    """

    def __init__(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        correlation_id: str | None = None,
    ):
        """
        Initialize RunHooks with database session and conversation context.

        Args:
            session: SQLAlchemy async session for database operations
            conversation_id: UUID of the conversation being processed
            correlation_id: Optional correlation ID for distributed tracing
        """
        self.session = session
        self.conversation_id = conversation_id
        self.correlation_id = correlation_id or str(conversation_id)

        # Track timing and metrics
        self.start_time: float | None = None
        self.end_time: float | None = None
        self.tool_call_count: int = 0
        self.tokens_used: int = 0

        logger.info(
            self._format_log(
                "RunHooks initialized",
                {
                    "conversation_id": str(conversation_id),
                    "correlation_id": self.correlation_id,
                },
            )
        )


    async def on_agent_start(
        self,
        context: AgentHookContext[CustomerSuccessContext],
        agent: Agent[CustomerSuccessContext],
    ) -> None:
        """Called before the agent is invoked. Called each time the current agent changes (T033).

        Args:
            context: The agent hook context.
            agent: The agent that is about to be invoked.
        """

        self.start_time = time.time()

        # Structured JSON logging with timestamps and correlation IDs (T034)
        logger.info(
            self._format_log(
                "Agent execution started",
                {
                    "agent_name": agent.name,
                    "conversation_id": str(self.conversation_id),
                    "correlation_id": self.correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        )


    async def on_agent_end(
        self,
        context: AgentHookContext[CustomerSuccessContext],
        agent: Agent[CustomerSuccessContext],
        output: Any,
    ) -> None:
        """Called when the agent produces a final output (T033).
        Extracts token usage from context.usage (T035) and populates
        AgentMetric with performance data (T036).

        Args:
            context: The agent hook context.
            agent: The agent that produced the output.
            output: The final output produced by the agent.
        """

        self.end_time = time.time()

        # Calculate latency
        latency_ms = (
            int((self.end_time - self.start_time) * 1000)
            if self.start_time
            else 0
        )

        # Extract token usage from context.usage (T035)
        tokens_used = context.usage.input_tokens + context.usage.output_tokens
        self.tokens_used = tokens_used
        
        # Calculate estimated cost (T036)
        estimated_cost = self._calculate_cost(tokens_used)

        # Determine success status
        success = not hasattr(output, "error") or output.error is None
        error_message = str(output.error) if hasattr(output, "error") and output.error else None

        # Structured JSON logging (T034)
        logger.info(
            self._format_log(
                "Agent execution completed",
                {
                    "agent_name": agent.name,
                    "conversation_id": str(self.conversation_id),
                    "correlation_id": self.correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": latency_ms,
                    "tokens_used": tokens_used,
                    "tool_call_count": self.tool_call_count,
                    "estimated_cost": estimated_cost,
                    "success": success,
                },
            )
        )

        # Populate AgentMetric in database (T036)
        try:
            await create_agent_metric(
                self.session,
                conversation_id=self.conversation_id,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                tool_call_count=self.tool_call_count,
                estimated_cost=estimated_cost,
                success=success,
                error_message=error_message,
            )
            logger.debug(
                f"AgentMetric created for conversation {self.conversation_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create AgentMetric for conversation {self.conversation_id}: {e}"
            )


    async def on_tool_start(
        self,
        context: RunContextWrapper[CustomerSuccessContext],
        agent: Agent,
        tool: Tool,
    ) -> None:
        """
        Called immediately before a local tool is invoked (T033).

        Args:
            context: The run hook context.
            agent: The agent that called the tool.
            tool: The tool that is being called.
        """
        self.tool_call_count += 1

        # Structured JSON logging (T034)
        logger.info(
            self._format_log(
                "Tool execution started",
                {
                    "tool_name": tool.name,
                    "conversation_id": str(self.conversation_id),
                    "correlation_id": self.correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tool_call_number": self.tool_call_count,
                },
            )
        )


    async def on_tool_end(
        self, 
        context: RunContextWrapper[CustomerSuccessContext],
        agent: Agent,
        tool: Tool,
        result: str,
    ) -> None:
        """
        Called immediately after a local tool is invoked (T033).

        Args:
            context: The run hook context.
            agent: The agent that called the tool.
            tool: The tool that is being called.
        """
        # Structured JSON logging (T034)
        logger.info(
            self._format_log(
                "Tool execution completed",
                {
                    "tool_name": tool.name,
                    "conversation_id": str(self.conversation_id),
                    "correlation_id": self.correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "output_preview": str(result)[:200],  # Truncate for logging
                },
            )
        )


    async def on_handoff(
        self,
        context: RunContextWrapper[CustomerSuccessContext],
        from_agent: Agent[CustomerSuccessContext],
        to_agent: Agent[CustomerSuccessContext],
    ) -> None:
        """
        Called when control is handed off between agents (T033).

        Args:
            context: The run hook context.
            from_agent: The agent that is handing off control.
            to_agent: The agent that is receiving control.
        """
        # Structured JSON logging (T034)
        logger.info(
            self._format_log(
                "Agent handoff",
                {
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "conversation_id": str(self.conversation_id),
                    "correlation_id": self.correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "context_preview": str(context)[:200],  # Truncate for logging
                },
            )
        )


    @staticmethod
    def _calculate_cost(tokens_used: int, model: str = settings.agent_model) -> float:
        """
        Calculate estimated cost based on token usage (T036).

        Uses GPT-4o pricing as default:
        - Input: $2.50 per 1M tokens
        - Output: $10.00 per 1M tokens
        - Simplified: Average $6.25 per 1M tokens

        Args:
            tokens_used: Total tokens used

        Returns:
            float: Estimated cost in USD
        """
        # Simplified cost calculation (average of input/output)
        cost_per_million_tokens = 6.25
        estimated_cost = (tokens_used / 1_000_000) * cost_per_million_tokens

        return round(estimated_cost, 6)  # Round to 6 decimal places


    def _format_log(self, message: str, data: dict[str, Any]) -> str:
        """
        Format structured JSON log message (T034).

        Args:
            message: Log message
            data: Structured data to include in log

        Returns:
            str: JSON-formatted log message
        """
        log_entry = {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self.correlation_id,
            **data,
        }

        try:
            return json.dumps(log_entry, default=str)
        except Exception as e:
            logger.warning(f"Failed to format log as JSON: {e}")
            return f"{message} | {data}"
