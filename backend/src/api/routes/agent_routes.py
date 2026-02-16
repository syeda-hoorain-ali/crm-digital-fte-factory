"""
API Routes for the Customer Success AI Agent with MCP Integration
"""

from fastapi import APIRouter, HTTPException
from agents import Runner, Agent, handoff
from src.agent import process_customer_query
from src.database.session_factory import create_session


# Create router instance
router = APIRouter()


from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    customer_identifier: str = "test-customer"
    channel: str = "web_form"


@router.post("/process-query")
async def process_customer_query_endpoint(request: QueryRequest):
    """Endpoint to process customer queries using the agent with MCP tools"""
    try:
        # Create an appropriate session for the customer based on environment
        session = create_session(request.customer_identifier)

        result = await process_customer_query(request.query, request.customer_identifier, request.channel, session)

        return {
            "success": True,
            "customer_identifier": request.customer_identifier,
            "channel": request.channel,
            "query": request.query,
            "response": result.final_output,
            "tool_calls": getattr(result, 'tool_calls', [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
