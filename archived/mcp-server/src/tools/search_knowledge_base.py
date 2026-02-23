"""Search knowledge base tool implementation."""
import time
from typing import Dict, Any, List
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session
from sqlalchemy import text, bindparam
from pgvector.sqlalchemy import Vector
from src.database.session import engine
from src.utils.metrics import metrics_collector
from src.utils.rate_limiter import check_rate_limit
from src.utils.embeddings import generate_embedding


class SearchKnowledgeBaseRequest(BaseModel):
    """Pydantic model for validating search knowledge base arguments."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query string")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of results to return")


def search_product_docs_impl(query: str, max_results: int = 5, client_id: str = "default_client") -> List[Dict[str, Any]]:
    """
    Production-ready implementation for searching product documentation using vector embeddings in PostgreSQL.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (default: 5, min: 1, max: 20)
        client_id: ID of the requesting client (for metrics/rate limiting)

    Returns:
        List of documentation results with relevance scores
    """
    # Record metrics
    metrics_collector.increment_request()
    metrics_collector.record_tool_usage("search_knowledge_base")
    start_time = time.time()

    # Check rate limit
    if not check_rate_limit(client_id):
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("search_knowledge_base", duration)
        raise Exception("Rate limit exceeded")

    try:
        # Input validation using Pydantic
        validated_input = SearchKnowledgeBaseRequest(query=query, max_results=max_results)
        query = validated_input.query
        max_results = validated_input.max_results

        # Verify we're using PostgreSQL
        if not engine.url.drivername.startswith('postgresql'):
            raise ValueError("This implementation requires PostgreSQL with pgvector extension")

        # Generate embedding for the query
        query_embedding = generate_embedding(query)

        # Use PostgreSQL with pgvector for semantic search
        with Session(engine) as session:
            # Raw SQL query for vector similarity search using pgvector
            # Using cosine distance (<=>) for similarity calculation
            sql_query = text("""
                SELECT
                    id,
                    title,
                    content,
                    category,
                    1 - (embedding <=> :query_embedding) AS similarity
                FROM knowledge_base
                ORDER BY embedding <=> :query_embedding
                LIMIT :limit
            """).bindparams(bindparam("query_embedding", type_=Vector(384)))

            # Pass the embedding as a list directly
            result = session.execute(sql_query, {
                "query_embedding": query_embedding,
                "limit": max_results
            }).fetchall()

            docs_list = []
            for row in result:
                docs_list.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "category": row[3],
                    "similarity_score": float(row[4]),
                    "search_method": "semantic"
                })

        duration = time.time() - start_time
        metrics_collector.record_response_time("search_knowledge_base", duration)
        return docs_list

    except ValidationError as ve:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("search_knowledge_base", duration)
        raise ValueError(f"Invalid input: {ve}")
    except Exception as e:
        metrics_collector.increment_error()
        duration = time.time() - start_time
        metrics_collector.record_response_time("search_knowledge_base", duration)

        # Log the actual error for debugging
        print(f"Search knowledge base failed: {e}")

        # Return graceful error message
        return [{
            "error": "Knowledge base temporarily unavailable. Suggest escalating if the query is urgent.",
            "search_method": "error_fallback"
        }]