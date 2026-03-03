"""Unit tests for agent hooks and callbacks."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, create_autospec
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.hooks import RunHooks
from src.agent.context import CustomerSuccessContext


# ============================================================================
# Tests for RunHooks (T082)
# ============================================================================

@pytest.mark.unit
@pytest.mark.hooks
class TestRunHooks:
    """Unit tests for RunHooks callbacks."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        return create_autospec(AsyncSession, instance=True)

    @pytest.fixture
    def conversation_id(self):
        """Create test conversation ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_on_agent_start_logs_execution(self, mock_session, conversation_id):
        """Test on_agent_start logs agent execution start."""
        hooks = RunHooks(
            session=mock_session,
            conversation_id=conversation_id,
        )

        mock_context = MagicMock()
        mock_agent = MagicMock()
        mock_agent.name = "Customer Success Agent"

        with patch("src.agent.hooks.logger") as mock_logger:
            await hooks.on_agent_start(mock_context, mock_agent)

            # Verify logging occurred
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_on_agent_end_creates_metrics(self, mock_session, conversation_id):
        """Test on_agent_end creates agent metrics."""
        hooks = RunHooks(
            session=mock_session,
            conversation_id=conversation_id,
        )

        mock_context = MagicMock()
        mock_context.usage.input_tokens = 100
        mock_context.usage.output_tokens = 50

        mock_agent = MagicMock()
        mock_agent.name = "Customer Success Agent"

        mock_output = MagicMock()

        with patch("src.agent.hooks.create_agent_metric", new_callable=AsyncMock) as mock_create_metric:
            await hooks.on_agent_end(mock_context, mock_agent, mock_output)

            # Verify metric was created
            mock_create_metric.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_tool_start_logs_execution(self, mock_session, conversation_id):
        """Test on_tool_start logs tool execution."""
        hooks = RunHooks(
            session=mock_session,
            conversation_id=conversation_id,
        )

        mock_context = MagicMock()
        mock_agent = MagicMock()
        mock_tool = MagicMock()
        mock_tool.name = "identify_customer"

        with patch("src.agent.hooks.logger") as mock_logger:
            await hooks.on_tool_start(mock_context, mock_agent, mock_tool)

            # Verify logging occurred
            mock_logger.info.assert_called()
            assert hooks.tool_call_count == 1

    @pytest.mark.asyncio
    async def test_on_tool_end_logs_completion(self, mock_session, conversation_id):
        """Test on_tool_end logs tool completion."""
        hooks = RunHooks(
            session=mock_session,
            conversation_id=conversation_id,
        )

        mock_context = MagicMock()
        mock_agent = MagicMock()
        mock_tool = MagicMock()
        mock_tool.name = "search_knowledge_base"
        tool_result = "Found 3 relevant articles"

        with patch("src.agent.hooks.logger") as mock_logger:
            await hooks.on_tool_end(mock_context, mock_agent, mock_tool, tool_result)

            # Verify logging occurred
            mock_logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_on_handoff_logs_agent_transition(self, mock_session, conversation_id):
        """Test on_handoff logs agent handoff."""
        hooks = RunHooks(
            session=mock_session,
            conversation_id=conversation_id,
        )

        mock_context = MagicMock()
        mock_from_agent = MagicMock()
        mock_from_agent.name = "Agent A"
        mock_to_agent = MagicMock()
        mock_to_agent.name = "Agent B"

        with patch("src.agent.hooks.logger") as mock_logger:
            await hooks.on_handoff(mock_context, mock_from_agent, mock_to_agent)

            # Verify logging occurred
            mock_logger.info.assert_called()
