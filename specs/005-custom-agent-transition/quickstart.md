# Quickstart Guide: Customer Success Agent Production Migration

**Feature**: 005-custom-agent-transition
**Date**: 2026-02-24
**Phase**: 1 - Design Artifacts

## Overview

This guide provides step-by-step instructions for setting up and running the Customer Success Agent production system. Follow these steps to migrate from incubation infrastructure to production infrastructure.

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.12+** installed
- **UV package manager** installed (`pip install uv`)
- **Neon PostgreSQL account** (free tier available at https://neon.tech)
- **OpenAI API key** (for agent execution)
- **Git** for version control
- **Access to incubation codebase** (mcp-server, skills) for reference

---

## Step 1: Clone Repository

```bash
git clone https://github.com/syeda-hoorain-ali/crm-digital-fte.git
cd crm-digital-fte
git checkout 005-custom-agent-transition
```

---

## Step 2: Install Dependencies

Navigate to the backend directory and install all dependencies using UV:

```bash
cd backend
uv sync
```

This will install:
- FastAPI (web framework)
- OpenAI Agents SDK (agent runtime)
- SQLModel (ORM)
- asyncpg (PostgreSQL driver)
- Alembic (migrations)
- FastEmbed (embeddings)
- pgvector (vector search)
- pytest (testing)
- And all other dependencies from pyproject.toml

**Verify installation:**
```bash
uv run python --version  # Should show Python 3.12+
uv run python -c "import fastapi; print(fastapi.__version__)"
```

---

## Step 3: Configure Environment Variables

Create a `.env` file in the backend directory:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require

# OpenAI Configuration
OPENAI_API_KEY=sk-proj-...

# Embedding Configuration (optional - uses FastEmbed defaults)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Application Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
```

**Get your Neon connection string:**
1. Go to https://neon.tech
2. Create a new project (or use existing)
3. Copy the connection string from the dashboard
4. Replace `postgresql://` with `postgresql+asyncpg://` for async support

**Get your OpenAI API key:**
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy and paste into `.env`

---

## Step 4: Initialize Database

### 4.1 Initialize Alembic

If Alembic is not already initialized:

```bash
cd backend
alembic init -t async alembic
```

### 4.2 Configure Alembic

Edit `alembic/env.py` to import all models:

```python
# Add at the top
from src.database.models import *
from sqlmodel import SQLModel

# Set target_metadata
target_metadata = SQLModel.metadata
```

Edit `alembic.ini` to use environment variable for database URL:

```ini
# Replace this line:
sqlalchemy.url = driver://user:pass@localhost/dbname

# With this:
sqlalchemy.url = postgresql+asyncpg://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

### 4.3 Create Initial Migration

Generate the initial migration with all tables:

```bash
alembic revision --autogenerate -m "Initial schema with pgvector"
```

**Review the generated migration** in `alembic/versions/xxx_initial_schema.py`:
- Verify all 6 tables are created (customer, ticket, message, escalation, knowledge_base, response)
- Ensure pgvector extension is enabled
- Check that vector index is created on knowledge_base.embedding

### 4.4 Apply Migration

Run the migration to create all tables:

```bash
alembic upgrade head
```

**Verify tables were created:**
```bash
# Connect to Neon database via psql or Neon console
# Run: \dt
# Should see: customer, ticket, message, escalation, knowledge_base, response
```

---

## Step 5: Migrate Knowledge Base

Run the one-time migration script to load knowledge base articles with embeddings:

```bash
cd backend
uv run scripts/migrate_knowledge_base.py
```

This script will:
1. Load all markdown files from `mcp-server/context/`
2. Generate embeddings using FastEmbed (all-MiniLM-L6-v2)
3. Insert articles into `knowledge_base` table with vector embeddings
4. Create HNSW index for fast similarity search

**Expected output:**
```
Found 47 markdown files to migrate
Migrated: Password Reset Guide
Migrated: Login Troubleshooting
Migrated: Billing FAQ
...
Migration complete! 47 articles migrated.
```

**Verify migration:**
```sql
-- Connect to database
SELECT COUNT(*) FROM knowledge_base;
-- Should return number of migrated articles

SELECT title, category FROM knowledge_base LIMIT 5;
-- Should show article titles
```

---

## Step 6: Run Development Server

Start the FastAPI development server:

```bash
cd backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify server is running:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-02-24T10:30:00Z"
}
```

---

## Step 7: Test Agent Processing

Test the agent with a sample customer inquiry:

```bash
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I reset my password?",
    "customer_email": "test@example.com",
    "channel": "api"
  }'
