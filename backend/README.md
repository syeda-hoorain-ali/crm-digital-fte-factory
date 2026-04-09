# Customer Success Agent - Backend

Production-ready customer support agent built with OpenAI Agents SDK, FastAPI, and PostgreSQL.

**🚀 Live API**: http://35.223.193.60
- Health Check: http://35.223.193.60/health
- API Docs: http://35.223.193.60/docs

## Overview

This backend service provides an intelligent customer success agent that:
- Identifies customers across multiple channels (email, phone, WhatsApp)
- Searches a knowledge base using semantic vector search
- Creates support tickets and tracks conversation history
- Escalates complex issues to human agents with intelligent routing
- Provides observability tracking for performance monitoring
- Rate limiting with Redis (sliding window algorithm)
- Message streaming with Apache Kafka
- Multi-channel support (Gmail, WhatsApp, Web Form)

**Tech Stack:**
- **Framework**: FastAPI (async)
- **Agent SDK**: OpenAI Agents SDK
- **Database**: PostgreSQL with pgvector extension (Neon)
- **ORM**: SQLAlchemy 2.0 (async)
- **Embeddings**: FastEmbed (sentence-transformers/all-MiniLM-L6-v2)
- **Message Queue**: Apache Kafka (aiokafka)
- **Cache/Rate Limiting**: Redis (redis.asyncio)
- **Package Manager**: UV
- **Deployment**: Kubernetes (GKE) with CI/CD via GitHub Actions

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ with pgvector extension (or Neon database)
- Gemini API key
- UV package manager (recommended) or pip

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/syeda-hoorian-ali/crm-digital-fte-factory.git
cd backend
```

### 2. Install dependencies

Using UV (recommended):
```bash
uv sync
```

Using pip:
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and configure the required variables:

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname?sslmode=require
GEMINI_API_KEY=AI...

# Optional (with defaults)
ENVIRONMENT=development
LOG_LEVEL=INFO
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

### 4. Run database migrations

```bash
# Apply migrations
alembic upgrade head
```

### 5. Migrate knowledge base (one-time setup)

```bash
# Migrate markdown files to knowledge base with vector embeddings
uv run scripts/migrate_knowledge_base.py --source-dir /path/to/markdown/files
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for complete documentation.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string with asyncpg driver | `postgresql+asyncpg://user:pass@host/db` |
| `GEMINI_API_KEY` | GEMINI API key for agent operations | `AI...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Application environment (development, staging, production) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | FastEmbed model for embeddings |
| `EMBEDDING_DIMENSION` | `384` | Embedding vector dimension (must match model) |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated CORS origins |
| `AGENT_MODEL` | `gemini-2.5-flash` | LLM model for agent |
| `AGENT_MAX_TOKENS` | `4096` | Maximum tokens for agent responses |
| `AGENT_TEMPERATURE` | `0.7` | Agent temperature (0.0-2.0) |
| `DB_POOL_SIZE` | `10` | Database connection pool size |
| `DB_MAX_OVERFLOW` | `20` | Maximum overflow connections |
| `DB_POOL_TIMEOUT` | `30` | Connection timeout in seconds |
| `KB_SEARCH_LIMIT` | `5` | Number of knowledge base results |
| `KB_MIN_SIMILARITY` | `0.7` | Minimum similarity score (0.0-1.0) |

## Running the Server

### Development

```bash
# Using uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or using UV
uv run uvicorn src.main:app --reload
```

### Production

```bash
# Using uvicorn with multiple workers
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or using gunicorn with uvicorn workers
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check

Check service health and database connectivity.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Process Customer Inquiry

Process a customer inquiry through the agent.

```bash
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I reset my password?",
    "customer_email": "customer@example.com",
    "channel": "api"
  }'
```

**Request Body:**
```json
{
  "message": "Customer inquiry text",
  "customer_email": "customer@example.com",
  "customer_phone": "+1234567890",
  "channel": "api",
  "conversation_id": "optional-uuid-to-continue-conversation"
}
```

**Response:**
```json
{
  "response": "Agent response text",
  "conversation_id": "uuid",
  "sentiment_score": 0.8,
  "escalated": false,
  "escalation_reason": null
}
```

### Get Conversation History

Retrieve conversation history with all messages.

```bash
curl http://localhost:8000/agent/history/{conversation_id}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "status": "active",
  "channel": "api",
  "started_at": "2024-01-01T12:00:00",
  "ended_at": null,
  "sentiment_score": 0.8,
  "escalated_to": null,
  "messages": [
    {
      "id": "uuid",
      "role": "customer",
      "content": "Message text",
      "created_at": "2024-01-01T12:00:00",
      "sentiment_score": 0.8,
      "tokens_used": 150,
      "latency_ms": 1200
    }
  ]
}
```

## Testing

### Run all tests

```bash
# Using pytest
uv run pytest

# With coverage report
uv run pytest --cov=src --cov-report=html

# Run only unit tests
uv run pytest tests/unit/

# Run only integration tests
uv run pytest tests/integration/
```

### Test categories

- **Unit tests** (`tests/unit/`): Fast tests with mocked dependencies
- **Integration tests** (`tests/integration/`): Tests with real database

## Development

### Project Structure

```
backend/
├── src/
│   ├── agent/
│   │   ├── tools/          # Agent tools (6 tools)
│   │   ├── context.py      # Agent context
│   │   ├── customer_success_agent.py
│   │   ├── hooks.py        # Observability hooks
│   │   ├── session.py      # PostgreSQL session
│   │   ├── prompts.py      # Skill prompts
│   │   └── formatters.py   # Channel formatters
│   ├── database/
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── queries/        # CRUD operations
│   │   └── connection.py   # Database connection
│   ├── config.py           # Pydantic settings
│   └── main.py             # FastAPI application
├── alembic/                # Database migrations
├── scripts/                # Utility scripts
├── tests/                  # Test suite
├── .env.example            # Environment template
├── pyproject.toml          # Project dependencies
└── README.md               # This file
```

### Agent Tools

The agent has 6 tools available:

1. **identify_customer**: Cross-channel customer identification
2. **search_knowledge_base**: Semantic search with pgvector
3. **create_ticket**: Support ticket creation
4. **get_customer_history**: Conversation history retrieval
5. **send_response**: Store agent response with observability
6. **escalate_to_human**: Intelligent escalation routing

### Database Schema

Key tables:
- **customers**: Customer records with metadata
- **customer_identifiers**: Cross-channel customer matching
- **conversations**: Conversation lifecycle tracking
- **messages**: Message history with observability fields
- **tickets**: Support ticket tracking
- **knowledge_base**: Vector embeddings for semantic search
- **channel_config**: Multi-channel configuration
- **agent_metrics**: Performance metrics

### Adding New Migrations

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration in alembic/versions/

# Apply migration
alembic upgrade head
```

### Code Style

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Add docstrings to all public functions (Google-style format)
- Run linters before committing:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
ruff check src/ tests/
```

## Observability

### Logging

Structured JSON logging with correlation IDs:
- All database operations are logged
- All tool executions are logged
- Request/response tracking in hooks

### Metrics

Agent performance metrics tracked in `agent_metrics` table:
- Token usage
- Latency (ms)
- Tool call count
- Estimated cost
- Success rate

### Tracing

OpenAI Agents SDK tracing enabled:
- All agent runs wrapped in `trace()` context
- Conversation-level grouping with `group_id`
- View traces in OpenAI dashboard

## Support

For issues and questions, please open an issue on GitHub or contact the development team.
