---
id: 1
title: "Production MCP Tool Upgrade and Knowledge Retrieval Skill Creation"
stage: "general"
date: "2026-02-17"
surface: "agent"
model: "claude-sonnet-4-5-20250929"
feature: "none"
branch: "main"
user: "user"
command: "upgrade-mcp-search-tool"
labels: ["mcp", "database", "postgres", "vector-search", "skill"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - "mcp-server/src/tools/crm_tools.py"
  - "mcp-server/src/database/vector_models.py"
  - "mcp-server/src/utils/embeddings.py"
  - "mcp-server/src/database/session.py"
  - "mcp-server/src/database/init_vector_db.py"
  - "mcp-server/src/main.py"
  - ".claude/skills/knowledge-retrieval-skill/SKILL.md"
tests: []
---

# Production MCP Tool Upgrade and Knowledge Retrieval Skill Creation

## Summary
Updated the `search_knowledge_base` MCP tool to meet production requirements with PostgreSQL, pgvector, and robust error handling. Created a Knowledge Retrieval Skill for agent usage.

## Changes Made

### MCP Tool Upgrades
1. Added Pydantic validation for tool arguments (query, max_results)
2. Implemented PostgreSQL and pgvector integration with semantic search
3. Added fastembed for generating vector embeddings
4. Created KnowledgeBaseEntry model with vector column support
5. Added proper error handling with graceful fallback messaging
6. Updated database initialization to include pgvector extension

### Database Improvements
1. Created vector-enhanced database model with `embedding` column of type `VECTOR(384)`
2. Implemented proper PostgreSQL connection handling with pool settings
3. Added migration script to initialize pgvector extension and knowledge_base table
4. Used cosine similarity (`<=>`) for semantic search queries

### Knowledge Retrieval Skill
1. Created comprehensive skill definition with purpose, usage, and guardrails
2. Defined proper execution path for the `search_knowledge_base` tool
3. Included input/output specifications and error handling guidance
4. Added guardrails to prevent fabrication of information

## Outcome
The MCP server now supports production-ready semantic search with PostgreSQL backend, providing better relevance for knowledge base queries while maintaining robust error handling and validation.