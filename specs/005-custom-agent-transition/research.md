# Research: Customer Success Agent Production Migration

**Feature**: 005-custom-agent-transition
**Date**: 2026-02-24
**Phase**: 0 - Research & Technology Decisions

## Overview

This document consolidates research findings and technology decisions for migrating the Customer Success Agent from incubation (Claude Code + MCP + file storage) to production (OpenAI Agents SDK + PostgreSQL + pgvector). All decisions prioritize maintaining 100% feature parity with the working MVP while upgrading infrastructure for production reliability.

---

## 1. FastEmbed Integration for Embeddings

### Decision
Use **FastEmbed (sentence-transformers)** with the `all-MiniLM-L6-v2` model for generating embeddings.

### Rationale
- **Free and local**: No API costs, no external dependencies
- **Fast inference**: ~50ms per document on CPU
- **Proven accuracy**: 384-dimensional embeddings with good semantic similarity
- **Lightweight**: ~90MB model download
- **Production-ready**: Used in production by many companies

### Implementation Pattern
```python
from fastembed import TextEmbedding

# Initialize once at startup
embedding_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Generate embeddings
def generate_embedding(text: str) -> list[float]:
    embeddings = list(embedding_model.embed([text]))
    return embeddings[0].tolist()  # 384 dimensions
```

### Alternatives Considered
- **OpenAI text-embedding-3-small**: Rejected due to API costs (~$0.02/1M tokens) and external dependency
- **Hybrid approach**: Rejected due to complexity of maintaining two embedding pipelines

### References
- FastEmbed documentation: https://github.com/qdrant/fastembed
- Model card: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

---

## 2. pgvector Setup in Neon PostgreSQL

### Decision
Use **pgvector extension** in Neon PostgreSQL for vector similarity search with cosine distance.

### Rationale
- **Native PostgreSQL**: No external vector database needed
- **Neon support**: pgvector fully supported in Neon Serverless
- **Proven performance**: Handles millions of vectors efficiently
- **SQL integration**: Query vectors alongside relational data
- **HNSW indexing**: Fast approximate nearest neighbor search

### Implementation Pattern
```sql
-- Enable extension (in Alembic migration)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table with vector column
CREATE TABLE knowledge_base (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    embedding vector(384),  -- 384 dimensions for all-MiniLM-L6-v2
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create HNSW index for fast similarity search
CREATE INDEX ON knowledge_base USING hnsw (embedding vector_cosine_ops);

-- Query for similar documents
SELECT id, title, content, 1 - (embedding <=> query_embedding) AS similarity
FROM knowledge_base
WHERE 1 - (embedding <=> query_embedding) > 0.7  -- similarity threshold
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

### SQLModel Integration
```python
from sqlalchemy import Column
from pgvector.sqlalchemy import Vector

