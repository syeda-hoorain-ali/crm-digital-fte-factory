import pytest
from collections.abc import AsyncGenerator
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session
from mcp.types import TextContent

from src.main import mcp


@pytest.fixture
def anyio_backend():
    # When using `trio`, `anyio_backend` should be set as `"trio"`.
    return "asyncio"


@pytest.fixture
async def client_session() -> AsyncGenerator[ClientSession]:
    # The `client` fixture creates a connected client that can be reused across multiple tests.
    async with create_connected_server_and_client_session(mcp, raise_exceptions=True) as _session:
        yield _session



@pytest.mark.anyio
async def test_call_search_knowledge_base_tool(client_session: ClientSession):
    result = await client_session.call_tool("search_knowledge_base", {"query": "test query"})
    # The result should be a valid response
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    # Check that output contains some kind of list or array structure since search returns a list
    assert '[' in output or output.startswith('{')  # Either a list or object with results


@pytest.mark.anyio
async def test_call_create_ticket_tool(client_session: ClientSession):
    result = await client_session.call_tool("create_ticket", {
        "customer_id": "customer_123",
        "issue": "Test issue description",
        "priority": "normal",
        "channel": "web_form"
    })

    # The result should be a valid response
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"ticket_id"' in output
    assert '"customer_id": "customer_123"' in output


@pytest.mark.anyio
async def test_call_get_customer_history_tool(client_session: ClientSession):
    result = await client_session.call_tool("get_customer_history", {"customer_id": "customer_123"})
    # The result should be a valid response
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"customer_id": "customer_123"' in output


@pytest.mark.anyio
async def test_call_escalate_to_human_tool(client_session: ClientSession):
    # First create a ticket to escalate
    create_result = await client_session.call_tool("create_ticket", {
        "customer_id": "customer_456",
        "issue": "Test issue for escalation",
        "priority": "normal",
        "channel": "web_form"
    })
    assert create_result is not None
    assert create_result.isError is False
    create_output = ''.join([part.text for part in create_result.content if isinstance(part, TextContent)])
    assert create_output
    assert '"ticket_id"' in create_output

    # Extract the ticket ID from the create result
    import json
    try:
        # Try to parse the JSON to extract ticket ID
        parsed_result = json.loads(create_output)
        ticket_id = parsed_result.get('ticket_id', '')
    except json.JSONDecodeError:
        # If parsing fails, try to extract using a regex or string manipulation
        import re
        ticket_match = re.search(r'"ticket_id"[^"]*"([^"]*)"', create_output)
        if ticket_match:
            ticket_id = ticket_match.group(1)
        else:
            # If we can't extract, we'll use a generic pattern - this shouldn't happen in practice
            ticket_id = "some_ticket_id"

    # Now escalate the ticket
    result = await client_session.call_tool("escalate_to_human", {
        "ticket_id": ticket_id,
        "reason": "Issue requires human attention"
    })
    # The result should be a valid response
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"escalation_id"' in output
    assert '"status": "escalated"' in output


@pytest.mark.anyio
async def test_call_send_response_tool(client_session: ClientSession):
    # First create a ticket to send response to
    create_result = await client_session.call_tool("create_ticket", {
        "customer_id": "customer_789",
        "issue": "Test issue for response",
        "priority": "normal",
        "channel": "web_form"
    })
    assert create_result is not None
    assert create_result.isError is False
    create_output = ''.join([part.text for part in create_result.content if isinstance(part, TextContent)])
    assert create_output
    assert '"ticket_id"' in create_output

    # Extract the ticket ID from the create result
    import json
    try:
        # Try to parse the JSON to extract ticket ID
        parsed_result = json.loads(create_output)
        ticket_id = parsed_result.get('ticket_id', '')
    except json.JSONDecodeError:
        # If parsing fails, try to extract using a regex or string manipulation
        import re
        ticket_match = re.search(r'"ticket_id"[^"]*"([^"]*)"', create_output)
        if ticket_match:
            ticket_id = ticket_match.group(1)
        else:
            # If we can't extract, we'll use a generic pattern - this shouldn't happen in practice
            ticket_id = "some_ticket_id"

    # Now send response to the ticket
    result = await client_session.call_tool("send_response", {
        "ticket_id": ticket_id,
        "message": "Thank you for contacting support.",
        "channel": "web_form"
    })
    # The result should be a valid response
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert f'"ticket_id": "{ticket_id}"' in output
    assert '"delivery_status": "sent"' in output


@pytest.mark.anyio
async def test_tool_list(client_session: ClientSession):
    # Get the list of available tools
    tools = await client_session.list_tools()
    tool_names = [tool.name for tool in tools.tools]

    # Verify all required tools are present
    required_tools = [
        "search_knowledge_base",
        "create_ticket",
        "get_customer_history",
        "escalate_to_human",
        "send_response"
    ]

    for tool_name in required_tools:
        assert tool_name in tool_names, f"Required tool '{tool_name}' not found in server"


@pytest.mark.anyio
async def test_server_health(client_session: ClientSession):
    # Test that the server is running and responsive
    # We should be able to call tools without getting connection errors
    result = await client_session.call_tool("search_knowledge_base", {"query": "health check"})
    assert result is not None
