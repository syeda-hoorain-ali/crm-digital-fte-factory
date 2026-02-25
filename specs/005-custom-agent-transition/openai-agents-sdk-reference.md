# OpenAI Agents SDK Research & Implementation Patterns

**Feature**: 005-custom-agent-transition
**Date**: 2026-02-24
**Purpose**: Comprehensive reference for OpenAI Agents SDK implementation patterns

## Overview

This document consolidates all research findings and implementation patterns for OpenAI Agents SDK based on AgentFactory documentation. This serves as a permanent reference for implementing the Customer Success Agent after conversation compaction.

**Source**: AgentFactory documentation (https://github.com/panaversity/agentfactory)
- Chapter 34: OpenAI Agents SDK
- Chapter 40: FastAPI for Agents
- Chapter 44: Relational Databases with SQLModel

---

## 1. Core Execution Pattern: Agent → Runner → Result

### Concept
Every agent follows a three-part pattern that underlies everything in agent development.

### Pattern
```python
from agents import Agent, Runner

# 1. Define Agent
agent = Agent(
    name="Customer Success Agent",
    instructions="You are a helpful customer support agent...",
    model="gpt-4o"
)

# 2. Execute with Runner
result = Runner.run_sync(agent, "How do I reset my password?")

# 3. Extract Result
print(result.final_output)
```

### Async Pattern
```python
# For FastAPI integration
result = await Runner.run(agent, user_message)
response = result.final_output
```

### Key Points
- **Agent**: Defines what the agent is (name, instructions, model, tools)
- **Runner**: Executes the agent with user input
- **Result**: Contains final output and execution metadata
- Always use `Runner.run()` for async contexts (FastAPI)
- Use `Runner.run_sync()` only for synchronous scripts

---

## 2. Function Tools with @function_tool

### Concept
Tools give agents the ability to **do** things. The `@function_tool` decorator transforms Python functions into agent tools.

### Basic Tool Pattern
```python
from agents import function_tool

@function_tool
def search_knowledge_base(query: str) -> str:
    """Search knowledge base for relevant articles.

    Args:
        query: The search query from customer inquiry

    Returns:
        String describing relevant articles found
    """
    # Implementation
    results = perform_search(query)
    return f"Found {len(results)} articles: {', '.join(results)}"
```

### Critical Requirements
1. **Decorator**: Must use `@function_tool`
2. **Type hints**: Required for all parameters and return type
3. **Docstring**: Agent uses this to understand when to call the tool
4. **Return strings**: Tools should return human-readable strings, not complex objects
5. **Async support**: Use `async def` for async operations

### Async Tool Pattern
```python
@function_tool
async def identify_customer(email: str, phone: str) -> str:
    """Identify or create customer based on email/phone.

    Args:
        email: Customer email address
        phone: Customer phone number

    Returns:
        String confirming customer identification
    """
    async with get_session() as session:
        customer = await session.exec(
            select(Customer).where(Customer.email == email)
        )
        if customer:
            return f"Customer identified: {customer.id}"
        else:
            # Create new customer
            new_customer = Customer(email=email, phone=phone)
            session.add(new_customer)
            await session.commit()
            return f"New customer created: {new_customer.id}"
```

### Tool Registration
```python
from agents import Agent

# Register tools with agent
agent = Agent(
    name="Customer Success Agent",
    instructions="...",
    tools=[
        search_knowledge_base,
        identify_customer,
        analyze_sentiment,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response
    ]
)
```

---

## 3. Context Objects for State Management

### Concept
Context objects are Pydantic models that hold shared state accessible to every tool, handoff, and agent in your system. Context flows forward—mutations persist across tool calls.

### Context Definition Pattern
```python
from pydantic import BaseModel

class CustomerSuccessContext(BaseModel):
    """Context for Customer Success Agent state management."""
    # Customer identification
    customer_id: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None

    # Ticket tracking
    ticket_id: str | None = None

    # Sentiment analysis
    sentiment_score: float | None = None

    # Escalation state
    escalation_triggered: bool = False
    escalation_reason: str | None = None

    # Knowledge retrieval
    knowledge_articles_retrieved: list[str] = []

    # Channel information
    channel: str = "api"

    # Conversation history
    conversation_history: list[dict] = []
```

### Accessing Context in Tools
```python
from agents import function_tool, RunContextWrapper

@function_tool
async def identify_customer(
    email: str,
    phone: str,
    context: RunContextWrapper[CustomerSuccessContext]
) -> str:
    """Identify or create customer based on email/phone."""
    # Read from context
    current_channel = context.context.channel

    # Write to context (note the double .context)
    context.context.customer_email = email
    context.context.customer_phone = phone

    # Database lookup...
    customer_id = "CUST-123"
    context.context.customer_id = customer_id

    return f"Customer identified: {customer_id}"
```

### Critical Pattern: Double .context
- **Access context**: `context.context.field_name`
- **NOT**: `context.field_name` (this will fail)
- First `.context` is the wrapper, second `.context` is the actual context object

### Passing Context to Runner
```python
# Initialize context
ctx = CustomerSuccessContext(
    channel="api",
    conversation_history=[]
)

# Pass to runner
result = await Runner.run(
    agent,
    user_message,
    context=ctx  # Pass context here
)

# Context is mutated by tools during execution
print(ctx.customer_id)  # Now populated
print(ctx.sentiment_score)  # Now populated
```

---

## 4. Agent Configuration

### Full Agent Definition
```python
from agents import Agent

agent = Agent(
    name="Customer Success Agent",
    instructions="""You are a helpful customer support agent for CloudStream CRM.

    Your workflow:
    1. Analyze sentiment of customer message
    2. Identify or create customer record
    3. Create support ticket
    4. Search knowledge base for relevant articles
    5. Make escalation decision based on sentiment and context
    6. Format response for specified channel

    Always be empathetic, concise, and proactive.
    """,
    model="gpt-4o",  # or "gpt-4o-mini" for faster/cheaper
    tools=[
        analyze_sentiment,
        identify_customer,
        create_ticket,
        search_knowledge_base,
        escalate_to_human,
        send_response
    ]
)
```

### Model Selection
- **gpt-4o**: Best quality, slower, more expensive
- **gpt-4o-mini**: Good quality, faster, cheaper (recommended for production)
- **gpt-3.5-turbo**: Fastest, cheapest, lower quality

### Instructions Best Practices
1. **Be specific**: Clear instructions produce reliable agents
2. **Define workflow**: List steps the agent should follow
3. **Set persona**: Define tone and style
4. **Provide context**: Explain the agent's role and domain
5. **Keep concise**: Long instructions can confuse the agent

---

## 5. FastAPI Integration

### Endpoint Pattern
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents import Agent, Runner

app = FastAPI()

# Define request/response models
class ProcessInquiryRequest(BaseModel):
    message: str
    customer_email: str | None = None
    customer_phone: str | None = None
    channel: str = "api"

class ProcessInquiryResponse(BaseModel):
    response: str
    ticket_id: str
    sentiment_score: float | None
    escalated: bool

# Initialize agent once at startup
agent = Agent(
    name="Customer Success Agent",
    instructions="...",
    tools=[...]
)

@app.post("/agent/process", response_model=ProcessInquiryResponse)
async def process_inquiry(request: ProcessInquiryRequest):
    """Process customer inquiry through agent."""
    try:
        # Initialize context
        ctx = CustomerSuccessContext(
            customer_email=request.customer_email,
            customer_phone=request.customer_phone,
            channel=request.channel
        )

        # Run agent
        result = await Runner.run(
            agent,
            request.message,
            context=ctx
        )

        # Return response
        return ProcessInquiryResponse(
            response=result.final_output,
            ticket_id=ctx.ticket_id,
            sentiment_score=ctx.sentiment_score,
            escalated=ctx.escalation_triggered
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Lifespan Events
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database, load models, etc.
    print("Starting up...")
    await create_db_and_tables()

    yield

    # Shutdown: Cleanup resources
    print("Shutting down...")
    await dispose_engine()

app = FastAPI(lifespan=lifespan)
```

---

## 6. Error Handling

### Tool Error Handling
```python
@function_tool
async def search_knowledge_base(query: str) -> str:
    """Search knowledge base for relevant articles."""
    try:
        # Generate embedding
        embedding = generate_embedding(query)

        # Search database
        async with get_session() as session:
            results = await session.exec(
                select(KnowledgeBase)
                .order_by(KnowledgeBase.embedding.cosine_distance(embedding))
                .limit(5)
            )
            articles = results.all()

        if not articles:
            return "No relevant articles found in knowledge base."

        return f"Found {len(articles)} relevant articles: " + ", ".join(a.title for a in articles)

    except Exception as e:
        # Return error as string (agent will see this)
        return f"Error searching knowledge base: {str(e)}"
```

### Agent Execution Error Handling
```python
@app.post("/agent/process")
async def process_inquiry(request: ProcessInquiryRequest):
    try:
        result = await Runner.run(agent, request.message, context=ctx)
        return {"response": result.final_output}

    except TimeoutError:
        raise HTTPException(status_code=504, detail="Agent processing timeout")

    except Exception as e:
        # Log error for debugging
        logger.error(f"Agent execution failed: {e}")
        raise HTTPException(status_code=500, detail="Agent processing failed")
```

---

## 7. Testing Patterns

### Testing Tools
```python
import pytest
from agents import function_tool, RunContextWrapper

@pytest.mark.asyncio
async def test_identify_customer():
    """Test customer identification tool."""
    # Create mock context
    ctx = CustomerSuccessContext()
    wrapper = RunContextWrapper(ctx)

    # Call tool
    result = await identify_customer(
        email="test@example.com",
        phone="+1234567890",
        context=wrapper
    )

    # Assert result
    assert "Customer identified" in result or "New customer created" in result
    assert ctx.customer_email == "test@example.com"
    assert ctx.customer_id is not None
```

### Testing Agent Execution
```python
@pytest.mark.asyncio
async def test_agent_processes_inquiry():
    """Test agent processes customer inquiry end-to-end."""
    # Initialize context
    ctx = CustomerSuccessContext(
        customer_email="test@example.com",
        channel="api"
    )

    # Run agent
    result = await Runner.run(
        agent,
        "How do I reset my password?",
        context=ctx
    )

    # Assert response
    assert result.final_output is not None
    assert len(result.final_output) > 0

    # Assert context was updated
    assert ctx.customer_id is not None
    assert ctx.ticket_id is not None
    assert ctx.sentiment_score is not None
```

---

## 8. Custom Session Implementation with PostgreSQL

### Concept
Sessions enable conversation memory persistence across multiple agent runs. Instead of using SQLiteSession, we implement a custom PostgreSQL-backed session using the Message table as storage.

### SessionABC Protocol
```python
from agents.memory.session import SessionABC
from typing import List

class PostgreSQLSession(SessionABC):
    """Custom PostgreSQL session using Message table as storage."""

    def __init__(self, conversation_id: str, db_session):
        """Initialize session with conversation_id as session_id.

        Args:
            conversation_id: UUID of conversation (serves as session_id)
            db_session: Async database session for queries
        """
        self.conversation_id = conversation_id
        self.db_session = db_session

    async def get_items(self, limit: int | None = None) -> List[dict]:
        """Retrieve conversation history as EasyInputMessageParam items.

        Queries Message table by conversation_id, transforms to SDK format:
        - content: Message.content
        - role: customer→user, agent→assistant, system→system
        - phase: agent→"final_answer", user→None
        - type: "message"

        Returns:
            List of EasyInputMessageParam dicts ordered by created_at
        """
        query = select(Message).where(
            Message.conversation_id == self.conversation_id
        ).order_by(Message.created_at)

        if limit:
            query = query.limit(limit)

        result = await self.db_session.execute(query)
        messages = result.scalars().all()

        items = []
        for msg in messages:
            # Map business role to SDK role
            sdk_role = {
                "customer": "user",
                "agent": "assistant",
                "system": "system"
            }[msg.role]

            # Set phase for assistant messages
            phase = "final_answer" if msg.role == "agent" else None

            items.append({
                "content": msg.content,
                "role": sdk_role,
                "phase": phase,
                "type": "message"
            })

        return items

    async def add_items(self, items: List[dict]) -> None:
        """Store new items as Message records.

        Transforms EasyInputMessageParam items to Message records:
        - Extract content and role from item
        - Map SDK role to business role (user→customer, assistant→agent)
        - Derive direction from role (user→inbound, assistant→outbound)
        - Store with conversation_id FK

        Args:
            items: List of EasyInputMessageParam dicts from SDK
        """
        for item in items:
            # Map SDK role to business role
            business_role = {
                "user": "customer",
                "assistant": "agent",
                "system": "system"
            }[item["role"]]

            # Derive direction from role
            direction = "inbound" if item["role"] == "user" else "outbound"

            # Create Message record
            message = Message(
                conversation_id=self.conversation_id,
                content=item["content"],
                role=business_role,
                direction=direction,
                channel="api",  # Default, override if needed
                delivery_status="sent"
            )

            self.db_session.add(message)

        await self.db_session.commit()

    async def pop_item(self) -> dict | None:
        """Remove and return most recent message.

        Deletes most recent Message by conversation_id ordered by created_at DESC.
        Useful for "undo" functionality.

        Returns:
            EasyInputMessageParam dict of removed message, or None if empty
        """
        query = select(Message).where(
            Message.conversation_id == self.conversation_id
        ).order_by(Message.created_at.desc()).limit(1)

        result = await self.db_session.execute(query)
        message = result.scalar_one_or_none()

        if not message:
            return None

        # Transform to EasyInputMessageParam before deleting
        sdk_role = {
            "customer": "user",
            "agent": "assistant",
            "system": "system"
        }[message.role]

        phase = "final_answer" if message.role == "agent" else None

        item = {
            "content": message.content,
            "role": sdk_role,
            "phase": phase,
            "type": "message"
        }

        # Delete message
        await self.db_session.delete(message)
        await self.db_session.commit()

        return item

    async def clear_session(self) -> None:
        """No-op to preserve all message data.

        We never delete business data. To start fresh conversation,
        create new Conversation with new conversation_id instead.
        """
        pass  # Preserve all messages for audit trail
```

### Usage Pattern
```python
from agents import Agent, Runner

# Create session for conversation
session = PostgreSQLSession(
    conversation_id=str(conversation.id),
    db_session=db_session
)

# Run agent with session memory
result = await Runner.run(
    agent,
    user_message,
    session=session,
    context=context
)

# Session automatically loads previous messages and stores new ones
```

### Key Points
- **Dual Purpose**: Message table serves both business data and session memory
- **No Additional Storage**: Existing fields (content, role, created_at) provide all session data
- **Role Mapping**: Business roles (customer, agent, system) map to SDK roles (user, assistant, system)
- **Phase Field**: Set to "final_answer" for agent messages, None for user messages
- **clear_session()**: No-op to preserve audit trail - create new conversation instead
- **Isolation**: conversation_id provides natural session isolation

---

## 9. Tracing and Observability with RunHooks

### Concept
Production agents need observability to debug issues, track costs, and monitor performance. The SDK provides tracing to OpenAI dashboard and RunHooks for custom metrics collection.

### trace() Context Manager
```python
from agents import Agent, Runner, trace

async def process_customer_inquiry(
    conversation_id: str,
    user_message: str
):
    """Process inquiry with tracing for observability."""

    # Wrap agent run in trace with group_id for conversation linking
    with trace(
        workflow_name="Customer Support",
        group_id=conversation_id,  # Links all turns in conversation
        metadata={
            "channel": "api",
            "customer_tier": "premium"
        }
    ):
        result = await Runner.run(
            agent,
            user_message,
            session=session,
            context=context,
            hooks=hooks
        )

    return result.final_output
```

### RunHooks Implementation
```python
from agents import RunHooks, RunContextWrapper, Agent
from datetime import datetime
import time
import json

class ObservabilityHooks(RunHooks):
    """Lifecycle hooks for metrics collection and logging."""

    def __init__(self, db_session):
        self.db_session = db_session
        self.start_time = None
        self.conversation_id = None

    async def on_agent_start(
        self,
        context: RunContextWrapper,
        agent: Agent
    ) -> None:
        """Called when agent begins processing.

        Log structured JSON with timestamp and correlation ID.
        Track start time for latency calculation.
        """
        self.start_time = time.time()
        self.conversation_id = context.context.conversation_id

        log_entry = {
            "event": "agent_start",
            "agent": agent.name,
            "conversation_id": self.conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": self.conversation_id
        }
        print(json.dumps(log_entry))

    async def on_agent_end(
        self,
        context: RunContextWrapper,
        agent: Agent,
        output
    ) -> None:
        """Called when agent completes.

        Calculate latency, extract token usage, populate AgentMetric table.
        """
        latency_ms = int((time.time() - self.start_time) * 1000)

        # Extract token usage from result
        total_input_tokens = 0
        total_output_tokens = 0

        if hasattr(output, 'raw_responses'):
            for response in output.raw_responses:
                if hasattr(response, 'usage') and response.usage:
                    total_input_tokens += response.usage.input_tokens
                    total_output_tokens += response.usage.output_tokens

        # Calculate estimated cost (GPT-4o pricing)
        INPUT_COST_PER_M = 2.50
        OUTPUT_COST_PER_M = 10.00
        estimated_cost = (
            (total_input_tokens / 1_000_000) * INPUT_COST_PER_M +
            (total_output_tokens / 1_000_000) * OUTPUT_COST_PER_M
        )

        # Log completion
        log_entry = {
            "event": "agent_end",
            "agent": agent.name,
            "conversation_id": self.conversation_id,
            "latency_ms": latency_ms,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "estimated_cost": estimated_cost,
            "timestamp": datetime.utcnow().isoformat()
        }
        print(json.dumps(log_entry))

        # Populate AgentMetric table
        metrics = [
            AgentMetric(
                metric_name="tokens_used",
                metric_value=total_input_tokens + total_output_tokens,
                channel=context.context.channel,
                dimensions={"type": "total"}
            ),
            AgentMetric(
                metric_name="latency_ms",
                metric_value=latency_ms,
                channel=context.context.channel,
                dimensions={}
            ),
            AgentMetric(
                metric_name="estimated_cost",
                metric_value=estimated_cost,
                channel=context.context.channel,
                dimensions={"currency": "USD"}
            )
        ]

        for metric in metrics:
            self.db_session.add(metric)

        await self.db_session.commit()

    async def on_tool_start(
        self,
        context: RunContextWrapper,
        agent: Agent,
        tool
    ) -> None:
        """Called before tool execution."""
        tool_name = tool.name if hasattr(tool, 'name') else str(tool)

        log_entry = {
            "event": "tool_start",
            "tool": tool_name,
            "conversation_id": self.conversation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        print(json.dumps(log_entry))

    async def on_tool_end(
        self,
        context: RunContextWrapper,
        agent: Agent,
        tool,
        result: str
    ) -> None:
        """Called after tool execution."""
        tool_name = tool.name if hasattr(tool, 'name') else str(tool)

        log_entry = {
            "event": "tool_end",
            "tool": tool_name,
            "conversation_id": self.conversation_id,
            "result_length": len(result),
            "timestamp": datetime.utcnow().isoformat()
        }
        print(json.dumps(log_entry))

        # Track tool call count
        metric = AgentMetric(
            metric_name="tool_call_count",
            metric_value=1,
            channel=context.context.channel,
            dimensions={"tool": tool_name}
        )
        self.db_session.add(metric)
        await self.db_session.commit()

    async def on_handoff(
        self,
        context: RunContextWrapper,
        from_agent: Agent,
        to_agent: Agent
    ) -> None:
        """Called when control transfers between agents."""
        log_entry = {
            "event": "handoff",
            "from": from_agent.name,
            "to": to_agent.name,
            "conversation_id": self.conversation_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        print(json.dumps(log_entry))
```

### Complete Usage Pattern
```python
from agents import Agent, Runner, trace

async def process_with_observability(
    conversation_id: str,
    user_message: str,
    db_session
):
    """Process inquiry with full observability."""

    # Initialize session and hooks
    session = PostgreSQLSession(conversation_id, db_session)
    hooks = ObservabilityHooks(db_session)

    # Wrap in trace for OpenAI dashboard
    with trace(
        workflow_name="Customer Support",
        group_id=conversation_id
    ):
        result = await Runner.run(
            agent,
            user_message,
            session=session,
            context=context,
            hooks=hooks
        )

    return result.final_output
```

### Key Points
- **trace()**: Groups related agent runs, links multi-turn conversations with group_id
- **RunHooks**: Lifecycle callbacks for custom metrics and logging
- **Token Tracking**: Extract from result.raw_responses.usage
- **AgentMetric Population**: Store metrics in database via hooks
- **Structured Logging**: JSON format with timestamps and correlation IDs
- **Cost Calculation**: Track estimated costs based on token usage
- **OpenAI Dashboard**: Automatic tracing to platform.openai.com/traces

---

## 10. Common Mistakes and Solutions

### Mistake 1: Missing Docstrings
**Problem**: Agent doesn't know when to call tool
```python
@function_tool
def search_knowledge_base(query: str) -> str:
    # No docstring - agent won't understand this tool
    return perform_search(query)
```

**Solution**: Always include comprehensive docstring
```python
@function_tool
def search_knowledge_base(query: str) -> str:
    """Search knowledge base for relevant articles.

    Use this when customer asks product questions, how-to guides,
    or needs documentation.

    Args:
        query: The search query from customer inquiry

    Returns:
        String describing relevant articles found
    """
    return perform_search(query)
```

### Mistake 2: Wrong Context Access
**Problem**: Using single `.context` instead of double
```python
@function_tool
def identify_customer(email: str, context: RunContextWrapper[CustomerSuccessContext]) -> str:
    context.customer_email = email  # WRONG - will fail
    return "Done"
```

**Solution**: Use double `.context`
```python
@function_tool
def identify_customer(email: str, context: RunContextWrapper[CustomerSuccessContext]) -> str:
    context.context.customer_email = email  # CORRECT
    return "Done"
```

### Mistake 3: Returning Complex Objects
**Problem**: Tools return SQLModel objects or dicts
```python
@function_tool
async def get_customer(email: str) -> Customer:
    # Returns SQLModel object - not JSON serializable
    return await session.get(Customer, email)
```

**Solution**: Return human-readable strings
```python
@function_tool
async def get_customer(email: str) -> str:
    customer = await session.get(Customer, email)
    if customer:
        return f"Customer found: {customer.email}, Account tier: {customer.metadata.get('tier')}"
    return "Customer not found"
```

### Mistake 4: Not Passing Context to Runner
**Problem**: Context created but not passed
```python
ctx = CustomerSuccessContext()
result = await Runner.run(agent, message)  # Context not passed
```

**Solution**: Always pass context parameter
```python
ctx = CustomerSuccessContext()
result = await Runner.run(agent, message, context=ctx)  # CORRECT
```

### Mistake 5: Forgetting Async/Await
**Problem**: Using sync code in async context
```python
@function_tool
async def search_knowledge_base(query: str) -> str:
    results = session.exec(select(KnowledgeBase))  # Missing await
    return str(results)
```

**Solution**: Always await async operations
```python
@function_tool
async def search_knowledge_base(query: str) -> str:
    results = await session.exec(select(KnowledgeBase))  # CORRECT
    return str(results.all())
```

---

## 9. Best Practices

### Tool Design
1. **Single responsibility**: Each tool does one thing well
2. **Clear naming**: Tool name describes what it does
3. **Comprehensive docstrings**: Agent uses these to decide when to call
4. **Return strings**: Human-readable strings, not complex objects
5. **Error handling**: Return error messages as strings, don't raise exceptions
6. **Context updates**: Update context with important state changes

### Agent Instructions
1. **Define workflow**: List steps the agent should follow
2. **Set boundaries**: Explain what the agent should NOT do
3. **Provide examples**: Show example interactions
4. **Keep concise**: Long instructions can confuse the agent
5. **Test iteratively**: Refine instructions based on agent behavior

### Context Management
1. **Minimal state**: Only store what's needed across tool calls
2. **Clear naming**: Field names should be self-explanatory
3. **Default values**: Provide sensible defaults for all fields
4. **Type safety**: Use Pydantic for validation
5. **Documentation**: Document what each field represents

### Performance
1. **Connection pooling**: Reuse database connections
2. **Async operations**: Use async/await for I/O operations
3. **Batch operations**: Combine multiple database queries when possible
4. **Caching**: Cache frequently accessed data (embeddings, knowledge base)
5. **Model selection**: Use gpt-4o-mini for production (faster, cheaper)

---

## Summary

This document provides comprehensive implementation patterns for OpenAI Agents SDK based on AgentFactory documentation. Key takeaways:

1. **Agent → Runner → Result**: Core execution pattern
2. **@function_tool**: Decorator for creating agent tools
3. **Context objects**: Pydantic models for state management
4. **RunContextWrapper[T]**: Access context in tools with double `.context`
5. **Return strings**: Tools return human-readable strings
6. **Async by default**: Use async/await for all I/O operations
7. **FastAPI integration**: Standard endpoint patterns
8. **Error handling**: Return errors as strings, don't raise exceptions
9. **Testing**: Unit tests for tools, integration tests for agent

**Next Steps**: Use these patterns to implement the 6 tools and Customer Success Agent as defined in the implementation plan.

---

**References**:
- AgentFactory OpenAI Agents SDK: https://github.com/panaversity/agentfactory/tree/main/apps/learn-app/docs/05-Building-Custom-Agents/34-openai-agents-sdk
- OpenAI Agents SDK: https://github.com/openai/openai-agents-sdk
- Customer Support Capstone: https://github.com/panaversity/agentfactory/blob/main/apps/learn-app/docs/05-Building-Custom-Agents/34-openai-agents-sdk/10-capstone-customer-support-fte.md

**Last Updated**: 2026-02-24
**Version**: 1.1.0
