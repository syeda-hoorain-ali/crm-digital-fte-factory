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
async def test_call_analyze_sentiment_tool(client_session: ClientSession):
    # Test positive sentiment
    result = await client_session.call_tool("analyze_sentiment", {
        "message_text": "I love this product! It works perfectly!"
    })
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"sentiment_score"' in output
    assert '"confidence"' in output
    assert '"sentiment_label"' in output

    # Test negative sentiment (escalation trigger)
    result = await client_session.call_tool("analyze_sentiment", {
        "message_text": "I am extremely frustrated and angry!"
    })
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"sentiment_label": "negative"' in output

    # Test empty string handling
    result = await client_session.call_tool("analyze_sentiment", {
        "message_text": ""
    })
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"sentiment_score": 0.5' in output  # Should return neutral


@pytest.mark.anyio
async def test_call_identify_customer_tool_with_email(client_session: ClientSession):
    """Test identify_customer with email only."""
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    result = await client_session.call_tool("identify_customer", {
        "email": email
    })
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"customer_id"' in output
    assert '"is_new": true' in output


@pytest.mark.anyio
async def test_call_identify_customer_tool_with_phone(client_session: ClientSession):
    """Test identify_customer with phone only."""
    import uuid
    phone = f"+1-555-{uuid.uuid4().hex[:4]}"

    result = await client_session.call_tool("identify_customer", {
        "phone": phone
    })
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"customer_id"' in output
    assert '"is_new": true' in output


@pytest.mark.anyio
async def test_call_identify_customer_tool_with_both(client_session: ClientSession):
    """Test identify_customer with both email and phone."""
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    phone = f"+1-555-{uuid.uuid4().hex[:4]}"

    result = await client_session.call_tool("identify_customer", {
        "email": email,
        "phone": phone
    })
    assert result is not None
    assert result.isError is False
    output = ''.join([part.text for part in result.content if isinstance(part, TextContent)])
    assert output
    assert '"customer_id"' in output
    assert '"is_new": true' in output


@pytest.mark.anyio
async def test_call_identify_customer_tool_existing_customer(client_session: ClientSession):
    """Test identify_customer finds existing customer."""
    import uuid
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    # Create customer
    result1 = await client_session.call_tool("identify_customer", {
        "email": email
    })
    assert result1 is not None
    assert result1.isError is False
    output1 = ''.join([part.text for part in result1.content if isinstance(part, TextContent)])
    assert '"is_new": true' in output1

    # Identify same customer
    result2 = await client_session.call_tool("identify_customer", {
        "email": email
    })
    assert result2 is not None
    assert result2.isError is False
    output2 = ''.join([part.text for part in result2.content if isinstance(part, TextContent)])
    assert '"is_new": false' in output2


@pytest.mark.anyio
async def test_call_identify_customer_tool_error_no_identifiers(client_session: ClientSession):
    """Test identify_customer error when no identifiers provided."""
    result = await client_session.call_tool("identify_customer", {})
    assert result is not None
    # Should return an error
    assert result.isError is True or "error" in ''.join([part.text for part in result.content if isinstance(part, TextContent)]).lower()


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
        "send_response",
        "analyze_sentiment",
        "identify_customer"
    ]

    for tool_name in required_tools:
        assert tool_name in tool_names, f"Required tool '{tool_name}' not found in server"


@pytest.mark.anyio
async def test_server_health(client_session: ClientSession):
    # Test that the server is running and responsive
    # We should be able to call tools without getting connection errors
    result = await client_session.call_tool("search_knowledge_base", {"query": "health check"})
    assert result is not None
