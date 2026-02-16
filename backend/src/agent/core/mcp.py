from agents.mcp import MCPServerStreamableHttp
from src.settings import get_settings


settings = get_settings()

# Prepare headers with authentication if token is provided
headers = {
    "Content-Type": "application/json",
}

if settings.mcp_server_token:
    headers["Authorization"] = f"Bearer {settings.mcp_server_token}"

crm_digital_fte_mcp_server = MCPServerStreamableHttp(
    name="CRM-Digital-FTE-MCP-Server",
    params={
        "url": settings.mcp_server_url,
        "headers": headers,
        "timeout": 30.0,  # 30 second timeout
    },
    cache_tools_list=True,
    max_retry_attempts=3
)
