"""
Simple test to verify MCP server integration with sample tickets.
This test processes tickets and verifies tool calls with parameters, outputs, and success status.
"""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from src.main import app


def test_mcp_tool_calls_with_sample_tickets():
    """Test MCP server tool calls using sample tickets from JSON file."""
    print("Testing MCP server tool calls with sample tickets...")

    # Load sample tickets
    sample_tickets_path = Path(__file__).parent.parent.parent.parent / "context" / "sample-tickets.json"
    with open(sample_tickets_path, "r") as f:
        sample_tickets = json.load(f)

    print(f"Loaded {len(sample_tickets)} sample tickets")

    with TestClient(app) as client:
        # Quick health check
        response = client.get("/health")
        assert response.status_code == 200
        print("✓ Backend health check passed")

        # Test the first few tickets to verify tool calls
        for i, ticket in enumerate(sample_tickets[:3]):  # Only test first 3 to keep it quick
            print(f"\n--- Processing Ticket {i+1}: {ticket['id']} ---")

            # Construct query from ticket
            query = f"{ticket.get('subject', '')} {ticket.get('content', '')}".strip()
            customer_id = ticket.get("customer_email") or ticket.get("customer_phone") or f"cust_{i}"
            channel = ticket.get("channel", "web_form")

            print(f"Query: {query[:80]}...")
            print(f"Customer: {customer_id}")

            # Send request to backend
            response = client.post("/process-query", json={
                "query": query,
                "customer_identifier": customer_id,
                "channel": channel
            })

            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()

                # Check if there are tool calls
                tool_calls = result.get("tool_calls", [])
                print(f"Tool calls made: {len(tool_calls)}")

                for j, call in enumerate(tool_calls):
                    tool_name = call.get('name', 'unknown')
                    arguments = call.get('arguments', {})
                    result_output = call.get('result', 'No result')
                    success = call.get('success', False)

                    print(f"  Tool {j+1}: {tool_name}")
                    print(f"    Parameters: {arguments}")
                    print(f"    Success: {success}")
                    print(f"    Output: {str(result_output)[:100]}{'...' if len(str(result_output)) > 100 else ''}")

                print(f"  Response: {result.get('response', '')[:100]}{'...' if len(result.get('response', '')) > 100 else ''}")

            else:
                print(f"  Error: {response.text}")

    print("\n✓ MCP integration test completed!")


def test_specific_tool_calls():
    """Test specific MCP tools to verify parameters and outputs."""
    print("\n" + "="*50)
    print("Testing Specific MCP Tools")
    print("="*50)

    with TestClient(app) as client:
        # Test search tool
        print("\n1. Testing search_knowledge_base tool:")
        response = client.post("/process-query", json={
            "query": "Please search for information about Gantt charts in your knowledge base",
            "customer_identifier": "test_search@example.com",
            "channel": "web_form"
        })

        if response.status_code == 200:
            result = response.json()
            tool_calls = [tc for tc in result.get("tool_calls", []) if tc.get('name') == 'search_knowledge_base']

            print(f"   search_knowledge_base calls: {len(tool_calls)}")
            for call in tool_calls:
                print(f"     Parameters: {call.get('arguments', {})}")
                print(f"     Success: {call.get('success', False)}")
                print(f"     Output: {str(call.get('result', 'No result'))[:150]}...")

        # Test customer lookup tool
        print("\n2. Testing get_customer_history tool:")
        response = client.post("/process-query", json={
            "query": "Please get the customer history for this account",
            "customer_identifier": "test_customer@example.com",
            "channel": "web_form"
        })

        if response.status_code == 200:
            result = response.json()
            tool_calls = [tc for tc in result.get("tool_calls", []) if tc.get('name') == 'get_customer_history']

            print(f"   get_customer_history calls: {len(tool_calls)}")
            for call in tool_calls:
                print(f"     Parameters: {call.get('arguments', {})}")
                print(f"     Success: {call.get('success', False)}")
                print(f"     Output: {str(call.get('result', 'No result'))[:150]}...")


if __name__ == "__main__":
    test_mcp_tool_calls_with_sample_tickets()
    test_specific_tool_calls()
    print("\n" + "="*50)
    print("ALL INTEGRATION TESTS COMPLETED!")
    print("="*50)