class KnowledgeBase(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    category: str | None = None
    embedding: list[float] = Field(sa_column=Column(Vector(384)))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Alternatives Considered
- **External vector database (Qdrant, Pinecone)**: Rejected to avoid additional infrastructure complexity
- **Elasticsearch with vector search**: Rejected due to resource overhead

### References
- pgvector documentation: https://github.com/pgvector/pgvector
- Neon pgvector guide: https://neon.tech/docs/extensions/pgvector

---

## 3. Async Database Patterns with SQLModel

### Decision
Use **async SQLModel with asyncpg** driver and connection pooling.

### Rationale
- **Non-blocking I/O**: Handles concurrent requests efficiently
- **Connection pooling**: Reuses connections, prevents exhaustion
- **Type safety**: SQLModel combines Pydantic validation with SQLAlchemy ORM
- **FastAPI integration**: Native async support in FastAPI

### Implementation Pattern
```python
from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession, AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

# Create async engine with connection pooling
engine = create_async_engine(
    database_url,  # postgresql+asyncpg://...
    echo=True,  # Log SQL queries in development
    pool_size=5,  # Number of connections to maintain
    max_overflow=10,  # Additional connections when pool exhausted
    pool_pre_ping=True,  # Verify connection health before use
    pool_recycle=300,  # Recycle connections after 5 minutes
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent DetachedInstanceError
)

# Dependency for FastAPI
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

# CRUD pattern: add -> flush -> commit -> refresh
async def create_customer(session: AsyncSession, email: str, phone: str):
    customer = Customer(email=email, phone=phone)
    session.add(customer)
    await session.flush()  # Get ID from database
    await session.commit()  # Make permanent
    await session.refresh(customer)  # Reload from database
    return customer
```

### Best Practices
- Always use `await` on session operations
- Use `pool_pre_ping=True` to detect stale connections
- Set `expire_on_commit=False` to avoid DetachedInstanceError
- Use `pool_recycle` to handle idle connection timeouts

### Alternatives Considered
- **Sync SQLModel**: Rejected due to blocking I/O limiting concurrency
- **Raw asyncpg**: Rejected due to lack of ORM features and type safety

### References
- SQLModel async documentation: https://sqlmodel.tiangolo.com/advanced/async/
- asyncpg documentation: https://magicstack.github.io/asyncpg/

---

## 4. OpenAI Agents SDK Context Design

### Decision
Use **Pydantic BaseModel** for agent context with conversation history tracking.

### Rationale
- **Type safety**: Pydantic validates context structure
- **Immutability**: Context changes are explicit and traceable
- **SDK integration**: Native support in OpenAI Agents SDK
- **Serialization**: Easy to persist and restore context

### Implementation Pattern
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
    channel: str = "api"  # gmail, whatsapp, web_form, api

    # Conversation history
    conversation_history: list[dict] = []  # [{"role": "user"|"assistant", "content": "...", "timestamp": "..."}]

# Usage in tools
from agents import function_tool, RunContextWrapper

@function_tool
def identify_customer(
    email: str,
    phone: str,
    context: RunContextWrapper[CustomerSuccessContext]
) -> str:
    """Identify or create customer based on email/phone."""
    # Access context
    context.context.customer_email = email
    context.context.customer_phone = phone

    # Database lookup...
    customer_id = "CUST-123"
    context.context.customer_id = customer_id

    return f"Customer identified: {customer_id}"
```

### Alternatives Considered
- **Dictionary-based context**: Rejected due to lack of type safety
- **Database-backed context**: Rejected due to complexity and latency

### References
- OpenAI Agents SDK context documentation: https://github.com/openai/openai-agents-sdk

---

## 5. MCP Tools to @function_tool Migration

### Decision
Convert all 7 MCP server tools to **@function_tool decorators** with identical behavior.

### Rationale
- **Direct integration**: No MCP transport overhead
- **Better performance**: Eliminates network round-trips
- **Type safety**: Pydantic schemas for tool inputs
- **Error handling**: Native Python exception handling
- **Observability**: Direct logging and tracing

### Migration Pattern
```python
# BEFORE (MCP server tool)
@mcp.tool()
def search_knowledge_base(query: str) -> dict:
    """Search knowledge base for relevant articles."""
    # TF-IDF search in files
    results = tfidf_search(query)
    return {"articles": results}

# AFTER (@function_tool)
from agents import function_tool, RunContextWrapper

@function_tool
async def search_knowledge_base(
    query: str,
    context: RunContextWrapper[CustomerSuccessContext]
) -> str:
    """Search knowledge base for relevant articles using semantic search.

    Args:
        query: The search query from customer inquiry
        context: Agent context for tracking retrieved articles

    Returns:
        String describing relevant articles found
    """
    # Generate query embedding
    query_embedding = generate_embedding(query)

    # Vector similarity search in PostgreSQL
    async with get_session() as session:
        results = await session.exec(
            select(KnowledgeBase)
            .order_by(KnowledgeBase.embedding.cosine_distance(query_embedding))
            .limit(5)
        )
        articles = results.all()

    # Track in context
    context.context.knowledge_articles_retrieved = [a.title for a in articles]

    # Return human-readable string for agent
    if not articles:
        return "No relevant articles found in knowledge base."

    return f"Found {len(articles)} relevant articles: " + ", ".join(a.title for a in articles)
```

### Key Differences
- **Async by default**: All tools use async/await
- **Context access**: Tools can read/write agent context
- **String returns**: Tools return human-readable strings, not complex objects
- **Database integration**: Direct database access instead of file operations

### Tool Mapping
| MCP Tool | @function_tool | Changes |
|----------|----------------|---------|
| `search_knowledge_base` | `search_knowledge_base` | TF-IDF → pgvector semantic search |
| `identify_customer` | `identify_customer` | File lookup → PostgreSQL query |
| `analyze_sentiment` | `analyze_sentiment` | Same VADER logic, store in database |
| `create_ticket` | `create_ticket` | File write → PostgreSQL insert |
| `get_customer_history` | `get_customer_history` | File read → PostgreSQL query with joins |
| `escalate_to_human` | `escalate_to_human` | File write → PostgreSQL insert |
| `send_response` | `send_response` | File write → PostgreSQL insert |

### Alternatives Considered
- **Keep MCP with database backend**: Rejected due to transport overhead
- **Hybrid MCP + direct tools**: Rejected due to complexity

### References
- OpenAI Agents SDK function tools: https://github.com/openai/openai-agents-sdk/blob/main/docs/function-tools.md

---

## 6. Knowledge Base Migration Strategy

### Decision
Use **one-time migration script** executed during initial setup.

### Rationale
- **Clean separation**: Migration is explicit and traceable
- **Manual control**: Operator decides when to migrate
- **Idempotent**: Script can be run multiple times safely
- **Future dashboard**: Will add UI for ongoing updates later

### Implementation Pattern
```python
# scripts/migrate_knowledge_base.py
import asyncio
from pathlib import Path
from fastembed import TextEmbedding
from sqlmodel import select
from database.connection import get_engine
from database.models import KnowledgeBase

async def migrate_knowledge_base():
    """Migrate markdown files to PostgreSQL with embeddings."""
    # Initialize embedding model
    embedding_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Load markdown files
    kb_dir = Path("mcp-server/context")
    markdown_files = list(kb_dir.glob("*.md"))

    print(f"Found {len(markdown_files)} markdown files to migrate")

    # Create database session
    engine = get_engine()
    async with AsyncSession(engine) as session:
        for md_file in markdown_files:
            # Read content
            content = md_file.read_text()
            title = md_file.stem.replace("-", " ").title()
            category = "product-docs"  # Extract from file path if needed

            # Check if already migrated
            existing = await session.exec(
                select(KnowledgeBase).where(KnowledgeBase.title == title)
            )
            if existing.first():
                print(f"Skipping {title} (already migrated)")
                continue

            # Generate embedding
            embedding = list(embedding_model.embed([content]))[0].tolist()

            # Insert into database
            article = KnowledgeBase(
                title=title,
                content=content,
                category=category,
                embedding=embedding
            )
            session.add(article)
            print(f"Migrated: {title}")

        await session.commit()

    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate_knowledge_base())
