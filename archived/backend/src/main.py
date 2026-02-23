import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.channels.channel_handler import run_channel_demo
from src.agent import crm_digital_fte_mcp_server, run_customer_success_demo
from src.settings import get_settings
from src.api.routes.agent_routes import router as agent_router


settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Connect to the MCP server when the app starts
        await crm_digital_fte_mcp_server.connect()
        print(f"MCP server connected at {settings.mcp_server_url}")
        yield

    finally:
        # Cleanup all MCP servers when the app stops
        await crm_digital_fte_mcp_server.cleanup()
        print("MCP server cleanup")


# Create the FastAPI app
app = FastAPI(
    title="CloudStream CRM Customer Success AI Agent API",
    description="API for the Customer Success AI Agent with MCP integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your frontend's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the agent routes
app.include_router(agent_router)

@app.get("/")
async def root():
    return {"message": "CloudStream CRM Customer Success AI Agent API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "mcp_configured": True}


def main():
    print("Starting CloudStream CRM Customer Success AI Agent - Specialization Stage")

    # Run the customer success demo
    # asyncio.run(run_customer_success_demo()) # Comment out fast api

    # Run the channel handler demo
    # asyncio.run(run_channel_demo()) # Comment out fast api

    # Start the FastAPI server
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