```

**Expected response:**
```json
{
  "response": "I can help you reset your password. Here are the steps: 1) Go to the login page, 2) Click 'Forgot Password', 3) Enter your email address, 4) Check your email for a reset link. The link will be valid for 24 hours.",
  "ticket_id": "TKT-2024-001",
  "sentiment_score": 0.0,
  "escalated": false,
  "knowledge_articles": ["Password Reset Guide"]
}
```

---

## Step 8: Run Tests

Run the test suite to verify everything is working:

```bash
cd backend
uv run pytest
```

**Expected output:**
```
============================= test session starts ==============================
collected 25 items

tests/test_agent.py ........                                             [ 32%]
tests/test_tools.py .........                                            [ 68%]
tests/test_database.py ....                                              [ 84%]
tests/test_api.py ....                                                   [100%]

============================== 25 passed in 12.34s ==============================
```

**Run tests with coverage:**
```bash
uv run pytest --cov=src --cov-report=html
```

**View coverage report:**
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

---

## Step 9: Explore API Documentation

FastAPI automatically generates interactive API documentation:

**Swagger UI:**
```
http://localhost:8000/docs
```

**ReDoc:**
```
http://localhost:8000/redoc
```

Use the Swagger UI to:
- Test API endpoints interactively
- View request/response schemas
- See example requests and responses

---

## Common Issues and Troubleshooting

### Issue: Database connection fails

**Symptoms:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**
1. Verify DATABASE_URL in `.env` is correct
2. Ensure connection string uses `postgresql+asyncpg://` (not `postgresql://`)
3. Check Neon project is active (not suspended)
4. Verify `?sslmode=require` is in connection string
5. Test connection with psql: `psql "postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require"`

### Issue: OpenAI API key invalid

**Symptoms:**
```
openai.error.AuthenticationError: Incorrect API key provided
```

**Solutions:**
1. Verify OPENAI_API_KEY in `.env` is correct
2. Check API key has not expired
3. Ensure API key starts with `sk-proj-` or `sk-`
4. Test API key: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`

### Issue: pgvector extension not found

**Symptoms:**
```
sqlalchemy.exc.ProgrammingError: type "vector" does not exist
```

**Solutions:**
1. Verify pgvector extension is enabled in Neon
2. Run migration again: `alembic upgrade head`
3. Manually enable extension: `CREATE EXTENSION IF NOT EXISTS vector;`
4. Check Neon project supports pgvector (all projects do by default)

### Issue: FastEmbed model download fails

**Symptoms:**
```
FileNotFoundError: Model not found
```

**Solutions:**
1. Ensure internet connection is available
2. Model will download on first use (~90MB)
3. Check disk space (need ~500MB free)
4. Manually download: `python -c "from fastembed import TextEmbedding; TextEmbedding()"`

### Issue: Tests fail with "database not found"

**Symptoms:**
```
pytest: sqlalchemy.exc.OperationalError: database "test_db" does not exist
```

**Solutions:**
1. Tests use same database as development (for now)
2. Ensure DATABASE_URL in `.env` points to valid database
3. Run migrations: `alembic upgrade head`
4. For CI/CD, use Neon branch creation (see research.md)

---

## Next Steps

After completing the quickstart:

1. **Review incubation code**: Compare MCP tools with new @function_tools
2. **Validate feature parity**: Test all 5 skills and 6 tools
3. **Run performance tests**: Verify <5 second processing time
4. **Configure CI/CD**: Set up GitHub Actions with Neon branching
5. **Add monitoring**: Implement logging and observability
6. **Deploy to production**: Follow deployment guide (coming soon)

---

## Development Workflow

### Making Database Changes

1. Update SQLModel models in `src/database/models.py`
2. Generate migration: `alembic revision --autogenerate -m "Description"`
3. Review migration in `alembic/versions/`
4. Apply migration: `alembic upgrade head`
5. Test migration: `alembic downgrade -1` then `alembic upgrade head`

### Adding New Tools

1. Create tool file in `src/agent/tools/`
2. Implement @function_tool with docstring
3. Add tool to agent in `src/agent/customer_success_agent.py`
4. Write tests in `tests/test_tools.py`
5. Update API documentation if needed

### Running in Production

1. Set `ENVIRONMENT=production` in `.env`
2. Use production database URL
3. Disable `echo=True` in database engine
4. Use `uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4`
5. Set up reverse proxy (nginx) for SSL/TLS
6. Configure monitoring and alerting

---

## Resources

- **Feature Spec**: `specs/005-custom-agent-transition/spec.md`
- **Implementation Plan**: `specs/005-custom-agent-transition/plan.md`
- **Research**: `specs/005-custom-agent-transition/research.md`
- **Data Model**: `specs/005-custom-agent-transition/data-model.md`
- **API Contracts**: `specs/005-custom-agent-transition/contracts/api.yaml`
- **Incubation Code**: `mcp-server/` (for reference)

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review research.md for technology decisions
3. Check GitHub issues
4. Contact team lead

---

**Last Updated**: 2024-02-24
**Version**: 1.0.0