```

### Alternatives Considered
- **Automatic migration on startup**: Rejected due to slow first startup and risk of blocking
- **Alembic data migration**: Rejected due to complexity for one-time operation

### References
- FastEmbed batch processing: https://github.com/qdrant/fastembed#batch-processing

---

## 7. Test Database Strategy with Neon

### Decision
Use **Neon test database** with branch creation in CI/CD.

### Rationale
- **Tests pgvector**: Validates vector similarity search in production environment
- **Realistic testing**: Same database engine as production
- **CI/CD integration**: Neon API creates/deletes branches per PR
- **Isolation**: Each PR gets isolated test environment

### Implementation Pattern

**Local Development:**
```python
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
```

**CI/CD Workflow (GitHub Actions):**
```yaml
name: Test

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Create Neon test branch
        id: neon
        run: |
          BRANCH_NAME="test-pr-${{ github.event.pull_request.number }}"
          BRANCH_ID=$(curl -X POST https://console.neon.tech/api/v2/projects/$PROJECT_ID/branches \
            -H "Authorization: Bearer $NEON_API_KEY" \
            -H "Content-Type: application/json" \
            -d "{\"branch\": {\"name\": \"$BRANCH_NAME\", \"parent_id\": \"$MAIN_BRANCH_ID\"}}" \
            | jq -r '.branch.id')
          echo "branch_id=$BRANCH_ID" >> $GITHUB_OUTPUT

      - name: Run migrations
        run: |
          export DATABASE_URL="postgresql+asyncpg://...@${{ steps.neon.outputs.branch_id }}.neon.tech/neondb"
          alembic upgrade head

      - name: Run tests
        run: |
          export DATABASE_URL="postgresql+asyncpg://...@${{ steps.neon.outputs.branch_id }}.neon.tech/neondb"
          pytest

      - name: Delete test branch
        if: always()
        run: |
          curl -X DELETE https://console.neon.tech/api/v2/projects/$PROJECT_ID/branches/${{ steps.neon.outputs.branch_id }} \
            -H "Authorization: Bearer $NEON_API_KEY"
