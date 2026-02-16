"""
Test script to verify the MCP server and backend agent integration
"""

import asyncio
import json
from http import HTTPStatus
from fastapi.testclient import TestClient
from src.main import app, crm_digital_fte_mcp_server
from src.agent.core.mcp import crm_digital_fte_mcp_server as mcp_server_instance


def test_api_endpoints():
    """Test the API endpoints to verify MCP server integration"""

    print("Testing API endpoints...")

    with TestClient(app) as client:
        # Test root endpoint
        response = client.get("/")
        print(f"Root endpoint: {response.status_code} - {response.json()}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert "message" in response.json(), f"Expected 'message' in response, got {response.json()}"

        # Test health endpoint
        response = client.get("/health")
        print(f"Health endpoint: {response.status_code} - {response.json()}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.json()["status"] == "healthy", f"Expected 'healthy', got {response.json()['status']}"

        # Test MCP search endpoint (this will try to use the MCP server)
        query = "Hey! My client is saying they can't see the 'Approve' button in the portal. Any idea why? I'm using the Pro plan."
        response = client.post("/process-query", params={"query": query})
        print(f"MCP search endpoint: {response.status_code}")
        print(response)
        if response.status_code != 200:
            print(f"MCP search error: {response.text}")
            response.raise_for_status()  # This will raise an exception for bad status codes
        else:
            result = response.json()
            print(f"MCP search result: {result}")

    print("API endpoint tests completed!")
