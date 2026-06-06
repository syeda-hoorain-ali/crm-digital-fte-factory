"""Service for handling agent invocation and result processing."""

import logging
import time
from uuid import UUID

from agents import RunResult, Runner
from openai.types.responses import ResponseFunctionToolCall
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.customer_success_agent import customer_success_agent, CustomerSuccessContext
from ..agent.hooks import RunHooks
from ..agent.session import PostgresSession
from ..agent.structured_output import AgentStructuredOutput
from ..database.models import Channel, MessageRole, MessageDirection, TicketStatus
from ..database.queries import get_conversation
from ..database.queries.agent_metric import create_agent_metric
from ..database.queries.message import create_message, update_message, get_conversation_history
from ..database.queries.ticket import get_ticket_by_conversation, update_ticket
from ..kafka.schemas import ChannelMessage

logger = logging.getLogger(__name__)


class AgentInvocationService:
    """Service for invoking the customer success agent and processing results."""

    async def invoke_agent(
        self,
        session: AsyncSession,
        channel_message: ChannelMessage,
    ) -> str | None:
        """
        Invoke the customer success agent to process a message.

        Args:
            session: Database session
            channel_message: Parsed channel message

        Returns:
            Agent response text, or None if no response needed
        """
        start_time = time.time()
        conversation_id = None
        hooks = None

        try:
            # Validate message
            conversation_id = await self._validate_message(session, channel_message)
            if not conversation_id:
                return None

            # Setup agent context
            ctx, agent_session, hooks = await self._setup_agent_context(
                session, channel_message, conversation_id
            )

            # Execute agent
            logger.info(f"Invoking agent for message {channel_message.message_id}")
            result = await Runner.run(
                customer_success_agent,
                channel_message.body,
                session=agent_session,
                context=ctx,
                hooks=hooks,
            )

            # Extract and process agent result
            structured_output = result.final_output_as(AgentStructuredOutput)

            # Extract tool calls and metrics
            tool_calls = self._extract_tool_calls(result)
            tokens_used, latency_ms = self._extract_metrics(hooks)

            # Create agent message
            await self._create_agent_message(
                session,
                conversation_id,
                channel_message.channel,
                structured_output,
                tool_calls,
                tokens_used,
                latency_ms,
            )

            # Update customer message
            await self._update_customer_message(
                session, conversation_id, structured_output.sentiment_score
            )

            # Update ticket status
            await self._update_ticket_status(
                session, conversation_id, structured_output
            )

            await session.commit()

            logger.info(
                f"Agent completed for message {channel_message.message_id}",
                extra={
                    "message_id": channel_message.message_id,
                    "response_length": len(structured_output.response_message),
                    "escalated": structured_output.is_escalated,
                    "tokens_used": tokens_used,
                    "latency_ms": latency_ms,
                    "ticket_status": structured_output.ticket_status,
                    "sentiment_score": structured_output.sentiment_score,
                }
            )

            return structured_output.response_message

        except Exception as e:
            logger.error(f"Failed to invoke agent: {e}", exc_info=True)
            await self._handle_agent_failure(
                session, channel_message, conversation_id, start_time, hooks, e
            )
            return None

    async def _validate_message(
        self, session: AsyncSession, channel_message: ChannelMessage
    ) -> UUID | None:
        """
        Validate message has required fields and conversation exists.

        Args:
            session: Database session
            channel_message: Channel message to validate

        Returns:
            Conversation UUID if valid, None otherwise
        """
        if not channel_message.customer_id:
            logger.warning("No customer_id in message, skipping agent invocation")
            return None

        conversation_id_str = channel_message.metadata.get("conversation_id")
        if not conversation_id_str:
            logger.warning("No conversation_id in message metadata, skipping agent invocation")
            return None

        conversation_id = UUID(conversation_id_str)
        conversation = await get_conversation(session, conversation_id)

        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found")
            return None

        return conversation_id

    async def _setup_agent_context(
        self,
        session: AsyncSession,
        channel_message: ChannelMessage,
        conversation_id: UUID,
    ) -> tuple[CustomerSuccessContext, PostgresSession, RunHooks]:
        """
        Setup agent context, session, and hooks.

        Args:
            session: Database session
            channel_message: Channel message
            conversation_id: Conversation UUID

        Returns:
            Tuple of (context, agent_session, hooks)
        """
        # Determine customer contact based on channel
        customer_email = None
        customer_phone = None
        if channel_message.channel in (Channel.EMAIL, Channel.WEB_FORM):
            customer_email = channel_message.customer_contact
        elif channel_message.channel == Channel.WHATSAPP:
            customer_phone = channel_message.customer_contact

        # Create agent context
        ctx = CustomerSuccessContext(
            db_session=session,
            customer_id=channel_message.customer_id,
            customer_email=customer_email,
            customer_phone=customer_phone,
            channel=channel_message.channel.value,
            conversation_id=str(conversation_id),
        )

        # Create agent session for conversation memory
        agent_session = PostgresSession(
            session=session,
            conversation_id=conversation_id,
            channel=channel_message.channel,
        )

        # Create hooks for observability
        hooks = RunHooks(
            session=session,
            conversation_id=conversation_id,
            correlation_id=channel_message.message_id,
        )

        return ctx, agent_session, hooks

    def _extract_tool_calls(self, result: RunResult) -> list[dict]:
        """
        Extract tool calls from agent result.

        Args:
            result: Agent execution result

        Returns:
            List of tool call dictionaries
        """
        tool_calls_to_store = {}
        for item in result.new_items:
            if item.type == "tool_call_item" and isinstance(item.raw_item, ResponseFunctionToolCall):
                call_id = item.raw_item.call_id
                tool_calls_to_store[call_id] = {
                    "call_id": call_id,
                    "name": item.raw_item.name,
                    "arguments": item.raw_item.arguments,
                }
            if item.type == "tool_call_output_item" and isinstance(item.raw_item, dict):
                call_id = item.raw_item.get("call_id", "")
                if call_id in tool_calls_to_store:
                    tool_calls_to_store[call_id]["output"] = item.raw_item.get("output")

        logger.debug(f"Captured {len(tool_calls_to_store)} tool calls from agent session")
        return list(tool_calls_to_store.values())

    def _extract_metrics(self, hooks: RunHooks) -> tuple[int | None, int | None]:
        """
        Extract metrics from hooks.

        Args:
            hooks: RunHooks instance

        Returns:
            Tuple of (tokens_used, latency_ms)
        """
        tokens_used = hooks.tokens_used if hasattr(hooks, 'tokens_used') else None
        latency_ms = (
            int((hooks.end_time - hooks.start_time) * 1000)
            if hasattr(hooks, 'end_time') and hasattr(hooks, 'start_time')
            and hooks.end_time and hooks.start_time
            else None
        )
        return tokens_used, latency_ms

    async def _create_agent_message(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        channel: Channel,
        structured_output: AgentStructuredOutput,
        tool_calls: list[dict],
        tokens_used: int | None,
        latency_ms: int | None,
    ) -> None:
        """
        Create agent message with observability metrics.

        Args:
            session: Database session
            conversation_id: Conversation UUID
            channel: Message channel
            structured_output: Agent structured output
            tool_calls: List of tool calls
            tokens_used: Tokens used by agent
            latency_ms: Agent latency in milliseconds
        """
        agent_message = await create_message(
            session,
            conversation_id=conversation_id,
            role=MessageRole.AGENT,
            content=structured_output.response_message,
            direction=MessageDirection.OUTBOUND,
            channel=channel,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            tool_calls=tool_calls,
        )

        logger.info(
            f"Created agent message with observability metrics",
            extra={
                "message_id": str(agent_message.id),
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "tool_calls_count": len(tool_calls),
                "sentiment_score": structured_output.sentiment_score,
                "is_escalated": structured_output.is_escalated,
            }
        )

    async def _update_customer_message(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        sentiment_score: float,
    ) -> None:
        """
        Update customer message with sentiment and delivery status.

        Args:
            session: Database session
            conversation_id: Conversation UUID
            sentiment_score: Sentiment score from agent
        """
        messages = await get_conversation_history(session, conversation_id, limit=10)
        customer_message = None
        for msg in reversed(messages):
            if msg.role == MessageRole.CUSTOMER and msg.direction == MessageDirection.INBOUND:
                customer_message = msg
                break

        if customer_message:
            await update_message(
                session,
                customer_message.id,
                delivery_status="delivered"
            )
            # Update sentiment score on customer message
            customer_message.sentiment_score = sentiment_score
            logger.info(f"Updated customer message with sentiment score and delivery status")

    async def _update_ticket_status(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        structured_output: AgentStructuredOutput,
    ) -> None:
        """
        Update ticket status based on agent's structured output.

        Args:
            session: Database session
            conversation_id: Conversation UUID
            structured_output: Agent structured output
        """
        ticket = await get_ticket_by_conversation(session, conversation_id)
        if not ticket:
            return

        # Map string status to enum
        status_map = {
            "open": TicketStatus.OPEN,
            "in_progress": TicketStatus.IN_PROGRESS,
            "resolved": TicketStatus.RESOLVED,
            "closed": TicketStatus.CLOSED,
        }

        new_status = status_map.get(structured_output.ticket_status, TicketStatus.IN_PROGRESS)
        await update_ticket(
            session,
            ticket.id,
            status=new_status,
            resolution=structured_output.resolution_summary,
        )

        logger.info(
            f"Updated ticket status",
            extra={
                "ticket_id": str(ticket.id),
                "status": structured_output.ticket_status,
                "is_escalated": structured_output.is_escalated,
            }
        )

    async def _handle_agent_failure(
        self,
        session: AsyncSession,
        channel_message: ChannelMessage,
        conversation_id: UUID | None,
        start_time: float,
        hooks: RunHooks | None,
        error: Exception,
    ) -> None:
        """
        Handle agent execution failure.

        Args:
            session: Database session
            channel_message: Channel message
            conversation_id: Conversation UUID (may be None)
            start_time: Agent start time
            hooks: RunHooks instance (may be None)
            error: Exception that occurred
        """
        try:
            conversation_id_str = channel_message.metadata.get("conversation_id")
            if not conversation_id_str:
                logger.error("No conversation_id in metadata during error handling")
                return

            conversation_id = UUID(conversation_id_str)

            # Extract metrics from hooks if available (agent ran but failed)
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)

            tokens_used = 0
            tool_call_count = 0
            estimated_cost = 0.0

            if hooks:
                tokens_used = hooks.tokens_used if hasattr(hooks, 'tokens_used') else 0
                tool_call_count = hooks.tool_call_count if hasattr(hooks, 'tool_call_count') else 0
                if tokens_used > 0:
                    estimated_cost = hooks._calculate_cost(tokens_used)

            # Create failed agent metric
            await create_agent_metric(
                session,
                conversation_id=conversation_id,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                tool_call_count=tool_call_count,
                estimated_cost=estimated_cost,
                channel=channel_message.channel.value,
                success=False,
                error_message=str(error)[:500],  # Truncate error message
            )

            logger.info(
                f"Created failed agent metric for conversation {conversation_id}",
                extra={
                    "tokens_used": tokens_used,
                    "latency_ms": latency_ms,
                    "tool_call_count": tool_call_count,
                }
            )

            # Update customer message delivery status to failed
            messages = await get_conversation_history(session, conversation_id, limit=10)
            customer_message = None
            for msg in reversed(messages):
                if msg.role == MessageRole.CUSTOMER and msg.direction == MessageDirection.INBOUND:
                    customer_message = msg
                    break

            if customer_message:
                await update_message(
                    session,
                    customer_message.id,
                    delivery_status="failed"
                )
                logger.info(f"Updated customer message delivery status to failed")

            await session.commit()

        except Exception as cleanup_error:
            logger.error(
                f"Failed to create agent metric or update message status: {cleanup_error}",
                exc_info=True
            )