```

**Pytest Configuration:**
```python
# tests/conftest.py
import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from database.connection import get_engine

@pytest.fixture
async def session():
    """Provide database session for tests."""
    engine = get_engine()
    async with AsyncSession(engine) as session:
        yield session
        # No rollback needed - Neon branch is deleted after tests
```

### Alternatives Considered
- **In-memory SQLite**: Rejected because it doesn't support pgvector
- **Hybrid (SQLite for unit, Neon for integration)**: Accepted as future optimization

### References
- Neon API documentation: https://neon.tech/docs/reference/api-reference
- Neon branching guide: https://neon.tech/docs/guides/branching

---

## 8. Alembic Async Migrations

### Decision
Use **Alembic with async template** for database migrations.

### Rationale
- **Async support**: Works with asyncpg and async SQLModel
- **Version control**: Tracks schema changes in git
- **Rollback capability**: Downgrade migrations for emergency rollback
- **Autogenerate**: Detects model changes automatically

### Implementation Pattern

**Initialize Alembic:**
```bash
cd backend
uv add alembic
alembic init -t async alembic
```

**Configure env.py:**
```python
# alembic/env.py
from sqlmodel import SQLModel
from database.models import *  # Import all models

target_metadata = SQLModel.metadata

# Async migration function
async def run_migrations_online():
    connectable = create_async_engine(config.get_main_option("sqlalchemy.url"))

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()
```

**Create Migration:**
```bash
# Generate migration from model changes
alembic revision --autogenerate -m "Add pgvector extension and knowledge_base table"

# Review generated migration
# Edit alembic/versions/xxx_add_pgvector.py if needed

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

**Initial Migration (with pgvector):**
```python
# alembic/versions/001_initial_schema.py
def upgrade():
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create tables (autogenerated)
    op.create_table('customer', ...)
    op.create_table('ticket', ...)
    op.create_table('message', ...)
    op.create_table('escalation', ...)
    op.create_table('knowledge_base', ...)
    op.create_table('response', ...)

    # Create vector index
    op.execute('''
        CREATE INDEX knowledge_base_embedding_idx
        ON knowledge_base
        USING hnsw (embedding vector_cosine_ops)
    ''')

def downgrade():
    op.drop_table('response')
    op.drop_table('knowledge_base')
    op.drop_table('escalation')
    op.drop_table('message')
    op.drop_table('ticket')
    op.drop_table('customer')
    op.execute('DROP EXTENSION IF EXISTS vector')
```

### Best Practices
- Always import ALL models in env.py for autogenerate
- Review autogenerated migrations before applying
- Test migrations in Neon branch before merging
- Keep downgrade migrations working for rollback
- Use `op.execute()` for PostgreSQL-specific features (pgvector, JSONB)

### Alternatives Considered
- **Manual SQL migrations**: Rejected due to lack of version control and autogenerate
- **SQLModel create_all()**: Rejected for production (no versioning or rollback)

### References
- Alembic async documentation: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
- Alembic autogenerate: https://alembic.sqlalchemy.org/en/latest/autogenerate.html

---

## Summary

All technology decisions have been made and documented with rationale, implementation patterns, and alternatives considered. The migration strategy prioritizes:

1. **100% feature parity** with incubation MVP
2. **Production reliability** with async database, connection pooling, and error handling
3. **Type safety** with Pydantic and SQLModel
4. **Testability** with Neon test database and pytest
5. **Maintainability** with Alembic migrations and clear documentation

**Next Phase**: Create data-model.md, contracts/api.yaml, and quickstart.md based on these research findings.
