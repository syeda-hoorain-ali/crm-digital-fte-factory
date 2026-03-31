---
id: 0015
title: FastAPI app lifespan health endpoint
stage: green
date: 2026-02-25
surface: agent
model: claude-sonnet-4-6
feature: 005-custom-agent-transition
branch: 005-custom-agent-transition
user: developer
command: implementation
labels: ["fastapi", "health-check", "lifespan", "database", "api"]
links:
  spec: specs/005-custom-agent-transition/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - backend/src/main.py
  - specs/005-custom-agent-transition/tasks.md
tests:
  - None (integration tests planned in T093)
---

## Prompt

Create FastAPI application with lifespan events and health endpoint.

**Tasks**: T040-T041 - FastAPI application setup

**Context**: Phase 3 (User Story 1) - Setting up the web framework for the agent API.

**Requirements**:

**T040 - FastAPI application with lifespan:**
- Update `backend/src/main.py`
- Create FastAPI app with lifespan context manager
- In startup: log "Starting up...", initialize database connection
- In shutdown: log "Shutting down...", dispose database engine
- Add title, description, version to FastAPI app

**T041 - Health endpoint:**
- Implement GET /health endpoint
- Check database connectivity by running a simple query
- Return {"status": "healthy", "database": "connected"} on success
- Return {"status": "unhealthy", "database": "disconnected", "error": str(e)} on failure with 503 status

**Implementation pattern:**
```python
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from src.database.connection import engine, get_session
from sqlalchemy import text

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    yield
    # Shutdown
    print("Shutting down...")
    await engine.dispose()

app = FastAPI(
    title="Customer Success Agent API",
    description="Production-ready customer support agent with OpenAI Agents SDK",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )
```

**After completion**: Mark T040 and T041 as completed in specs/005-custom-agent-transition/tasks.md

Work in: backend

## Response snapshot

Created FastAPI application in `backend/src/main.py` with:

1. **Lifespan context manager** that handles:
   - Startup: Logs "Starting up..." and calls `init_db()` to initialize database connection with retry logic
   - Shutdown: Logs "Shutting down..." and calls `close_engine()` to cleanup connections
   - Error handling for database initialization failures

2. **FastAPI app instance** with:
   - Title: "Customer Success Agent API"
   - Description: "Production-ready customer support agent with OpenAI Agents SDK"
   - Version: "1.0.0"
   - Lifespan: Connected to the lifespan context manager

3. **Health check endpoint** (GET /health) that:
   - Executes `SELECT 1` query to verify database connectivity
   - Returns `{"status": "healthy", "database": "connected"}` on success
   - Returns 503 status with error details on failure
   - Logs errors for debugging

Marked T040 and T041 as completed in tasks.md.

## Outcome

- ✅ Impact: FastAPI application ready with database lifecycle management and health monitoring
- 🧪 Tests: None yet (integration tests planned in T093)
- 📁 Files: Created main.py, updated tasks.md
- 🔁 Next prompts: T042 (Create basic Customer Success Agent), T043 (POST /agent/process endpoint)
- 🧠 Reflection: Used existing `init_db()` and `close_engine()` functions from connection.py for proper database lifecycle management with retry logic

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Not applicable
- Prompt variant (if applicable): None
- Next experiment (smallest change to try): Test health endpoint with actual database connection
